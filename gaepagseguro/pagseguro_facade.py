# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals
from gaegraph.business_base import DestinationsSearch

from gaepagseguro.admin_commands import FindAccessDataCmd, CreateOrUpdateAccessData
from gaepagseguro.search_commands import PaymentsByStatusSearch, AllPaymentsSearch, SearchLogs, SearchOwnerPayments, \
    SearchItems
from gaepagseguro.connection_commands import GeneratePayment
from gaepagseguro.model import STATUSES, ToPagSegPayment, PagSegPaymentToLog, PagSegPaymentToItem, STATUS_CREATED, \
    STATUS_SENT_TO_PAGSEGURO, STATUS_ANALYSIS, STATUS_ACCEPTED, STATUS_AVAILABLE, STATUS_CHARGEBACK_DEBT, \
    STATUS_CHARGEBACK, STATUS_CANCELLED, STATUS_RETURNED, STATUS_DISPUTE
from gaepagseguro.update_commands import FetchNotificationAndUpdatePayment, ProcessExternalPaymentCmd
from gaepagseguro.validation_commands import ValidateAddressCmd, ValidateItemCmd, PaymentForm


PAYMENT_STATUSES = STATUSES

_STATUS_LABEL_DCT = {STATUS_CREATED: 'Criado',
                     STATUS_SENT_TO_PAGSEGURO: 'Enviado ao Pagseguro',
                     STATUS_ANALYSIS: 'Em análise',
                     STATUS_ACCEPTED: 'Aceito',
                     STATUS_AVAILABLE: 'Disponível',
                     STATUS_DISPUTE: 'Em Disputa',
                     STATUS_RETURNED: 'Devolvido',
                     STATUS_CANCELLED: 'Cancelado',
                     STATUS_CHARGEBACK: 'Chargeback',
                     STATUS_CHARGEBACK_DEBT: 'Chargeback crédito'}


def status_label(status):
    return _STATUS_LABEL_DCT.get(status)


def search_access_data_cmd():
    """
    Returns a command to find AccessData from pagseguro.
     The data contains the email and token used in API calls
    """
    return FindAccessDataCmd()


def create_or_update_access_data_cmd(email, token):
    """
    Returns a command to create or update de email and token needed for Pagseguro's API calls
    """
    return CreateOrUpdateAccessData(email, token)


def pagseguro_url(transaction_code):
    """
    Returns the url which the user must be sent after the payment generation
    """
    return str("https://pagseguro.uol.com.br/v2/checkout/payment.html?code=%s" % transaction_code)


def generate_payment(redirect_url, client_name, client_email, payment_owner, validate_address_cmd, *validate_item_cmds):
    """
    Function used to generate a payment on pagseguro
    See facade_tests to undestand the steps before generating a payment


    @param redirect_url: the url where payment status change must be sent
    @param client_name: client's name
    @param client_email: client's email
    @param payment_owner: owner of payment. Her payments can be listed with search_payments function
    @param validate_address_cmd: cmd generated with validate_address_cmd function
    @param validate_item_cmds: list of cmds generated with validate_item_cmd function
    @return: A command that generate the payment when executed
    """
    return GeneratePayment(redirect_url, client_name, client_email, payment_owner, validate_address_cmd,
                           *validate_item_cmds)


def payment_notification(notification_code):
    """
    Used when PagSeguro redirect user after payment
    notification_code: the transaction code returned from payment

    Returns a command that contacts pagseguro site and change payment status and its history according to status code
    (https://pagseguro.uol.com.br/v3/guia-de-integracao/api-de-notificacoes.html)
     The command keep the entire xml string on xml attribute if the user need more details
    """
    return FetchNotificationAndUpdatePayment(notification_code)


def validate_address_cmd(street, number, quarter, postalcode, town, state, complement="Sem Complemento"):
    """
    Build an address form to be used with payment function
    """
    return ValidateAddressCmd(street=street, number=number, quarter=quarter, postalcode=postalcode, town=town,
                              state=state, complement=complement)


def validate_item_cmd(description, price, quantity, reference=None):
    """
    Create a commando to save items from the order.
    A list of items or commands must be created to save a order
    @param description: Item's description
    @param price: Item's price
    @param quantity: Item's quantity
    @param reference: a product reference for the item. Must be a Node
    @return: A Command that validate and save a item
    """
    return ValidateItemCmd(description=description, price=price, quantity=quantity, reference=reference)


def search_payments(owner, relations=None):
    """
    Returns a command to search owner's payment
    """
    return SearchOwnerPayments(owner)


def search_all_payments(payment_status=None, page_size=20, start_cursor=None, offset=0, use_cache=True,
                        cache_begin=True, relations=None):
    """
    Returns a command to search all payments ordered by creation desc
    @param payment_status: The payment status. If None is going to return results independent from status
    @param page_size: number of payments per page
    @param start_cursor: cursor to continue the search
    @param offset: offset number of payment on search
    @param use_cache: indicates with should use cache or not for results
    @param cache_begin: indicates with should use cache on beginning or not for results
    @param relations: list of relations to bring with payment objects. possible values on list: logs, items, owner
    @return: Returns a command to search all payments ordered by creation desc
    """
    if payment_status:
        return PaymentsByStatusSearch(payment_status, page_size, start_cursor, offset, use_cache,
                                      cache_begin, relations)
    return AllPaymentsSearch(page_size, start_cursor, offset, use_cache, cache_begin, relations)


def search_items(payment):
    """
    Returns a command that returns the items from a payment
    """
    return SearchItems(payment)


def search_logs(payment):
    """
    Returns a command that returns the logs from a payment
    """
    return SearchLogs(payment)


def procces_external_payment_cmd(xml):
    """
    Returns a command that process external payment, e.g., those made directly on Pagseguro or with credit card readers
    @param xml: The xml comming from pagseguro notification
    @return: Command instance
    """
    return ProcessExternalPaymentCmd(xml)


def payment_form(**properties):
    """
    Returns a ModelForm instance of PagSegPayment
    @param properties: properties to populate the form coming from request
    @return: ModelForm
    """
    return PaymentForm(**properties)