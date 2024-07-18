import time
import os 
import sys 

import utils 

# under test 
from logger import FileLogger 

class FakeClock:
    def __init__(self, fake_time):
        self._fake_time = fake_time
    
    def time_since_epoch(self):
        return self._fake_time
    
    def advance_time(self, seconds):
        self._fake_time += seconds

class TestCase:
    
    test_dir = 'test_logs'

    def setUp(self):
        
        utils.create_dir(self.test_dir, exist_ok=False)
        FileLogger.log_dir = self.test_dir

        # Set up the fake time and clock
        fake_time = utils.date_to_timestamp('2023-07-04')
        self.fake_clock = FakeClock(fake_time)

    def test_clear_old_logs(self):
        self.old_log_file = self.test_dir + "/log_2023-07-01.txt"
        self.new_log_file = self.test_dir + "/log_2023-07-04.txt"

        with open(self.old_log_file, 'w') as f:
            f.write("Old log file content")

        with open(self.new_log_file, 'w') as f:
            f.write("New log file content")

        # Verify both files exist before clearing
        assert utils.file_exists(self.old_log_file), "Old log file does not exist."
        assert utils.file_exists(self.new_log_file), "New log file does not exist."
        
        # Run clear_old_logs to remove files older than 2 days
        FileLogger.clear_old_logs(self.fake_clock, days=2)

        # Check results
        assert not utils.file_exists(self.old_log_file), "Old log file was not removed."
        assert utils.file_exists(self.new_log_file), "New log file should not be removed."

    def test_record_log_message(self):
        # Test record_log_message creates new file on date change
        logger = FileLogger(self.fake_clock)

        # Log a message on the initial date
        initial_message = "This is a log message on the initial date."
        new_message = "This is a log message on the new date."

        logger._record_log_message(initial_message)
        initial_log_file = logger.log_file
        self. fake_clock.advance_time(24 * 3600 + 1)
        logger._record_log_message(new_message)
        new_log_file = logger.log_file

        assert utils.file_exists(initial_log_file), "Initial log file was not created."
        assert utils.file_exists(new_log_file), "New log file was not created after date change."

        # Verify the content of the initial log file
        with open(initial_log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1, f"Initial log file contains {len(lines)}."
            msg = lines[0].strip()
            assert msg == initial_message, f"Message incorrect: {msg}"

        # Verify the content of the new log file
        with open(new_log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1, f"Initial log file contains {len(lines)}."
            msg = lines[0].strip()
            assert msg == new_message, f"Message incorrect: {msg}"


    def tearDown(self):
        utils.rm_tree(self.test_dir)



def run_test(test_case, test_method):
    test_case.setUp()
    try: 
        test_method()
        print("Test passed.")
    except Exception as e:
        print(f"Test '{test_method.__name__}' failed")
        sys.print_exception(e)
    finally:
        test_case.tearDown()


test_case = TestCase()
run_test(test_case, test_case.test_clear_old_logs)
run_test(test_case, test_case.test_record_log_message)



