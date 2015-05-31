# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from decimal import Decimal
from gaegraph.model import Node
from google.appengine.ext import ndb
from mock import patch
from base import GAETestCase
from connection_tests import _build_mock, _SUCCESS_PAGSEGURO_CODE
from gaepagseguro import pagseguro_facade
from gaepagseguro.model import STATUS_SENT_TO_PAGSEGURO, STATUS_CREATED, PagSegItem


class IntegrationTests(GAETestCase):
    @patch('gaepagseguro.connection_commands.UrlFetchCommand')
    def test_succesfull_call(self, UrlFetchCommandMock):
        # Mocking call to pagseguro
        UrlFetchCommandMock.return_value = _build_mock()

        # Before making a payment, email and token must be saved
        pagseguro_facade.create_or_update_access_data_cmd('foo@bar.com', 'abc123')()

        # Creating the address validation cmd that will be used on payment
        validate_address_cmd = pagseguro_facade.validate_address_cmd(complement='apto 4', state='SP',
                                                                     town='São Paulo',
                                                                     postalcode='12345-678',
                                                                     quarter='Jardins', number='2',
                                                                     street='Av Vicente de Carvalho')

        # Creating items included on payment
        class ProductMock(Node):
            pass

        product1 = ProductMock()
        product2 = ProductMock()
        ndb.put_multi([product1, product2])
        validate_item_cmds = [pagseguro_facade.validate_item_cmd('Python Birds', '18.99', '1', product1.key),
                              pagseguro_facade.validate_item_cmd('App Engine', '45.58', '2', product2.key)]

        # Creating payment owner. User or other mother can be payment owner

        class UserMock(Node):
            name = ndb.StringProperty(required=True)
            email = ndb.StringProperty(required=True)

        owner = UserMock(name='Renzo Nuccitelli', email='renzon@gmail.com')
        owner.put()

        # Generating payment

        payment_cmd = pagseguro_facade.generate_payment('http://somedomain.com/receive',
                                                        owner.name,
                                                        owner.email,
                                                        owner,
                                                        validate_address_cmd, *validate_item_cmds)

        payment = payment_cmd()

        # Payment assertions
        self.assertEqual(_SUCCESS_PAGSEGURO_CODE, payment_cmd.checkout_code)
        self.assertEqual(STATUS_SENT_TO_PAGSEGURO, payment.status)
        self.assertEqual(Decimal('110.15'), payment.total, "Should be the sum of item's totals")

        # Owner assertion

        owner_payments = pagseguro_facade.search_payments(owner, relations=['owner', 'pay_items', 'logs'])()
        self.assertListEqual([payment], owner_payments)
        payment = owner_payments[0]
        # Log assertions

        statuses = [log.status for log in payment.logs]
        self.assertEqual([STATUS_CREATED, STATUS_SENT_TO_PAGSEGURO], statuses)

        # Items assertions
        self.assertEqual(2, len(payment.pay_items))
        self.assertIsInstance(payment.pay_items[0], PagSegItem)