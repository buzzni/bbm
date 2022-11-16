from bbm import logging, setup
from .conftest import TEST_ES_URL, TEST_ES_INDEX


def test_one_plus_one():
    assert 1 + 1 == 2


def test_setup(requests_mock):
    setup(es_url=TEST_ES_URL, index_prefix=TEST_ES_INDEX)
    assert requests_mock.call_count == 1

    @logging()
    def temp_func():
        return "Hello World"
    temp_func()
    # logging decorator calls two times because of start and complete
    # so, total call count is 3
    assert requests_mock.call_count == 3
