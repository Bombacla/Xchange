import sys
import os

# Option 1: If main.py is run from project root (`python src/main.py`)
# Then `currency_monitor` is already in path if the root is the CWD or in PYTHONPATH.
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))) # Adds project root

# Option 2: If main.py is run from `src` directory (`cd src; python main.py`)
# Then we need to add the parent of `src` (i.e., project root) to path.
# The problem description's sys.path logic seems to target this scenario.
if os.path.basename(os.getcwd()) == 'src':
    # current __file__ is /app/currency_monitor/src/main.py
    # os.path.dirname(__file__) is /app/currency_monitor/src
    # os.path.join(os.path.dirname(__file__), '..') is /app/currency_monitor
    # This makes 'currency_monitor' itself a package that can be imported.
    # However, the imports are `from currency_monitor.src.models`
    # so we need the directory *containing* `currency_monitor` to be in sys.path.
    # This would be /app
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
elif os.path.basename(os.getcwd()) == 'currency_monitor' and 'src' in os.listdir('.'):
    # This case handles running from /app/currency_monitor: python src/main.py
    # We need /app in sys.path
    sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '..')))
else:
    # Default: assume running from project root /app
    # or that PYTHONPATH is set up.
    # Adding /app to path if it's not already there.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


from currency_monitor.src.models import AlertCondition
from currency_monitor.src.core_logic import check_currency_drops

def main():
    """
    Main function to run the Currency Exchange Rate Monitor.
    """
    print("--- Currency Exchange Rate Monitor ---")
    print("Initializing...")

    # Predefined list of alert conditions
    conditions = [
        AlertCondition(target_currency_code="USD", percentage_drop_threshold=2.0, time_period_days=30),
        AlertCondition(target_currency_code="GBP", percentage_drop_threshold=1.5, time_period_days=14),
        AlertCondition(target_currency_code="JPY", percentage_drop_threshold=5.0, time_period_days=60),
        AlertCondition(target_currency_code="AUD", percentage_drop_threshold=2.0, time_period_days=30),
        # A condition that is unlikely to trigger for testing the "no alert" path
        AlertCondition(target_currency_code="CAD", percentage_drop_threshold=50.0, time_period_days=7),
        # A condition that might involve a currency for which data might be sparse or problematic
        AlertCondition(target_currency_code="TRY", percentage_drop_threshold=10.0, time_period_days=90),
    ]

    print(f"\nChecking for alerts based on {len(conditions)} predefined conditions...")
    print("This may take a moment as data is fetched from the API.")

    # Call the core logic function
    triggered_alerts = check_currency_drops(conditions)

    # Process and print results
    if triggered_alerts:
        print("\n--- Triggered Alerts ---")
        for condition, hist_rate, curr_rate in triggered_alerts:
            if hist_rate.rate == 0: # Should be caught by core_logic, but good to double check
                print(f"Warning: Historical rate for {condition.target_currency_code} is zero, cannot calculate drop.")
                continue
            
            actual_drop = ((hist_rate.rate - curr_rate.rate) / hist_rate.rate) * 100
            
            print(f"\nALERT: {condition.target_currency_code} has dropped by {actual_drop:.2f}% over the last {condition.time_period_days} days.")
            print(f"  Threshold was: >{condition.percentage_drop_threshold}%")
            print(f"  Historical Rate ({hist_rate.timestamp.date()}): 1 EUR = {hist_rate.rate:.4f} {hist_rate.target_currency_code}")
            print(f"  Current Rate ({curr_rate.timestamp.date()}): 1 EUR = {curr_rate.rate:.4f} {curr_rate.target_currency_code}")
            print("--------------------")
    else:
        print("\n--- No Currency Drops Met Alert Conditions ---")
        print("All monitored currencies are within their defined thresholds.")

    print("\nMonitoring check complete.")

if __name__ == "__main__":
    # The sys.path adjustments are now at the top of the file.
    # This makes sure that the imports `from currency_monitor.src...` work correctly
    # regardless of how the script is run (from root, from src/, etc.)
    main()
