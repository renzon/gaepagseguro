# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from gaebusiness.gaeutil import ModelSearchCommand, SingleModelSearchCommand
from gaegraph.business_base import DestinationsSearch, SingleDestinationSearch, ModelSearchWithRelations, \
    SingleOriginSearch

from gaepagseguro.model import PagSegPayment, PagSegPaymentToLog, ToPagSegPayment, PagSegPaymentToItem


class SearchLogs(DestinationsSearch):
    arc_class = PagSegPaymentToLog


class SearchOwnerPayments(DestinationsSearch):
    arc_class = ToPagSegPayment


class SearchOwner(SingleOriginSearch):
    arc_class = ToPagSegPayment


class SearchItems(DestinationsSearch):
    arc_class = PagSegPaymentToItem


payment_relations = {'pay_items': SearchItems, 'owner': SearchOwner, 'logs': SearchLogs}


class PaymentSearchBase(ModelSearchWithRelations):
    _relations = payment_relations


class AllPaymentsSearch(PaymentSearchBase):
    def __init__(self, page_size=20, start_cursor=None, offset=0, use_cache=True, cache_begin=True, relations=None,
                 **kwargs):
        query = PagSegPayment.query().order(-PagSegPayment.update)
        super(AllPaymentsSearch, self).__init__(query, page_size, start_cursor, offset, use_cache, cache_begin,
                                                relations, **kwargs)


class PaymentsByStatusSearch(PaymentSearchBase):
    def __init__(self, payment_status, page_size=20, start_cursor=None, offset=0, use_cache=True, cache_begin=True,
                 relations=None,
                 **kwargs):
        query = PagSegPayment.query(PagSegPayment.status == payment_status).order(-PagSegPayment.update)
        super(PaymentsByStatusSearch, self).__init__(query, page_size, start_cursor, offset, use_cache, cache_begin,
                                                     relations=relations,
                                                     **kwargs)


class PaymentByPagseguroCode(PaymentSearchBase):
    def __init__(self, transaction_code, relations=None,
                 **kwargs):
        super(PaymentByPagseguroCode, self).__init__(PagSegPayment.query(PagSegPayment.code == transaction_code),
                                                     page_size=1, relations=relations,
                                                     **kwargs)

    def do_business(self):
        super(PaymentByPagseguroCode, self).do_business()
        self.result = self.result[0] if self.result else None

