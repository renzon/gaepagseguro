# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from decimal import Decimal
from gaegraph.business_base import DestinationsSearch
from gaegraph.model import to_node_key
from gaepagseguro.commands import GeneratePayment, UpdatePaymentStatus, CreateOrUpdateAccessData, FindAccessDataCmd, \
    AllPaymentsSearch, PaymentsByStatusSearch
from gaepagseguro.model import PagSegItem, PagSegPaymentToItem, OriginToPagSegPayment, PagSegPaymentToLog, STATUSES

PAYMENT_STATUSES = STATUSES


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


def payment(redirect_url, client_name, client_email, payment_origin, items, address=None,
            currency='BRL', fetch_cmd=None):
    '''Args:
    redirect_url: the url where pagseguro should contact when some transaction ocurs
    client_email: the client's email who is gonna to pay
    client_name: the client's email who is gonna to pay
    payment_origin: your payment's reference. Most of times, it is the id of the order owner on BD
    items: a list of facade.create_item objects
    address: the shipping address. Must be facade.address instance
    currency: default is BLR
    fetch_cmd: comand to fetch pagsegur site. It's purpose is dependency injection on tests
    Returns a Command that contacts pagseguro site to generate a payment. If successful, it contains the transaction
    code on its result attribute'''

    return GeneratePayment(redirect_url, client_name, client_email, payment_origin, items, address,
                           currency, fetch_cmd)


def payment_detail(transaction_code):
    '''
    Used when PagSeguro redirect user after payment
    transaction_code: the transaction code returned from payment

    Returns a command that contacts pagseguro site and change payment status and its history according to status code
    (https://pagseguro.uol.com.br/v2/guia-de-integracao/finalizacao-do-pagamento.html)
     The command keep the entire xml string on xml attribute if the user need more details
    '''
    return UpdatePaymentStatus(transaction_code, "https://ws.pagseguro.uol.com.br/v2/transactions")


def payment_notification(notification_code):
    '''
    Used when PagSeguro redirect user after payment
    notification_code: the transaction code returned from payment

    Returns a command that contacts pagseguro site and change payment status and its history according to status code
    (https://pagseguro.uol.com.br/v2/guia-de-integracao/api-de-notificacoes.html#!v2-item-api-de-notificacoes-status-da-transacao)
     The command keep the entire xml string on xml attribute if the user need more details
    '''
    return UpdatePaymentStatus(notification_code,
                               "https://ws.pagseguro.uol.com.br/v2/transactions/notifications")


def address(street, number, quarter, postalcode, town, state, complement="Sem Complemento", country="BRA"):
    '''
    Build an address to be used with payment function
    '''
    return {'street': street,
            'number': number,
            'quarter': quarter,
            'postalcode': postalcode,
            'town': town,
            'state': state,
            'complement': complement,
            'country': country}


def create_item(reference, description, price, quantity):
    '''
    Creates a item.
    A list of this items must be passed as argument to function payment
    Reference must be a node, or its key or its id. This reference is a link
    Between a pagseguro item and an external entity
    '''
    reference = to_node_key(reference)
    return {'reference': reference,
            'quantity': quantity,
            'price': price,
            'description': description}


def search_payments(owner):
    '''
    Returns a command to search owner's payment
    '''
    return DestinationsSearch(OriginToPagSegPayment, to_node_key(owner))


def search_all_payments(payment_status=None, page_size=20, start_cursor=None, offset=0, use_cache=True,
                        cache_begin=True):
    '''
    Returns a command to search all payments ordered by creation desc
    '''
    if payment_status:
        return PaymentsByStatusSearch(payment_status, page_size, start_cursor, offset, use_cache,
                                      cache_begin)
    return AllPaymentsSearch(page_size, start_cursor, offset, use_cache, cache_begin)


def search_items(payment):
    '''
    Returns a command that returns the items from a payment
    '''
    return DestinationsSearch(PagSegPaymentToItem, to_node_key(payment))


def search_logs(payment):
    '''
    Returns a command that returns the logs from a payment
    '''
    return DestinationsSearch(PagSegPaymentToLog, to_node_key(payment))
