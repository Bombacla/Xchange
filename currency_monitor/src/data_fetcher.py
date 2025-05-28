import requests
from datetime import datetime
from currency_monitor.src.models import ExchangeRate
from currency_monitor.config import settings

def fetch_current_exchange_rates(target_currencies: list[str]) -> list[ExchangeRate]:
    """
    Fetches the latest exchange rates for target currencies against EUR.
    """
    if not target_currencies:
        return []

    params = {"to": ",".join(target_currencies)}
    try:
        response = requests.get(f"{settings.FRANKFURTER_API_BASE_URL}/latest", params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        data = response.json()
        
        rates = []
        api_date_str = data.get("date")
        # Ensure the timestamp is a datetime object. Frankfurter API 'latest' endpoint returns just a date.
        # We'll use the beginning of the day for the timestamp.
        timestamp = datetime.strptime(api_date_str, "%Y-%m-%d") if api_date_str else datetime.today()

        for currency_code, rate_value in data.get("rates", {}).items():
            if currency_code in target_currencies: # Ensure we only process requested currencies
                rates.append(ExchangeRate(
                    base_currency_code="EUR",  # API default base is EUR
                    target_currency_code=currency_code,
                    rate=float(rate_value),
                    timestamp=timestamp
                ))
        return rates
    except requests.exceptions.RequestException as e:
        print(f"Error fetching current exchange rates: {e}")
        return []
    except ValueError as e: # Handles JSON decoding errors
        print(f"Error decoding JSON response: {e}")
        return []

def fetch_historical_exchange_rate(target_currency: str, date_str: str) -> ExchangeRate | None:
    """
    Fetches the historical exchange rate for a target currency against EUR for a specific date.
    Date string should be in "YYYY-MM-DD" format.
    """
    params = {"to": target_currency}
    try:
        response = requests.get(f"{settings.FRANKFURTER_API_BASE_URL}/{date_str}", params=params)
        response.raise_for_status()
        data = response.json()

        rate_value = data.get("rates", {}).get(target_currency)
        
        if rate_value is None:
            # This case might happen if the API doesn't have data for that currency on that day,
            # or if the target_currency was not correctly returned in the 'rates' dictionary.
            print(f"Rate for {target_currency} not found in response for date {date_str}.")
            return None

        # Convert the input date_str to a datetime object for the timestamp
        timestamp = datetime.strptime(date_str, "%Y-%m-%d")

        return ExchangeRate(
            base_currency_code="EUR", # API default base is EUR for historical rates too unless 'from' is specified
            target_currency_code=target_currency,
            rate=float(rate_value),
            timestamp=timestamp
        )
    except requests.exceptions.RequestException as e:
        print(f"Error fetching historical exchange rate for {target_currency} on {date_str}: {e}")
        return None
    except ValueError as e: # Handles JSON decoding errors or date parsing errors
        print(f"Error processing data for {target_currency} on {date_str}: {e}")
        return None

if __name__ == '__main__':
    import sys
    import os
    # Add the project root to sys.path to allow direct execution of this script with project imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    # Re-import with the new path.
    # These re-imports are needed because the script is being run directly,
    # and the original imports at the top of the file might have failed
    # if currency_monitor was not yet in sys.path.
    from currency_monitor.config import settings
    from currency_monitor.src.models import ExchangeRate

    # Example Usage
    print("Fetching current rates for USD and JPY:")
    current_rates = fetch_current_exchange_rates(["USD", "JPY", "GBP"])
    if current_rates:
        for rate_obj in current_rates:
            print(rate_obj)
    else:
        print("No current rates fetched.")

    print("\nFetching historical rate for USD on 2023-01-15:")
    historical_rate_usd = fetch_historical_exchange_rate("USD", "2023-01-15")
    if historical_rate_usd:
        print(historical_rate_usd)
    else:
        print("No historical rate fetched for USD.")
    
    print("\nFetching historical rate for CAD on 2022-05-20:")
    historical_rate_cad = fetch_historical_exchange_rate("CAD", "2022-05-20")
    if historical_rate_cad:
        print(historical_rate_cad)
    else:
        print("No historical rate fetched for CAD.")

    print("\nFetching current rates for an invalid currency (should be handled by API or gracefully):")
    current_rates_invalid = fetch_current_exchange_rates(["XYZ"])
    if current_rates_invalid:
        for rate_obj in current_rates_invalid:
            print(rate_obj)
    else:
        print("No current rates fetched for XYZ (as expected or API handled).")

    print("\nFetching historical rate for non-existent date (should fail):")
    historical_rate_non_existent_date = fetch_historical_exchange_rate("USD", "2023-13-01") # Invalid date
    if historical_rate_non_existent_date:
        print(historical_rate_non_existent_date)
    else:
        print("Failed to fetch historical rate for non-existent date (as expected).")

    print("\nFetching current rates with empty list:")
    current_rates_empty = fetch_current_exchange_rates([])
    if not current_rates_empty:
        print("No current rates fetched for empty list (as expected).")

    print("\nFetching historical rate for a currency that might not exist on a specific date:")
    historical_rate_specific = fetch_historical_exchange_rate("TRY", "2000-01-01") # Turkish Lira on an old date
    if historical_rate_specific:
        print(historical_rate_specific)
    else:
        print("No historical rate fetched for TRY on 2000-01-01 (possibly no data).")
