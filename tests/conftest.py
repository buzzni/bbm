import json
from datetime import datetime

import pytest

from bbm.constants import KST

TEST_ES_URL = "http://elasticsearch"
TEST_ES_INDEX = "test-index"
TEST_SLACK_TOKEN = "TEST_SLACK_TOKEN"
TEST_SLACK_CHANNEL_ID = "TEST_SLACK_CHANNEL_ID"


@pytest.fixture(scope="function", autouse=True)
def set_up(requests_mock):
    now_kst = datetime.now(tz=KST)
    get_date_to_index = now_kst.strftime("%Y.%m.%d")
    requests_mock.get("http://ipgrab.io", text="0.0.0.0")
    # mock ES Requests
    requests_mock.post(
        f"{TEST_ES_URL}/{TEST_ES_INDEX}-{get_date_to_index}/_doc",
        json={"_index": TEST_ES_INDEX, "_type": "_doc", "_id": "1", "_version": 1},
    )
    requests_mock.post(
        f"{TEST_ES_URL}/{TEST_ES_INDEX}-*/_search?scroll=2m",
        json=json.loads(open("./tests/test_data/es_search_scroll_response.json", "r").read()),
    )
    requests_mock.post(
        f"{TEST_ES_URL}/_search/scroll",
        json=json.loads(open("./tests/test_data/es_search_scroll_response.json", "r").read()),
    )
    requests_mock.get(
        "https://slack.com/api/conversations.list",
        json={
            "ok": True,
            "channels": [
                {"id": "C01", "name": "general", "is_member": True},
                {"id": "C02", "name": "random", "is_member": True},
                {"id": "C03", "name": "test", "is_member": False},
                {"id": TEST_SLACK_CHANNEL_ID, "name": "test2", "is_member": True},
            ],
        },
    )
    requests_mock.post(
        "https://slack.com/api/chat.postMessage",
        json={"ok": True, "channel": TEST_SLACK_CHANNEL_ID, "ts": "1234567890.123456"},
    )
    requests_mock.post(
        "https://slack.com/api/files.upload",
        json={"ok": True, "file": {"id": "F1234567890"}},
    )
