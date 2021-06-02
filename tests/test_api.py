import json
import unittest
from unittest.mock import patch
from collections import namedtuple
from transbank.webpay.webpay_plus.response import TransactionStatusResponse, TransactionCommitResponse
from transbank.error.transaction_commit_error import TransactionCommitError
from transbank.error.transaction_status_error import TransactionStatusError
from api import app

TransactionCreateMock = namedtuple('Transaction', ('token', 'url'))

status_response = {
    "vci": "TSY",
    "amount": 100.0,
    "status": "INITIALIZED",
    "buy_order": "EOL-00001",
    "session_id": "EOL-00001",
    "card_detail": {"card_number": "XXXX"},
    "accounting_date": "0601",
    "transaction_date": "2021-06-02T00:00:00.000Z",
    "authorization_code": None,
    "payment_type_code": "VD",
    "response_code": None,
    "installments_number": 0,
    "installments_amount": None,
    "balance": None
}


class FlaskTest(unittest.TestCase):

    def setup():
        app.config['TESTING'] = True

    def test_create_unauthorized(self):
        response = app.test_client().post('/process-webpay', json={
            "notify_url": "https://ecommerce/notify",
            "order_number": "EOL-00001",
            "total_incl_tax": "100",
            "api_secret": "no_api_secret"
        })
        self.assertEqual(response.status_code, 403)

    @patch('transbank.webpay.webpay_plus.transaction.Transaction.create')
    def test_create(self, mock_transaction):
        mock_transaction.return_value = TransactionCreateMock(
            'example_token', 'https://webpay/token')

        response = app.test_client().post('/process-webpay', json={
            "notify_url": "https://ecommerce/notify",
            "order_number": "EOL-00001",
            "total_incl_tax": "100",
            "api_secret": "api_secret"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["token"], 'example_token')
        self.assertEqual(response.json["url"], 'https://webpay/token')

    def test_get_transaction_unauthorized(self):
        response = app.test_client().post('/transaction-status', json={
            "token": "example_token",
            "api_secret": "no_api_secret"
        })
        self.assertEqual(response.status_code, 403)

    @patch('transbank.webpay.webpay_plus.transaction.Transaction.status')
    def test_get_transaction(self, mock_transaction):
        mock_transaction.return_value = TransactionStatusResponse(
            **status_response)

        response = app.test_client().post('/transaction-status', json={
            "token": "example_token",
            "api_secret": "api_secret"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode("UTF-8"),
                         json.dumps(status_response))

    @patch('transbank.webpay.webpay_plus.transaction.Transaction.status')
    def test_get_transaction(self, mock_transaction):
        mock_transaction.side_effect = TransactionStatusError(
            "This error is a test")

        response = app.test_client().post('/transaction-status', json={
            "token": "example_token",
            "api_secret": "api_secret"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["response_code"], -1)
        self.assertEqual(response.json["reason"], "This error is a test")

    def test_get_transaction_data_unauthorized(self):
        response = app.test_client().post('/get-transaction', json={
            "token": "example_token",
            "api_secret": "no_api_secret"
        })
        self.assertEqual(response.status_code, 403)

    @patch('transbank.webpay.webpay_plus.transaction.Transaction.commit')
    def test_get_transaction_data(self, mock_transaction_c):
        commit_response = status_response.copy()
        commit_response["status"] = "AUTHORIZED"
        commit_response.pop("installments_amount")
        commit_response.pop("balance")
        mock_transaction_c.return_value = TransactionCommitResponse(
            **commit_response)

        response = app.test_client().post('/get-transaction', json={
            "token": "example_token",
            "api_secret": "api_secret"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode("UTF-8"),
                         json.dumps(commit_response))

    @patch('transbank.webpay.webpay_plus.transaction.Transaction.create')
    @patch('transbank.webpay.webpay_plus.transaction.Transaction.status')
    def test_get_transaction_data_error(self, mock_transaction_s, mock_transaction_c):
        mock_transaction_c.side_effect = TransactionCommitError(
            "This commit error is a test")
        mock_transaction_s.return_value = TransactionStatusResponse(
            **status_response)

        response = app.test_client().post('/get-transaction', json={
            "token": "example_token",
            "api_secret": "api_secret"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode("UTF-8"),
                         json.dumps(status_response))

    @patch('transbank.webpay.webpay_plus.transaction.Transaction.create')
    @patch('transbank.webpay.webpay_plus.transaction.Transaction.status')
    def test_get_transaction_data_error_error(self, mock_transaction_s, mock_transaction_c):
        mock_transaction_c.side_effect = TransactionCommitError(
            "This commit error is a test")
        mock_transaction_s.side_effect = TransactionStatusError(
            "This error is a test")

        response = app.test_client().post('/get-transaction', json={
            "token": "example_token",
            "api_secret": "api_secret"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["response_code"], -1)
        self.assertEqual(response.json["reason"], "This error is a test")


if __name__ == '__main__':
    unittest.main()
