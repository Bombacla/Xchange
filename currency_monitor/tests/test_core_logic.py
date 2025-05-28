import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta
import logging # Added

# Adjust sys.path to ensure project modules can be imported
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from currency_monitor.src.core_logic import check_currency_drops
from currency_monitor.src.models import AlertCondition, ExchangeRate
from currency_monitor.src.data_fetcher import APIError # Added

# Helper function to create ExchangeRate objects consistently for tests
def create_rate(currency_code, rate_value, date_str):
    dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return ExchangeRate(base_currency_code="EUR", target_currency_code=currency_code, rate=rate_value, timestamp=dt_obj)

class TestCoreLogic(unittest.TestCase):

    # Test case: Alert is triggered when the percentage drop exceeds the threshold
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    def test_alert_triggered_when_drop_exceeds_threshold(self, mock_fetch_historical, mock_fetch_current):
        mock_fetch_current.return_value = [create_rate("USD", 1.05, "2023-10-27")]
        mock_fetch_historical.return_value = create_rate("USD", 1.10, "2023-09-27")
        condition = AlertCondition(target_currency_code="USD", percentage_drop_threshold=4.0, time_period_days=30)
        triggered_alerts = check_currency_drops([condition])
        self.assertEqual(len(triggered_alerts), 1)
        alert_condition, hist_rate, curr_rate = triggered_alerts[0]
        self.assertEqual(alert_condition, condition)
        self.assertEqual(hist_rate.rate, 1.10)
        self.assertEqual(curr_rate.rate, 1.05)
        mock_fetch_current.assert_called_once_with(["USD"])
        mock_fetch_historical.assert_called_once_with("USD", (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d"))

    # Test case: No alert is triggered when the percentage drop is below the threshold
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    def test_no_alert_when_drop_below_threshold(self, mock_fetch_historical, mock_fetch_current):
        mock_fetch_current.return_value = [create_rate("USD", 1.08, "2023-10-27")]
        mock_fetch_historical.return_value = create_rate("USD", 1.10, "2023-09-27")
        condition = AlertCondition(target_currency_code="USD", percentage_drop_threshold=3.0, time_period_days=30)
        triggered_alerts = check_currency_drops([condition])
        self.assertEqual(len(triggered_alerts), 0)

    # Test case: No alert is triggered when the currency appreciates (rate increases)
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    def test_no_alert_when_currency_appreciates(self, mock_fetch_historical, mock_fetch_current):
        mock_fetch_current.return_value = [create_rate("USD", 1.15, "2023-10-27")]
        mock_fetch_historical.return_value = create_rate("USD", 1.10, "2023-09-27")
        condition = AlertCondition(target_currency_code="USD", percentage_drop_threshold=1.0, time_period_days=30)
        triggered_alerts = check_currency_drops([condition])
        self.assertEqual(len(triggered_alerts), 0)

    # Test case: Multiple conditions, only one of which should trigger an alert
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    def test_multiple_conditions_one_trigger(self, mock_fetch_historical, mock_fetch_current):
        def current_side_effect(codes_list):
            if codes_list == ["USD"]: return [create_rate("USD", 1.05, "2023-10-27")]
            elif codes_list == ["GBP"]: return [create_rate("GBP", 1.50, "2023-10-27")]
            return []
        def historical_side_effect(code, date_str):
            if code == "USD": return create_rate("USD", 1.10, "2023-09-27")
            elif code == "GBP": return create_rate("GBP", 1.45, "2023-09-27")
            return None
        mock_fetch_current.side_effect = current_side_effect
        mock_fetch_historical.side_effect = historical_side_effect
        condition_usd_triggers = AlertCondition("USD", 4.0, 30)
        condition_gbp_no_trigger = AlertCondition("GBP", 1.0, 30)
        triggered_alerts = check_currency_drops([condition_usd_triggers, condition_gbp_no_trigger])
        self.assertEqual(len(triggered_alerts), 1)
        self.assertEqual(triggered_alerts[0][0].target_currency_code, "USD")

    # Test case: Fetching historical rate fails with APIError, logs error
    @patch('currency_monitor.src.core_logic.logger')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    def test_historical_rate_fetch_fails_with_apierror_logs_error(self, mock_fetch_current, mock_fetch_historical, mock_logger):
        mock_fetch_current.return_value = [create_rate("USD", 1.05, "2023-10-27")]
        mock_fetch_historical.side_effect = APIError("Simulated API error for historical fetch")
        condition = AlertCondition("USD", 5.0, 30)
        results = check_currency_drops([condition])
        self.assertEqual(results, [])
        mock_logger.error.assert_called_once()
        self.assertIn("Skipping alert condition for USD", mock_logger.error.call_args[0][0])
        self.assertIn("Simulated API error for historical fetch", mock_logger.error.call_args[0][0])

    # Test case: Fetching current rate fails with APIError, logs error
    @patch('currency_monitor.src.core_logic.logger')
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate') # Still need to patch it
    def test_current_rate_fetch_fails_with_apierror_logs_error(self, mock_fetch_historical, mock_fetch_current, mock_logger):
        mock_fetch_current.side_effect = APIError("Simulated API error for current fetch")
        condition = AlertCondition("USD", 5.0, 30)
        results = check_currency_drops([condition])
        self.assertEqual(results, [])
        mock_logger.error.assert_called_once()
        self.assertIn("Skipping alert condition for USD", mock_logger.error.call_args[0][0])
        self.assertIn("Simulated API error for current fetch", mock_logger.error.call_args[0][0])
        mock_fetch_historical.assert_not_called()

    # Test case: Historical rate is zero (to prevent division by zero), logs warning
    @patch('currency_monitor.src.core_logic.logger')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    def test_historical_rate_is_zero_logs_warning(self, mock_fetch_current, mock_fetch_historical, mock_logger):
        mock_fetch_current.return_value = [create_rate("USD", 1.05, "2023-10-27")]
        mock_fetch_historical.return_value = create_rate("USD", 0.0, "2023-09-27")
        condition = AlertCondition("USD", 5.0, 30)
        results = check_currency_drops([condition])
        self.assertEqual(results, [])
        # Check that a warning was logged for the zero rate.
        # The structure of call_args is ((args_tuple), {kwargs_dict})
        # So call_args[0][0] is the first positional argument to the logger call.
        # We expect a specific warning message here.
        # Example: mock_logger.warning.assert_any_call("Historical rate for USD on 2023-09-27 is zero. Skipping comparison to avoid division by zero.")
        
        # Let's make a more flexible check for the warning content
        found_warning = False
        for call in mock_logger.warning.call_args_list:
            if "Historical rate for USD" in call[0][0] and "is zero" in call[0][0]:
                found_warning = True
                break
        self.assertTrue(found_warning, "Expected warning about zero historical rate was not logged.")

    # Test for when fetch_historical_exchange_rate returns None (data not found, not an APIError)
    @patch('currency_monitor.src.core_logic.logger')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    def test_historical_rate_not_found_returns_none_logs_warning(self, mock_fetch_current, mock_fetch_historical, mock_logger):
        mock_fetch_current.return_value = [create_rate("USD", 1.05, "2023-10-27")]
        mock_fetch_historical.return_value = None # Simulate data not found
        
        condition = AlertCondition("USD", 5.0, 30)
        results = check_currency_drops([condition])
        
        self.assertEqual(results, [])
        found_warning = False
        for call in mock_logger.warning.call_args_list:
            if "Could not obtain historical rate for USD" in call[0][0]:
                found_warning = True
                break
        self.assertTrue(found_warning, "Expected warning about missing historical rate was not logged.")

if __name__ == '__main__':
    # Setup logging to a high level to avoid seeing log messages during tests,
    # unless a specific test needs to assert logger calls.
    logging.basicConfig(level=logging.CRITICAL) 
    unittest.main()
