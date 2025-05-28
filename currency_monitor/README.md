# Currency Exchange Rate Monitor

This tool monitors global currency exchange rates and alerts the user if a specified currency has dropped in value by a predefined percentage against the Euro (EUR) over a defined period.

## Features (Work in Progress)

*   Fetches latest and historical exchange rates from the Frankfurter.app API.
*   Compares current rates to historical rates to identify significant drops.
*   Basic Command-Line Interface (CLI) to display alerts.

## Project Structure

*   `src/`: Contains the main application logic.
    *   `models.py`: Defines core data structures (Currency, ExchangeRate, AlertCondition).
    *   `config/settings.py`: Stores configuration like API URLs.
    *   `data_fetcher.py`: Handles fetching data from the exchange rate API.
    *   `core_logic.py`: Implements the logic for checking currency drops against alert conditions.
    *   `main.py`: The main entry point for the CLI application.
*   `tests/`: Contains unit tests for the application.
*   `data/`: (Currently unused, intended for potential local data storage).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://your-git-repository-url-here/currency_monitor.git
    ```
    **Note:** The URL above is a placeholder. Replace `https://your-git-repository-url-here/currency_monitor.git` with the actual URL of your Git repository.
    ```bash
    cd currency_monitor
    ```

2.  **Install dependencies:**
    This project uses the `requests` library to fetch data from the API.
    It's recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install requests
    ```

## How to Run

The main entry point for the application is `src/main.py`. This script currently uses a predefined set of alert conditions.

1.  **Ensure you have completed the setup steps (cloning and installing dependencies).**

2.  **Run the application from the project's root directory (`currency_monitor/`):**
    ```bash
    python src/main.py
    ```
    Or, navigate into the `src` directory and run:
    ```bash
    python main.py
    ```

    The application will then print out any currency drop alerts that meet the predefined criteria.

## Running Tests

Unit tests are located in the `tests/` directory. To run the tests, navigate to the project's root directory (`currency_monitor/`) and run:

```bash
python -m unittest discover tests
```

This will discover and run all tests in the `tests` directory.

## Logging

The application logs important events, warnings, and errors to a file named `currency_monitor.log`, located in the root directory of the project. Logs are also output to the console.
The log file can be useful for monitoring the application's activity and for troubleshooting any issues that may arise.
The default logging levels are INFO for console output and DEBUG for file output.

## Future Enhancements (Planned)

*   Allow users to define alert conditions via CLI arguments or a configuration file.
*   More sophisticated error logging.
*   Option for email or other notification methods.
*   Web interface.
```
