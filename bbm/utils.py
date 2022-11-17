import socket
from datetime import datetime, timedelta
from time import mktime
from bbm.constants import ES_LIMIT_SIZE

import requests


def get_ip():
    return requests.get("http://ipgrab.io").text


def get_hostname():
    return socket.gethostname()


def convert_to_logstash_date(from_date: str, to_date: str):
    from_date = datetime.strptime(str(from_date), "%Y%m%d%H%M%S")
    from_date = int(mktime(from_date.utctimetuple()) * 1000)
    if to_date != "now":
        to_date = int(mktime(datetime.strptime(str(to_date), "%Y%m%d%H%M%S").utctimetuple()) * 1000)
    return from_date, to_date


def get_data_from_es(
    query: str,
    es_index: str,
    es_url: str,
    *,
    num=10000,
    from_date="",
    to_date="now",
    order="desc",
):
    if not from_date:
        from_date = (datetime.today() - timedelta(days=3)).strftime("%Y%m%d%H%M%S")
    from_date, to_date = convert_to_logstash_date(from_date, to_date)

    if num > ES_LIMIT_SIZE:
        scroll_size = ES_LIMIT_SIZE
    else:
        scroll_size = num

    query_dsl = {
        "size": scroll_size,
        "query": {
            "bool": {
                "must": [{"query_string": {"query": query}}],
                "filter": {"range": {"@timestamp": {"from": from_date, "to": to_date}}},
            }
        },
        "sort": [{"@timestamp": {"order": order}}],
    }

    param = {"body": query_dsl}
    if es_index:
        param["index"] = es_index
    param["request_timeout"] = 1200
    param["scroll"] = "2m"

    results = requests.post(
        f"{es_url}/{es_index}/_search?scroll=2m",
        json=query_dsl,
    ).json()
    data_list = []
    while len(results["hits"]["hits"]) > 0:
        data_list += results["hits"]["hits"]
        if len(data_list) >= num:
            break
        scroll_id = results["_scroll_id"]
        results = requests.post(
            f"{es_url}/{es_index}/_search/scroll",
            json={"scroll": "2m", "scroll_id": scroll_id},
        ).json()
    return data_list
