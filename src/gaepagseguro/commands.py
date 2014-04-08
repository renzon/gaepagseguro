# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from xml.etree import ElementTree
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from gaebusiness.business import CommandList, Command
from gaebusiness.gaeutil import UrlFetchCommand, ModelSearchCommand
from gaegraph.business_base import NodeSearch
from gaegraph.model import Node, to_node_key
from gaepagseguro.model import PagSegAccessData, PagSegItem, OriginToPagSegPayment, PagSegPayment, PagSegPaymentToItem, \
    STATUS_SENT_TO_PAGSEGURO, PagSegLog, PagSegPaymentToLog, STATUS_CREATED, STATUS_ANALYSIS, STATUS_ACCEPTED, \
    STATUS_AVAILABLE, STATUS_DISPUTE, STATUS_CANCELLED, STATUS_RETURNED

import re


def _make_params(email, token, redirect_url, client_name, client_email, payment_reference, items, address,
                 currency):
    d = {"email": email,
         "token": token,
         "currency": currency,
         "reference": str(payment_reference),
         "senderName": client_name,
         "senderEmail": client_email,
         "shippingType": "3",
         "redirectURL": redirect_url
    }

    for index, item in enumerate(items):
        # starting with index 1
        index += 1
        d["itemId%s" % index] = unicode(item.reference.id())
        d["itemDescription%s" % index] = item.description
        d["itemAmount%s" % index] = item.price
        d["itemQuantity%s" % index] = unicode(item.quantity)

    if address:
        d.update({
            "shippingAddressStreet": address.street,
            "shippingAddressNumber": unicode(address.number),
            "shippingAddressComplement": address.complement or "Sem Complemento",
            "shippingAddressDistrict": address.quarter,
            "shippingAddressPostalCode": address.postalcode,
            "shippingAddressCity": address.town,
            "shippingAddressState": address.state,
            "shippingAddressCountry": "BRA"
        })
    return d


_PAYMENT_URL = "https://ws.pagseguro.uol.com.br/v2/checkout"


class FindAccessDataCmd(ModelSearchCommand):
    def __init__(self):
        super(FindAccessDataCmd, self).__init__(PagSegAccessData.query(), 1)

    def do_business(self, stop_on_error=True):
        super(FindAccessDataCmd, self).do_business(stop_on_error)
        self.result = self.result[0] if self.result else None


class CreateOrUpdateAccessData(FindAccessDataCmd):
    def __init__(self, email, token):
        super(CreateOrUpdateAccessData, self).__init__()
        self.token = token
        self.email = email

    def do_business(self, stop_on_error=True):
        super(CreateOrUpdateAccessData, self).do_business(stop_on_error)
        if self.result:
            self.result.email = self.email
            self.result.token = self.token
        else:
            self.result = PagSegAccessData(email=self.email, token=self.token)

    def commit(self):
        return self.result


class SaveNodes(Command):
    def __init__(self, node_or_nodes):
        super(SaveNodes, self).__init__()
        self.result = [node_or_nodes] if isinstance(node_or_nodes, Node) else node_or_nodes
        self.__futures = None


    def set_up(self):
        self.__futures = ndb.put_multi_async(self.result)

    def do_business(self, stop_on_error=True):
        [f.get_result() for f in self.__futures]


class SaveNode(Command):
    def __init__(self, node):
        super(SaveNode, self).__init__()
        self.result = node
        self.__future = None

    def set_up(self):
        self.__future = self.result.put_async()

    def do_business(self, stop_on_error=True):
        self.__future.get_result()


class SaveNewPayment(CommandList):
    def __init__(self, owner, items):
        self.__owner = to_node_key(owner)
        payment = PagSegPayment(status=STATUS_CREATED)
        payment.total = sum(i.total() for i in items)
        self.__save_payment = SaveNode(payment)
        self.__save_log = SaveNode(PagSegLog(status=payment.status))
        self.__save_items = SaveNodes(items)
        self.__arcs = None
        self.items = items
        super(SaveNewPayment, self).__init__([self.__save_log, self.__save_items, self.__save_payment])

    def do_business(self, stop_on_error=True):
        super(SaveNewPayment, self).do_business(stop_on_error)
        payment_key = self.__save_payment.result.key
        log_key = self.__save_log.result.key
        items = self.__save_items.result
        self.__arcs = [PagSegPaymentToItem(origin=payment_key, destination=i.key) for i in items]
        self.__arcs.append(OriginToPagSegPayment(origin=self.__owner, destination=payment_key))
        self.__arcs.append(PagSegPaymentToLog(origin=payment_key, destination=log_key))

    def commit(self):
        return super(SaveNewPayment, self).commit() + self.__arcs


class GeneratePayment(SaveNewPayment):
    def __init__(self, redirect_url, client_name, client_email, payment_owner, items, address,
                 currency, fetch_cmd=None):
        super(GeneratePayment, self).__init__(payment_owner, items)
        self.currency = currency
        self.address = address
        self.client_email = client_email
        self.client_name = client_name
        self.redirect_url = redirect_url
        # Fetch is here just for testing purpose, allowing dependency injection on tests
        self.fetch_cmd = fetch_cmd
        self.__to_commit = None

    def set_up(self):
        if self.client_email:
            if len(self.client_email) > 60:
                self.add_error('client_email', 'Email deve ter menos de 60 caracteres')
            match = re.match(r"[^@]+@[^@\.]+(\.[^@\.]+)+", self.client_email)
            if not match or match.group(0) != self.client_email:
                self.add_error('client_email', 'Email inválido')
        else:
            self.add_error('client_email', 'Email obrigatório')
        if not self.errors:
            super(GeneratePayment, self).set_up()


    def do_business(self, stop_on_error=False):
        if not self.errors:
            super(GeneratePayment, self).do_business(stop_on_error)
            data_access = FindAccessDataCmd().execute().result
            params = _make_params(data_access.email, data_access.token,
                                  self.redirect_url, self.client_name,
                                  self.client_email, self.result.key.id(),
                                  self.items, self.address,
                                  self.currency)
            params = {k: unicode(v).encode('iso-8859-1') for k, v in params.iteritems()}
            headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=ISO-8859-1'}
            fetch_cmd = self.fetch_cmd or UrlFetchCommand(_PAYMENT_URL, params, urlfetch.POST, headers)
            fetch_result = fetch_cmd.execute().result

            if fetch_result:
                content = fetch_result.content
                root = ElementTree.XML(content)
                if root.tag != "errors":
                    self.result.code = root.findtext("code").decode('ISO-8859-1')
                    self.result.status = STATUS_SENT_TO_PAGSEGURO
                    log_key = PagSegLog(status=STATUS_SENT_TO_PAGSEGURO).put()
                    arc = PagSegPaymentToLog(origin=self.result.key, destination=log_key)
                    self.__to_commit = [self.result, arc]
                    # handler error here on else


    def commit(self):
        if not self.errors:
            list_to_commit = super(GeneratePayment, self).commit()
            if self.__to_commit:
                list_to_commit.extend(self.__to_commit)
            return list_to_commit


class AllPaymentsSearch(ModelSearchCommand):
    def __init__(self, page_size=20, start_cursor=None, offset=0, use_cache=True, cache_begin=True):
        query = PagSegPayment.query().order(-PagSegPayment.creation)
        super(AllPaymentsSearch, self).__init__(query, page_size, start_cursor, offset, use_cache, cache_begin)


class PaymentsByStatusSearch(ModelSearchCommand):
    def __init__(self, payment_status, page_size=20, start_cursor=None, offset=0, use_cache=True, cache_begin=True):
        query = PagSegPayment.query(PagSegPayment.status == payment_status).order(-PagSegPayment.creation)
        super(PaymentsByStatusSearch, self).__init__(query, page_size, start_cursor, offset, use_cache, cache_begin)


XML_STATUS_TO_MODEL_STATUS = {'1': STATUS_SENT_TO_PAGSEGURO,
                              '2': STATUS_ANALYSIS,
                              '3': STATUS_ACCEPTED,
                              '4': STATUS_AVAILABLE,
                              '5': STATUS_DISPUTE,
                              '6': STATUS_RETURNED,
                              '7': STATUS_CANCELLED}


class UpdatePaymentStatus(Command):
    def __init__(self, transaction_code, url_base):
        self._fetch_command = None
        self.url = "/".join([url_base, transaction_code])
        super(UpdatePaymentStatus, self).__init__()

    def set_up(self):
        access_data = FindAccessDataCmd().execute().result
        params = {'email': access_data.email, 'token': access_data.token}
        self.__to_commit = None
        # attribution to allow dependency injection of fetch_command
        if self._fetch_command is None:
            self._fetch_command = UrlFetchCommand(self.url, params)
        else:
            self._fetch_command = self._fetch_command(self.url, params)
        self._fetch_command.set_up()

    def do_business(self, stop_on_error=False):
        self._fetch_command.do_business()
        pagseguro_fetch_result = self._fetch_command.result
        if pagseguro_fetch_result:
            content = pagseguro_fetch_result.content
            self.xml = content
            root = ElementTree.XML(content)
            if root.tag != "errors":
                status = root.findtext("status").decode('ISO-8859-1')
                payment_id = root.findtext("reference").decode('ISO-8859-1')
                payment = NodeSearch(payment_id).execute().result
                self.result = payment
                internal_status = XML_STATUS_TO_MODEL_STATUS[status]
                if payment.status != internal_status:
                    log_key = PagSegLog(status=internal_status).put()
                    payment.status = internal_status
                    self.__to_commit = [payment,
                                        PagSegPaymentToLog(origin=payment.key, destination=log_key)]

                    # handler error here on else

    def commit(self):
        return self.__to_commit

