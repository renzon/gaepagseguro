# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from decimal import Decimal
from gaegraph.business_base import DestinationsSearch
from gaegraph.model import to_node_key
from gaepagseguro.commands import GeneratePayment, RetrievePaymentDetail, CreateOrUpdateAccessData, FindAccessDataCmd
from gaepagseguro.model import PagSegItem, PagSegOrderToItem, OriginToPagSegOrder


def search_access_data():
    '''
    Returns a command to find AccessData from pagseguro.
     The data contains the email and token used in API calls
    '''
    return FindAccessDataCmd()


def create_or_update_access_data(email, token):
    '''
    Returns a command to create or update de email and token needed for Pagseguro's API calls
    '''
    return CreateOrUpdateAccessData(email, token)


def pagseguro_url(transaction_code):
    '''
    Returns the url which the user must be sent after the payment generation
    '''
    return str("https://pagseguro.uol.com.br/v2/checkout/payment.html?code=%s" % transaction_code)


def payment(redirect_url, client_name, client_email, order_origin, items, address=None,
            currency='BRL'):
    '''Args:
    redirect_url: the url where pagseguro should contact when some transaction ocurs
    client_email: the client's email who is gonna to pay
    client_name: the client's email who is gonna to pay
    order_origin: your order's reference. Most of times, it is the id of the order owner on BD
    items: a list of facade.create_item objects
    address: the shipping address. Must be facade.address instance
    currency: default is BLR
    Returns a Command that contacts pagseguro site to generate a payment. If successful, it contains the transaction
    code on its result attribute'''

    return GeneratePayment(redirect_url, client_name, client_email, order_origin, items, address,
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


class _PagSeguroAddress(object):
    def __init__(self, street, number, quarter, postalcode, town, state, complement="Sem Complemento", country="BRA"):
        self.street = street
        self.number = number
        self.quarter = quarter
        self.postalcode = postalcode
        self.town = town
        self.state = state
        self.complement = complement
        self.country = country


def address(street, number, quarter, postalcode, town, state, complement="Sem Complemento", country="BRA"):
    '''
    Build an address to be used with payment function
    '''
    return _PagSeguroAddress(street, number, quarter, postalcode, town, state, complement, country)


def create_item(reference, description, price, quantity):
    '''
    Creates a item.
    A list of this items must be passed as argument to function payment
    Reference must be a node, or its key or its id. This reference is a link
    Between a pagseguro item and an external entity
    '''
    reference = to_node_key(reference)
    return PagSegItem(reference=reference,
                      quantity=quantity,
                      price=price,
                      description=description)


def search_orders(owner):
    '''
    Returns a command that returns the orders from a owner
    '''
    return DestinationsSearch(OriginToPagSegOrder,to_node_key(owner))


def search_items(order):
    '''
    Returns a command that returns the items from a order
    '''
    return DestinationsSearch(PagSegOrderToItem,to_node_key(order))