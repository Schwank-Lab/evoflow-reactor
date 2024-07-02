import unittest
import time
import os
import shutil
from logger import FileLogger

class FakeClock:
    def __init__(self, fake_time):
        self._fake_time = fake_time
    
    def time_since_epoch(self):
        return self._fake_time
    
    def advance_time(self, seconds):
        self._fake_time += seconds

class TestFileLogger(unittest.TestCase):

    def setUp(self):
        self.test_dir = 'test_logs/'
        if not os.path.exists(self.test_dir):
            os.mkdir(self.test_dir)
        FileLogger.log_dir = self.test_dir
        self.fake_time = int(time.time())
        self.fake_clock = FakeClock(self.fake_time)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_clear_old_logs(self):
        # Create log files with different timestamps
        old_timestamp = self.fake_time - 3 * 24 * 3600  # 3 days old
        new_timestamp = self.fake_time - 1 * 24 * 3600  # 1 day old
        
        old_log_file = os.path.join(self.test_dir, f"log_2023-07-01_{old_timestamp}.txt")
        new_log_file = os.path.join(self.test_dir, f"log_2023-07-03_{new_timestamp}.txt")
        
        with open(old_log_file, 'w') as f:
            f.write("Old log file content.")
        
        with open(new_log_file, 'w') as f:
            f.write("New log file content.")
        
        # Assert both files exist before clearing
        self.assertTrue(os.path.exists(old_log_file))
        self.assertTrue(os.path.exists(new_log_file))
        
        # Run clear_old_logs to remove files older than 2 days
        FileLogger.clear_old_logs(self.fake_clock, days=2)
        
        # Check results
        self.assertFalse(os.path.exists(old_log_file), "Old log file was not removed.")
        self.assertTrue(os.path.exists(new_log_file), "New log file should not be removed.")

    def test_record_log_message_creates_new_file_on_date_change(self):
        # Create an instance of FileLogger
        logger = FileLogger(self.fake_clock)
        
        # Log a message on the initial date
        initial_message = "This is a log message on the initial date."
        new_message = "This is a log message on the new date."
        
        logger._record_log_message(initial_message)
        initial_log_file = logger.log_file
        self.fake_clock.advance_time(24 * 3600 + 1)
        logger._record_log_message(new_message)
        new_log_file = logger.log_file
        
        self.assertTrue(os.path.exists(initial_log_file), "Initial log file was not created.")
        self.assertTrue(os.path.exists(new_log_file), "New log file was not created after date change.")
        
        # Verify the content of the initial log file
        with open(initial_log_file, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1, "Initial log file does not contain exactly one log message.")
            self.assertEqual(lines[0].strip(), initial_message, "Initial log message content is incorrect.")
        
        # Verify the content of the new log file
        with open(new_log_file, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1, "New log file does not contain exactly one log message.")
            self.assertEqual(lines[0].strip(), new_message, "New log message content is incorrect.")

if __name__ == '__main__':
    unittest.main()