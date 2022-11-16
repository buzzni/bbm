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
