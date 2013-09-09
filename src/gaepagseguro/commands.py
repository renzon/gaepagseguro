# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.api import urlfetch
from gaebusiness.business import CommandList
from gaebusiness.gaeutil import UrlFecthCommand


def _make_params(email, token, redirect_url, client_name, client_email, order_reference, items, address,
                 currency):
    d = {"email": email,
         "token": token,
         "currency": currency,
         "reference": str(order_reference),
         "senderName": client_name,
         "senderEmail": client_email,
         "shippingType": "3",
         "redirectURL": redirect_url
    }

    for index, item in enumerate(items):
        # starting with index 1
        index+=1
        d["itemId%s" % index] = str(item.id)
        d["itemDescription%s" % index] = item.description
        d["itemAmount%s" % index] = item.price
        d["itemQuantity%s" % index] = str(item.quantity)

    if address:
        d.update({
            "shippingAddressStreet": address.street, \
            "shippingAddressNumber": str(address.number), \
            "shippingAddressComplement": address.complement or "Sem Complemento", \
            "shippingAddressDistrict": address.quarter, \
            "shippingAddressPostalCode": address.postalcode, \
            "shippingAddressCity": address.town, \
            "shippingAddressState": address.state, \
            "shippingAddressCountry": "BRA"
        })
    return d


_PAYMENT_URL = "https://ws.pagseguro.uol.com.br/v2/checkout"


class GeneratePayment(CommandList):
    def __init__(self, email, token, redirect_url, client_name, client_email, order_reference, items, address,
                 currency):
        params = _make_params(email, token, redirect_url, client_name, client_email, order_reference, items, address,
                              currency)
        params = {k: v.encode('iso-8859-1') for k, v in params.iteritems()}
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=ISO-8859-1'}
        self._fetch_command=UrlFecthCommand(_PAYMENT_URL, params, urlfetch.POST, headers)
        super(GeneratePayment,self).__init__([self._fetch_command])

    def do_business(self, stop_on_error=False):
        super(GeneratePayment,self).do_business(stop_on_error)
