import requests
from datetime import datetime
import logging
import json # Added for JSONDecodeError
from currency_monitor.src.models import ExchangeRate
from currency_monitor.config import settings

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Custom exception for API related errors."""
    pass

def fetch_current_exchange_rates(target_currencies: list[str]) -> list[ExchangeRate]:
    """
    Fetches the latest exchange rates for target currencies against EUR.
    Raises APIError for network, API, or JSON decoding issues.
    """
    if not target_currencies:
        return []

    params = {"to": ",".join(target_currencies)}
    response = None
    try:
        response = requests.get(f"{settings.FRANKFURTER_API_BASE_URL}/latest", params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        
        data = response.json()
        
        rates = []
        api_date_str = data.get("date")
        timestamp = datetime.strptime(api_date_str, "%Y-%m-%d") if api_date_str else datetime.today()

        for currency_code, rate_value in data.get("rates", {}).items():
            if currency_code in target_currencies:
                rates.append(ExchangeRate(
                    base_currency_code="EUR",
                    target_currency_code=currency_code,
                    rate=float(rate_value),
                    timestamp=timestamp
                ))
        return rates
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error or API unavailable while fetching current rates: {e}")
        raise APIError(f"Network error or API unavailable: {e}") from e
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON response while fetching current rates: {e}. Response text: '{response.text if response else 'No response'}'")
        raise APIError(f"Invalid JSON response: {e}") from e


def fetch_historical_exchange_rate(target_currency: str, date_str: str) -> ExchangeRate | None:
    """
    Fetches the historical exchange rate for a target currency against EUR for a specific date.
    Date string should be in "YYYY-MM-DD" format.
    Raises APIError for network, API, or JSON decoding issues.
    Returns None if the specific rate is not found in a valid response.
    """
    params = {"to": target_currency}
    response = None
    try:
        response = requests.get(f"{settings.FRANKFURTER_API_BASE_URL}/{date_str}", params=params)
        response.raise_for_status() # Raises HTTPError for 4XX/5XX
        
        data = response.json()

        rates_data = data.get("rates")
        if rates_data is None or target_currency not in rates_data:
            logger.warning(f"Rate for {target_currency} not found in historical data for date {date_str}.")
            return None

        rate_value = rates_data[target_currency]
        timestamp = datetime.strptime(data.get("date", date_str), "%Y-%m-%d") # Use API date if available, else input

        return ExchangeRate(
            base_currency_code=data.get("base", "EUR"), # Use API base if available
            target_currency_code=target_currency,
            rate=float(rate_value),
            timestamp=timestamp
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error or API unavailable while fetching historical rate for {target_currency} on {date_str}: {e}")
        raise APIError(f"Network error or API unavailable: {e}") from e
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON response for {target_currency} on {date_str}: {e}. Response text: '{response.text if response else 'No response'}'")
        raise APIError(f"Invalid JSON response: {e}") from e


if __name__ == '__main__':
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    
    from currency_monitor.src.logger_config import setup_logging
    setup_logging()

    from currency_monitor.config import settings # settings is used by the functions
    from currency_monitor.src.models import ExchangeRate # ExchangeRate is used by the functions

    logger.info("--- Testing Data Fetcher with Exception Handling ---")

    # Test fetch_current_exchange_rates
    try:
        logger.info("Fetching current rates for USD, JPY, GBP:")
        current_rates = fetch_current_exchange_rates(["USD", "JPY", "GBP"])
        if current_rates:
            for rate_obj in current_rates:
                logger.info(rate_obj)
        else:
            logger.info("No current rates fetched (or all failed gracefully before this point).")
    except APIError as e:
        logger.error(f"An API error occurred (current rates): {e}")

    # Test fetch_historical_exchange_rate
    try:
        logger.info("\nFetching historical rate for USD on 2023-01-15:")
        historical_rate_usd = fetch_historical_exchange_rate("USD", "2023-01-15")
        if historical_rate_usd:
            logger.info(historical_rate_usd)
        else:
            logger.info("No historical rate fetched for USD (possibly data not found).")
    except APIError as e:
        logger.error(f"An API error occurred (historical USD): {e}")

    # Test with potentially problematic date for historical fetch (API might return error)
    try:
        logger.info("\nFetching historical rate for USD on an invalid date (e.g., 2023-13-01):")
        # The Frankfurter API actually handles "2023-13-01" by redirecting to "latest"
        # A truly bad request like a non-existent endpoint or malformed date might be better
        # For now, we'll test with a date that *should* fail validation if API was stricter,
        # or rely on raise_for_status for server errors.
        # Let's try a very old date that might return an error or empty rates
        historical_rate_invalid_date = fetch_historical_exchange_rate("USD", "1900-01-01")
        if historical_rate_invalid_date:
            logger.info(historical_rate_invalid_date)
        else:
            logger.info("No historical rate fetched for USD on 1900-01-01 (expected).")
    except APIError as e:
        logger.error(f"An API error occurred (historical invalid date): {e}")

    # Test fetch_current_exchange_rates with an empty list
    try:
        logger.info("\nFetching current rates with empty list:")
        current_rates_empty = fetch_current_exchange_rates([])
        if not current_rates_empty: # Expected to be empty list
            logger.info("No current rates fetched for empty list (as expected).")
        else:
            logger.info(f"Received unexpected data for empty list: {current_rates_empty}")
    except APIError as e:
        logger.error(f"An API error occurred (current rates empty list): {e}") # Should not happen for empty list

    # Test for a currency that might not be found in historical data
    try:
        logger.info("\nFetching historical rate for a potentially non-existent currency (XXX) on 2023-01-15:")
        historical_rate_xxx = fetch_historical_exchange_rate("XXX", "2023-01-15")
        if historical_rate_xxx is None:
            logger.info("No historical rate fetched for XXX (as expected, data not found).")
        else:
            logger.warning(f"Unexpectedly received data for XXX: {historical_rate_xxx}")
    except APIError as e:
        logger.error(f"An API error occurred (historical XXX): {e}")
        
    logger.info("\n--- Data Fetcher Tests Finished ---")
