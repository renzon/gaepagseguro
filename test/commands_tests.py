# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest
from gaepagseguro import facade, commands
from gaepagseguro.commands import _make_params
from mock import Mock

_SUCCESS_PAGSEGURO_CODE = '8CF4BE7DCECEF0F004A6DFA0A8243412'

_SUCCESS_PAGSEGURO_XML = '''<?xml version="1.0" encoding="ISO-8859-1"?>
<checkout>
    <code>%s</code>
    <date>2010-12-02T10:11:28.000-02:00</date>
</checkout>  ''' % _SUCCESS_PAGSEGURO_CODE

_SUCESS_PARAMS = {"email": 'foo@bar.com',
                  "token": '4567890oiuytfgh',
                  "currency": "BRL",
                  "reference": '1234',
                  "senderName": 'Jhon Doe',
                  "senderEmail": 'jhon@bar.com',
                  "shippingType": "3",
                  "redirectURL": 'https://store.com/pagseguro',
                  "itemId1": '1',
                  "itemDescription1": 'Python Course',
                  "itemAmount1": '120.00',
                  "itemQuantity1": '1',
                  "itemId2": '2',
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


class GeneratePaymentTests(unittest.TestCase):
    def test_make_params(self):
        items = [facade.PagSeguroItem(1, 'Python Course', 12000, 1),
                 facade.PagSeguroItem(2, 'Another Python Course', 24000, 2)]
        address = facade.PagSeguroAddress('Rua 1', 2, 'meu bairro', '12345678', 'São Paulo', 'SP', 'apto 4')
        email = 'foo@bar.com'
        token = '4567890oiuytfgh'
        client_name = 'Jhon Doe'
        client_email = 'jhon@bar.com'
        redirect_url = 'https://store.com/pagseguro'
        order_reference = '1234'
        dct = _make_params(email, token, redirect_url, client_name, client_email, order_reference,
                           items, address, 'BRL')
        self.assertDictEqual(_SUCESS_PARAMS, dct)


    def test_success(self):
        # Setup data
        items = [facade.PagSeguroItem(1, 'Python Course', 12000, 1),
                 facade.PagSeguroItem(2, 'Another Python Course', 24000, 2)]
        address = facade.PagSeguroAddress('Rua 1', 2, 'meu bairro', '12345678', 'São Paulo', 'SP', 'apto 4')
        email = 'foo@bar.com'
        token = '4567890oiuytfgh'
        client_name = 'Jhon Doe'
        client_email = 'jhon@bar.com'
        redirect_url = 'https://store.com/pagseguro'
        order_reference = '1234'
        generate_payment = facade.payment(email, token, redirect_url, client_name, client_email, order_reference,
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
        generate_payment.execute()

        #asserting code extraction
        self.assertEqual(_SUCCESS_PAGSEGURO_CODE, generate_payment.result)


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





