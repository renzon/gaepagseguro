# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from gaebusiness.business import Command, CommandParallel
from gaegraph.business_base import CreateArc, CreateSingleOriginArc

from gaepagseguro.model import PagSegPayment, PagSegPaymentToItem, PagSegPaymentToLog, ToPagSegPayment, PagSegLog


class SaveItemCmd(Command):
    def handle_previous(self, command):
        """
        Method to generate item from a ItemForm. The form must be exposed on form attribute
        @param command: a command tha expose data through form attributte
        """
        self.result = command.items
        self._to_commit = self.result


class _DataMixin(object):
    def _create_attributes(self):
        self.items = None
        self.access_data = None
        self.client_form = None
        self.address_form = None

    def _set_attributes(self, command):
        self.items = command.items
        self.access_data = command.access_data
        self.address_form = command.address_form
        self.client_form = command.client_form


class SavePagseguroDataCmd(CommandParallel, _DataMixin):
    def __init__(self):
        super(SavePagseguroDataCmd, self).__init__()
        self._create_attributes()
        self.result = PagSegPayment()


    def handle_previous(self, command):
        self._set_attributes(command)
        self.result.total = sum(i.total() for i in self.items)

    def commit(self):
        self._to_commit = [self.result] + self.items
        return super(SavePagseguroDataCmd, self).commit()


class CreatePagToItem(CreateArc):
    arc_class = PagSegPaymentToItem


class SavePaymentToItemsArcs(CommandParallel, _DataMixin):
    def __init__(self):
        super(SavePaymentToItemsArcs, self).__init__()
        self._create_attributes()

    def handle_previous(self, command):
        self._set_attributes(command)
        self.extend([CreatePagToItem(command.result, i) for i in command.items])


class SimpleSave(Command):
    def __init__(self, node):
        super(SimpleSave, self).__init__()
        self._to_commit = node
        self.result = node


class CreatePagSegPaymentToLog(CreateArc):
    arc_class = PagSegPaymentToLog


class SavePaymentToLog(CommandParallel):
    def handle_previous(self, command):
        payment = command.result
        if isinstance(payment, PagSegPayment):
            log = PagSegLog(status=payment.status)
            self.append(CreatePagSegPaymentToLog(payment, SimpleSave(log)))


class UpdatePaymentAndSaveLog(CommandParallel):
    def __init__(self, payment=None):
        super(UpdatePaymentAndSaveLog, self).__init__()
        self.__payment = payment
        self._setup_update()

    def _setup_update(self):
        if isinstance(self.__payment, PagSegPayment):
            log = PagSegLog(status=self.__payment.status)
            create_arc = CreateArc(SimpleSave(self.__payment), SimpleSave(log))
            create_arc.arc_class = PagSegPaymentToLog
            self.append(create_arc)

    def handle_previous(self, command):
        self.__payment = command.result
        self._setup_update()

    def do_business(self):
        super(UpdatePaymentAndSaveLog, self).do_business()
        self.result = self.__payment


class SaveToPayment(CreateSingleOriginArc):
    arc_class = ToPagSegPayment

    def handle_previous(self, command):
        self.destination = command.result


class SavePaymentArcsCmd(CommandParallel, _DataMixin):
    def __init__(self, payment_owner):
        super(SavePaymentArcsCmd, self).__init__(SaveToPayment(payment_owner),
                                                 SavePaymentToLog(),
                                                 SavePaymentToItemsArcs())
        self._create_attributes()
        self.__payment = None

    def handle_previous(self, command):
        super(SavePaymentArcsCmd, self).handle_previous(command)
        self._set_attributes(command)
        self.__payment = command.result


    def do_business(self):
        super(SavePaymentArcsCmd, self).do_business()
        self.result = self.__payment


