import socket

import requests


def get_ip():
    return requests.get("http://ipgrab.io").text


def get_hostname():
    return socket.gethostname()
