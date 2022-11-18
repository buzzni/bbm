from bbm.exceptions import NoJoinChannelException
from bbm.utils import get_hostname, get_ip
from datetime import datetime
from bbm.constants import KST
import requests


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


class Reporter:
    url = "https://slack.com/api/chat.postMessage"

    def __init__(self, slack_token: str, slack_channel_id: str, apply_code_block: bool = True):
        self.slack_token = slack_token
        self.slack_channel_id = slack_channel_id
        self.apply_code_block = apply_code_block
        if not self.is_token_joined_at_channel(slack_channel_id):
            raise NoJoinChannelException("Token is not joined at channel")

    def get_channel_list(self):
        url = "https://slack.com/api/conversations.list"
        headers = {
            "Authorization": f"Bearer {self.slack_token}",
            "Content-Type": "application/json",
        }
        response = requests.get(url=url, headers=headers)
        return response.json()

    def is_token_joined_at_channel(self, slack_channel_id: str):
        channel_list = self.get_channel_list()
        for channel in channel_list["channels"]:
            if channel["id"] == slack_channel_id and channel["is_member"]:
                return True
        return False

    def post_message(self, text: str):
        payload = {
            "channel": self.slack_channel_id,
            "text": f"```{text}```" if self.apply_code_block else text,
        }
        headers = {
            "Authorization": f"Bearer {self.slack_token}",
            "Content-Type": "application/json",
        }
        response = requests.post(url=self.url, headers=headers, json=payload)
        return response.json()
