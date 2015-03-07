# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from decimal import Decimal
from gaeforms.ndb.property import SimpleCurrency, IntegerBounded
from google.appengine.ext import ndb
from gaegraph.model import Node, Arc

STATUS_CREATED = 'CREATED'
STATUS_SENT_TO_PAGSEGURO = 'SENT_TO_PAGSEGURO'
STATUS_ANALYSIS = 'ANALYSIS'
# Payment accepted become availble after 30 days if nothing wrong happens
STATUS_ACCEPTED = 'ACCEPTED'
STATUS_AVAILABLE = 'AVAILABLE'
STATUS_DISPUTE = 'DISPUTE'
STATUS_RETURNED = 'RETURNED'
STATUS_CANCELLED = 'CANCELLED'
STATUS_CHARGEBACK='CHARGEBACK'  # status when user contested payment on credit card operation
STATUS_CHARGEBACK_DEBT='CHARGEBACK_DEBT'  # status contested value on operator
STATUSES = [STATUS_CREATED, STATUS_SENT_TO_PAGSEGURO,
            STATUS_ANALYSIS, STATUS_ACCEPTED, STATUS_AVAILABLE,
            STATUS_DISPUTE, STATUS_RETURNED, STATUS_CANCELLED,STATUS_CHARGEBACK,STATUS_CHARGEBACK_DEBT]


class PagSegAccessData(Node):
    email = ndb.StringProperty(required=True, indexed=False)
    token = ndb.StringProperty(required=True, indexed=False)


class PagSegLog(Node):
    status = ndb.StringProperty(required=True, choices=STATUSES, indexed=False)


class PagSegPayment(Node):
    # code returned from Pagseguro after payment generation
    code = ndb.StringProperty()
    status = ndb.StringProperty(default=STATUS_CREATED, choices=STATUSES)
    total = SimpleCurrency()
    net_amount = SimpleCurrency()
    update=ndb.DateTimeProperty(auto_now=True)

    @classmethod
    def query_by_code(cls, code):
        return cls.query(cls.code == code)


class PagSegPaymentToLog(Arc):
    origin = ndb.KeyProperty(PagSegPayment, required=True)
    destination = ndb.KeyProperty(PagSegLog, required=True)


class ToPagSegPayment(Arc):
    '''
    Arc to link some out of the app entity to a PagSegPayment
    '''
    destination = ndb.KeyProperty(PagSegPayment, required=True)


class PagSegItem(Node):
    '''
    PagSegPayment can have several items
    '''
    #references a property from outside pagseguro app
    reference = ndb.KeyProperty()
    description = ndb.TextProperty(required=True, indexed=False)
    price = SimpleCurrency(required=True, indexed=False, upper='9999999.00', lower='0.01')
    quantity = IntegerBounded(required=True, lower=1, upper=999, indexed=False)

    def total(self):
        if isinstance(self.price, Decimal):
            return self.price * self.quantity
        return Decimal(self.price) * self.quantity


class PagSegPaymentToItem(Arc):
    '''
    Defines the a item corresponding to a Payment
    '''
    origin = ndb.KeyProperty(PagSegPayment, required=True)
    destination = ndb.KeyProperty(PagSegItem, required=True)





