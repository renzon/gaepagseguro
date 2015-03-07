# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest
from decimal import Decimal
from gaebusiness.business import CommandExecutionException
from google.appengine.ext import ndb
from google.appengine.ext.ndb.model import Model
from base import GAETestCase
from gaepagseguro.admin_commands import CreateOrUpdateAccessData, FindAccessDataCmd
from gaepagseguro.model import PagSegItem
from gaepagseguro.validation_commands import ValidateAddressCmd, ValidateItemCmd, ValidatePagseguroDataCmd, AddressForm, \
    ClientForm


def generate_validate_address_cmd(**kwargs):
    dct = {'complement': 'apto 4', 'state': 'SP', 'town': 'São Paulo', 'postalcode': '12345-678',
           'quarter': 'Jardins', 'number': '2', 'street': 'Av Vicente de Carvalho'}
    dct = dct.copy()
    dct.update(**kwargs)
    return ValidateAddressCmd(**dct)


valid_address_cmd = generate_validate_address_cmd()


class Reference(ndb.Model):
    pass


valid_item_cmds = [ValidateItemCmd(description='Curso Python Birds', price=Decimal('18.99'), quantity=1),
                   ValidateItemCmd(description='Objetos Pythônicos', price=Decimal('29.99'), quantity=2,
                                   reference=ndb.Key(Reference, 10))]


class InvalidPagseguroDataTests(GAETestCase):
    def test_access_data_not_saved(self):
        cmd = ValidatePagseguroDataCmd('Renzo Nuccitelli', 'a@foo.com', valid_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'access_data': 'Must save access data before making payments'})


    def test_email_not_present(self):
        self.assert_email_error('', 'Required field')

    def test_invalid_email(self):
        self.assert_email_error('a', 'Invalid email')
        self.assert_email_error('a@', 'Invalid email')
        self.assert_email_error('a@foo', 'Invalid email')
        self.assert_email_error('a@foo.', 'Invalid email')

    def test_email_with_more_than_60_chars(self):
        self.assert_email_error('a@foo.com.br' + ('a' * 49), 'Has 61 characters and it must have 60 or less')

    def test_required_client_name(self):
        cmd = ValidatePagseguroDataCmd('', 'a@foo', valid_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'access_data': 'Must save access data before making payments'})

    def test_only_first_client_name(self):
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', valid_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'access_data': 'Must save access data before making payments'})

    def test_only_huge_street(self):
        v_address_cmd = generate_validate_address_cmd(street='a' * 81)
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Has 81 characters and it must have 80 or less',
                                 'access_data': 'Must save access data before making payments'})

    def test_absent_street(self):
        v_address_cmd = generate_validate_address_cmd(street='')
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'access_data': 'Must save access data before making payments'})

    def test_huge_number(self):
        v_address_cmd = generate_validate_address_cmd(street='', number='a' * 21)
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'number': 'Has 21 characters and it must have 20 or less',
                                 'access_data': 'Must save access data before making payments'})

    def test_absent_number(self):
        v_address_cmd = generate_validate_address_cmd(street='', number='')
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'number': 'Required field',
                                 'access_data': 'Must save access data before making payments'})

    def test_invalid_postalcode(self):
        v_address_cmd = generate_validate_address_cmd(street='', number='', postalcode='1234567')
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'number': 'Required field',
                                 'postalcode': 'CEP must have exactly 8 characters',
                                 'access_data': 'Must save access data before making payments'})

    def test_absent_postalcode(self):
        v_address_cmd = generate_validate_address_cmd(street='', number='', postalcode='')
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'number': 'Required field',
                                 'postalcode': 'Required field',
                                 'access_data': 'Must save access data before making payments'})

    def test_huge_town(self):
        v_address_cmd = generate_validate_address_cmd(street='', number='', postalcode='', town='a' * 61)
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'number': 'Required field',
                                 'postalcode': 'Required field',
                                 'town': 'Has 61 characters and it must have 60 or less',
                                 'access_data': 'Must save access data before making payments'})

    def test_tiny_town(self):
        v_address_cmd = generate_validate_address_cmd(street='', number='', postalcode='', town='a')
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'number': 'Required field',
                                 'postalcode': 'Required field',
                                 'town': 'Has 1 characters and it must have 2 or more',
                                 'access_data': 'Must save access data before making payments'})

    def test_invalid_state(self):
        v_address_cmd = generate_validate_address_cmd(street='', number='', postalcode='', town='a', state='SPP')
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'number': 'Required field',
                                 'postalcode': 'Required field',
                                 'town': 'Has 1 characters and it must have 2 or more',
                                 'state': 'Has 3 characters and it must have exactly 2',
                                 'access_data': 'Must save access data before making payments'})

    def test_huge_complement(self):
        v_address_cmd = generate_validate_address_cmd(street='', number='', postalcode='', town='a', state='SPP',
                                                      complement='a' * 41)
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'number': 'Required field',
                                 'postalcode': 'Required field',
                                 'town': 'Has 1 characters and it must have 2 or more',
                                 'state': 'Has 3 characters and it must have exactly 2',
                                 'complement': 'Has 41 characters and it must have 40 or less',
                                 'access_data': 'Must save access data before making payments'})

    def test_absent_item_complement(self):
        self.maxDiff = None
        v_address_cmd = generate_validate_address_cmd(street='', number='', postalcode='', town='a', state='SPP',
                                                      complement='a' * 41)
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd)  # not passing any items here as third parameter
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'number': 'Required field',
                                 'postalcode': 'Required field',
                                 'town': 'Has 1 characters and it must have 2 or more',
                                 'state': 'Has 3 characters and it must have exactly 2',
                                 'complement': 'Has 41 characters and it must have 40 or less',
                                 'item_number': 'Should have one item at least',
                                 'access_data': 'Must save access data before making payments'})

    def test_first_invalid_item_complement(self):
        self.maxDiff = None
        v_address_cmd = generate_validate_address_cmd(street='', number='', postalcode='', town='a', state='SPP',
                                                      complement='a' * 41)
        invalid_description_item_cmd = ValidateItemCmd(description='', price=Decimal('18.99'), quantity=1)
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd,
                                       invalid_description_item_cmd,
                                       valid_item_cmds[0])  # not passing any items here as third parameter
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'number': 'Required field',
                                 'postalcode': 'Required field',
                                 'town': 'Has 1 characters and it must have 2 or more',
                                 'state': 'Has 3 characters and it must have exactly 2',
                                 'complement': 'Has 41 characters and it must have 40 or less',
                                 'items': [{'description': 'Required field'},
                                     {}],
                                 'access_data': 'Must save access data before making payments'})

    def test_second_item_invalid_price(self):
        self.maxDiff = None
        v_address_cmd = generate_validate_address_cmd(street='', number='', postalcode='', town='a', state='SPP',
                                                      complement='a' * 41)
        invalid_description_item_cmd = ValidateItemCmd(description='', price='a', quantity='1')
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd,

                                       valid_item_cmds[0],
                                       invalid_description_item_cmd,
                                       valid_item_cmds[1])  # not passing any items here as third parameter
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'number': 'Required field',
                                 'postalcode': 'Required field',
                                 'town': 'Has 1 characters and it must have 2 or more',
                                 'state': 'Has 3 characters and it must have exactly 2',
                                 'complement': 'Has 41 characters and it must have 40 or less',
                                 'items': [{},
                                     {'description': 'Required field', 'price': 'Must be a number'},
                                     {}],
                                 'access_data': 'Must save access data before making payments'})

    def test_second_item_absent_price_invalid_quantity(self):
        self.maxDiff = None
        v_address_cmd = generate_validate_address_cmd(street='', number='', postalcode='', town='a', state='SPP',
                                                      complement='a' * 41)
        invalid_description_item_cmd = ValidateItemCmd(description='', price='', quantity='a')
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd,

                                       valid_item_cmds[0],
                                       invalid_description_item_cmd,
                                       valid_item_cmds[1])  # not passing any items here as third parameter
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'number': 'Required field',
                                 'postalcode': 'Required field',
                                 'town': 'Has 1 characters and it must have 2 or more',
                                 'state': 'Has 3 characters and it must have exactly 2',
                                 'complement': 'Has 41 characters and it must have 40 or less',
                                 'items': [{},
                                     {'description': 'Required field', 'price': 'Required field',
                                      'quantity': 'Must be integer'},
                                     {}],
                                 'access_data': 'Must save access data before making payments'})

    def test_third_absent_quantity_invalid_reference(self):
        self.maxDiff = None
        v_address_cmd = generate_validate_address_cmd(street='', number='', postalcode='', town='a', state='SPP',
                                                      complement='a' * 41)
        invalid_description_item_cmd = ValidateItemCmd(description='', price='', quantity='', reference='a')
        cmd = ValidatePagseguroDataCmd('Renzo', 'a@foo', v_address_cmd,

                                       valid_item_cmds[0],
                                       valid_item_cmds[1],
                                       invalid_description_item_cmd)  # not passing any items here as third parameter
        self.assertRaises(CommandExecutionException, cmd)
        item_errors = [{}, {},
            {'description': 'Required field', 'price': 'Required field', 'quantity': 'Required field',
             'reference': 'Invalid key'}]
        self.assertListEqual(item_errors, cmd.errors['items'])
        self.assert_errors(cmd, {'email': 'Invalid email',
                                 'name': 'Nome informado deve ser completo',
                                 'street': 'Required field',
                                 'number': 'Required field',
                                 'postalcode': 'Required field',
                                 'town': 'Has 1 characters and it must have 2 or more',
                                 'state': 'Has 3 characters and it must have exactly 2',
                                 'complement': 'Has 41 characters and it must have 40 or less',
                                 'items': item_errors,
                                 'access_data': 'Must save access data before making payments'})


    def test_success(self):
        CreateOrUpdateAccessData('renzo@gmail.com', 'token_code')()
        v_address_cmd = generate_validate_address_cmd()

        cmd = ValidatePagseguroDataCmd('Renzo Nuccitelli', 'a@foo.com', v_address_cmd,
                                       ValidateItemCmd(description='Python Birds', price='18.99', quantity='3',
                                                       reference=ndb.Key(Reference, 1)), *valid_item_cmds)
        cmd()  # Should execute without exception

        # asserting data used for in sequential commands are exposed
        self.assertEqual(3, len(cmd.items), 'number of forms should be the same of ValidateItemCommands')
        self.assertIsInstance(cmd.items[0], PagSegItem)
        self.assertEqual(cmd.access_data, FindAccessDataCmd()())
        self.assertIsInstance(cmd.address_form, AddressForm)
        self.assertIsInstance(cmd.client_form, ClientForm)


    def assert_errors(self, cmd, expected_errors):
        self.assertRaises(CommandExecutionException, cmd)
        self.assertDictEqual(expected_errors, cmd.errors)

    def assert_email_error(self, email, error_msg):
        cmd = ValidatePagseguroDataCmd('Jhon Doe', email, valid_address_cmd, *valid_item_cmds)
        self.assert_errors(cmd, {'email': error_msg,
                                 'access_data': 'Must save access data before making payments'})


