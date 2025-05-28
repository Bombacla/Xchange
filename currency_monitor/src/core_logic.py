from datetime import datetime, timedelta
from typing import List, Tuple

# Adjust sys.path for imports when running tests or the main block directly from this file's directory.
# This setup assumes that the script might be run directly, and ensures that 'currency_monitor'
# and its sub-packages are discoverable.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from currency_monitor.src.data_fetcher import fetch_current_exchange_rates, fetch_historical_exchange_rate
from currency_monitor.src.models import AlertCondition, ExchangeRate


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
        print(f"\nProcessing condition for {condition.target_currency_code}: "
              f"Drop > {condition.percentage_drop_threshold}% in {condition.time_period_days} days.")

        # Fetch current rate
        current_rates_list = fetch_current_exchange_rates([condition.target_currency_code])
        if not current_rates_list:
            print(f"Warning: Could not fetch current rate for {condition.target_currency_code}. Skipping condition.")
            continue
        
        current_rate_obj = None
        # The API might return rates for other currencies if multiple were requested,
        # or if the base currency is different. We need to find the specific one.
        # For fetch_current_exchange_rates([code]), it should ideally be the only one.
        for rate_obj in current_rates_list:
            if rate_obj.target_currency_code == condition.target_currency_code:
                current_rate_obj = rate_obj
                break
        
        if not current_rate_obj:
            print(f"Warning: Current rate for {condition.target_currency_code} not found in API response. Skipping condition.")
            continue
        
        print(f"  Current rate for {current_rate_obj.target_currency_code} on {current_rate_obj.timestamp.date()}: {current_rate_obj.rate}")

        # Calculate past date
        past_date = today - timedelta(days=condition.time_period_days)
        past_date_str = past_date.strftime("%Y-%m-%d")
        print(f"  Calculated historical date for comparison: {past_date_str}")

        # Fetch historical rate
        historical_rate_obj = fetch_historical_exchange_rate(condition.target_currency_code, past_date_str)
        if not historical_rate_obj:
            print(f"Warning: Could not fetch historical rate for {condition.target_currency_code} on {past_date_str}. Skipping condition.")
            continue
        
        print(f"  Historical rate for {historical_rate_obj.target_currency_code} on {historical_rate_obj.timestamp.date()}: {historical_rate_obj.rate}")

        # Compare rates
        if historical_rate_obj.rate == 0:
            print(f"Warning: Historical rate for {condition.target_currency_code} on {past_date_str} is zero. Skipping comparison to avoid division by zero.")
            continue

        if current_rate_obj.rate < historical_rate_obj.rate:
            percentage_drop = ((historical_rate_obj.rate - current_rate_obj.rate) / historical_rate_obj.rate) * 100
            print(f"  Calculated percentage drop: {percentage_drop:.2f}%")
            if percentage_drop >= condition.percentage_drop_threshold:
                print(f"  ALERT! Drop of {percentage_drop:.2f}% exceeds threshold of {condition.percentage_drop_threshold}%.")
                triggered_alerts.append((condition, historical_rate_obj, current_rate_obj))
            else:
                print(f"  Drop of {percentage_drop:.2f}% is below threshold of {condition.percentage_drop_threshold}%.")
        else:
            print(f"  Current rate {current_rate_obj.rate} is not lower than historical rate {historical_rate_obj.rate}. No drop.")
            
    return triggered_alerts

if __name__ == '__main__':
    # The sys.path adjustment is already done at the top of the file.
    # Re-importing is good practice if there's a concern about the initial import failing
    # before sys.path was set, though for this specific file structure it might not be strictly necessary
    # as the imports are below the sys.path modification.
    
    # Re-import necessary modules to be absolutely sure they are loaded after sys.path modification
    # This is particularly useful if this script were part of a larger package and being run in tricky ways.
    from currency_monitor.src.data_fetcher import fetch_current_exchange_rates, fetch_historical_exchange_rate
    from currency_monitor.src.models import AlertCondition, ExchangeRate # ExchangeRate re-imported for clarity

    print("\n--- Testing core_logic.py ---")
    # Example: Check if USD dropped by 0.5% in the last 7 days
    # Note: This requires the API to be live and might not always trigger an alert.
    # For robust tests, data_fetcher functions should be mocked.
    test_condition_usd = AlertCondition(target_currency_code="USD", percentage_drop_threshold=0.5, time_period_days=7)
    
    # Example: Check if JPY dropped by 1% in the last 30 days
    test_condition_jpy = AlertCondition(target_currency_code="JPY", percentage_drop_threshold=1.0, time_period_days=30)
    
    # Example: Check for a currency that might not exist or have recent data, e.g., a very old currency code
    # Or a condition that is unlikely to trigger to test the "no alerts" path
    test_condition_gbp = AlertCondition(target_currency_code="GBP", percentage_drop_threshold=5.0, time_period_days=1) # 5% drop in 1 day is rare

    alerts_found = check_currency_drops([test_condition_usd, test_condition_jpy, test_condition_gbp])
    
    print("\n--- Summary of Alerts ---")
    if alerts_found:
        for alert_condition, hist_rate, curr_rate in alerts_found:
            print(f"ALERT TRIGGERED FOR: {alert_condition.target_currency_code}")
            print(f"  Condition: Drop > {alert_condition.percentage_drop_threshold}% in {alert_condition.time_period_days} days")
            print(f"  Historical Rate ({hist_rate.timestamp.date()}): {hist_rate.rate:.4f} EUR/{hist_rate.target_currency_code}")
            print(f"  Current Rate ({curr_rate.timestamp.date()}): {curr_rate.rate:.4f} EUR/{curr_rate.target_currency_code}")
            if hist_rate.rate != 0: # Should be guaranteed by check inside function
                drop = ((hist_rate.rate - curr_rate.rate) / hist_rate.rate) * 100
                print(f"  Actual Drop: {drop:.2f}%")
            print("-" * 30)
    else:
        print("No alerts triggered for the test conditions.")

    # Example with a very high threshold that should not trigger
    print("\n--- Testing with high threshold (no alert expected) ---")
    test_condition_high_threshold = AlertCondition(target_currency_code="USD", percentage_drop_threshold=90.0, time_period_days=7)
    alerts_high = check_currency_drops([test_condition_high_threshold])
    if not alerts_high:
        print("No alerts triggered for high threshold USD condition (as expected).")
    else:
        print("Alert triggered for high threshold USD, which is unexpected.")
        for alert_condition, hist_rate, curr_rate in alerts_high:
             print(f"  Historical: {hist_rate.rate}, Current: {curr_rate.rate}")

    # Example for a currency that might not be in the 'latest' endpoint sometimes (e.g. less common ones)
    # Or testing with a currency code that the API might not support, e.g. "XXX"
    # The data_fetcher handles this returning empty list or None, core_logic should skip.
    print("\n--- Testing with potentially problematic currency code ---")
    test_condition_problematic = AlertCondition(target_currency_code="XXX", percentage_drop_threshold=1.0, time_period_days=7)
    alerts_problematic = check_currency_drops([test_condition_problematic])
    if not alerts_problematic:
        print("No alerts triggered for 'XXX' currency (as expected, due to fetch error or no data).")
    else:
        print("Alert triggered for 'XXX', which is unexpected.")

    print("\n--- Core logic tests finished ---")
