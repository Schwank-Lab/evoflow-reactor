import os
import json 
import time
import sys

import utils

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
    
    def exception(self, msg, e):
        import uio
        buf = uio.StringIO()
        sys.print_exception(e, buf)
        self.critical(msg, '\n', buf.getvalue())

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
    

class SerialLogger(Logger):

    def __init__(self, clock, serial, level=L_INFO):
        super().__init__(clock, level)
        self._serial = serial 
    
    def _record_log_message(self, message):
        try: 
            self._serial.send_message('logs', message)
        except Exception as ex:
            print('exception occured')


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
