import json
import sys
import time
import traceback
from datetime import datetime
from functools import wraps
from uuid import uuid4

from confluent_kafka import Producer

from bbm import Interval
from bbm.exceptions import BBMKafkaNotInitialized
from bbm.utils import get_caller_file_name, get_hostname, get_ip


class BBMKafka:
    def __init__(
        self,
        kafka_bootstrap_servers: str,
        kafka_topic: str,
        process_category: str = "batch-process",
        index_prefix: str = "batch-process-log",
    ):
        self.ip = get_ip()
        self.hostname = get_hostname()
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.process_category = process_category
        self.kafka_topic = kafka_topic
        self.index_prefix = index_prefix
        self.producer = Producer({"bootstrap.servers": kafka_bootstrap_servers})

    def produce_log(self, process: str, func: str, param: dict, level: str = "info"):
        data = {
            "index_prefix": self.index_prefix,
            "process": process,
            "func": func,
            "level": level,
            "ip": self.ip,
            "param": param,
            "host": self.hostname,
            "@timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        }
        try:
            self.producer.produce(self.kafka_topic, json.dumps(data).encode("utf-8"))
        except Exception as e:
            raise e
        finally:
            self.producer.flush()


bbm_kafka: BBMKafka = None


def get_bbm_kafka():
    global bbm_kafka
    if not bbm_kafka:
        raise BBMKafkaNotInitialized("BBM is not initialized")
    return bbm_kafka


def setup(kafka_bootstrap_servers: str, kafka_topic: str, index_prefix: str):
    global bbm_kafka
    bbm_kafka = BBMKafka(
        kafka_bootstrap_servers=kafka_bootstrap_servers, kafka_topic=kafka_topic, index_prefix=index_prefix
    )


def logging(
    process_name="",
    interval=Interval.A_HOUR,
):
    def wrapper(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            if not bbm_kafka:
                raise BBMKafkaNotInitialized("BBM Kafka Extension is not initialized")
            process = process_name or get_caller_file_name()
            process_category = bbm_kafka.process_category
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
                bbm_kafka.produce_log(
                    process=process,
                    func=func_name,
                    param=start_log_param,
                )
                result = func(*args, **kwargs)
                duration = round(time.time() - start_time, 2)
                complete_log_param["duration"] = duration
                bbm_kafka.produce_log(
                    process=process,
                    func=func_name,
                    param=complete_log_param,
                )
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                error_traceback = "\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                duration = round(time.time() - start_time, 2)
                bbm_kafka.produce_log(
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
                raise e
            return result

        return decorator

    return wrapper
