from bbm import logging, setup_logging, setup_reporter, get_reporter, get_bbm

from tests.conftest import TEST_ES_INDEX, TEST_ES_URL, TEST_SLACK_TOKEN, TEST_SLACK_CHANNEL_ID


def test_one_plus_one():
    assert 1 + 1 == 2


def test_setup_and_logging_decorator(requests_mock):
    setup_logging(es_url=TEST_ES_URL, index_prefix=TEST_ES_INDEX)
    assert requests_mock.call_count == 1

    @logging()
    def temp_func():
        return "Hello World"

    temp_func()
    # logging decorator calls two times because of start and complete
    # so, total call count is 3
    assert requests_mock.call_count == 3


def test_setup_reporter(requests_mock):
    setup_reporter(slack_token=TEST_SLACK_TOKEN, slack_channel_id=TEST_SLACK_CHANNEL_ID)
    assert requests_mock.call_count == 1
    reporter = get_reporter()
    reporter.post_message("test message")
    assert requests_mock.call_count == 2


def test_get_bbm_before_init():
    try:
        get_bbm()
    except Exception as e:
        assert str(e) == "BBM is not initialized"


def test_get_reporter_before_init():
    try:
        get_reporter()
    except Exception as e:
        assert str(e) == "Reporter is not initialized"
