import logging
import sys
import os # Added for log file path management

def setup_logging(log_file='currency_monitor.log', console_level=logging.INFO, file_level=logging.DEBUG):
    """Configures logging to file and console."""
    
    # Determine the project root directory to place the log file there
    # Assuming this file (logger_config.py) is in currency_monitor/src/
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    log_file_path = os.path.join(project_root, log_file)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG) # Set root logger level to the lowest (DEBUG) to capture all messages

    # Prevent multiple handlers if setup_logging is called more than once (e.g., in tests)
    # This is a common pattern to avoid duplicate log entries if the setup function is inadvertently called multiple times.
    if logger.hasHandlers():
        # Check if handlers are already configured for our specific file and console streams
        # to avoid clearing handlers set up by other parts of an application (e.g. test runners)
        # This simple clear is fine for this project's scope.
        logger.handlers.clear()

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create a file handler
    try:
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # Fallback to console logging if file handler fails (e.g., permission issues)
        print(f"Error setting up file handler for logging: {e}. Logging to console only.", file=sys.stderr)


    # Create a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Return the configured root logger (optional, can also just import logging and use getLogger directly elsewhere)
    return logger

# Example of how to get a logger in other modules:
# import logging
# logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Example usage:
    # Initialize logging (this will create 'currency_monitor.log' in the project root)
    root_logger = setup_logging()
    
    # Get a logger for this specific module
    module_logger = logging.getLogger(__name__) # or logging.getLogger("my_app.logger_config_example")

    root_logger.info("This is an info message from the root logger (will go to console and file).")
    module_logger.debug("This is a debug message from the module logger (will go to file only by default).")
    module_logger.warning("This is a warning message from the module logger (will go to console and file).")
    
    # Example of getting another logger as if from another module
    other_module_logger = logging.getLogger("another.module")
    other_module_logger.error("This is an error from another.module (console and file).")

    print(f"Logging configured. Check console output and the log file: {os.path.abspath('currency_monitor.log')}")
