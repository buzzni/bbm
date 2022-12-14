import inspect
import os
import socket
from datetime import datetime, timedelta
from time import mktime

import requests
from prettytable import PrettyTable

import bbm
from bbm.constants import DEFAULT_ALLOW_INTERVAL_TIME, ES_LIMIT_SIZE, KST, STANDARD_DATETIME_ALLOW_BUFFER_RATIO, UTC


def get_caller_file_name():
    frame = inspect.stack()[2]
    module = inspect.getmodule(frame[0])
    filename = module.__file__
    return os.path.basename(filename)


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

    es_response = requests.post(
        f"{es_url}/{es_index}/_search?scroll=2m",
        json=query_dsl,
    ).json()
    data_list = []
    while len(es_response["hits"]["hits"]) > 0:
        data_list += es_response["hits"]["hits"]
        if len(data_list) >= num:
            break
        scroll_id = es_response["_scroll_id"]
        es_response = requests.post(
            f"{es_url}/_search/scroll",
            json={"scroll": "2m", "scroll_id": scroll_id},
        ).json()

    result = []
    for data in data_list:
        result.append(data["_source"])
    return result


def create_report():
    bbm_obj = bbm.get_bbm()
    dql = "param.msg:start OR param.msg:complete"
    if bbm_obj.process_category:
        dql = f"({dql}) AND param.cate:{bbm_obj.process_category}"
    query_result = get_data_from_es(query=dql, num=20000, es_index=bbm_obj.index_prefix + "*", es_url=bbm_obj.es_url)
    process_distinct = set()
    process_info_dict = dict()
    default_standard_datetime = datetime.now().astimezone(UTC) - timedelta(seconds=int(DEFAULT_ALLOW_INTERVAL_TIME))
    for data in query_result:
        if data["process"] not in process_info_dict:
            process_distinct.add(data["process"])
            if data["param"].get("interval", False):
                process_info_dict[data["process"]] = {
                    "process": data["process"],
                    "last_run_at": "",
                    "last_completed_at": "",
                    "duration": None,
                    "interval": data["param"]["interval"],
                }
            else:
                process_info_dict[data["process"]] = {
                    "process": data["process"],
                    "last_run_at": "",
                    "last_completed_at": "",
                    "duration": None,
                }

        if data["param"]["msg"] == "start":
            if process_info_dict[data["process"]]["last_run_at"] == "" or (
                process_info_dict[data["process"]]["last_run_at"] < data["@timestamp"]
            ):
                process_info_dict[data["process"]]["last_run_at"] = data["@timestamp"]

        if data["param"]["msg"] == "complete":
            if process_info_dict[data["process"]]["last_completed_at"] == "" or (
                process_info_dict[data["process"]]["last_completed_at"] < data["@timestamp"]
            ):
                process_info_dict[data["process"]]["last_completed_at"] = data["@timestamp"]

        if not process_info_dict[data["process"]].get("interval", False) and data["param"].get("interval", False):
            process_info_dict[data["process"]]["interval"] = data["param"]["interval"]

        # timestamp ?????????????????? ??????????????? ????????? ????????? ???????????? ?????? ?????? ?????????
        if (
            data["param"].get("duration")
            and process_info_dict[data["process"]]
            and process_info_dict[data["process"]].get("duration") is None
        ):
            process_info_dict[data["process"]]["duration"] = data["param"]["duration"]

    elasticsearch_timestamp_format = "%Y-%m-%dT%H:%M:%S.%f%z"
    for process in process_info_dict:
        last_run_at = None
        last_completed_at = None
        if process_info_dict[process]["last_run_at"]:
            last_run_at = datetime.strptime(
                process_info_dict[process]["last_run_at"],
                elasticsearch_timestamp_format,
            )
            process_info_dict[process]["last_run_at"] = last_run_at

        if process_info_dict[process]["last_completed_at"]:
            last_completed_at = datetime.strptime(
                process_info_dict[process]["last_completed_at"],
                elasticsearch_timestamp_format,
            )
            process_info_dict[process]["last_completed_at"] = last_completed_at

        if process_info_dict[process].get("interval", False) and last_run_at:
            must_run_at = last_run_at + timedelta(seconds=process_info_dict[process]["interval"])
            process_info_dict[process]["next_run"] = must_run_at
            # es timestamp??? kst??? ????????? ????????? kst??? ??????
            process_info_dict[process]["standard_datetime"] = (datetime.now().astimezone(KST)) - timedelta(
                seconds=process_info_dict[process]["interval"] * 2
                + (process_info_dict[process]["interval"] * 2) * STANDARD_DATETIME_ALLOW_BUFFER_RATIO
            )
            process_info_dict[process]["run_count"] = 0

    # complete log??? ????????? ??? ??????????????? run_count??? ????????????
    for data in query_result:
        if data["param"]["msg"] == "complete" and process_info_dict[data["process"]].get("standard_datetime", False):
            log_datetime = datetime.strptime(data["@timestamp"], elasticsearch_timestamp_format)
            if (
                process_info_dict[data["process"]]["standard_datetime"] <= log_datetime
                and data["param"]["msg"] == "complete"
            ):
                process_info_dict[data["process"]]["run_count"] += 1

    # ???????????? ???????????? process_last_run_dict?????? interval??? ?????? process???
    # ??????????????? ????????? ??????(last_run_at), ????????? ????????? ??????(next_run)
    # ????????? * 2 ??? ??????????????? ????????????(standard_datetime), ?????????????????? ???????????? ????????? ??????
    # ????????? ??? 4?????? ????????? ?????? ??????.

    # ?????? ???????????? ????????????
    total_process_table = PrettyTable()
    total_process_table.field_names = [
        "process_name",
        "last_run_at",
        "last_completed_at",
        "next_estimated",
        "need_to_check",
        "duration(s)",
    ]
    total_process_table.align["process_name"] = "l"
    total_process_table.align["duration(s)"] = "r"
    need_to_check_table = total_process_table.copy()
    need_to_check_count = 0
    process_list = sorted(list(process_info_dict))

    for process in process_list:
        if process in bbm_obj.ignore_process_list:
            continue
        row = [""] * len(total_process_table.field_names)
        row[0] = process
        # row = [process, "", "", "", "", ""]
        # 1. ????????? ??????????????? 3???????????? ?????????
        # 2. ????????? ??????????????? ?????? ??????????????? ???????????? 2?????? ?????? ?????? ??????????????? need_to_check??? True

        if process not in process_info_dict or not process_info_dict[process].get("last_run_at"):
            row[3] = "??????"
            need_to_check_count += 1
            need_to_check_table.add_row(row)
            total_process_table.add_row(row)
            continue
        try:
            row[1] = (
                process_info_dict[process]["last_run_at"].strftime("%Y-%m-%d %H:%M")
                if process_info_dict[process]["last_run_at"]
                else ""
            )
            row[2] = (
                process_info_dict[process]["last_completed_at"].strftime("%Y-%m-%d %H:%M")
                if process_info_dict[process]["last_completed_at"]
                else ""
            )
            next_run = process_info_dict[process].get("next_run", "")
            if next_run != "":
                next_run = next_run.strftime("%Y-%m-%d %H:%M")
            row[3] = next_run

            # passed ?????? (?????? ???????????? ?????? ???????????? ??????-????????????-??? ?????? ???????????? ??????)
            # 1. ??????????????? standard_datetime ????????? 2??? ???????????? ??????????????????
            passed = (
                True
                if (process_info_dict[process].get("run_count", 0) > 1)
                or (process_info_dict[process].get("last_run_at") > default_standard_datetime)
                else False
            )
            # 2. next_estimated??? ???????????? ???????????? ??????????????? 0?????? ??????
            passed = False if next_run and process_info_dict[process].get("run_count", 0) < 1 else passed
            # 3. next_estimated??? ?????????????????? ????????? ??????
            # passed = True if next_run > datetime.now().strftime("%Y-%m-%d %H:%M") else passed
            # 4. ????????? ??????????????? ?????? ??????
            passed = False if not process_info_dict[process].get("last_completed_at") else passed
            # 5. ????????? ??????????????? ????????? ???????????? ?????? ??????
            passed = (
                False
                if process_info_dict[process].get("last_completed_at", None)
                and (
                    process_info_dict[process].get("last_completed_at") < process_info_dict[process].get("last_run_at")
                )
                else passed
            )

            # passed ?????? (?????? ???????????? ?????? ????????? ???????????? ???????????? ??????)
            # 1. run_count??? 1??? ???????????? next_estimated??? ?????????????????? ????????? ?????? -> ?????? ?????? ????????????
            passed = (
                True
                if (next_run > datetime.now().strftime("%Y-%m-%d %H:%M"))
                and (process_info_dict[process].get("run_count", 0) > 0)
                else passed
            )
            # 2. last_run_at??? 3??? ????????? passed
            passed = (
                True
                if process_info_dict[process].get("last_run_at")
                and (datetime.now().astimezone(UTC) - process_info_dict[process].get("last_run_at")).seconds < 180
                else passed
            )
        except Exception as e:
            passed = False

        row[4] = "" if passed else "??????"
        row[5] = (
            round(process_info_dict[process].get("duration", 0), 2)
            if process_info_dict[process].get("duration", 0)
            else ""
        )

        if not passed:
            need_to_check_table.add_row(row)
            need_to_check_count += 1
        total_process_table.add_row(row)

    ignored_process_count = len([process for process in process_list if process in bbm_obj.ignore_process_list])
    total_process_msg = str(total_process_table)
    total_process_msg += f"\ntotal: {len(process_list)}"
    total_process_msg += f"\nignored: {ignored_process_count}"
    total_process_msg += f"\nneed_to_check: {need_to_check_count}"

    need_to_check_process_msg = ""
    if need_to_check_count:
        need_to_check_process_msg = str(need_to_check_table)
        need_to_check_process_msg += f"\ntotal: {len(process_list)}"
        need_to_check_process_msg += f"\nignored: {ignored_process_count}"
        need_to_check_process_msg += f"\nneed_to_check: {need_to_check_count}"
    else:
        need_to_check_process_msg += f"\ntotal: {len(process_list)}"
        need_to_check_process_msg += f"\nignored: {ignored_process_count}"
        need_to_check_process_msg += f"\nneed_to_check: {need_to_check_count}"
        need_to_check_process_msg += f"\n??? Everything is Ok ???"

    return need_to_check_process_msg, total_process_msg


def get_file_content(file_path: str):
    with open(file_path, "rb") as f:
        content = f.read()
    return content
