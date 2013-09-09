# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from decimal import Decimal
from gaepagseguro.commands import GeneratePayment, RetrievePaymentDetail


def pagseguro_url(transaction_code):
    '''
    Returns the url which the user must be sent after the payment generation
    '''
    return str("https://pagseguro.uol.com.br/v2/checkout/payment.html?code=%s" % transaction_code)


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


def payment_detail(email, token, transaction_code):
    '''
    Used when PagSeguro redirect user after payment

    email: the pagseguro registered email
    token: the pagseguro registered token
    transaction_code: the transaction code returned from payment

    Returns a command that contacts pagseguro site an has the status code for the transaction in result attibute
    (https://pagseguro.uol.com.br/v2/guia-de-integracao/api-de-notificacoes.html#!v2-item-api-de-notificacoes-status-da-transacao)
     The command keep the entire xml string on xml attribute if the user need more details than just the status code
     and keep the order_reference code on the attribute with same name


    '''
    return RetrievePaymentDetail(email, token, transaction_code, "https://ws.pagseguro.uol.com.br/v2/transactions")


def payment_notification(email, token, transaction_code):
    '''
    Used when PagSeguro notifies that something happened with transaction
    email: the pagseguro registered email
    token: the pagseguro registered token
    transaction_code: the transaction code returned from payment

    Returns a command that contacts pagseguro site an has the status code for the transaction in result attibute
    (https://pagseguro.uol.com.br/v2/guia-de-integracao/api-de-notificacoes.html#!v2-item-api-de-notificacoes-status-da-transacao)
     The command keep the entire xml string on xml attribute if the user need more details than just the status code
     and keep the order_reference code on the attribute with same name
    '''
    return RetrievePaymentDetail(email, token, transaction_code,
                                 "https://ws.pagseguro.uol.com.br/v2/transactions/notifications")


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
