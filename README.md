# bbm
📊 Buzzni Batch process Monitor -> BBM 

</p>
<p align="center">
<a href="https://pypi.org/project/bbm" target="_blank">
    <img src="https://img.shields.io/pypi/v/bbm?color=%2334D058&label=pypi%20package" alt="Package version">
</a>
<a href="https://pypi.org/project/bbm" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/bbm?color=%2334D058" alt="Supported Python versions">
</a>
</p>

## Installation
```bash
pip install bbm
```

## Example
### logging
```python
from bbm import Interval, logging, setup


@logging()
def temp_func():
    return "Hello World"


@logging(process_name="custom_name_of_process", interval=Interval.A_DAY)
def temp_func2():
    return "Hello World"


if __name__ == "__main__":
    setup(es_url="your-es-url", index_prefix="your-index-prefix")
    temp_func()
    temp_func2()
```
### post report
```python
from bbm import reporter, setup

if __name__ == "__main__":
    # init bbm
    setup(es_url="your-es-url", index_prefix="your-index-prefix")
    
    # init reporter and send simple messages
    reporter = reporter.Reporter(slack_token="your-slack-token", slack_channel_id="your-slack-channel-id")
    post_response = reporter.post_message(title="title", text="text")
    ts = post_response["ts"]
    post_message_to_thread = reporter.post_message(title="title", text="text", ts=ts)
    
    # send report    
    reporter.post_report()
```
