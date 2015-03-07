from __future__ import absolute_import, unicode_literals
# -*- coding: utf-8 -*-
import re

from gaebusiness.business import Command, CommandParallel, CommandExecutionException
from gaeforms.base import Form, StringField, CepField, EmailField
from gaeforms.ndb.form import ModelForm
from gaepagseguro.admin_commands import FindAccessDataCmd
from gaepagseguro.model import PagSegItem, PagSegPayment

# Forms

class PaymentForm(ModelForm):
    _model_class = PagSegPayment

    def fill_with_model(self, model, *fields):
        dct = super(PaymentForm, self).fill_with_model(model, *fields)
        try:
            dct['owner'] = model.owner.to_dict(include=['name', 'id', 'email'])
        except AttributeError:
            pass
        try:
            dct['pay_items'] = [ItemForm().fill_with_model(item) for item in model.pay_items]
        except AttributeError:
            pass

        return dct


class ItemForm(ModelForm):
    _model_class = PagSegItem
    _exclude = [PagSegItem.creation]


class AddressForm(Form):
    street = StringField(required=True, max_len=80)
    number = StringField(required=True, max_len=20)
    quarter = StringField(required=True, max_len=60)
    postalcode = CepField(required=True)
    town = StringField(required=True, max_len=60, min_len=2)
    state = StringField(required=True, exactly_len=2)
    complement = StringField(default="Sem Complemento", max_len=40)
    country = 'BRA'


class ClientForm(Form):
    email = EmailField(required=True, max_len=60)
    name = StringField(required=True, max_len=50)

    def validate(self):
        errors = super(ClientForm, self).validate()
        if not re.match(r'.+ .+', self.name):
            errors['name'] = 'Nome informado deve ser completo'
        return errors


class ValidateCommand(Command):
    """
    Base class command for validation
    """
    _form_class = None

    def __init__(self, **kwargs):
        super(ValidateCommand, self).__init__()
        self.form = self._form_class(**kwargs)

    def do_business(self):
        self.update_errors(**self.form.validate())


class ValidateItemCmd(ValidateCommand):
    _form_class = ItemForm


class ValidateAddressCmd(ValidateCommand):
    _form_class = AddressForm


class ValidateClientCmd(ValidateCommand):
    _form_class = ClientForm


class ValidateAccessData(FindAccessDataCmd):
    def do_business(self):
        super(ValidateAccessData, self).do_business()
        if not self.result:
            self.add_error('access_data', 'Must save access data before making payments')


class ValidatePagseguroDataCmd(CommandParallel):
    def __init__(self, name, email, validate_address_cmd, *validate_item_cmds):
        self.__validate_item_cmds = validate_item_cmds
        self.__validate_client_cmd = ValidateClientCmd(name=name, email=email)
        self.__validate_address_cmd = validate_address_cmd
        self.__find_access_data = ValidateAccessData()
        self.items = None
        self.access_data = None
        self.address_form = validate_address_cmd.form
        self.client_form = self.__validate_client_cmd.form
        super(ValidatePagseguroDataCmd, self).__init__(self.__find_access_data,
                                                       self.__validate_client_cmd,
                                                       validate_address_cmd,
                                                       *validate_item_cmds)


    def do_business(self):
        try:
            super(ValidatePagseguroDataCmd, self).do_business()
            self.items = [c.form.fill_model() for c in self.__validate_item_cmds]
            self.access_data = self.__find_access_data.result
        except CommandExecutionException:
            errors = {}
            errors.update(self.__validate_client_cmd.errors)
            errors.update(self.__validate_address_cmd.errors)
            self.access_data = self.__find_access_data.result
            if self.access_data is None:
                errors['access_data'] = 'Must save access data before making payments'
            if not self.__validate_item_cmds:
                errors['item_number'] = 'Should have one item at least'
            items_errors = [c.errors for c in self.__validate_item_cmds]
            for e in items_errors:
                if e:
                    errors['items'] = items_errors
                    break
            self.errors = errors
            self.raise_exception_if_errors()


