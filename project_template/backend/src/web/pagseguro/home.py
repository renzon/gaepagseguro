# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from gaepagseguro import facade
from gaepagseguro.model import STATUS_CREATED, STATUS_SENT_TO_PAGSEGURO, STATUS_ANALYSIS, STATUS_ACCEPTED, \
    STATUS_AVAILABLE


def _to_msg(status):
    processing = 'PROCESSING'
    ok = 'OK'
    dct = {STATUS_CREATED: processing,
           STATUS_SENT_TO_PAGSEGURO: processing,
           STATUS_ANALYSIS: processing,
           STATUS_ACCEPTED: ok,
           STATUS_AVAILABLE: ok, }
    return dct.get(status, 'PROBLEM')


def index(_write_tmpl, transaction_id):
    payment = facade.payment_detail(transaction_id).execute().result

    _write_tmpl('templates/gaepagseguro/payment_return.html',
                {'payment': payment, 'msg': _to_msg(payment.status)})