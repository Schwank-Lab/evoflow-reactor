import os

L_DEBUG = 1
L_INFO = 2
L_CRITICAL = 3

class Logger:
    _instance = None
    log_dir = 'logs/'

    @classmethod
    def create_instance(cls, clock):
        """Create the Logger instance with a specific clock."""
        if not cls._instance:
            cls._instance = Logger(clock)
        return cls._instance

    @classmethod
    def get_instance(cls):
        """Retrieve the existing Logger instance."""
        if not cls._instance:
            raise Exception("Logger instance not created yet. Call create_instance first.")
        return cls._instance

    def __init__(self, clock):
        if not hasattr(self, 'initialized'):  # Prevent reinitialization
            self.initialized = True
            self.level = L_INFO
            self.clock = clock
            self._create_log_file()

    def _create_log_file(self):
        try:
            os.mkdir(Logger.log_dir)
        except OSError:
            # Assume the directory exists
            pass
        # Simplified timestamp using epoch seconds
        timestamp = self.clock.time_since_epoch()
        self.log_file = Logger.log_dir + "log_" + str(timestamp) + ".txt"
        
    def log(self, level, *args):
        if level >= self.level:
            level_name = self._get_level_name(level)
            timestamp = self.clock.localtime()
            message = "[{}] [{}] {}".format(timestamp, level_name, ' '.join(map(str, args)))
            with open(self.log_file, 'a') as f:
                f.write(message + '\n')

    def debug(self, *args):
        self.log(L_DEBUG, *args)

    def info(self, *args):
        self.log(L_INFO, *args)

    def critical(self, *args):
        self.log(L_CRITICAL, *args)

    def _get_level_name(self, level):
        if level == L_DEBUG:
            return "DEBUG"
        elif level == L_INFO:
            return "INFO"
        elif level == L_CRITICAL:
            return "CRITICAL"
        else:
            return "UNKNOWN"

    @staticmethod
    def clear_old_logs(clock, days=2):
        for filename in os.listdir(Logger.log_dir):
            file_path = os.path.join(Logger.log_dir, filename)
            # Use file creation time for comparison (not available in MicroPython, so using a workaround)
            try:
                # Workaround: Assume file name contains creation timestamp
                file_timestamp = int(filename.split('_')[1].split('.')[0])
                if (clock.time_since_epoch() - file_timestamp) > (days * 24 * 3600):
                    os.remove(file_path)
            except ValueError:
                # Filename does not contain a valid timestamp; ignore
                pass
