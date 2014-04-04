# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from tekton import router
from google.appengine.ext.ndb.query import Cursor
from gaepagseguro import facade
from web.pagseguro.pagamento import detalhar, historico


def index(_write_tmpl):
    find_data_access = facade.search_access_data().execute()

    save_path = router.to_path(salvar)
    dct = {'save_path': save_path,
           'data_access': find_data_access.result}
    _write_tmpl('templates/gaepagseguro/data_access_form.html', dct)


def salvar(_write_tmpl, email, token):
    cmd = facade.create_or_update_access_data(email, token).execute()
    if cmd.errors:
        class DataAccess(object):
            def __init__(self, email, token):
                self.token = token
                self.email = email

        save_path = router.to_path(salvar)
        dct = {'save_path': save_path,
               'data_access': DataAccess(email, token),
               'errors': cmd.errors}
        _write_tmpl('templates/gaepagseguro/data_access_form.html', dct)
    else:
        _write_tmpl('templates/gaepagseguro/data_access_saved.html')


def listar(_write_tmpl, status='', cursor=''):
    cursor = Cursor(urlsafe=cursor) if cursor else None
    cmd = facade.search_all_payments(status, 2, cursor, cache_begin=False).execute()
    next_cursor = cmd.cursor.urlsafe() if cmd.cursor else ''

    dct = {'status': status,
           'search_path': router.to_path(listar),
           'next_page_path': router.to_path(listar, cursor=next_cursor),
           'has_next_page': next_cursor and cmd.more,
           'statuses': facade.PAYMENT_STATUSES,
           'payments': cmd.result,
           'detail_path': router.to_path(detalhar),
           'log_path': router.to_path(historico)}
    _write_tmpl('templates/gaepagseguro/admin_payment_list.html', dct)