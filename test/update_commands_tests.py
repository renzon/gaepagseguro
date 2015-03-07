# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from decimal import Decimal
from gaepermission.model import MainUser
from mock import patch, Mock
from mommygae import mommy
from base import GAETestCase
from gaepagseguro import pagseguro_facade
from gaepagseguro.model import PagSegPayment, STATUS_SENT_TO_PAGSEGURO, STATUS_ANALYSIS, STATUS_ACCEPTED, \
    STATUS_CHARGEBACK, STATUS_CHARGEBACK_DEBT, STATUS_CANCELLED, STATUS_RETURNED, STATUS_DISPUTE, STATUS_CREATED, \
    STATUS_AVAILABLE
from gaepagseguro.update_commands import FetchNotificationDetail


class FetchNotificationTests(GAETestCase):
    @patch('gaepagseguro.update_commands.UrlFetchCommand')
    def test_success(self, UrlFetchClassMock):
        # Pre conditions
        pagseguro_facade.create_or_update_access_data_cmd('foo@bar.com', 'abc123')()
        payment = mommy.save_one(PagSegPayment, code=None, net_amount=None, status=STATUS_SENT_TO_PAGSEGURO)

        # Mocking fetch
        fetch_cmd_obj = Mock()
        fetch_cmd_obj.result.content = generate_xml(payment.key.id(), '2', '18.99')
        UrlFetchClassMock.return_value = fetch_cmd_obj

        # Command execution
        cmd = FetchNotificationDetail('12345')

        cmd()

        # Assertions

        UrlFetchClassMock.assert_called_once_with(
            'https://ws.pagseguro.uol.com.br/v3/transactions/notifications/12345?token=abc123&email=foo%40bar.com')

        self.assertEqual(cmd.result, str(payment.key.id()))
        self.assertEqual(cmd.code, CODE)
        self.assertEqual(cmd.net_amount, '18.99')
        self.assertEqual(cmd.status, STATUS_ANALYSIS)  # status respective to number 2 coming from xml


class IntegrationTests(GAETestCase):
    def assert_payment_notification_saved(self, cmd, expected_statuses, payment):
        cmd()
        payment = payment.key.get()  # Searching from db to see updates
        self.assertEqual(payment.status, expected_statuses[-1])
        logs = pagseguro_facade.search_logs(payment)()
        self.assertEqual(len(expected_statuses), len(logs))
        self.assertListEqual(expected_statuses, [log.status for log in logs])

    @patch('gaepagseguro.update_commands.UrlFetchCommand')
    def test_success(self, UrlFetchClassMock):
        # Pre conditions
        pagseguro_facade.create_or_update_access_data_cmd('foo@bar.com', 'abc123')()
        payment = mommy.save_one(PagSegPayment, code=None, net_amount=None, status=STATUS_SENT_TO_PAGSEGURO)

        # Mocking fetch
        fetch_cmd_obj = Mock()
        fetch_cmd_obj.result.content = generate_xml(payment.key.id(), '2', '18.99')
        UrlFetchClassMock.return_value = fetch_cmd_obj

        # Command execution
        cmd = pagseguro_facade.payment_notification('12345')

        cmd()

        # Assertions for first call after payment for pagseguro

        UrlFetchClassMock.assert_called_once_with(
            'https://ws.pagseguro.uol.com.br/v3/transactions/notifications/12345?token=abc123&email=foo%40bar.com')

        self.assertEqual(cmd.result, payment)
        payment = payment.key.get()  # Searching from db to see updates
        self.assertEqual(payment.code, CODE)
        self.assertEqual(payment.net_amount, Decimal('18.99'))
        self.assertEqual(payment.status, STATUS_ANALYSIS)  # status respective to number 2 coming from xml

        logs = pagseguro_facade.search_logs(payment)()

        self.assertEqual(1, len(logs))
        self.assertEqual(STATUS_ANALYSIS, logs[0].status)

        # Emulating paid status

        fetch_cmd_obj.result.content = generate_xml(payment.key.id(), '3', '18.99')
        expected_statuses = [STATUS_ANALYSIS, STATUS_ACCEPTED]
        self.assert_payment_notification_saved(cmd, expected_statuses, payment)

        # Emulating contesting status
        fetch_cmd_obj.result.content = generate_xml(payment.key.id(), '9', '18.99')
        expected_statuses = [STATUS_ANALYSIS, STATUS_ACCEPTED, STATUS_CHARGEBACK]
        self.assert_payment_notification_saved(cmd, expected_statuses, payment)


        # Emulating chargeback debt status
        fetch_cmd_obj.result.content = generate_xml(payment.key.id(), '8', '18.99')
        expected_statuses = [STATUS_ANALYSIS, STATUS_ACCEPTED, STATUS_CHARGEBACK, STATUS_CHARGEBACK_DEBT]
        self.assert_payment_notification_saved(cmd, expected_statuses, payment)


        # Emulating canceled status
        fetch_cmd_obj.result.content = generate_xml(payment.key.id(), '7', '18.99')
        expected_statuses.append(STATUS_CANCELLED)
        self.assert_payment_notification_saved(cmd, expected_statuses, payment)

        # Emulating Returned
        fetch_cmd_obj.result.content = generate_xml(payment.key.id(), '6', '18.99')
        expected_statuses.append(STATUS_RETURNED)
        self.assert_payment_notification_saved(cmd, expected_statuses, payment)

        # Emulating dispute status
        fetch_cmd_obj.result.content = generate_xml(payment.key.id(), '5', '18.99')
        expected_statuses.append(STATUS_DISPUTE)
        self.assert_payment_notification_saved(cmd, expected_statuses, payment)

        # Emulating created status
        fetch_cmd_obj.result.content = generate_xml(payment.key.id(), '1', '18.99')
        expected_statuses.append(STATUS_SENT_TO_PAGSEGURO)
        self.assert_payment_notification_saved(cmd, expected_statuses, payment)

        # Emulating available status
        fetch_cmd_obj.result.content = generate_xml(payment.key.id(), '4', '18.99')
        expected_statuses.append(STATUS_AVAILABLE)
        self.assert_payment_notification_saved(cmd, expected_statuses, payment)


def generate_xml(reference_id, status_number, net_amount):
    return (NOTIFICATION_XML % (CODE, reference_id, status_number, net_amount)).encode('ISO-8859-1')


CODE = '9E884542-81B3-4419-9A75-BCC6FB495EF1'

NOTIFICATION_XML = '''<!--?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?-->
<transaction>
    <date>2011-02-10T16:13:41.000-03:00</date>
    <code>%s</code>
    <reference>%s</reference>
    <type>1</type>
    <status>%s</status>
    <paymentmethod>
        <type>1</type>
        <code>101</code>
    </paymentmethod>
    <grossAmount>49900.00</grossAmount>
    <discountamount>0.00</discountamount>
    <creditorfees>
        <intermediationrateamount>0.40</intermediationrateamount>
        <intermediationfeeamount>1644.80
        </intermediationfeeamount>
    </creditorfees>
    <netAmount>%s</netAmount>
    <extraamount>0.00</extraamount>
    <installmentcount>1</installmentcount>
    <itemcount>2</itemcount>
    <items>
        <item>
            <id>0001</id>
            <description>Notebook Prata</description>
            <quantity>1</quantity>
            <amount>24300.00</amount>
        </item>
        <item>
            <id>0002</id>
            <description>Notebook Rosa</description>
            <quantity>1</quantity>
            <amount>25600.00</amount>
        </item>
    </items>
    <sender>
        <name>José Comprador</name>
        <email>comprador@uol.com.br</email>
        <phone>
            <areacode>11</areacode>
            <number>56273440</number>
        </phone>
    </sender>
    <shipping>
        <address>
            <street>Av. Brig. Faria Lima</street>
            <number>1384</number>
            <complement>5o andar</complement>
            <district>Jardim Paulistano</district>
            <postalcode>01452002</postalcode>
            <city>Sao Paulo</city>
            <state>SP</state>
            <country>BRA</country>
        </address>
        <type>1</type>
        <cost>21.50</cost>
    </shipping>
</transaction>'''


def create_credit_card_xml(status=4):
    return ('''<?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>
<transaction>
    <date>2014-10-09T11:17:26.000-03:00</date>
    <code>6F09ACBC-BEC1-463F-9174-5E0CF5BE33F1</code>
    <type>1</type>
    <status>%s</status>
    <lastEventDate>2014-10-10T11:33:12.000-03:00</lastEventDate>
    <paymentMethod>
        <type>8</type>
        <code>801</code>
    </paymentMethod>
    <grossAmount>1.00</grossAmount>
    <discountAmount>0.00</discountAmount>
    <creditorFees>
        <intermediationRateAmount>0.00</intermediationRateAmount>
        <intermediationFeeAmount>0.02</intermediationFeeAmount>
    </creditorFees>
    <netAmount>0.98</netAmount>
    <extraAmount>0.00</extraAmount>
    <escrowEndDate>2014-10-10T11:17:26.000-03:00</escrowEndDate>
    <installmentCount>1</installmentCount>
    <itemCount>1</itemCount>
    <items>
        <item>
            <id>1</id>
            <description>Venda pelo celular com leitor de chip e senha</description>
            <quantity>1</quantity>
            <amount>1.00</amount>
        </item>
    </items>
</transaction>''' % status).encode(
        'ISO-8859-1')


class ProcessExternalPaymentCommand(GAETestCase):
    def test_credit_card_reader_payment(self):
        # Payment creation
        cmd = pagseguro_facade.procces_external_payment_cmd(create_credit_card_xml())
        cmd()
        payment = PagSegPayment.query().get()
        self.assertEqual('6F09ACBC-BEC1-463F-9174-5E0CF5BE33F1', payment.code)
        self.assertEqual(Decimal('1.00'), payment.total)
        self.assertEqual(Decimal('0.98'), payment.net_amount)
        self.assertEqual(STATUS_AVAILABLE, payment.status)
        logs = pagseguro_facade.search_logs(payment)()
        self.assertEqual(1, len(logs))
        self.assertEqual(STATUS_AVAILABLE, logs[0].status)
        items = pagseguro_facade.search_items(payment)()
        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(Decimal('1.00'), item.price)
        self.assertEqual(1, item.quantity)
        self.assertEqual('Venda pelo celular com leitor de chip e senha', item.description)

        # Payment update
        cmd = pagseguro_facade.procces_external_payment_cmd(create_credit_card_xml(7))
        cmd()
        payments = PagSegPayment.query().fetch()
        self.assertEqual(1, len(payments))
        payment = payments[0]

        self.assertEqual('6F09ACBC-BEC1-463F-9174-5E0CF5BE33F1', payment.code)
        self.assertEqual(Decimal('1.00'), payment.total)
        self.assertEqual(Decimal('0.98'), payment.net_amount)
        self.assertEqual(STATUS_CANCELLED, payment.status)
        logs = pagseguro_facade.search_logs(payment)()
        self.assertListEqual([STATUS_AVAILABLE, STATUS_CANCELLED], [log.status for log in logs])
        items = pagseguro_facade.search_items(payment)()
        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(Decimal('1.00'), item.price)
        self.assertEqual(1, item.quantity)
        self.assertEqual('Venda pelo celular com leitor de chip e senha', item.description)

    def test_user_creation(self):
        # Payment creation
        cmd = pagseguro_facade.procces_external_payment_cmd(generate_xml('non particular id', '1', '18.99'))
        cmd()
        payments = pagseguro_facade.search_all_payments(relations=['owner'])()
        self.assertEqual(1, len(payments))
        self.assertIsInstance(payments[0].owner, MainUser)
        self.assertEqual('comprador@uol.com.br', payments[0].owner.email)
        self.assertEqual('José Comprador', payments[0].owner.name)

    def test_user_arc_creation(self):
        # Payment creation
        user = mommy.save_one(MainUser, email='comprador@uol.com.br')
        cmd = pagseguro_facade.procces_external_payment_cmd(generate_xml('non particular id', '1', '18.99'))
        cmd()
        payments = pagseguro_facade.search_all_payments(relations=['owner'])()
        self.assertEqual(1, len(payments))
        self.assertEqual(user, payments[0].owner)

    def test_integration_button_payment(self):
        # Payment creation
        cmd = pagseguro_facade.procces_external_payment_cmd(generate_xml('non particular id', '1', '18.99'))
        cmd()
        payment = PagSegPayment.query().get()
        self.assertEqual(CODE, payment.code)
        self.assertEqual(Decimal('49900'), payment.total)
        self.assertEqual(Decimal('18.99'), payment.net_amount)
        self.assertEqual(STATUS_SENT_TO_PAGSEGURO, payment.status)
        logs = pagseguro_facade.search_logs(payment)()
        self.assertEqual(1, len(logs))
        self.assertEqual(STATUS_SENT_TO_PAGSEGURO, logs[0].status)
        items = pagseguro_facade.search_items(payment)()
        self.assertEqual(2, len(items))
        item = items[0]
        self.assertEqual(Decimal('24300'), item.price)
        self.assertEqual(1, item.quantity)
        self.assertEqual('Notebook Prata', item.description)

        # Payment update
        cmd = pagseguro_facade.procces_external_payment_cmd(generate_xml('non particular id', '7', '18.99'))
        cmd()
        payments = PagSegPayment.query().fetch()
        self.assertEqual(1, len(payments))
        payment = payments[0]

        self.assertEqual(CODE, payment.code)
        self.assertEqual(Decimal('49900'), payment.total)
        self.assertEqual(Decimal('18.99'), payment.net_amount)
        self.assertEqual(STATUS_CANCELLED, payment.status)
        logs = pagseguro_facade.search_logs(payment)()
        self.assertListEqual([STATUS_SENT_TO_PAGSEGURO, STATUS_CANCELLED], [log.status for log in logs])
        items = pagseguro_facade.search_items(payment)()
        self.assertEqual(2, len(items))
        item = items[0]
        self.assertEqual(Decimal('24300'), item.price)
        self.assertEqual(1, item.quantity)
        self.assertEqual('Notebook Prata', item.description)

