# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest
from google.appengine.ext import ndb
from gaegraph.model import Node
from gaepagseguro import facade, commands
from gaepagseguro.commands import _make_params, FindAccessDataCmd, SaveNewOrder
from gaepagseguro.model import PagSegAccessData, PagSegOrder
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


def _generate_xml_detail(order_reference, status):
    xml = _PAGSEGURO_DETAIL_XML % (order_reference, status)
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


class OrderOwner(Node):
    pass


class GeneratePaymentTests(GAETestCase):
    def test_save_new_order(self):
        owner = OrderOwner()
        reference0 = ItemReferenceMock()
        reference1 = ItemReferenceMock()
        ndb.put_multi([reference0, reference1, owner])
        items = [facade.create_item(reference0, 'Python Course', '120.00', 1),
                 facade.create_item(reference1, 'Another Python Course', '240.00', 2)]
        cmd = SaveNewOrder(owner, items).execute()

        items_keys = [i.key for i in items]
        orders = facade.search_orders(owner).execute().result
        self.assertEqual(1, len(orders))
        searched_items = facade.search_items(orders[0]).execute().result
        self.assertEqual(2, len(searched_items))
        searched_keys = [i.key for i in searched_items]
        self.assertListEqual(items_keys, searched_keys)


    def test_make_params(self):
        #creating dataaccess
        email = 'foo@bar.com'
        token = '4567890oiuytfgh'
        reference0 = ItemReferenceMock()
        reference1 = ItemReferenceMock()
        owner = OrderOwner()
        ndb.put_multi([reference0, reference1, owner])
        items = [facade.create_item(reference0, 'Python Course', '120.00', 1),
                 facade.create_item(reference1, 'Another Python Course', '240.00', 2)]

        address = facade.address('Rua 1', 2, 'meu bairro', '12345678', 'São Paulo', 'SP', 'apto 4')

        client_name = 'Jhon Doe'
        client_email = 'jhon@bar.com'
        redirect_url = 'https://mystore.com/pagseguro'
        order_reference = '1234'
        dct = _make_params(email, token, redirect_url, client_name, client_email, order_reference,
                           items, address, 'BRL')
        self.maxDiff = None
        self.assertDictEqual(_build_success_params(reference0.key.id(), reference1.key.id()), dct)


    def test_success(self):
        # Setup data
        email = 'foo@bar.com'
        token = '4567890oiuytfgh'
        facade.create_or_update_access_data(email, token).execute()
        items = [facade.create_item(1, 'Python Course', '120.00', 1),
                 facade.create_item(2, 'Another Python Course', '240.00', 2)]
        address = facade.address('Rua 1', 2, 'meu bairro', '12345678', 'São Paulo', 'SP', 'apto 4')
        client_name = 'Jhon Doe'
        client_email = 'jhon@bar.com'
        redirect_url = 'https://store.com/pagseguro'
        order_reference = '1234'
        generate_payment = facade.payment(redirect_url, client_name, client_email, order_reference,
                                          items, address)
        # mocking pagseguro connection
        fetch_mock = Mock()
        fetch_mock.result.content = _SUCCESS_PAGSEGURO_XML
        fetch_mock.result.status_code = 200
        fetch_mock.errors = {}
        fetch_mock.commit = Mock(return_value=[])
        generate_payment._fetch_command = fetch_mock
        generate_payment._CommandList__commands[0] = fetch_mock

        # Executing command
        order = generate_payment.execute().result

        #asserting code extraction
        self.assertEqual(_SUCCESS_PAGSEGURO_CODE, order.code)
        order_key = PagSegOrder.query_by_code(_SUCCESS_PAGSEGURO_CODE).get(keys_only=True)
        self.assertEqual(order.key, order_key)
        self.assertEqual(2, len(facade.search_items(order_key).execute().result))


class RetrieveDetailTests(unittest.TestCase):
    def test_success(self):
        # Setup data

        email = 'foo@bar.com'
        token = '4567890oiuytfgh'
        order_reference = '1234'
        status = '1'

        # mocking pagseguro connection

        fetch_mock = Mock()
        commands.UrlFecthCommand = fetch_mock
        payment_detail = facade.payment_detail(email, token, _SUCCESS_PAGSEGURO_CODE)
        fetch_mock.result.content = _generate_xml_detail(order_reference, status)
        fetch_mock.result.status_code = 200
        fetch_mock.errors = {}
        fetch_mock.commit = Mock(return_value=[])
        payment_detail._fetch_command = fetch_mock
        payment_detail.commands[0] = fetch_mock

        # Executing command
        payment_detail.execute()

        #asserting code extraction
        self.assertEqual(status, payment_detail.result)
        self.assertEqual(order_reference, payment_detail.order_reference)
        self.assertIsNotNone(payment_detail.xml)
        fetch_mock.assert_any_call('https://ws.pagseguro.uol.com.br/v2/transactions/' + _SUCCESS_PAGSEGURO_CODE,
                                   {'email': email, 'token': token})





