# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from tekton import router
from web.pagseguro import admin, form


def index(_write_tmpl):
    dct = {'admin_form': router.to_path(admin.index),
           'payment_form': router.to_path(form.index)}
    _write_tmpl('templates/home.html', dct)
