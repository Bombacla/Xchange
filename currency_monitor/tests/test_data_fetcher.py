import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# Adjust sys.path for imports to work in the test environment
# We need to add the directory *containing* 'currency_monitor' to sys.path
# __file__ is currency_monitor/tests/test_data_fetcher.py
# os.path.dirname(__file__) is currency_monitor/tests
# os.path.join(os.path.dirname(__file__), '..', '..') is the parent of currency_monitor
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


from currency_monitor.src.data_fetcher import fetch_current_exchange_rates, fetch_historical_exchange_rate
from currency_monitor.src.models import ExchangeRate
from currency_monitor.config import settings # Required by data_fetcher
# Ensure requests is importable for the side_effect
import requests

class TestDataFetcher(unittest.TestCase):

    @patch('currency_monitor.src.data_fetcher.requests.get')
    def test_fetch_current_exchange_rates_success(self, mock_get):
        # Configure the mock_get object
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "amount": 1.0,
            "base": "EUR",
            "date": "2023-10-27",
            "rates": {
                "USD": 1.0587,
                "JPY": 158.05
            }
        }
        mock_get.return_value = mock_response

        target_currencies = ["USD", "JPY"]
        rates = fetch_current_exchange_rates(target_currencies)

        # Assert that mock_get was called once with the correct URL
        expected_url = f"{settings.FRANKFURTER_API_BASE_URL}/latest"
        mock_get.assert_called_once_with(expected_url, params={"to": ",".join(target_currencies)})

        # Assert that the function returns a list of two ExchangeRate objects
        self.assertEqual(len(rates), 2)
        self.assertIsInstance(rates[0], ExchangeRate)
        self.assertIsInstance(rates[1], ExchangeRate)

        # Assert the details of the returned ExchangeRate objects
        expected_date = datetime.strptime("2023-10-27", "%Y-%m-%d")

        # Note: The order of rates in the API response's 'rates' dict is not guaranteed.
        # So, we check if the expected currencies are present and then their values.
        usd_rate = next((r for r in rates if r.target_currency_code == "USD"), None)
        jpy_rate = next((r for r in rates if r.target_currency_code == "JPY"), None)

        self.assertIsNotNone(usd_rate)
        self.assertEqual(usd_rate.base_currency_code, "EUR")
        self.assertEqual(usd_rate.rate, 1.0587)
        self.assertEqual(usd_rate.timestamp, expected_date)

        self.assertIsNotNone(jpy_rate)
        self.assertEqual(jpy_rate.base_currency_code, "EUR")
        self.assertEqual(jpy_rate.rate, 158.05)
        self.assertEqual(jpy_rate.timestamp, expected_date)

    @patch('currency_monitor.src.data_fetcher.requests.get')
    @patch('builtins.print') # To capture print output for error messages
    def test_fetch_current_exchange_rates_api_error(self, mock_print, mock_get):
        # Simulate an API error
        mock_get.side_effect = requests.exceptions.RequestException("Test API error")

        rates = fetch_current_exchange_rates(["USD"])

        # Assert that the function returns an empty list
        self.assertEqual(len(rates), 0)
        
        # Assert that an error message was printed
        mock_print.assert_any_call("Error fetching current exchange rates: Test API error")

    @patch('currency_monitor.src.data_fetcher.requests.get')
    def test_fetch_historical_exchange_rate_success(self, mock_get):
        # Configure mock_response for a successful historical fetch
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "amount": 1.0,
            "base": "EUR",
            "date": "2023-01-15",
            "rates": {
                "GBP": 0.88525
            }
        }
        mock_get.return_value = mock_response

        target_currency = "GBP"
        date_str = "2023-01-15"
        rate = fetch_historical_exchange_rate(target_currency, date_str)

        # Assert mock_get was called with the correct URL
        expected_url = f"{settings.FRANKFURTER_API_BASE_URL}/{date_str}"
        mock_get.assert_called_once_with(expected_url, params={"to": target_currency})

        # Assert a correct ExchangeRate object is returned
        self.assertIsInstance(rate, ExchangeRate)
        self.assertEqual(rate.base_currency_code, "EUR")
        self.assertEqual(rate.target_currency_code, target_currency)
        self.assertEqual(rate.rate, 0.88525)
        self.assertEqual(rate.timestamp, datetime.strptime(date_str, "%Y-%m-%d"))

    @patch('currency_monitor.src.data_fetcher.requests.get')
    @patch('builtins.print') # To capture print output for error messages
    def test_fetch_historical_exchange_rate_api_error(self, mock_print, mock_get):
        # Simulate an API error
        mock_get.side_effect = requests.exceptions.RequestException("Test API error")
        
        date_str = "2023-01-15"
        rate = fetch_historical_exchange_rate("USD", date_str)

        # Assert that the function returns None
        self.assertIsNone(rate)
        
        # Assert that an error message was printed
        mock_print.assert_any_call(f"Error fetching historical exchange rate for USD on {date_str}: Test API error")

    # Test for when the 'rates' key is missing or the specific currency is not in 'rates'
    @patch('currency_monitor.src.data_fetcher.requests.get')
    @patch('builtins.print')
    def test_fetch_historical_exchange_rate_no_rate_in_response(self, mock_print, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "amount": 1.0,
            "base": "EUR",
            "date": "2023-01-15",
            "rates": { # GBP is missing
                "USD": 1.089
            }
        }
        mock_get.return_value = mock_response

        target_currency = "GBP"
        date_str = "2023-01-15"
        rate = fetch_historical_exchange_rate(target_currency, date_str)

        self.assertIsNone(rate)
        mock_print.assert_any_call(f"Rate for {target_currency} not found in response for date {date_str}.")

    @patch('currency_monitor.src.data_fetcher.requests.get')
    @patch('builtins.print')
    def test_fetch_current_exchange_rates_empty_target_list(self, mock_print, mock_get):
        rates = fetch_current_exchange_rates([])
        self.assertEqual(len(rates), 0)
        mock_get.assert_not_called() # Should not make an API call if list is empty

if __name__ == '__main__':
    # This allows running the tests directly from this file
    unittest.main()
