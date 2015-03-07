# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from xml.etree import ElementTree
from gaebusiness.business import CommandParallel, CommandSequential
from gaebusiness.gaeutil import UrlFetchCommand
from google.appengine.api import urlfetch
from gaepagseguro.model import STATUS_SENT_TO_PAGSEGURO
from gaepagseguro.save_commands import SavePagseguroDataCmd, SavePaymentArcsCmd, UpdatePaymentAndSaveLog
from gaepagseguro.validation_commands import ValidatePagseguroDataCmd


_PAYMENT_URL = "https://ws.pagseguro.uol.com.br/v2/checkout"


class ContactPagseguro(CommandParallel):
    headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=ISO-8859-1'}
    currency = 'BRL'

    def __init__(self, redirect_url):
        super(ContactPagseguro, self).__init__()
        self.redirect_url = redirect_url
        self.fetch_cmd = None
        self.payment = None,
        self.checkout_code = None

    def handle_previous(self, command):
        access_data = command.access_data
        items = command.items
        client_form = command.client_form
        address_form = command.address_form
        self.payment = command.result
        params = _make_params(access_data.email, access_data.token,
                              self.redirect_url, client_form.name,
                              client_form.email, self.payment.key.id(),
                              items, address_form,
                              self.currency)
        params = {k: unicode(v).encode('iso-8859-1') for k, v in params.iteritems()}
        self.fetch_cmd = UrlFetchCommand(_PAYMENT_URL, params, urlfetch.POST, self.headers)
        self.append(self.fetch_cmd)


    def do_business(self):
        super(ContactPagseguro, self).do_business()
        if self.result:
            content = self.result.content
            if self.result.status_code == 200 and content != 'Unauthorized':
                root = ElementTree.XML(content)
                if root.tag != "errors":
                    self.checkout_code = root.findtext("code").decode('ISO-8859-1')
                    self.payment.status = STATUS_SENT_TO_PAGSEGURO
                    self.result = self.payment
                    return
            self.add_error('pagseguro', content)
        else:
            self.add_error('pagseguro', 'Not Contacted%s')


class GeneratePayment(CommandSequential):
    def __init__(self, redirect_url, client_name, client_email, payment_owner, validate_address_cmd,
                 *validate_item_cmds):
        validate_data_cmd = ValidatePagseguroDataCmd(client_name, client_email, validate_address_cmd,
                                                     *validate_item_cmds)
        save_data_cmd = SavePagseguroDataCmd()
        save_arcs_cmd = SavePaymentArcsCmd(payment_owner)
        self.__contact_pagseguro_cmd = ContactPagseguro(redirect_url)
        super(GeneratePayment, self).__init__(validate_data_cmd, save_data_cmd, save_arcs_cmd,
                                              self.__contact_pagseguro_cmd,
                                              UpdatePaymentAndSaveLog())
        self.checkout_code = None

    def do_business(self):
        super(GeneratePayment, self).do_business()
        self.checkout_code = self.__contact_pagseguro_cmd.checkout_code


def _make_params(email, token, redirect_url, client_name, client_email, payment_reference, items, address,
                 currency):
    d = {"email": email,
         "token": token,
         "currency": currency,
         "reference": unicode(payment_reference),
         "senderName": client_name,
         "senderEmail": client_email,
         "shippingType": "3",
         "redirectURL": redirect_url
    }

    for index, item in enumerate(items, 1):
        d["itemId%s" % index] = unicode(
            item.reference.id() if item.reference else '9999')  # if ref is None return fake id 9999
        d["itemDescription%s" % index] = item.description
        d["itemAmount%s" % index] = '%.2f' % item.price
        d["itemQuantity%s" % index] = unicode(item.quantity)

    if address:
        d.update({
            "shippingAddressStreet": address.street,
            "shippingAddressNumber": unicode(address.number),
            "shippingAddressComplement": address.complement,
            "shippingAddressDistrict": address.quarter,
            "shippingAddressPostalCode": address.postalcode,
            "shippingAddressCity": address.town,
            "shippingAddressState": address.state,
            "shippingAddressCountry": "BRA"
        })
    return d