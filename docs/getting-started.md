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

The main function supplied is `stream_read_xbrl_zip`. This takes a single argument:

1. An iterable that yields the bytes of a ZIP of Companies Accounts data.

It returns a two-tuple of:

1. A tuple of column names.
2. An iterable of the rows of the data, where each row it itself a tuple.


### Basic usage

To use `stream_read_xbrl_zip`, typically an HTTP client is required to fetch the data from Companies House. For example [httpx](https://www.python-httpx.org/).

```python
import httpx
from stream_read_xbrl import stream_read_xbrl_zip

# A URL taken from http://download.companieshouse.gov.uk/en_accountsdata.html
url = 'http://download.companieshouse.gov.uk/Accounts_Bulk_Data-2023-03-02.zip'
with httpx.stream('GET', url) as r:
    r.raise_for_status()
    columns, rows = stream_read_xbrl_zip(r.iter_bytes(chunk_size=65536))
    for row in rows:
        print(row)
```

### Pandas DataFrame

The results of `stream_read_xbrl_zip` can be converted a Pandas DataFrame by passing them to `pd.DataFrame`.

```python
import httpx
import pandas as pd
from stream_read_xbrl import stream_read_xbrl_zip

url = 'http://download.companieshouse.gov.uk/Accounts_Bulk_Data-2023-03-02.zip'
with httpx.stream('GET', url) as r:
    columns, rows = stream_read_xbrl_zip(r.iter_bytes(chunk_size=65536))
    df = pd.DataFrame(rows, columns=columns)

print(df)
```

Note that this will load the data of the file into memory at once, and so is not really streaming.
