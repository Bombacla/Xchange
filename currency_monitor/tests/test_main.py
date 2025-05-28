import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
import logging # For checking logging levels

# Adjust sys.path to ensure project modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from currency_monitor.src.main import main as actual_main_function
from currency_monitor.src.models import AlertCondition
# No need to import main_module specifically if we're patching its attributes directly via their full path

class TestMainArgParsing(unittest.TestCase):

    @patch('currency_monitor.src.main.setup_logging')
    @patch('currency_monitor.src.main.check_currency_drops')
    @patch('sys.argv', ['main.py', '--condition', 'USD', '5', '30'])
    def test_single_condition_arg_success(self, mock_check_currency_drops, mock_setup_logging):
        actual_main_function()
        
        mock_setup_logging.assert_called_once() # Basic check that logging was set up
        mock_check_currency_drops.assert_called_once()
        
        # Inspect the AlertCondition objects passed to mock_check_currency_drops
        args_list = mock_check_currency_drops.call_args[0][0]
        self.assertEqual(len(args_list), 1)
        self.assertIsInstance(args_list[0], AlertCondition)
        self.assertEqual(args_list[0].target_currency_code, 'USD')
        self.assertEqual(args_list[0].percentage_drop_threshold, 5.0)
        self.assertEqual(args_list[0].time_period_days, 30)

    @patch('currency_monitor.src.main.setup_logging')
    @patch('currency_monitor.src.main.check_currency_drops')
    @patch('sys.argv', ['main.py', '--condition', 'USD', '5', '30', '--condition', 'GBP', '2.5', '14'])
    def test_multiple_conditions_arg_success(self, mock_check_currency_drops, mock_setup_logging):
        actual_main_function()

        mock_setup_logging.assert_called_once()
        mock_check_currency_drops.assert_called_once()
        
        args_list = mock_check_currency_drops.call_args[0][0]
        self.assertEqual(len(args_list), 2)
        self.assertIsInstance(args_list[0], AlertCondition)
        self.assertEqual(args_list[0].target_currency_code, 'USD')
        self.assertEqual(args_list[0].percentage_drop_threshold, 5.0)
        self.assertEqual(args_list[0].time_period_days, 30)
        
        self.assertIsInstance(args_list[1], AlertCondition)
        self.assertEqual(args_list[1].target_currency_code, 'GBP')
        self.assertEqual(args_list[1].percentage_drop_threshold, 2.5)
        self.assertEqual(args_list[1].time_period_days, 14)

    @patch('currency_monitor.src.main.logger') # Patching the logger instance in main.py
    @patch('currency_monitor.src.main.setup_logging')
    @patch('currency_monitor.src.main.check_currency_drops')
    @patch('sys.argv', ['main.py', '--condition', 'USD', 'five', '30'])
    def test_invalid_condition_arg_percentage_format(self, mock_check_currency_drops, mock_setup_logging, mock_logger):
        with self.assertRaises(SystemExit) as cm:
            with patch('sys.exit') as mock_exit:
                mock_exit.side_effect = SystemExit # Make the mock raise SystemExit
                actual_main_function()
        
        self.assertEqual(cm.exception.code, 1) # Check the exit code
        
        # Check that a warning was logged for the invalid number format
        found_warning = False
        for call_obj in mock_logger.warning.call_args_list:
            if "Invalid number format for percentage ('five')" in call_obj[0][0]:
                found_warning = True
                break
        self.assertTrue(found_warning, "Expected warning about invalid number format was not logged.")
        
        # Also check that an error was logged because no valid conditions were processed
        found_error = False
        for call_obj in mock_logger.error.call_args_list:
             if "No valid alert conditions could be processed" in call_obj[0][0]:
                found_error = True
                break
        self.assertTrue(found_error, "Expected error about no valid conditions processed was not logged.")

        mock_check_currency_drops.assert_not_called()

    @patch('currency_monitor.src.main.logger.error') # Patching the error method of the logger
    @patch('currency_monitor.src.main.setup_logging')
    @patch('currency_monitor.src.main.check_currency_drops')
    @patch('sys.argv', ['main.py']) # No conditions
    def test_no_condition_args_exits(self, mock_check_currency_drops, mock_setup_logging, mock_logger_error):
        with self.assertRaises(SystemExit) as cm:
            with patch('sys.exit') as mock_exit:
                mock_exit.side_effect = SystemExit # Make the mock raise SystemExit
                with patch('argparse.ArgumentParser.print_help') as mock_print_help: # Also mock print_help
                    actual_main_function()
        
        self.assertEqual(cm.exception.code, 1)
        mock_logger_error.assert_called_once_with("No alert conditions provided. Use the --condition argument to specify at least one.")
        mock_print_help.assert_called_once() # Ensure help was printed
        mock_check_currency_drops.assert_not_called()

    @patch('currency_monitor.src.main.setup_logging')
    @patch('currency_monitor.src.main.check_currency_drops')
    @patch('sys.argv', ['main.py', '--condition', 'USD', '5', '30', '-v'])
    def test_verbosity_argument_info(self, mock_check_currency_drops, mock_setup_logging):
        actual_main_function()
        
        # Assert mock_setup_logging was called with console_level=logging.INFO
        # call_args is a tuple ((pos_args), {kw_args})
        # We need to check the keyword arguments passed to setup_logging
        self.assertEqual(mock_setup_logging.call_args[1]['console_level'], logging.INFO)
        mock_check_currency_drops.assert_called_once() # Ensure it still runs the main logic

    @patch('currency_monitor.src.main.setup_logging')
    @patch('currency_monitor.src.main.check_currency_drops')
    @patch('sys.argv', ['main.py', '--condition', 'USD', '5', '30', '-vv'])
    def test_verbosity_argument_debug(self, mock_check_currency_drops, mock_setup_logging):
        actual_main_function()
        
        self.assertEqual(mock_setup_logging.call_args[1]['console_level'], logging.DEBUG)
        mock_check_currency_drops.assert_called_once()

    @patch('currency_monitor.src.main.logger')
    @patch('currency_monitor.src.main.setup_logging')
    @patch('currency_monitor.src.main.check_currency_drops')
    @patch('sys.argv', ['main.py', '--condition', 'US', '5', '30']) # Invalid currency code length
    def test_invalid_condition_arg_currency_code_format(self, mock_check_currency_drops, mock_setup_logging, mock_logger):
        with self.assertRaises(SystemExit) as cm:
            with patch('sys.exit') as mock_exit:
                mock_exit.side_effect = SystemExit
                actual_main_function()
        
        self.assertEqual(cm.exception.code, 1)
        found_warning = False
        for call_obj in mock_logger.warning.call_args_list:
            if "Invalid currency code 'US'" in call_obj[0][0]:
                found_warning = True
                break
        self.assertTrue(found_warning, "Expected warning about invalid currency code format was not logged.")
        mock_check_currency_drops.assert_not_called()

    @patch('currency_monitor.src.main.logger')
    @patch('currency_monitor.src.main.setup_logging')
    @patch('currency_monitor.src.main.check_currency_drops')
    @patch('sys.argv', ['main.py', '--condition', 'USD', '101', '30']) # Invalid percentage
    def test_invalid_condition_arg_percentage_value(self, mock_check_currency_drops, mock_setup_logging, mock_logger):
        with self.assertRaises(SystemExit) as cm:
            with patch('sys.exit') as mock_exit:
                mock_exit.side_effect = SystemExit
                actual_main_function()

        self.assertEqual(cm.exception.code, 1)
        found_warning = False
        for call_obj in mock_logger.warning.call_args_list:
            if "Invalid percentage drop '101.0'" in call_obj[0][0]:
                found_warning = True
                break
        self.assertTrue(found_warning, "Expected warning about invalid percentage value was not logged.")
        mock_check_currency_drops.assert_not_called()

    @patch('currency_monitor.src.main.logger')
    @patch('currency_monitor.src.main.setup_logging')
    @patch('currency_monitor.src.main.check_currency_drops')
    @patch('sys.argv', ['main.py', '--condition', 'USD', '5', '-10']) # Invalid days
    def test_invalid_condition_arg_days_value(self, mock_check_currency_drops, mock_setup_logging, mock_logger):
        with self.assertRaises(SystemExit) as cm:
            with patch('sys.exit') as mock_exit:
                mock_exit.side_effect = SystemExit
                actual_main_function()

        self.assertEqual(cm.exception.code, 1)
        found_warning = False
        for call_obj in mock_logger.warning.call_args_list:
            if "Invalid time period '-10'" in call_obj[0][0]:
                found_warning = True
                break
        self.assertTrue(found_warning, "Expected warning about invalid days value was not logged.")
        mock_check_currency_drops.assert_not_called()

if __name__ == '__main__':
    unittest.main()
