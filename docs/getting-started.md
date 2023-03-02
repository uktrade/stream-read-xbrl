## Prerequisites

Python 3.7+

## Installation

You can install stream-read-xbrl and its dependencies from [PyPI](https://pypi.org/project/stream-read-xbrl/) using pip.

```bash
pip install stream-read-xbrl
```

This installs the latest version of stream-read-xbrl, and the latest compatible version of all of its dependencies.

If you regularly install stream-read-xbrl, such as during application deployment, to avoid unexpected changes as new versions are released, you can pin to specific versions. [Poetry](https://python-poetry.org/) or [pip-tools](https://pip-tools.readthedocs.io/en/latest/) are popular tools that can be used for this.


## Usage

A single function is exposed, `stream_read_xbrl_unzip`, that takes a single argument: an iterable that should yield the bytes of a ZIP file of Companies Accounts data [with no zero-length chunks]. It returns a tuple of column names, along an iterable yielding the rows of the data. The `stream-unzip` function is used to unzip the ZIP files which are then parsed by the `XBLRParser` function, resulting in the values returned.

### Basic Example
```python
import httpx
from stream_read_xbrl import stream_read_xbrl_zip

url = 'http://download.companieshouse.gov.uk/Accounts_Bulk_Data-2023-03-02.zip'
with httpx.stream('GET', url) as r:
    columns, rows = stream_read_xbrl_zip(r.iter_bytes(chunk_size=65536))
    for row in row:
        print(row)
```

### Pandas DataFrames Example

This example will load the data from the entire file into memory at once and is not really streaming. 
```python
import httpx
from stream_read_xbrl import stream_read_xbrl_zip

url = 'http://download.companieshouse.gov.uk/Accounts_Bulk_Data-2023-03-02.zip'
with httpx.stream('GET', url) as r:
    columns, rows = stream_read_xbrl_zip(r.iter_bytes(chunk_size=65536))
    df = pd.DataFrame(rows, columns=columns)

print(df)
```