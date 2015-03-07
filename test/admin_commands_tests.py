# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from gaegraph.model import Node
from base import GAETestCase
from gaepagseguro import pagseguro_facade
from gaepagseguro.admin_commands import FindAccessDataCmd
from gaepagseguro.model import PagSegAccessData


class PagSeguroAccessDataTests(GAETestCase):
    def test_create_or_update_access_data(self):
        data = FindAccessDataCmd().execute().result
        self.assertIsNone(data)
        pagseguro_facade.create_or_update_access_data_cmd('foo@gmail.com', 'abc').execute()
        data = FindAccessDataCmd().execute().result
        self.assertEqual('foo@gmail.com', data.email)
        self.assertEqual('abc', data.token)
        pagseguro_facade.create_or_update_access_data_cmd('other@gmail.com', '123').execute()
        data2 = FindAccessDataCmd().execute().result
        self.assertEqual(data.key, data2.key)
        self.assertEqual('other@gmail.com', data2.email)
        self.assertEqual('123', data2.token)

        # Another change to assure data is not cached
        pagseguro_facade.create_or_update_access_data_cmd('bar@gmail.com', 'xpto').execute()
        data3 = FindAccessDataCmd().execute().result
        self.assertEqual(data.key, data3.key)
        self.assertEqual('bar@gmail.com', data3.email)
        self.assertEqual('xpto', data3.token)

    def test_find_access_data_cmd(self):
        cmd = pagseguro_facade.search_access_data_cmd().execute()
        self.assertIsNone(cmd.result)
        PagSegAccessData(email='foo@gmail.com', token='abc').put()
        data = pagseguro_facade.search_access_data_cmd().execute().result

        self.assertEqual('foo@gmail.com', data.email)
        self.assertEqual('abc', data.token)

