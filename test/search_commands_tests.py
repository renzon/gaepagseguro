# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.ext import ndb
from base import GAETestCase
from gaepagseguro import pagseguro_facade
from gaepagseguro.model import PagSegPayment, STATUS_CREATED, STATUS_SENT_TO_PAGSEGURO
from gaepagseguro.search_commands import GetPayment


class PaymentSearchTests(GAETestCase):
    def test_all_payment_search(self):
        created_payments = [PagSegPayment(status=STATUS_CREATED) for i in xrange(3)]
        ndb.put_multi(created_payments)
        # reversing because search is desc
        created_payments.reverse()

        sent_payments = [PagSegPayment(status=STATUS_SENT_TO_PAGSEGURO) for i in xrange(3)]
        ndb.put_multi(sent_payments)
        sent_payments.reverse()
        # Testing search for all
        cmd = pagseguro_facade.search_all_payments(page_size=3).execute()
        self.assertListEqual(sent_payments, cmd.result)
        cmd2 = pagseguro_facade.search_all_payments(page_size=3, start_cursor=cmd.cursor).execute()
        self.assertListEqual(created_payments, cmd2.result)
        cmd3 = pagseguro_facade.search_all_payments(page_size=3, start_cursor=cmd2.cursor).execute()
        self.assertListEqual([], cmd3.result)

        # Test search based on status
        cmd = pagseguro_facade.search_all_payments(STATUS_SENT_TO_PAGSEGURO, page_size=4).execute()
        self.assertListEqual(sent_payments, cmd.result)
        cmd = pagseguro_facade.search_all_payments(STATUS_CREATED, page_size=4).execute()
        self.assertListEqual(created_payments, cmd.result)

    def test_get_payment_search(self):
        created_payment = PagSegPayment(status=STATUS_CREATED)
        created_payment.put()
        comand = GetPayment(created_payment.key.id())
        payment = comand()
        self.assertEqual(created_payment, payment)


