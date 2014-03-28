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


class PagSegOrder(Node):
    # code returned from Pagseguro after payment generation
    code = ndb.StringProperty()
    status = ndb.StringProperty(default=STATUS_CREATED, choices=STATUSES)

    @classmethod
    def query_by_code(cls, code):
        return cls.query(cls.code == code)


class OriginToPagSegOrder(Arc):
    '''
    Arc to link some out of the app entity to a PagSegOrder
    '''
    destination = ndb.KeyProperty(PagSegOrder, required=True)


class PagSegItem(Node):
    '''
    PagSegOrder can have several items
    '''
    #references a property from outside pagseguro app
    reference = ndb.KeyProperty(required=True)
    description = ndb.TextProperty(required=True, indexed=False)
    price = SimpleCurrency(required=True, indexed=False)
    quantity = IntegerBounded(required=True, lower=1, indexed=False)

    def total(self):
        return self.price * self.quantity


class PagSegOrderToItem(Arc):
    '''
    Defines the items corresponding to a Order
    '''
    origin = ndb.KeyProperty(PagSegOrder, required=True)
    destination = ndb.KeyProperty(PagSegItem, required=True)





