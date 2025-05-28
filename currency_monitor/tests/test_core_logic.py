import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta

# Adjust sys.path to ensure project modules can be imported
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from currency_monitor.src.core_logic import check_currency_drops
from currency_monitor.src.models import AlertCondition, ExchangeRate
# from typing import List # Not strictly needed for this file but good for consistency

# Helper function to create ExchangeRate objects consistently for tests
def create_rate(currency_code, rate_value, date_str):
    dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return ExchangeRate(base_currency_code="EUR", target_currency_code=currency_code, rate=rate_value, timestamp=dt_obj)

class TestCoreLogic(unittest.TestCase):

    # Test case: Alert is triggered when the percentage drop exceeds the threshold
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    def test_alert_triggered_when_drop_exceeds_threshold(self, mock_fetch_historical, mock_fetch_current):
        # Configure mock responses
        # Current rate: USD is 1.05 on 2023-10-27
        mock_fetch_current.return_value = [create_rate("USD", 1.05, "2023-10-27")]
        # Historical rate: USD was 1.10 on 2023-09-27 (30 days prior)
        # This represents a drop of ((1.10 - 1.05) / 1.10) * 100 = 4.545...%
        mock_fetch_historical.return_value = create_rate("USD", 1.10, "2023-09-27")

        # Alert condition: USD drop > 4.0% over 30 days
        condition = AlertCondition(target_currency_code="USD", percentage_drop_threshold=4.0, time_period_days=30)
        
        # Call the function under test
        triggered_alerts = check_currency_drops([condition])

        # Assertions
        self.assertEqual(len(triggered_alerts), 1, "Should trigger one alert")
        alert_condition, hist_rate, curr_rate = triggered_alerts[0]
        
        self.assertEqual(alert_condition, condition)
        self.assertEqual(hist_rate.rate, 1.10)
        self.assertEqual(curr_rate.rate, 1.05)
        
        # Verify that the mocks were called as expected
        # The date for historical fetch is calculated inside check_currency_drops,
        # so we can't directly assert the date_str without more complex mocking or knowing today's date.
        # However, we can check the currency code.
        mock_fetch_current.assert_called_once_with(["USD"])
        mock_fetch_historical.assert_called_once_with("USD", (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d"))


    # Test case: No alert is triggered when the percentage drop is below the threshold
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    def test_no_alert_when_drop_below_threshold(self, mock_fetch_historical, mock_fetch_current):
        # Current rate: 1.08 (representing a ~1.8% drop from 1.10)
        mock_fetch_current.return_value = [create_rate("USD", 1.08, "2023-10-27")]
        # Historical rate: 1.10
        mock_fetch_historical.return_value = create_rate("USD", 1.10, "2023-09-27")

        # Alert condition: USD drop > 3.0% over 30 days. Actual drop is ~1.8%
        condition = AlertCondition(target_currency_code="USD", percentage_drop_threshold=3.0, time_period_days=30)
        
        triggered_alerts = check_currency_drops([condition])
        
        self.assertEqual(len(triggered_alerts), 0, "Should not trigger an alert if drop is below threshold")

    # Test case: No alert is triggered when the currency appreciates (rate increases)
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    def test_no_alert_when_currency_appreciates(self, mock_fetch_historical, mock_fetch_current):
        # Current rate: 1.15 (higher than historical)
        mock_fetch_current.return_value = [create_rate("USD", 1.15, "2023-10-27")]
        # Historical rate: 1.10
        mock_fetch_historical.return_value = create_rate("USD", 1.10, "2023-09-27")

        condition = AlertCondition(target_currency_code="USD", percentage_drop_threshold=1.0, time_period_days=30)
        
        triggered_alerts = check_currency_drops([condition])
        
        self.assertEqual(len(triggered_alerts), 0, "Should not trigger an alert if currency appreciates")

    # Test case: Multiple conditions, only one of which should trigger an alert
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    def test_multiple_conditions_one_trigger(self, mock_fetch_historical, mock_fetch_current):
        # Define side effects for mock functions
        def current_side_effect(codes_list):
            if codes_list == ["USD"]:
                return [create_rate("USD", 1.05, "2023-10-27")] # USD drops
            elif codes_list == ["GBP"]:
                return [create_rate("GBP", 1.50, "2023-10-27")] # GBP appreciates
            return []

        def historical_side_effect(code, date_str): # date_str will be determined by the test run time
            # We only care about the currency code and rate for this test's logic
            if code == "USD":
                return create_rate("USD", 1.10, "2023-09-27") # USD historical (higher)
            elif code == "GBP":
                return create_rate("GBP", 1.45, "2023-09-27") # GBP historical (lower)
            return None

        mock_fetch_current.side_effect = current_side_effect
        mock_fetch_historical.side_effect = historical_side_effect

        # Condition for USD: drop > 4.0% (will trigger as 1.10 -> 1.05 is ~4.5% drop)
        condition_usd_triggers = AlertCondition("USD", 4.0, 30)
        # Condition for GBP: drop > 1.0% (will not trigger as 1.45 -> 1.50 is appreciation)
        condition_gbp_no_trigger = AlertCondition("GBP", 1.0, 30)
        
        triggered_alerts = check_currency_drops([condition_usd_triggers, condition_gbp_no_trigger])
        
        self.assertEqual(len(triggered_alerts), 1, "Exactly one alert should be triggered")
        self.assertEqual(triggered_alerts[0][0].target_currency_code, "USD", "The triggered alert should be for USD")

    # Test case: Fetching historical rate fails
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    @patch('builtins.print') # To check for warning print
    def test_historical_rate_fetch_fails(self, mock_print, mock_fetch_historical, mock_fetch_current):
        mock_fetch_current.return_value = [create_rate("USD", 1.05, "2023-10-27")]
        mock_fetch_historical.return_value = None # Simulate failure

        condition = AlertCondition("USD", 5.0, 30)
        triggered_alerts = check_currency_drops([condition])
        
        self.assertEqual(len(triggered_alerts), 0, "Should not trigger alert if historical fetch fails")
        # Check if a warning was printed (optional, but good for robustness)
        # The exact message depends on the implementation in core_logic.py
        # Example: mock_print.assert_any_call(expected_warning_message)
        # For now, just ensuring it runs without error and returns empty.
        
        # Verify historical fetch was attempted
        mock_fetch_historical.assert_called_once()


    # Test case: Fetching current rate fails
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    @patch('builtins.print')
    def test_current_rate_fetch_fails(self, mock_print, mock_fetch_historical, mock_fetch_current):
        mock_fetch_current.return_value = [] # Simulate failure (empty list)
        
        condition = AlertCondition("USD", 5.0, 30)
        triggered_alerts = check_currency_drops([condition])
        
        self.assertEqual(len(triggered_alerts), 0, "Should not trigger alert if current fetch fails")
        mock_fetch_historical.assert_not_called() # Historical fetch should not be attempted if current fails

    # Test case: Historical rate is zero (to prevent division by zero)
    @patch('currency_monitor.src.core_logic.fetch_current_exchange_rates')
    @patch('currency_monitor.src.core_logic.fetch_historical_exchange_rate')
    @patch('builtins.print')
    def test_historical_rate_is_zero(self, mock_print, mock_fetch_historical, mock_fetch_current):
        mock_fetch_current.return_value = [create_rate("USD", 1.05, "2023-10-27")]
        mock_fetch_historical.return_value = create_rate("USD", 0.0, "2023-09-27") # Historical rate is zero

        condition = AlertCondition("USD", 5.0, 30)
        triggered_alerts = check_currency_drops([condition])
        
        self.assertEqual(len(triggered_alerts), 0, "Should not trigger alert if historical rate is zero")
        # Check for a warning print if implemented in core_logic.py
        # For example: mock_print.assert_any_call("Warning: Historical rate for USD on ... is zero. Skipping comparison...")


if __name__ == '__main__':
    unittest.main()
