# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from decimal import Decimal

from gaebusiness.business import CommandSequential
from gaegraph.business_base import SingleDestinationSearch, DestinationsSearch
from gaegraph.model import Node
from google.appengine.ext import ndb
from mock import Mock
from mommygae import mommy

from base import GAETestCase
from gaepagseguro import pagseguro_facade
from gaepagseguro.admin_commands import CreateOrUpdateAccessData
from gaepagseguro.model import PagSegItem, PagSegPayment, ToPagSegPayment, PagSegPaymentToLog, PagSegPaymentToItem, \
    STATUS_CREATED, STATUS_SENT_TO_PAGSEGURO
from gaepagseguro.save_commands import SaveItemCmd, SavePagseguroDataCmd, SavePaymentArcsCmd, SavePaymentToItemsArcs, \
    SavePaymentToLog, UpdatePaymentAndSaveLog
from gaepagseguro.search_commands import SearchLogs, SearchItems


class SaveTests(GAETestCase):
    def test_save_items(self):
        command_with_item_forms = Mock()
        command_with_item_forms.items = [PagSegItem(description='Python Birds', price=Decimal('18.99'), quantity=3),
                                         PagSegItem(description='Objetos Pythônicos', price=Decimal('24.99'),
                                                    quantity=2,
                                                    reference=ndb.Key(PagSegItem, 10))]
        save_items_cmd = SaveItemCmd()
        CommandSequential(command_with_item_forms, save_items_cmd).execute()
        items = PagSegItem.query().fetch()
        self.assertEqual(2, len(items))
        self.assertEqual(items, save_items_cmd.result)

    def test_save_pagseguro_data(self):
        access_data = CreateOrUpdateAccessData('renzo@gmail.com', 'abc1234')()
        command_with_item_forms = Mock()
        command_with_item_forms.items = [PagSegItem(description='Python Birds', price=Decimal('18.99'), quantity=3),
                                         PagSegItem(description='Objetos Pythônicos', price=Decimal('24.99'),
                                                    quantity=2,
                                                    reference=ndb.Key(PagSegItem, 10))]
        address_form_mock = Mock()
        client_form_mock = Mock()
        command_with_item_forms.address_form = address_form_mock
        command_with_item_forms.client_form = client_form_mock
        command_with_item_forms.access_data = access_data

        save_pagseguro_data_cmd = SavePagseguroDataCmd()
        CommandSequential(command_with_item_forms, save_pagseguro_data_cmd).execute()

        items = PagSegItem.query().fetch()
        self.assertEqual(2, len(items))
        self.assertEqual(set(i.key for i in items), set(i.key for i in save_pagseguro_data_cmd.items))
        payment = PagSegPayment.query().get()
        self.assertIsNotNone(payment)
        self.assertEqual(payment, save_pagseguro_data_cmd.result)
        self.assertEqual(Decimal('106.95'), save_pagseguro_data_cmd.result.total,
                         'Total should be the some of the total of items')
        self.assertEqual('renzo@gmail.com', save_pagseguro_data_cmd.access_data.email)
        self.assertEqual('abc1234', save_pagseguro_data_cmd.access_data.token)

        # Data used for sequential commands
        self.assertEqual(save_pagseguro_data_cmd.address_form, address_form_mock)
        self.assertEqual(save_pagseguro_data_cmd.client_form, client_form_mock)


    def test_save_item_arcs_command(self):
        command_with_item_forms = Mock()
        access_data = CreateOrUpdateAccessData('renzo@gmail.com', 'abc1234')()

        items = [PagSegItem(description='Python Birds', price=Decimal('18.99'), quantity=3),
                 PagSegItem(description='Objetos Pythônicos', price=Decimal('24.99'), quantity=2,
                            reference=ndb.Key(PagSegItem, 10))]
        command_with_item_forms.items = items

        address_form_mock = Mock()
        client_form_mock = Mock()

        command_with_item_forms.address_form = address_form_mock
        command_with_item_forms.client_form = client_form_mock
        command_with_item_forms.access_data = access_data

        ndb.put_multi(items)
        payment = mommy.save_one(PagSegPayment)
        command_with_item_forms.result = payment

        save_payment_to_items_arcs_cmd = SavePaymentToItemsArcs()
        CommandSequential(command_with_item_forms, save_payment_to_items_arcs_cmd).execute()

        self.assertListEqual(items, SearchItems(payment)())
        self.assertListEqual(items, save_payment_to_items_arcs_cmd.items)

        # Data used for sequential commands
        self.assertEqual('renzo@gmail.com', save_payment_to_items_arcs_cmd.access_data.email)
        self.assertEqual('abc1234', save_payment_to_items_arcs_cmd.access_data.token)
        self.assertEqual(save_payment_to_items_arcs_cmd.address_form, address_form_mock)
        self.assertEqual(save_payment_to_items_arcs_cmd.client_form, client_form_mock)

    def test_save_payment_to_log_command(self):
        command_with_item_forms = Mock()
        payment = mommy.save_one(PagSegPayment)
        command_with_item_forms.result = payment

        save_payment_to_log_cmd = SavePaymentToLog()
        CommandSequential(command_with_item_forms, save_payment_to_log_cmd).execute()

        logs = SearchLogs(payment)()
        self.assertEqual(1, len(logs))
        self.assertEqual(STATUS_CREATED, logs[0].status)

    def test_update_payment_and_save_log_command(self):
        command_with_item_forms = Mock()
        payment = mommy.save_one(PagSegPayment, status=STATUS_CREATED)
        command_with_item_forms.result = payment
        payment.status = STATUS_SENT_TO_PAGSEGURO

        save_payment_to_log_cmd = UpdatePaymentAndSaveLog()
        CommandSequential(command_with_item_forms, save_payment_to_log_cmd).execute()

        search = SearchLogs(payment)
        logs = search()
        self.assertEqual(1, len(logs))
        self.assertEqual(STATUS_SENT_TO_PAGSEGURO, logs[0].status)
        self.assertEqual(STATUS_SENT_TO_PAGSEGURO, payment.key.get().status)
        self.assertEqual(save_payment_to_log_cmd.result, payment)


    def test_save_payment_arcs_command_mocked(self):
        command_with_item_forms = Mock()
        items = [PagSegItem(description='Python Birds', price=Decimal('18.99'), quantity=3),
                 PagSegItem(description='Objetos Pythônicos', price=Decimal('24.99'), quantity=2,
                            reference=ndb.Key(PagSegItem, 10))]
        command_with_item_forms.items = items

        ndb.put_multi(items)
        payment = mommy.save_one(PagSegPayment)
        command_with_item_forms.result = payment

        payment_owner = mommy.save_one(Node)
        save_payment_arcs_cmd = SavePaymentArcsCmd(payment_owner)
        CommandSequential(command_with_item_forms, save_payment_arcs_cmd).execute()

        self.assertEqual(payment, pagseguro_facade.search_payments(payment_owner)()[0])

        logs = SearchLogs(payment)()
        self.assertEqual(1, len(logs))
        self.assertEqual(STATUS_CREATED, logs[0].status)

        self.assertListEqual(items, SearchItems(payment)())


