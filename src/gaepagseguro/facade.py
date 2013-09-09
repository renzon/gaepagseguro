# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from decimal import Decimal
from gaepagseguro.commands import GeneratePayment


class PagSeguroItem(object):
    def __init__(self, id, description, price, quantity):
        '''
        Representation of an order item
        id: item's identification
        description:  item's description
        price: items price. Must be an int idicating the cents. Ex: R$ 1,21 will be 121 and R$ 1,00 will be 100
        '''
        self.id = id
        self.description = description
        self.price = '%.2f' % (Decimal(price) / Decimal(100))
        self.quantity = quantity


class PagSeguroAddress(object):
    def __init__(self, street, number, quarter, postalcode, town, state, complement="Sem Complemento", country="BRA"):
        self.street = street
        self.number = number
        self.quarter = quarter
        self.postalcode = postalcode
        self.town = town
        self.state = state
        self.complement = complement
        self.country = country


def payment(email, token, redirect_url, client_name, client_email, order_reference, items, address=None,
            currency='BRL'):
    '''Args:
    email: the pagseguro registered email
    token: the pagseguro registered token
    redirect_url: the url where pagseguro should contact when some transaction ocurs
    client_email: the client's email who is gonna to pay
    client_name: the client's email who is gonna to pay
    order_reference: your order's reference. Most of times, it is the id of the order on BD
    items: a list of facade.PagSeguroItem objects
    address: the shipping address. Must be facade.PagSeguroAddress instance
    currency: default is BLR
    Returns a Command that contacts pagseguro site to generate a payment. If successful, it contains the transaction
    code on its result attribute'''

    return GeneratePayment(email, token, redirect_url, client_name, client_email, order_reference, items, address,
                           currency)
