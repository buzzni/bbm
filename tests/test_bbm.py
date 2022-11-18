from bbm import logging, setup
from bbm.reporter import Reporter
from tests.conftest import TEST_ES_INDEX, TEST_ES_URL, TEST_SLACK_CHANNEL_ID, TEST_SLACK_TOKEN


def test_one_plus_one():
    assert 1 + 1 == 2


def test_setup_and_logging_decorator(requests_mock):
    setup(es_url=TEST_ES_URL, index_prefix=TEST_ES_INDEX)
    assert requests_mock.call_count == 1

    @logging()
    def temp_func():
        return "Hello World"

    temp_func()
    # logging decorator calls two times because of start and complete
    # so, total call count is 3
    assert requests_mock.call_count == 3


def test_setup_reporter(requests_mock):
    reporter = Reporter(slack_token=TEST_SLACK_TOKEN, slack_channel_id=TEST_SLACK_CHANNEL_ID)
    assert requests_mock.call_count == 1
    reporter.post_message("test message")
    assert requests_mock.call_count == 2
