# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from xml.etree import ElementTree
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from gaebusiness.business import CommandList, Command
from gaebusiness.gaeutil import UrlFetchCommand, ModelSearchCommand
from gaegraph.model import Node, to_node_key
from gaepagseguro.model import PagSegAccessData, PagSegItem, OriginToPagSegOrder, PagSegOrder, PagSegOrderToItem

import re

_noxmlns_re = re.compile('''xmlns=["'].*["']''')


def _remove_first_xmlns(xmlstr):
    return "".join(_noxmlns_re.split(xmlstr, 1))


def _make_params(email, token, redirect_url, client_name, client_email, order_reference, items, address,
                 currency):
    d = {"email": email,
         "token": token,
         "currency": currency,
         "reference": str(order_reference),
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


class SaveNewOrder(CommandList):
    def __init__(self, owner, items):
        self.__owner = to_node_key(owner)
        self.__save_order = SaveNode(PagSegOrder())
        self.__save_items = SaveNodes(items)
        self.__arcs = None
        self.items = items
        super(SaveNewOrder, self).__init__([self.__save_items, self.__save_order])

    def do_business(self, stop_on_error=True):
        super(SaveNewOrder, self).do_business(stop_on_error)
        order_key = self.__save_order.result.key
        items = self.__save_items.result
        self.__arcs = [PagSegOrderToItem(origin=order_key, destination=i.key) for i in items]
        self.__arcs.append(OriginToPagSegOrder(origin=self.__owner, destination=order_key))

    def commit(self):
        return super(SaveNewOrder, self).commit() + self.__arcs


class GeneratePayment(CommandList):
    def __init__(self, redirect_url, client_name, client_email, order_owner, items, address,
                 currency):
        data_access = FindAccessDataCmd().execute().result
        self.__save_new_order=SaveNewOrder(order_owner,items)
        params = _make_params(data_access.email, data_access.token, redirect_url, client_name, client_email,
                              order_owner, items, address,
                              currency)
        params = {k: v.encode('iso-8859-1') for k, v in params.iteritems()}
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=ISO-8859-1'}
        self._fetch_command = UrlFetchCommand(_PAYMENT_URL, params, urlfetch.POST, headers)
        super(GeneratePayment, self).__init__([self._fetch_command])

    def set_up(self):
        super(GeneratePayment, self).set_up()
        self.__save_new_order.set_up()

    def do_business(self, stop_on_error=False):
        super(GeneratePayment, self).do_business(stop_on_error)
        self.__save_new_order.do_business(stop_on_error)
        ndb.put_multi(self.__save_new_order.commit())
        self.result=self.__save_new_order.result
        fetch_result = self._fetch_command.result

        if fetch_result:
            content = _remove_first_xmlns(fetch_result.content)
            root = ElementTree.XML(content)
            if root.tag != "errors":
                self.result.code = root.findtext("code")
                # handler error here on else

    def commit(self):
        if self.result.code:
            return self.result


class RetrievePaymentDetail(CommandList):
    def __init__(self, email, token, transaction_code, url_base):
        params = {'email': email, 'token': token}
        url = "/".join([url_base, transaction_code])
        self._fetch_command = UrlFetchCommand(url, params)
        super(RetrievePaymentDetail, self).__init__([self._fetch_command])

    def do_business(self, stop_on_error=False):
        super(RetrievePaymentDetail, self).do_business(stop_on_error)
        result = self._fetch_command.result
        if result:
            content = _remove_first_xmlns(result.content)
            root = ElementTree.XML(content)
            if root.tag != "errors":
                self.result = root.findtext("status")
                self.order_reference = root.findtext("reference")
                self.xml = result
                # handler error here on else
