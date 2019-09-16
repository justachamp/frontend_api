import copy
import errno
import logging
import os
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler

import arrow
from pythonjsonlogger import jsonlogger

from customate.settings import GENERAL_APP_NAME

"""
https://docs.python.org/3/howto/logging-cookbook.html#context-info
Python's cookbook suggests to use LoggerAdapters to impart contextual information, but this information is attached to 
individual logger. Some disadvantages:
 - we can pass extra parameters only during LoggerAdapter creation, it cuts down the possible list of parameters
 - errors/exceptions from not-our application (django, GBG client and other external apis) will not include extra
   information that was specified in LoggerAdapter
 - if we would like to keep separate applications (authentication, external_apis, frontend_api, payment_api) in logger  
   settings (apps could require different log level), then it will be required to create separate adapters for each 
   logger instance (with the same extra parameters)


As opposite to LoggerAdapter we will use "shared resource" (something similar to "Mapped Diagnostic Context", the concept  
that was taken from Java), it should allow us to add (just once, for all loggers) some contextual information to our  
logging output. For example, we can set unique requestId in middleware (before processing the request) and all loggers  
will output log information that will contain requestId as extra-parameter. Some links:
https://logback.qos.ch/manual/mdc.html
https://gist.github.com/mdaniel/8347533

Use examples:
logger.info("Started schedule processing", extra={'scheduleId': schedule.id})

will produce:
{
  "message": "Started schedule processing",
  "data": {
    "scheduleId": "78e6cce6-7fb7-412c-9401-4b10593e9017"
  },
  "requestId": "cc23f0d2-cc73-435d-ad43-34d787265530",
  "customer": {
    "userId": "c8df3b60-0c90-41b2-80c6-2521d850c392",
    "accountId": "65717684-0101-4800-8dcd-d14d11d6ea11"
  },
  "dateCreated": "2019-09-12T14:28:32.482646",
  "logLevel": "INFO",
  "duration": 292,
  "app": {
    "name": "frontend_api",
    "threadName": "Thread-2"
  }
}
"""
logging._shared_extra = threading.local()


class CustomateLogger(logging.Logger):
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
        if extra is not None:
            # Based on required format we need to make sure that any extra information is placed in "data" section.
            extra = {'data': extra}

        return super(CustomateLogger, self).makeRecord(name, level, fn, lno, msg, args, exc_info, func, extra, sinfo)


class BetterRotatingFileHandler(RotatingFileHandler):
    def _open(self):
        self._ensure_dir(os.path.dirname(self.baseFilename))
        return logging.handlers.RotatingFileHandler._open(self)

    def _ensure_dir(self, path):
        # type: (AnyStr) -> None
        """os.path.makedirs without EEXIST."""
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise


class CustomateJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomateJsonFormatter, self).add_fields(log_record, record, message_dict)

        # Map all shared_extra params to root level
        # @NOTE: we cannot map shared_extra in CustomateLogger, because not all loggers are CustomateLogger,
        # so there is a risk to lost this information in log record
        shared_extra = logging.get_shared_extra()
        if len(shared_extra) > 0:
            current_data = log_record.get('data', {})
            shared_extra = copy.deepcopy(shared_extra)
            shared_extra = {**shared_extra, **current_data}
            log_record.update(shared_extra)

        if not log_record.get('dateCreated'):
            now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')
            log_record['dateCreated'] = now

        if log_record.get('logLevel'):
            log_record['logLevel'] = log_record['level'].upper()
        else:
            log_record['logLevel'] = record.levelname

        if log_record.get('startProcessing') and not log_record.get('duration'):
            log_record['duration'] = int((arrow.utcnow() - log_record.get('startProcessing')).microseconds / 1000)
            del(log_record['startProcessing'])

        log_record['app'] = {
            'name': GENERAL_APP_NAME,
            "threadName": record.threadName
        }

        self._move_unexpected_params_to_data(log_record)

    # We move some unexpected parameters (like request, status_code, exc_info, stack_info) to "data" section
    def _move_unexpected_params_to_data(self, log_record):
        top_level_attributes = ['dateCreated', 'logLevel', 'duration', 'message', 'requestId', 'customer', 'app', 'data']
        for key, _ in log_record.copy().items():
            if key not in top_level_attributes:
                if not log_record.get('data'):
                    log_record['data'] = {}

                log_record['data'][key] = log_record.get(key)
                del(log_record[key])


def set_shared_extra(attributes: dict):
    for key, value in attributes.items():
        setattr(logging._shared_extra, key, value)


logging.set_shared_extra = set_shared_extra
del set_shared_extra


def get_shared_extra() -> dict:
    results = {}
    for x in dir(logging._shared_extra):
        if x.startswith('__'):
            continue
        results[x] = getattr(logging._shared_extra, x)

    return results


logging.get_shared_extra = get_shared_extra
del get_shared_extra


def get_shared_extra_param(key: str):
    return logging.get_shared_extra().get(key, None)


logging.get_shared_extra_param = get_shared_extra_param
del get_shared_extra_param
