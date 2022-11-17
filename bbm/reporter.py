import requests
from bbm.exceptions import NoJoinChannelException


class SlackClient:
    url = "https://slack.com/api/chat.postMessage"

    def __init__(self, token: str, channel_id: str, apply_code_block: bool = True):
        self.token = token
        self.channel_id = channel_id
        self.apply_code_block = apply_code_block
        if not self.is_token_joined_at_channel(channel_id):
            raise NoJoinChannelException("Token is not joined at channel")

    def get_channel_list(self):
        url = "https://slack.com/api/conversations.list"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        response = requests.get(url=url, headers=headers)
        return response.json()

    def is_token_joined_at_channel(self, channel_id: str):
        channel_list = self.get_channel_list()
        for channel in channel_list["channels"]:
            if channel["id"] == channel_id and channel["is_member"]:
                return True
        return False

    def post_message(self, text: str):
        payload = {
            "channel": self.channel_id,
            "text": f"```{text}```" if self.apply_code_block else text,
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        response = requests.post(url=self.url, headers=headers, json=payload)
        return response.json()

