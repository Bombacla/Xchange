import sys
import os
import argparse # Added
import logging # Added to use logging levels

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

# --- Logging Setup (will be done in main() after parsing args) ---
from currency_monitor.src.logger_config import setup_logging

# --- Application Imports (after logging is set up) ---
from currency_monitor.src.models import AlertCondition
from currency_monitor.src.core_logic import check_currency_drops

# Define logger globally, but it will be configured in main()
logger = logging.getLogger(__name__)

def main():
    """
    Main function to run the Currency Exchange Rate Monitor.
    """
    parser = argparse.ArgumentParser(description="Monitor currency exchange rates for significant drops against the EUR.")
    parser.add_argument(
        '--condition',
        nargs=3,  # Expects 3 values: CURRENCY, PERCENT_DROP, DAYS
        action='append',  # Allows specifying the argument multiple times
        metavar=('CURRENCY', 'PERCENT', 'DAYS'),
        dest='conditions_args', # Store the parsed arguments in an attribute named 'conditions_args'
        help="Define an alert condition: currency code (e.g., USD), "
             "percentage drop threshold (e.g., 2.5), and time period in days (e.g., 30). "
             "Can be specified multiple times for multiple conditions."
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count', # Allows -v, -vv, etc.
        default=0,
        help="Increase output verbosity. -v for INFO on console, -vv for DEBUG on console."
    )
    args = parser.parse_args()

    # Adjust logging level based on verbosity
    console_log_level = logging.WARNING # Default if no -v
    if args.verbose == 1:
        console_log_level = logging.INFO
    elif args.verbose >= 2:
        console_log_level = logging.DEBUG
    
    # Initialize logging with potentially adjusted console level
    # The file level can remain DEBUG or be configured as needed
    setup_logging(console_level=console_log_level, file_level=logging.DEBUG)
    
    # Now that logging is configured, we can use the logger
    logger.info("--- Currency Exchange Rate Monitor ---")
    logger.info(f"Verbosity level set to: {args.verbose}, Console log level: {logging.getLevelName(console_log_level)}")
    logger.info("Initializing...")

    # Handle cases where no conditions are provided
    if not args.conditions_args:
        logger.error("No alert conditions provided. Use the --condition argument to specify at least one.")
        parser.print_help() # Optionally, print parser help
        sys.exit(1) # Ensure sys is imported (already imported at the top)

    # Process command-line arguments into AlertCondition objects
    user_defined_conditions = []
    if args.conditions_args: # This check is technically redundant due to the earlier exit if None, but good for clarity
        logger.info(f"Processing {len(args.conditions_args)} condition(s) from command line arguments.")
        for cond_arg in args.conditions_args:
            currency_code_str, percent_str, days_str = cond_arg
            
            try:
                # Validate currency code
                if not currency_code_str or not currency_code_str.isalpha() or len(currency_code_str) != 3:
                    logger.warning(
                        f"Invalid currency code '{currency_code_str}'. Must be 3 alphabetic characters. Skipping this condition."
                    )
                    continue 

                target_currency = currency_code_str.upper()

                # Convert percentage and days
                percentage_drop = float(percent_str)
                time_period_days = int(days_str)

                # Validate percentage and days
                if not (0 < percentage_drop <= 100):
                    logger.warning(
                        f"Invalid percentage drop '{percentage_drop}'. Must be between 0 and 100. Skipping condition for {target_currency}."
                    )
                    continue
                
                if time_period_days <= 0:
                    logger.warning(
                        f"Invalid time period '{time_period_days}'. Must be a positive number of days. Skipping condition for {target_currency}."
                    )
                    continue

                # Create AlertCondition object and add to list
                condition_obj = AlertCondition( # Renamed to condition_obj to avoid conflict with loop variable 'condition' later
                    target_currency_code=target_currency,
                    percentage_drop_threshold=percentage_drop,
                    time_period_days=time_period_days
                )
                user_defined_conditions.append(condition_obj)
                logger.info(f"Added alert condition: Monitor {target_currency} for a {percentage_drop}% drop over {time_period_days} days.")

            except ValueError:
                logger.warning(
                    f"Invalid number format for percentage ('{percent_str}') or days ('{days_str}'). Skipping this condition."
                )
                continue 
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred while processing condition arguments {cond_arg}: {e}. Skipping this condition."
                )
                continue
    
    # Ensure that if --condition arguments were provided, at least one valid condition was processed.
    # The initial check `if not args.conditions_args: sys.exit(1)` handles the case where no --condition args are given.
    if args.conditions_args and not user_defined_conditions: 
        logger.error("No valid alert conditions could be processed from the provided arguments. Please check input formats and try again.")
        sys.exit(1)
    
    # No need for an `else` block that re-introduces hardcoded conditions.
    # If `args.conditions_args` was None/empty, the program exits earlier.
    # If `args.conditions_args` was provided but all were invalid, the program exits just above.
    # So, `user_defined_conditions` is the definitive list.

    logger.info(f"\nStarting currency drop check for {len(user_defined_conditions)} user-defined condition(s)...")
    logger.info("This may take a moment as data is fetched from the API.")

    # Call the core logic function
    triggered_alerts = check_currency_drops(user_defined_conditions)

    # Process and print results
    if triggered_alerts:
        logger.info("\n--- Triggered Alerts ---")
        for condition, hist_rate, curr_rate in triggered_alerts:
            if hist_rate.rate == 0:
                logger.warning(f"Historical rate for {condition.target_currency_code} is zero, cannot calculate drop.")
                continue
            
            actual_drop = ((hist_rate.rate - curr_rate.rate) / hist_rate.rate) * 100
            
            logger.info(f"\nALERT: {condition.target_currency_code} has dropped by {actual_drop:.2f}% over the last {condition.time_period_days} days.")
            logger.info(f"  Threshold was: >{condition.percentage_drop_threshold}%")
            logger.info(f"  Historical Rate ({hist_rate.timestamp.date()}): 1 EUR = {hist_rate.rate:.4f} {hist_rate.target_currency_code}")
            logger.info(f"  Current Rate ({curr_rate.timestamp.date()}): 1 EUR = {curr_rate.rate:.4f} {curr_rate.target_currency_code}")
            logger.info("--------------------")
    else:
        logger.info("\n--- No Currency Drops Met Alert Conditions ---")
        logger.info("All monitored currencies are within their defined thresholds.")

    logger.info("\nMonitoring check complete.")

if __name__ == "__main__":
    main()
