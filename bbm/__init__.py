import sys
import time
import traceback
from datetime import datetime
from functools import wraps
from uuid import uuid4

import requests

from bbm.constants import KST, Interval
from bbm.exceptions import BBMNotInitialized, NoJoinChannelException, ReporterNotInitialized
from bbm.utils import create_report, get_caller_file_name, get_hostname, get_ip

# package info
__version__ = "0.0.4"


class BBM:
    def __init__(
        self,
        es_url: str,
        process_category: str = "fission-tasks",
        index_prefix: str = "batch-process-log",
        ignore_process_list=None,
    ):
        self.ip = get_ip()
        self.hostname = get_hostname()
        self.es_url = es_url
        self.process_category = process_category
        self.index_prefix = index_prefix if index_prefix.endswith("-") else f"{index_prefix}-"
        self.ignore_process_list = ignore_process_list if ignore_process_list else []

    def post_log(
        self,
        process: str,
        func: str,
        param: dict,
        level: str = "info",
    ):
        now_kst = datetime.now(tz=KST)
        get_date_to_index = now_kst.strftime("%Y.%m.%d")
        index = f"{self.index_prefix}{get_date_to_index}"
        datetime_to_write_at_es = now_kst.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
        write_dict = {
            "process": process,
            "func": func,
            "level": level,
            "ip": self.ip,
            "param": param,
            "host": self.hostname,
            "@timestamp": datetime_to_write_at_es,
        }
        try:
            return requests.post(f"{self.es_url}/{index}/_doc", json=write_dict)
        except Exception as e:
            raise e


bbm: BBM = None


def get_bbm():
    global bbm
    if not bbm:
        raise BBMNotInitialized("BBM is not initialized")
    return bbm


def setup(es_url: str, process_category: str = "", index_prefix: str = "batch-process-log"):
    global bbm
    bbm = BBM(es_url=es_url, process_category=process_category, index_prefix=index_prefix)


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
