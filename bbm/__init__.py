import inspect
import os
import sys
import time
import traceback
from functools import wraps
from uuid import uuid4

from bbm.constants import KST, Interval
from bbm.exceptions import BBMNotInitialized, ReporterNotInitialized
from bbm.implements import BBM, Reporter

# package info
__version__ = "0.0.4"


reporter: Reporter = None
bbm: BBM = None


def get_reporter():
    global reporter
    if not reporter:
        raise ReporterNotInitialized("Reporter is not initialized")
    return reporter


def get_bbm():
    global bbm
    if not bbm:
        raise BBMNotInitialized("BBM is not initialized")
    return bbm


def setup_logging(es_url: str, process_category: str = "", index_prefix: str = "batch-process-log"):
    global bbm
    bbm = BBM(es_url=es_url, process_category=process_category, index_prefix=index_prefix)


def setup_reporter(slack_token: str, slack_channel_id: str, apply_code_block: bool = True):
    global reporter
    reporter = Reporter(slack_token=slack_token, slack_channel_id=slack_channel_id, apply_code_block=apply_code_block)


def get_caller_file_name():
    frame = inspect.stack()[2]
    module = inspect.getmodule(frame[0])
    filename = module.__file__
    return os.path.basename(filename)


def logging(
    process_name="",
    interval=Interval.A_HOUR,
):
    def wrapper(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            if not bbm:
                raise BBMNotInitialized("BBM is not initialized")
            process = process_name or get_caller_file_name()
            process_category = bbm.process_category
            func_name = func.__name__
            process_uuid = str(uuid4())
            result = None
            start_time = time.time()
            start_log_param = {
                "msg": "start",
                "cate": process_category,
                "interval": interval,
                "process_uuid": process_uuid,
            }
            complete_log_param = {
                "msg": "complete",
                "cate": process_category,
                "process_uuid": process_uuid,
            }
            try:
                bbm.post_log(
                    process=process,
                    func=func_name,
                    param=start_log_param,
                )
                result = func(*args, **kwargs)
                duration = round(time.time() - start_time, 2)
                complete_log_param["duration"] = duration
                bbm.post_log(
                    process=process,
                    func=func_name,
                    param=complete_log_param,
                )
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                error_traceback = "\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                duration = round(time.time() - start_time, 2)
                bbm.post_log(
                    process=process,
                    func=func_name,
                    level="error",
                    param={
                        "msg": "fail",
                        "cate": process_category,
                        "process_uuid": process_uuid,
                        "duration": duration,
                        "error_traceback": error_traceback,
                    },
                )
            return result

        return decorator

    return wrapper
