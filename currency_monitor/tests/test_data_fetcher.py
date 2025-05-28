import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os
import json # For JSONDecodeError

# Adjust sys.path for imports to work in the test environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from currency_monitor.src.data_fetcher import fetch_current_exchange_rates, fetch_historical_exchange_rate, APIError
from currency_monitor.src.models import ExchangeRate
from currency_monitor.config import settings
import requests # For requests.exceptions

class TestDataFetcher(unittest.TestCase):

    @patch('currency_monitor.src.data_fetcher.requests.get')
    def test_fetch_current_exchange_rates_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "amount": 1.0, "base": "EUR", "date": "2023-10-27",
            "rates": {"USD": 1.0587, "JPY": 158.05}
        }
        mock_get.return_value = mock_response

        target_currencies = ["USD", "JPY"]
        rates = fetch_current_exchange_rates(target_currencies)

        expected_url = f"{settings.FRANKFURTER_API_BASE_URL}/latest"
        mock_get.assert_called_once_with(expected_url, params={"to": ",".join(target_currencies)})
        self.assertEqual(len(rates), 2)
        self.assertIsInstance(rates[0], ExchangeRate)
        # ... (rest of assertions for success case remain similar)

    @patch('currency_monitor.src.data_fetcher.requests.get')
    def test_fetch_current_exchange_rates_network_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Simulated network error")
        with self.assertRaises(APIError) as context:
            fetch_current_exchange_rates(["USD"])
        self.assertIn("Network error or API unavailable", str(context.exception))

    @patch('currency_monitor.src.data_fetcher.requests.get')
    def test_fetch_current_exchange_rates_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Server Error")
        mock_get.return_value = mock_response
        
        with self.assertRaises(APIError) as context:
            fetch_current_exchange_rates(["USD"])
        self.assertIn("Network error or API unavailable", str(context.exception)) # HTTPError is a subclass of RequestException

    @patch('currency_monitor.src.data_fetcher.requests.get')
    def test_fetch_current_exchange_rates_invalid_json(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("err", "doc", 0)
        mock_get.return_value = mock_response

        with self.assertRaises(APIError) as context:
            fetch_current_exchange_rates(["USD"])
        self.assertIn("Invalid JSON response", str(context.exception))

    @patch('currency_monitor.src.data_fetcher.requests.get')
    def test_fetch_historical_exchange_rate_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "amount": 1.0, "base": "EUR", "date": "2023-01-15",
            "rates": {"GBP": 0.88525}
        }
        mock_get.return_value = mock_response

        target_currency = "GBP"
        date_str = "2023-01-15"
        rate = fetch_historical_exchange_rate(target_currency, date_str)

        expected_url = f"{settings.FRANKFURTER_API_BASE_URL}/{date_str}"
        mock_get.assert_called_once_with(expected_url, params={"to": target_currency})
        self.assertIsInstance(rate, ExchangeRate)
        # ... (rest of assertions for success case remain similar)

    @patch('currency_monitor.src.data_fetcher.requests.get')
    def test_fetch_historical_exchange_rate_network_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Simulated network error")
        date_str = "2023-01-15"
        with self.assertRaises(APIError) as context:
            fetch_historical_exchange_rate("USD", date_str)
        self.assertIn("Network error or API unavailable", str(context.exception))

    @patch('currency_monitor.src.data_fetcher.requests.get')
    def test_fetch_historical_exchange_rate_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404 # Example HTTP error
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Not Found")
        mock_get.return_value = mock_response
        
        date_str = "2023-01-15"
        with self.assertRaises(APIError) as context:
            fetch_historical_exchange_rate("USD", date_str)
        self.assertIn("Network error or API unavailable", str(context.exception))

    @patch('currency_monitor.src.data_fetcher.requests.get')
    def test_fetch_historical_exchange_rate_invalid_json(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("err", "doc", 0)
        mock_get.return_value = mock_response

        date_str = "2023-01-15"
        with self.assertRaises(APIError) as context:
            fetch_historical_exchange_rate("USD", date_str)
        self.assertIn("Invalid JSON response", str(context.exception))
    
    @patch('currency_monitor.src.data_fetcher.requests.get')
    @patch('currency_monitor.src.data_fetcher.logger') # Patch logger to check warnings
    def test_fetch_historical_exchange_rate_no_rate_in_response(self, mock_logger, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "amount": 1.0, "base": "EUR", "date": "2023-01-15",
            "rates": {"USD": 1.089} # GBP is missing
        }
        mock_get.return_value = mock_response

        target_currency = "GBP"
        date_str = "2023-01-15"
        rate = fetch_historical_exchange_rate(target_currency, date_str)

        self.assertIsNone(rate)
        mock_logger.warning.assert_called_once_with(
            f"Rate for {target_currency} not found in historical data for date {date_str}."
        )

    @patch('currency_monitor.src.data_fetcher.requests.get')
    def test_fetch_current_exchange_rates_empty_target_list(self, mock_get):
        rates = fetch_current_exchange_rates([])
        self.assertEqual(len(rates), 0)
        mock_get.assert_not_called()

if __name__ == '__main__':
    unittest.main()
