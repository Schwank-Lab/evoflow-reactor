import os

L_DEBUG = 1
L_INFO = 2
L_CRITICAL = 3


class Logger: 

    def __init__(self, clock, level=L_INFO):
        self.level = level
        self.clock = clock
  
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
        
    def log(self, level, *args):
        if level >= self.level:
            level_name = self._get_level_name(level)
            timestamp = self.clock.localtime()
            message = "[{}] [{}] {}".format(timestamp, level_name, ' '.join(map(str, args)))
            self._record_log_message(message)

    def _record_log_message(self, message):
        raise NotImplementedError()
    

class FileLogger(Logger):
    log_dir = 'logs/'

    def __init__(self, clock, level=L_INFO):
        super().__init__(clock, level)
        self._create_log_file()

    def _create_log_file(self):
        try:
            os.mkdir(FileLogger.log_dir)
        except OSError:
            # Assume the directory exists
            pass
        # Simplified timestamp using epoch seconds
        timestamp = self.clock.time_since_epoch()
        self.log_file = FileLogger.log_dir + "log_" + str(timestamp) + ".txt"
        
  
    def _record_log_message(self, message):
        with open(self.log_file, 'a') as f:
                f.write(message + '\n')

    @staticmethod
    def clear_old_logs(clock, days=2):
        for filename in os.listdir(FileLogger.log_dir):
            file_path = os.path.join(FileLogger.log_dir, filename)
            # Use file creation time for comparison (not available in MicroPython, so using a workaround)
            try:
                # Workaround: Assume file name contains creation timestamp
                file_timestamp = int(filename.split('_')[1].split('.')[0])
                if (clock.time_since_epoch() - file_timestamp) > (days * 24 * 3600):
                    os.remove(file_path)
            except ValueError:
                # Filename does not contain a valid timestamp; ignore
                pass

class MqttLogger(Logger): 

    TOPIC_LOG = 'log'
    
    def __init__(self, mqtt_client, clock, level=L_INFO):
        super().__init__(clock, level)
        self.mqtt_client = mqtt_client

    def _record_log_message(self, message):
        self.mqtt_client.publish(MqttLogger.TOPIC_LOG, message)


class ConsoleLogger(Logger): 

    def __init__(self, clock, level=L_INFO):
        super().__init__(clock, level)

    def _record_log_message(self, message):
        print(message)


class CompositeLogger(Logger): 

    def __init__(self, loggers):
        self.loggers = loggers

    def log(self, level, *args):
        for logger in self.loggers:
            logger.log(level, *args)
            
