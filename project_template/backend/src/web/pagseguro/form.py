# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from tekton import router
from web.pagseguro import api


def index(_write_tmpl):
    dct = {'payment_path': router.to_path(api.gerar_pagamento)}
    _write_tmpl('templates/gaepagseguro/payment_form.html', dct)