# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from itertools import izip
from google.appengine.ext import ndb
from commands import FindOrCreateUserCmd
from gaegraph.model import Node
from gaepagseguro import facade
from tekton import router
from model import OrderItem
from web.pagseguro import home

# essas classes tem que ser do seu dominio



def gerar_pagamento(_handler, _write_tmpl, client_name,
                    client_email, description, quantity, price,
                    street, number, quarter, postalcode, town, state, complement="Sem Complemento", country="BRA",
                    currency='BRL'):
    #saving mocking objects
    owner_key = FindOrCreateUserCmd().execute().result
    items_references = [OrderItem() for i in xrange(len(description))]
    ndb.put_multi(items_references)

    #generating parameters
    items = [facade.create_item(ref, description, price, quantity) for ref, description, price, quantity
             in izip(items_references, description, price, quantity)]
    address = facade.address(street, number, quarter, postalcode, town, state, complement, country)
    return_path = 'https://gaepagseguro.appspot.com%s' % router.to_path(home.index)

    #generating payment
    cmd = facade.payment(return_path, client_name, client_email, owner_key, items, address, currency=currency)
    cmd.execute()
    if cmd.errors:
        dct = {'client_name': client_name,
               'client_email': client_email,
               'items': items,
               'street': street, 'number': number,
               'quarter': quarter, 'postalcode': postalcode,
               'town': town, 'state': state, 'complement': complement,
               'payment_path': router.to_path(gerar_pagamento),
               'errors': cmd.errors}
        _write_tmpl('templates/gaepagseguro/payment_form.html', dct)
    else:
        # Redirecting to pag seguro site
        code = cmd.result.code
        _handler.redirect(facade.pagseguro_url(code))


def notificacao(notificationCode, notificationType):
    facade.payment_notification(notificationCode).execute()
