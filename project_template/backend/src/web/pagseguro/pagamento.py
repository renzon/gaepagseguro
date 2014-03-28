# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from commands import FindOrCreateUserCmd
from gaepagseguro import facade
from tekton import router


def listar(_write_tmpl):
    user = FindOrCreateUserCmd().execute().result
    payments = facade.search_orders(user).execute().result
    dct = {'payments': payments, 'detail_path': router.to_path(detalhar)}
    _write_tmpl('templates/gaepagseguro/payment_list.html', dct)


def detalhar(_write_tmpl, order_id):
    items = facade.search_items(order_id).execute().result
    total = sum(i.total() for i in items)
    dct = {'items': items, 'total': total}
    _write_tmpl('templates/gaepagseguro/payment_detail.html', dct)
