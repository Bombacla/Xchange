import sys
import os

# --- Path Adjustments (should be done early) ---
# Option 1: If main.py is run from project root (`python src/main.py`)
# Then `currency_monitor` is already in path if the root is the CWD or in PYTHONPATH.
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))) # Adds project root

# Option 2: If main.py is run from `src` directory (`cd src; python main.py`)
# Then we need to add the parent of `src` (i.e., project root) to path.
if os.path.basename(os.getcwd()) == 'src':
    # current __file__ is /app/currency_monitor/src/main.py
    # os.path.dirname(__file__) is /app/currency_monitor/src
    # os.path.join(os.path.dirname(__file__), '..', '..') is /app
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
elif os.path.basename(os.getcwd()) == 'currency_monitor' and 'src' in os.listdir('.'):
    # This case handles running from /app/currency_monitor: python src/main.py
    # We need /app in sys.path, which is parent of os.getcwd()
    sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '..')))
else:
    # Default: assume running from project root /app
    # or that PYTHONPATH is set up.
    # Adding /app to path if it's not already there.
    project_root_for_imports = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root_for_imports not in sys.path:
        sys.path.insert(0, project_root_for_imports)

# --- Logging Setup (after path adjustments, before other project imports) ---
from currency_monitor.src.logger_config import setup_logging

# Initialize logging. This configures the root logger.
# Subsequent calls to logging.getLogger(__name__) in other modules will use this configuration.
setup_logging() 

# Get a logger for the main module (optional, if you want to log directly in main.py)
import logging
logger = logging.getLogger(__name__) 

# --- Application Imports (after logging is set up) ---
from currency_monitor.src.models import AlertCondition
from currency_monitor.src.core_logic import check_currency_drops


def main():
    """
    Main function to run the Currency Exchange Rate Monitor.
    """
    logger.info("--- Currency Exchange Rate Monitor ---")
    logger.info("Initializing...")
    logger.info("Initializing...") # Replaced print with logger.info

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

    logger.info(f"\nChecking for alerts based on {len(conditions)} predefined conditions...")
    logger.info("This may take a moment as data is fetched from the API.") # Replaced print

    # Call the core logic function
    triggered_alerts = check_currency_drops(conditions)

    # Process and print results
    if triggered_alerts:
        logger.info("\n--- Triggered Alerts ---") # Replaced print
        for condition, hist_rate, curr_rate in triggered_alerts:
            if hist_rate.rate == 0: # Should be caught by core_logic, but good to double check
                logger.warning(f"Historical rate for {condition.target_currency_code} is zero, cannot calculate drop.") # Replaced print
                continue
            
            actual_drop = ((hist_rate.rate - curr_rate.rate) / hist_rate.rate) * 100
            
            # Using logger.info for alerts, could be logger.warning or a custom level if more severity is needed
            logger.info(f"\nALERT: {condition.target_currency_code} has dropped by {actual_drop:.2f}% over the last {condition.time_period_days} days.")
            logger.info(f"  Threshold was: >{condition.percentage_drop_threshold}%")
            logger.info(f"  Historical Rate ({hist_rate.timestamp.date()}): 1 EUR = {hist_rate.rate:.4f} {hist_rate.target_currency_code}")
            logger.info(f"  Current Rate ({curr_rate.timestamp.date()}): 1 EUR = {curr_rate.rate:.4f} {curr_rate.target_currency_code}")
            logger.info("--------------------")
    else:
        logger.info("\n--- No Currency Drops Met Alert Conditions ---") # Replaced print
        logger.info("All monitored currencies are within their defined thresholds.") # Replaced print

    logger.info("\nMonitoring check complete.") # Replaced print

if __name__ == "__main__":
    # The sys.path adjustments and logging setup are now at the top of the file.
    main()
