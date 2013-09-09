# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest
from gaepagseguro import facade
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
                           items, address,'BRL')
        self.assertDictEqual(_SUCESS_PARAMS,dct)


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
        fetch_mock.result.status_code=200
        fetch_mock.errors = {}
        fetch_mock.commit = Mock(return_value=[])
        generate_payment._fetch_command = fetch_mock
        generate_payment.commands[0] = fetch_mock

        # Executing command
        generate_payment.execute()

        #asserting code extraction
        self.assertEqual(_SUCCESS_PAGSEGURO_CODE, generate_payment.result)





