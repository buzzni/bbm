import requests

from bbm.exceptions import NoJoinChannelException
from bbm.utils import create_report, get_file_content
from datetime import datetime


class Reporter:
    SLACK_API_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
    SLACK_API_CONVERSATIONS_LIST_URL = "https://slack.com/api/conversations.list"
    SLACK_API_FILE_UPLOAD_URL = "https://slack.com/api/files.upload"

    def __init__(self, slack_token: str, slack_channel_id: str):
        self.slack_token = slack_token
        self.slack_channel_id = slack_channel_id
        if not self.is_token_joined_at_channel(slack_channel_id):
            raise NoJoinChannelException("Token is not joined at channel")

    def get_channel_list(self):
        headers = {
            "Authorization": f"Bearer {self.slack_token}",
            "Content-Type": "application/json",
        }
        response = requests.get(url=self.SLACK_API_CONVERSATIONS_LIST_URL, headers=headers)
        found_joined_channels = []
        for channel in response.json()["channels"]:
            if channel["is_member"]:
                found_joined_channels.append(channel)
        if response.json().get("response_metadata") and response.json()["response_metadata"]["next_cursor"]:
            next_cursor = response.json()["response_metadata"]["next_cursor"]
            while next_cursor:
                response = requests.get(
                    url=self.SLACK_API_CONVERSATIONS_LIST_URL, headers=headers, params={"cursor": next_cursor}
                )
                for channel in response.json()["channels"]:
                    if channel["is_member"]:
                        found_joined_channels.append(channel)
                next_cursor = response.json()["response_metadata"]["next_cursor"]
            return found_joined_channels
        else:
            return found_joined_channels

    def is_token_joined_at_channel(self, slack_channel_id: str):
        channel_list = self.get_channel_list()
        for channel in channel_list:
            if channel["id"] == slack_channel_id and channel["is_member"]:
                return True
        return False

    def post_message(self, title: str, text: str, ts: str = None):
        send_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"*{title}*"
        content += f"```{text}```\n"
        content += f"\n{send_datetime}"
        payload = {
            "channel": self.slack_channel_id,
            "text": content,
        }
        if ts:
            payload["thread_ts"] = ts
        headers = {
            "Authorization": f"Bearer {self.slack_token}",
            "Content-Type": "application/json",
        }
        response = requests.post(url=self.SLACK_API_POST_MESSAGE_URL, headers=headers, json=payload)
        return response.json()

    def post_message_with_file(self, file_path: str, file_name: str, ts: str = None):
        file_content = get_file_content(file_path)
        payload = {
            "token": self.slack_token,
            "channels": self.slack_channel_id,
            "content": file_content,
            "filename": file_name,
            "filetype": "text",
            "thread_ts": ts,
        }
        headers = {
            "Authorization": f"Bearer {self.slack_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = requests.post(url=self.SLACK_API_FILE_UPLOAD_URL, headers=headers, data=payload)
        return response.json()

    def post_report(self):
        need_to_check_report, full_report = create_report()
        need_to_check_report_send_response = self.post_message("BBM - Need to check report", need_to_check_report)
        ts = need_to_check_report_send_response["ts"]
        with open("full_process_report.txt", "w") as f:
            f.write(full_report)
        upload_response = self.post_message_with_file("full_process_report.txt", "full_process_report.txt", ts=ts)
        return upload_response

