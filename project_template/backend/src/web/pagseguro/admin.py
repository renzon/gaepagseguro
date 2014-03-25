# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from tekton import router
from gaepagseguro import facade


def index(_write_tmpl):
    find_data_access = facade.find_access_data().execute()

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
