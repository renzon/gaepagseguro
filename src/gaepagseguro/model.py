# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.ext import ndb
from gaegraph.model import Node, Arc
from ndbext.property import SimpleCurrency, IntegerBounded

STATUS_CREATED = 'CREATED'
STATUS_SENT_TO_PAGSEGURO = 'SENT_TO_PAGSEGURO'
STATUSES = [STATUS_CREATED, STATUS_SENT_TO_PAGSEGURO]


class PagSegAccessData(Node):
    email = ndb.StringProperty(required=True, indexed=False)
    token = ndb.StringProperty(required=True, indexed=False)


class PagSegPayment(Node):
    # code returned from Pagseguro after payment generation
    code = ndb.StringProperty()
    status = ndb.StringProperty(default=STATUS_CREATED, choices=STATUSES)

    @classmethod
    def query_by_code(cls, code):
        return cls.query(cls.code == code)


class OriginToPagSegPayment(Arc):
    '''
    Arc to link some out of the app entity to a PagSegPayment
    '''
    destination = ndb.KeyProperty(PagSegPayment, required=True)


class PagSegItem(Node):
    '''
    PagSegPayment can have several items
    '''
    #references a property from outside pagseguro app
    reference = ndb.KeyProperty(required=True)
    description = ndb.TextProperty(required=True, indexed=False)
    price = SimpleCurrency(required=True, indexed=False)
    quantity = IntegerBounded(required=True, lower=1, indexed=False)

    def total(self):
        return self.price * self.quantity


class PagSegPaymentToItem(Arc):
    '''
    Defines the a item corresponding to a Payment
    '''
    origin = ndb.KeyProperty(PagSegPayment, required=True)
    destination = ndb.KeyProperty(PagSegItem, required=True)





