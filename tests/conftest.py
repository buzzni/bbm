from bbm.constants import KST
import pytest
from datetime import datetime

TEST_ES_URL = "http://elasticsearch"
TEST_ES_INDEX = "test-index"


@pytest.fixture(scope="function", autouse=True)
def set_up(requests_mock):
    now_kst = datetime.now(tz=KST)
    get_date_to_index = now_kst.strftime("%Y.%m.%d")
    requests_mock.get(
        "http://ipgrab.io",
        text="0.0.0.0"
    )
    requests_mock.post(
        f"{TEST_ES_URL}/{TEST_ES_INDEX}-{get_date_to_index}/_doc",
        json={"_index": TEST_ES_INDEX, "_type": "_doc", "_id": "1", "_version": 1},
    )
