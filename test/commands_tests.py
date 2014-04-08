# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from decimal import Decimal
import unittest
from google.appengine.ext import ndb
from gaegraph.business_base import DestinationsSearch
from gaegraph.model import Node
from gaepagseguro import facade, commands
from gaepagseguro.commands import _make_params, FindAccessDataCmd, SaveNewPayment
from gaepagseguro.model import PagSegAccessData, PagSegPayment, STATUS_SENT_TO_PAGSEGURO, STATUS_CREATED, PagSegLog, \
    PagSegPaymentToLog, STATUS_ANALYSIS, STATUS_ACCEPTED, STATUS_RETURNED, STATUS_DISPUTE, STATUS_AVAILABLE, \
    STATUS_CANCELLED
from mock import Mock
from util import GAETestCase

_SUCCESS_PAGSEGURO_CODE = '8CF4BE7DCECEF0F004A6DFA0A8243412'

_SUCCESS_PAGSEGURO_XML = '''<?xml version="1.0" encoding="ISO-8859-1"?>
<checkout>
    <code>%s</code>
    <date>2010-12-02T10:11:28.000-02:00</date>
</checkout>  ''' % _SUCCESS_PAGSEGURO_CODE


def _build_success_params(id1, id2):
    return {"email": 'foo@bar.com',
            "token": '4567890oiuytfgh',
            "currency": "BRL",
            "reference": '1234',
            "senderName": 'Jhon Doe',
            "senderEmail": 'jhon@bar.com',
            "shippingType": "3",
            "redirectURL": 'https://mystore.com/pagseguro',
            "itemId1": '%s' % id1,
            "itemDescription1": 'Python Course',
            "itemAmount1": '120.00',
            "itemQuantity1": '1',
            "itemId2": '%s' % id2,
            "itemDescription2": 'Another Python Course',
            "itemAmount2": '240.00',
            "itemQuantity2": '2',
            "shippingAddressStreet": 'Rua 1',
            "shippingAddressNumber": '2',
            "shippingAddressComplement": 'apto 4',
            "shippingAddressDistrict": 'meu bairro',
            "shippingAddressPostalCode": '12345678',
            "shippingAddressCity": 'São Paulo',
            "shippingAddressState": 'SP',
            "shippingAddressCountry": "BRA"
    }


_PAGSEGURO_DETAIL_XML = '''<?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>
  <transaction>
      <date>2011-02-05T15:46:12.000-02:00</date>
      <lastEventDate>2011-02-15T17:39:14.000-03:00</lastEventDate>
      <code>9E884542-81B3-4419-9A75-BCC6FB495EF1</code>
      <reference>%s</reference>
      <type>1</type>
      <status>%s</status>
      <paymentMethod>
          <type>1</type>
          <code>101</code>
      </paymentMethod>
      <grossAmount>49900.00</grossAmount>
      <discountAmount>0.00</discountAmount>
      <feeAmount>0.00</feeAmount>
      <netAmount>49900.50</netAmount>
      <extraAmount>0.00</extraAmount>
      <installmentCount>1</installmentCount>
      <itemCount>2</itemCount>
      <items>
          <item>
              <id>0001</id>
              <description>Notebook Prata</description>
              <quantity>1</quantity>
              <amount>24300.00</amount>
          </item>
          <item>
              <id>0002</id>
              <description>Notebook Rosa</description>
              <quantity>1</quantity>
              <amount>25600.00</amount>
          </item>
      </items>
      <sender>
          <name>Jose Comprador</name>
          <email>comprador@uol.com.br</email>
          <phone>
              <areaCode>11</areaCode>
              <number>56273440</number>
          </phone>
      </sender>
      <shipping>
          <address>
              <street>Av. Brig. Faria Lima</street>
              <number>1384</number>
              <complement>5o andar</complement>
              <district>Jardim Paulistano</district>
              <postalCode>01452002</postalCode>
              <city>Sao Paulo</city>
              <state>SP</state>
              <country>BRA</country>
          </address>
          <type>1</type>
          <cost>21.50</cost>
      </shipping>
  </transaction>  '''


def _generate_xml_detail(payment_reference, status):
    xml = _PAGSEGURO_DETAIL_XML % (payment_reference, status)
    return xml


class PagSeguroAccessDataTests(GAETestCase):
    def test_create_or_update_access_data(self):
        data = FindAccessDataCmd().execute().result
        self.assertIsNone(data)
        facade.create_or_update_access_data('foo@gmail.com', 'abc').execute()
        data = FindAccessDataCmd().execute().result
        self.assertEqual('foo@gmail.com', data.email)
        self.assertEqual('abc', data.token)
        facade.create_or_update_access_data('other@gmail.com', '123').execute()
        data2 = FindAccessDataCmd().execute().result
        self.assertEqual(data.key, data2.key)
        self.assertEqual('other@gmail.com', data2.email)
        self.assertEqual('123', data2.token)

        # Another change to assure data is not cached
        facade.create_or_update_access_data('bar@gmail.com', 'xpto').execute()
        data3 = FindAccessDataCmd().execute().result
        self.assertEqual(data.key, data3.key)
        self.assertEqual('bar@gmail.com', data3.email)
        self.assertEqual('xpto', data3.token)

    def test_find_access_data_cmd(self):
        cmd = facade.search_access_data().execute()
        self.assertIsNone(cmd.result)
        PagSegAccessData(email='foo@gmail.com', token='abc').put()
        data = facade.search_access_data().execute().result

        self.assertEqual('foo@gmail.com', data.email)
        self.assertEqual('abc', data.token)


class ItemReferenceMock(Node):
    pass


class PaymentOwner(Node):
    pass


class GeneratePaymentTests(GAETestCase):
    def test_save_new_payment(self):
        owner = PaymentOwner()
        reference0 = ItemReferenceMock()
        reference1 = ItemReferenceMock()
        ndb.put_multi([reference0, reference1, owner])
        items = [facade.create_item(reference0, 'Python Course', '120.00', 1),
                 facade.create_item(reference1, 'Another Python Course', '240.00', 2)]
        cmd = SaveNewPayment(owner, items).execute()

        items_keys = [i.key for i in items]
        payments = facade.search_payments(owner).execute().result
        self.assertEqual(1, len(payments))
        searched_items = facade.search_items(payments[0]).execute().result
        self.assertEqual(2, len(searched_items))
        searched_keys = [i.key for i in searched_items]
        self.assertListEqual(items_keys, searched_keys)
        logs = facade.search_logs(payments[0]).execute().result
        self.assertListEqual([STATUS_CREATED], [log.status for log in logs])


    def test_make_params(self):
        #creating dataaccess
        email = 'foo@bar.com'
        token = '4567890oiuytfgh'
        reference0 = ItemReferenceMock()
        reference1 = ItemReferenceMock()
        owner = PaymentOwner()
        ndb.put_multi([reference0, reference1, owner])
        items = [facade.create_item(reference0, 'Python Course', '120.00', 1),
                 facade.create_item(reference1, 'Another Python Course', '240.00', 2)]

        address = facade.address('Rua 1', 2, 'meu bairro', '12345678', 'São Paulo', 'SP', 'apto 4')

        client_name = 'Jhon Doe'
        client_email = 'jhon@bar.com'
        redirect_url = 'https://mystore.com/pagseguro'
        payment_reference = '1234'
        dct = _make_params(email, token, redirect_url, client_name, client_email, payment_reference,
                           items, address, 'BRL')
        self.maxDiff = None
        self.assertDictEqual(_build_success_params(reference0.key.id(), reference1.key.id()), dct)


class IntegrationTests(GAETestCase):
    def test_payment_generation(self):
        # Setup data
        email = 'foo@bar.com'
        token = '4567890oiuytfgh'
        facade.create_or_update_access_data(email, token).execute()
        items = [facade.create_item(1, 'Python Course', '121.67', 1),
                 facade.create_item(2, 'Another Python Course', '240.00', 2)]
        address = facade.address('Rua 1', 2, 'meu bairro', '12345678', 'São Paulo', 'SP', 'apto 4')
        client_name = 'Jhon Doe'
        client_email = 'jhon@bar.com'
        redirect_url = 'https://store.com/pagseguro'
        payment_reference = '1234'
        # mocking pagseguro connection
        fetch_mock = Mock()
        fetch_mock.execute = Mock(return_value=fetch_mock)
        fetch_mock.result.content = _SUCCESS_PAGSEGURO_XML
        fetch_mock.result.status_code = 200
        fetch_mock.errors = {}
        fetch_mock.commit = Mock(return_value=[])

        generate_payment = facade.payment(redirect_url, client_name, client_email, payment_reference,
                                          items, address, fetch_cmd=fetch_mock)

        # Executing command
        payment = generate_payment.execute().result

        #asserting code extraction
        self.assertEqual(Decimal('601.67'), payment.total)
        self.assertEqual(STATUS_SENT_TO_PAGSEGURO, payment.status)
        self.assertEqual(_SUCCESS_PAGSEGURO_CODE, payment.code)
        # Asserting items saved
        payment_key = PagSegPayment.query_by_code(_SUCCESS_PAGSEGURO_CODE).get(keys_only=True)
        self.assertEqual(payment.key, payment_key)
        self.assertEqual(2, len(facade.search_items(payment_key).execute().result))

        #Asserting logs saved
        logs = facade.search_logs(payment_key).execute().result
        self.assertListEqual([STATUS_CREATED, STATUS_SENT_TO_PAGSEGURO], [log.status for log in logs])

    def test_all_payment_search(self):
        self.maxDiff = None
        created_payments = [PagSegPayment(status=STATUS_CREATED) for i in xrange(3)]
        ndb.put_multi(created_payments)
        #reversing because search is desc
        created_payments.reverse()

        sent_payments = [PagSegPayment(status=STATUS_SENT_TO_PAGSEGURO) for i in xrange(3)]
        ndb.put_multi(sent_payments)
        sent_payments.reverse()
        # Testing search for all
        cmd = facade.search_all_payments(page_size=3).execute()
        self.assertListEqual(sent_payments, cmd.result)
        cmd2 = facade.search_all_payments(page_size=3, start_cursor=cmd.cursor).execute()
        self.assertListEqual(created_payments, cmd2.result)
        cmd3 = facade.search_all_payments(page_size=3, start_cursor=cmd2.cursor).execute()
        self.assertListEqual([], cmd3.result)

        #Test search based on status
        cmd = facade.search_all_payments(STATUS_SENT_TO_PAGSEGURO, page_size=4).execute()
        self.assertListEqual(sent_payments, cmd.result)
        cmd = facade.search_all_payments(STATUS_CREATED, page_size=4).execute()
        self.assertListEqual(created_payments, cmd.result)


class HistoryTests(GAETestCase):
    def _assert_history_change(self, acess_data, payment_key, pagseguro_xml_status, expected_status_history):
        # mocking pagseguro connection
        fetch_mock = Mock()
        commands.UrlFecthCommand = fetch_mock
        payment_detail = facade.payment_detail(_SUCCESS_PAGSEGURO_CODE)
        fetch_mock.result.content = _generate_xml_detail(payment_key.id(), pagseguro_xml_status)
        fetch_mock.result.status_code = 200
        fetch_mock.errors = {}
        fetch_mock.commit = Mock(return_value=[])
        fetch_class_mock = Mock(return_value=fetch_mock)
        payment_detail._fetch_command = fetch_class_mock
        # Executing command
        updated_payment = payment_detail.execute().result
        #asserting code extraction
        saved_logs = DestinationsSearch(PagSegPaymentToLog, payment_key).execute().result
        saved_statuses = [log.status for log in saved_logs]
        self.assertListEqual(expected_status_history, saved_statuses)
        self.assertEqual(expected_status_history[-1], updated_payment.status)
        self.assertIsNotNone(payment_detail.xml)
        fetch_class_mock.assert_called_once_with(
            'https://ws.pagseguro.uol.com.br/v2/transactions/' + _SUCCESS_PAGSEGURO_CODE,
            {'email': acess_data.email, 'token': acess_data.token})

    def test_detail(self):
        # Setup data

        acess_data = PagSegAccessData(email='renzo@python.pro.br', token='abc123')
        acess_data.put()

        payment_key = PagSegPayment(code='FOO', status=STATUS_SENT_TO_PAGSEGURO).put()

        # Mocking logs that are generated when payment is sent
        logs_keys = [PagSegLog(status=STATUS_CREATED).put(), PagSegLog(status=STATUS_SENT_TO_PAGSEGURO).put()]
        for log_key in logs_keys:
            PagSegPaymentToLog(origin=payment_key, destination=log_key).put()
        expected_statuses = [STATUS_CREATED, STATUS_SENT_TO_PAGSEGURO]
        self._assert_history_change(acess_data, payment_key, '1', expected_statuses)
        expected_statuses.append(STATUS_ANALYSIS)
        self._assert_history_change(acess_data, payment_key, '2', expected_statuses)
        expected_statuses.append(STATUS_ACCEPTED)
        self._assert_history_change(acess_data, payment_key, '3', expected_statuses)
        expected_statuses.append(STATUS_AVAILABLE)
        self._assert_history_change(acess_data, payment_key, '4', expected_statuses)
        expected_statuses.append(STATUS_DISPUTE)
        self._assert_history_change(acess_data, payment_key, '5', expected_statuses)
        expected_statuses.append(STATUS_RETURNED)
        self._assert_history_change(acess_data, payment_key, '6', expected_statuses)
        expected_statuses.append(STATUS_CANCELLED)
        self._assert_history_change(acess_data, payment_key, '7', expected_statuses)

    def _assert_notification_change(self, acess_data, payment_key, pagseguro_xml_status, expected_status_history):
        # mocking pagseguro connection
        fetch_mock = Mock()
        commands.UrlFecthCommand = fetch_mock
        # xml is identical to payment_detail
        payment_notification = facade.payment_notification(_SUCCESS_PAGSEGURO_CODE)
        fetch_mock.result.content = _generate_xml_detail(payment_key.id(), pagseguro_xml_status)
        fetch_mock.result.status_code = 200
        fetch_mock.errors = {}
        fetch_mock.commit = Mock(return_value=[])
        fetch_class_mock = Mock(return_value=fetch_mock)
        payment_notification._fetch_command = fetch_class_mock
        # Executing command
        updated_payment = payment_notification.execute().result
        #asserting code extraction
        saved_logs = DestinationsSearch(PagSegPaymentToLog, payment_key).execute().result
        saved_statuses = [log.status for log in saved_logs]
        self.assertListEqual(expected_status_history, saved_statuses)
        self.assertEqual(expected_status_history[-1], updated_payment.status)
        self.assertIsNotNone(payment_notification.xml)
        fetch_class_mock.assert_called_once_with(
            'https://ws.pagseguro.uol.com.br/v2/transactions/notifications/' + _SUCCESS_PAGSEGURO_CODE,
            {'email': acess_data.email, 'token': acess_data.token})

    def test_notification(self):
        # Setup data

        acess_data = PagSegAccessData(email='renzo@python.pro.br', token='abc123')
        acess_data.put()

        payment_key = PagSegPayment(code='FOO', status=STATUS_SENT_TO_PAGSEGURO).put()

        # Mocking logs that are generated when payment is sent
        logs_keys = [PagSegLog(status=STATUS_CREATED).put(), PagSegLog(status=STATUS_SENT_TO_PAGSEGURO).put()]
        for log_key in logs_keys:
            PagSegPaymentToLog(origin=payment_key, destination=log_key).put()
        expected_statuses = [STATUS_CREATED, STATUS_SENT_TO_PAGSEGURO]
        self._assert_notification_change(acess_data, payment_key, '1', expected_statuses)
        expected_statuses.append(STATUS_ANALYSIS)
        self._assert_notification_change(acess_data, payment_key, '2', expected_statuses)
        expected_statuses.append(STATUS_ACCEPTED)
        self._assert_notification_change(acess_data, payment_key, '3', expected_statuses)
        expected_statuses.append(STATUS_AVAILABLE)
        self._assert_notification_change(acess_data, payment_key, '4', expected_statuses)
        expected_statuses.append(STATUS_DISPUTE)
        self._assert_notification_change(acess_data, payment_key, '5', expected_statuses)
        expected_statuses.append(STATUS_RETURNED)
        self._assert_notification_change(acess_data, payment_key, '6', expected_statuses)
        expected_statuses.append(STATUS_CANCELLED)
        self._assert_notification_change(acess_data, payment_key, '7', expected_statuses)
