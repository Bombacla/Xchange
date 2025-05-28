from datetime import datetime, timedelta
from typing import List, Tuple
import logging

# Adjust sys.path for imports when running tests or the main block directly from this file's directory.
# This setup assumes that the script might be run directly, and ensures that 'currency_monitor'
# and its sub-packages are discoverable.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from currency_monitor.src.data_fetcher import fetch_current_exchange_rates, fetch_historical_exchange_rate, APIError # Added APIError
from currency_monitor.src.models import AlertCondition, ExchangeRate

logger = logging.getLogger(__name__)


def check_currency_drops(conditions: List[AlertCondition]) -> List[Tuple[AlertCondition, ExchangeRate, ExchangeRate]]:
    """
    Checks for currency drops based on a list of alert conditions.

    Args:
        conditions: A list of AlertCondition objects.

    Returns:
        A list of tuples, where each tuple contains the triggered AlertCondition,
        the historical ExchangeRate, and the current ExchangeRate.
    """
    triggered_alerts: List[Tuple[AlertCondition, ExchangeRate, ExchangeRate]] = []
    today = datetime.today()

    for condition in conditions:
        logger.info(f"\nProcessing condition for {condition.target_currency_code}: "
              f"Drop > {condition.percentage_drop_threshold}% in {condition.time_period_days} days.")
        
        try:
            # Fetch current rate
            current_rates_list = fetch_current_exchange_rates([condition.target_currency_code])
            if not current_rates_list:
                # This case might happen if APIError was not raised but list is empty (e.g. if API returns empty rates for valid currency)
                logger.warning(f"Current rate data for {condition.target_currency_code} is empty. Skipping condition.")
                continue
            
            current_rate_obj = None
            for rate_obj in current_rates_list:
                if rate_obj.target_currency_code == condition.target_currency_code:
                    current_rate_obj = rate_obj
                    break
            
            if not current_rate_obj:
                logger.warning(f"Current rate for {condition.target_currency_code} not found in API response. Skipping condition.")
                continue
            
            logger.debug(f"  Current rate for {current_rate_obj.target_currency_code} on {current_rate_obj.timestamp.date()}: {current_rate_obj.rate}")

            # Calculate past date
            past_date = today - timedelta(days=condition.time_period_days)
            past_date_str = past_date.strftime("%Y-%m-%d")
            logger.debug(f"  Calculated historical date for comparison: {past_date_str}")

            # Fetch historical rate
            historical_rate_obj = fetch_historical_exchange_rate(condition.target_currency_code, past_date_str)
            if not historical_rate_obj:
                # This handles cases where fetch_historical_exchange_rate returns None (e.g. currency not found for that date)
                logger.warning(f"Could not obtain historical rate for {condition.target_currency_code} on {past_date_str}. Skipping condition.")
                continue
            
            logger.debug(f"  Historical rate for {historical_rate_obj.target_currency_code} on {historical_rate_obj.timestamp.date()}: {historical_rate_obj.rate}")

            # Compare rates
            if historical_rate_obj.rate == 0:
                logger.warning(f"Historical rate for {condition.target_currency_code} on {past_date_str} is zero. Skipping comparison to avoid division by zero.")
                continue

            if current_rate_obj.rate < historical_rate_obj.rate:
                percentage_drop = ((historical_rate_obj.rate - current_rate_obj.rate) / historical_rate_obj.rate) * 100
                logger.debug(f"  Calculated percentage drop: {percentage_drop:.2f}%")
                if percentage_drop >= condition.percentage_drop_threshold:
                    logger.info(f"  ALERT! Drop of {percentage_drop:.2f}% exceeds threshold of {condition.percentage_drop_threshold}%.")
                    triggered_alerts.append((condition, historical_rate_obj, current_rate_obj))
                else:
                    logger.debug(f"  Drop of {percentage_drop:.2f}% is below threshold of {condition.percentage_drop_threshold}%.")
            else:
                logger.debug(f"  Current rate {current_rate_obj.rate} is not lower than historical rate {historical_rate_obj.rate}. No drop.")
        
        except APIError as e:
            logger.error(f"Skipping alert condition for {condition.target_currency_code} due to an API error: {e}")
            continue # Move to the next condition
            
    return triggered_alerts

if __name__ == '__main__':
    # The sys.path adjustment is already done at the top of the file.
    
    # Setup logging for direct script execution
    from currency_monitor.src.logger_config import setup_logging
    setup_logging(console_level=logging.DEBUG)

    # Re-import necessary modules to be absolutely sure they are loaded after sys.path modification
    from currency_monitor.src.data_fetcher import fetch_current_exchange_rates, fetch_historical_exchange_rate, APIError # APIError for example usage
    from currency_monitor.src.models import AlertCondition, ExchangeRate

    logger.info("\n--- Testing core_logic.py with APIError Handling ---")
    
    # Example conditions
    test_conditions = [
        AlertCondition(target_currency_code="USD", percentage_drop_threshold=0.5, time_period_days=7),
        AlertCondition(target_currency_code="JPY", percentage_drop_threshold=1.0, time_period_days=30),
        AlertCondition(target_currency_code="GBP", percentage_drop_threshold=5.0, time_period_days=1)
    ]
    
    # Simulate APIError for one of the currencies if possible (requires mocking or specific setup)
    # For now, this will run against the live API; APIErrors will be caught if they occur naturally.
    
    logger.info("Running check_currency_drops with test conditions:")
    alerts_found = check_currency_drops(test_conditions)
    
    logger.info("\n--- Summary of Alerts (core_logic.py test) ---")
    if alerts_found:
        for alert_condition, hist_rate, curr_rate in alerts_found:
            logger.info(f"ALERT TRIGGERED FOR: {alert_condition.target_currency_code}")
            logger.info(f"  Condition: Drop > {alert_condition.percentage_drop_threshold}% in {alert_condition.time_period_days} days")
            logger.info(f"  Historical Rate ({hist_rate.timestamp.date()}): {hist_rate.rate:.4f} EUR/{hist_rate.target_currency_code}")
            logger.info(f"  Current Rate ({curr_rate.timestamp.date()}): {curr_rate.rate:.4f} EUR/{curr_rate.target_currency_code}")
            if hist_rate.rate != 0:
                drop = ((hist_rate.rate - curr_rate.rate) / hist_rate.rate) * 100
                logger.info(f"  Actual Drop: {drop:.2f}%")
            logger.info("-" * 30)
    else:
        logger.info("No alerts triggered for the test conditions in core_logic.py test run.")

    # Example with a currency that might cause an APIError (e.g., if API returns 4xx for it)
    # The Frankfurter API is quite robust; "XXX" usually returns valid JSON with empty rates.
    # True API errors might be harder to simulate without mocking or network issues.
    logger.info("\n--- Testing with a potentially problematic currency (e.g., 'FOO') ---")
    problem_condition = [AlertCondition(target_currency_code="FOO", percentage_drop_threshold=1.0, time_period_days=7)]
    alerts_problem = check_currency_drops(problem_condition)
    if not alerts_problem:
        logger.info("No alerts for 'FOO' (expected if APIError occurred and was handled, or if data was simply not found).")

    logger.info("\n--- Core logic tests finished ---")
