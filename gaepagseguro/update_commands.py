# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from decimal import Decimal
import logging
from gaebusiness.business import CommandParallel, Command, CommandSequential, CommandExecutionException
from gaebusiness.gaeutil import UrlFetchCommand
from gaegraph.business_base import NodeSearch, CreateArc
from gaepermission import facade
from tekton import router
import xmltodict
from gaepagseguro.admin_commands import FindAccessDataCmd
from gaepagseguro.model import STATUS_SENT_TO_PAGSEGURO, STATUS_ANALYSIS, STATUS_ACCEPTED, STATUS_AVAILABLE, \
    STATUS_DISPUTE, STATUS_RETURNED, STATUS_CANCELLED, PagSegPaymentToLog, PagSegLog, STATUS_CHARGEBACK_DEBT, \
    STATUS_CHARGEBACK, PagSegPayment, PagSegPaymentToItem, PagSegItem
from gaepagseguro.save_commands import UpdatePaymentAndSaveLog, CreatePagSegPaymentToLog, SaveToPayment
from gaepagseguro.search_commands import PaymentByPagseguroCode


class FetchNotificationDetail(FindAccessDataCmd):
    def __init__(self, notification_code):
        super(FetchNotificationDetail, self).__init__()
        self.notification_code = notification_code
        self.code = None
        self.status = None
        self.net_amount = None
        self.xml = None

    def do_business(self, stop_on_error=True):
        super(FetchNotificationDetail, self).do_business(stop_on_error)
        access_data = self.result
        notification_url = router.to_path('https://ws.pagseguro.uol.com.br/v3/transactions/notifications',
                                          self.notification_code,
                                          email=access_data.email,
                                          token=access_data.token)
        fetch_cmd = UrlFetchCommand(notification_url)
        fetch_cmd()
        if fetch_cmd.result and fetch_cmd.result.content:
            content = fetch_cmd.result.content
            content_dct = xmltodict.parse(content, 'ISO-8859-1')
            self.code = content_dct['transaction']['code']
            self.status = XML_STATUS_TO_MODEL_STATUS[content_dct['transaction']['status']]
            self.net_amount = content_dct['transaction']['netAmount']

            try:
                self.result = content_dct['transaction']['reference']
            except KeyError:
                self.xml = content
                self.add_error('no_reference', content)

        else:
            self.add_error('pagseguro', 'Notification not contacted')


class _SimpleSave(Command):
    def __init__(self, node):
        super(_SimpleSave, self).__init__()
        self._to_commit = node
        self.result = node


class UpdatePayment(CommandParallel):
    def __init__(self):
        super(UpdatePayment, self).__init__()
        self.code = None
        self.status = None
        self.net_amount = None

    def handle_previous(self, command):
        self.append(NodeSearch(command.result))
        self.code = command.code
        self.status = command.status
        self.net_amount = command.net_amount

    def do_business(self):
        super(UpdatePayment, self).do_business()
        payment = self.result
        if payment is not None:
            payment.net_amount = payment.net_amount or Decimal(self.net_amount)
            payment.status = self.status
            payment.code = payment.code or self.code
            CreatePagSegPaymentToLog(
                _SimpleSave(payment),
                _SimpleSave(PagSegLog(status=self.status)))()
        else:
            self.add_error('payment', 'Payment not found for %s' % self[0].node_key)


class FetchNotificationAndUpdatePayment(CommandSequential):
    def __init__(self, notification_code):
        super(FetchNotificationAndUpdatePayment, self).__init__(FetchNotificationDetail(notification_code),
                                                                UpdatePayment())
        self.xml = None

    def do_business(self):
        try:
            super(FetchNotificationAndUpdatePayment, self).do_business()
        except CommandExecutionException, e:
            self.xml = self[0].xml
            raise e


class CreatePaymentToItem(CreateArc):
    arc_class = PagSegPaymentToItem


class ProcessExternalPaymentCmd(CommandParallel):
    def __init__(self, xml):
        self.__transaction_dct = xmltodict.parse(xml, 'ISO-8859-1')
        super(ProcessExternalPaymentCmd, self).__init__(
            PaymentByPagseguroCode(self.__transaction_dct['transaction']['code']))

    def do_business(self):
        super(ProcessExternalPaymentCmd, self).do_business()
        dct = self.__transaction_dct
        if self.result:
            self.result.status = XML_STATUS_TO_MODEL_STATUS.get(dct['transaction']['status'])
            cmd = UpdatePaymentAndSaveLog(self.result)
            cmd.execute()
        else:
            self.result = PagSegPayment(code=dct['transaction']['code'],
                                        status=XML_STATUS_TO_MODEL_STATUS.get(dct['transaction']['status']),
                                        total=dct['transaction']['grossAmount'],
                                        net_amount=dct['transaction']['netAmount'])
            payment_key = self.result.put()


            def create_item_cmd(item):
                return _SimpleSave(PagSegItem(description=item['description'],
                                              price=Decimal(item['amount']),
                                              quantity=int(item['quantity'])))

            items = dct['transaction']['items']['item']
            if isinstance(items, dict):
                items = [items]
            items_cmd = [CreatePaymentToItem(payment_key, create_item_cmd(item)) for item in
                         items]
            cmd = CommandParallel(
                CreatePagSegPaymentToLog(payment_key, _SimpleSave(PagSegLog(status=self.result.status))), *items_cmd)

            sender = dct['transaction'].get('sender')
            if sender:
                user = facade.get_user_by_email(sender['email'])()
                if user is None:
                    user = facade.save_user_cmd(sender['email'], sender['name'])()
                cmd.append(SaveToPayment(user,payment_key))
            cmd.execute()


XML_STATUS_TO_MODEL_STATUS = {'1': STATUS_SENT_TO_PAGSEGURO,
                              '2': STATUS_ANALYSIS,
                              '3': STATUS_ACCEPTED,
                              '4': STATUS_AVAILABLE,
                              '5': STATUS_DISPUTE,
                              '6': STATUS_RETURNED,
                              '8': STATUS_CHARGEBACK_DEBT,
                              '9': STATUS_CHARGEBACK,
                              '7': STATUS_CANCELLED}




