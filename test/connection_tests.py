# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from decimal import Decimal

from google.appengine.ext import ndb

from gaebusiness.business import CommandSequential
from gaegraph.model import Node
from mock import patch, Mock
from base import GAETestCase
from gaepagseguro import pagseguro_facade
from gaepagseguro.connection_commands import _make_params, ContactPagseguro
from gaepagseguro.model import PagSegItem, PagSegPayment, STATUS_SENT_TO_PAGSEGURO
from gaepagseguro.validation_commands import ValidateClientCmd


class ConectToPagseguroTests(GAETestCase):
    @patch('gaepagseguro.connection_commands.UrlFetchCommand')
    def test_success(self, UrlFetchClassMock):
        # Mocking pagseguro Fetch
        UrlFetchClassMock.return_value = _build_mock()

        # Mocking previous command
        data_cmd_mock = Mock()
        data_cmd_mock.access_data.email = 'foo@bar.com'
        data_cmd_mock.access_data.token = '4567890oiuytfgh'
        reference0 = ItemReferenceMock()
        reference1 = ItemReferenceMock()
        items = [PagSegItem(description='Python Course', price=Decimal('120'), quantity=1, reference=reference0.key),
                 PagSegItem(description='Another Python Course', price=Decimal('240'), quantity=2,
                            reference=reference1.key)]
        ndb.put_multi(items)
        data_cmd_mock.items = items
        data_cmd_mock.client_form = ValidateClientCmd(email='jhon@bar.com', name='Jhon Doe').form
        data_cmd_mock.address_form = pagseguro_facade.validate_address_cmd('Rua 1', '2', 'meu bairro', '12345678',
                                                                              'São Paulo', 'SP', 'apto 4').form

        payment = PagSegPayment()
        payment.put()
        data_cmd_mock.result = payment

        contact_pagseguro_cmd = ContactPagseguro('https://store.com/pagseguro')
        CommandSequential(data_cmd_mock, contact_pagseguro_cmd).execute()

        self.assertEqual(payment, contact_pagseguro_cmd.result)
        self.assertEqual(payment.status, STATUS_SENT_TO_PAGSEGURO)
        self.assertEqual(contact_pagseguro_cmd.checkout_code, _SUCCESS_PAGSEGURO_CODE,
                         'Should have the code extracted from xml _PAGSEGURO_DETAIL_XML')
        self.assertIsNone(payment.code)


    def test_make_params(self):
        # creating dataaccess
        email = 'foo@bar.com'
        token = '4567890oiuytfgh'
        reference0 = ItemReferenceMock()
        reference1 = ItemReferenceMock()
        owner = PaymentOwner()
        ndb.put_multi([reference0, reference1, owner])
        items = [PagSegItem(description='Python Course', price=Decimal('120'), quantity=1, reference=reference0.key),
                 PagSegItem(description='Another Python Course', price=Decimal('240'), quantity=2,
                            reference=reference1.key)]
        ndb.put_multi(items)
        validate_address_cmd = pagseguro_facade.validate_address_cmd('Rua 1', '2', 'meu bairro', '12345678',
                                                                        'São Paulo', 'SP', 'apto 4')

        client_name = 'Jhon Doe'
        client_email = 'jhon@bar.com'

        redirect_url = 'https://mystore.com/pagseguro'
        payment_reference = '1234'
        dct = _make_params(email, token, redirect_url, client_name, client_email, payment_reference,
                           items, validate_address_cmd.form, 'BRL')
        self.maxDiff = None
        self.assertDictEqual(_build_success_params(reference0.key.id(), reference1.key.id()), dct)


def _build_mock():
    fetch_mock = Mock()
    fetch_mock.execute = Mock(return_value=fetch_mock)
    fetch_mock.result.content = _SUCCESS_PAGSEGURO_XML.encode('ISO-8859-1')
    fetch_mock.result.status_code = 200
    fetch_mock.errors = {}
    fetch_mock.commit = Mock(return_value=[])
    return fetch_mock


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
    return xml.encode('ISO-8859-1')


class ItemReferenceMock(Node):
    pass


class PaymentOwner(Node):
    pass