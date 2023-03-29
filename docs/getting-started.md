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

It returns a two-tuple context of:

1. A tuple of column names.
2. An iterable of the rows of the data, where each row it itself a tuple.

A context allows stream-read-xbrl to clean up any resources robustly.


### Basic usage

To use `stream_read_xbrl_zip`, typically an HTTP client is required to fetch the data from Companies House. For example [httpx](https://www.python-httpx.org/).

```python
import httpx
from stream_read_xbrl import stream_read_xbrl_zip

# A URL taken from http://download.companieshouse.gov.uk/en_accountsdata.html
url = 'http://download.companieshouse.gov.uk/Accounts_Bulk_Data-2023-03-02.zip'
with \
        httpx.stream('GET', url) as r, \
        stream_read_xbrl_zip(r.iter_bytes(chunk_size=65536)) as (columns, rows):
    r.raise_for_status()
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
with \
        httpx.stream('GET', url) as r, \
        stream_read_xbrl_zip(r.iter_bytes(chunk_size=65536)) as (columns, rows):
    df = pd.DataFrame(rows, columns=columns)

print(df)
```

Note that this will load the data of the file into memory at once, and so is not really streaming.


### Regularly syncing data to a local store

A utility function is supplied that fetches the data from Companies House, `stream_read_xbrl_sync`. It takes a single optional `date` argument, and returns data after this date.

```python
import datetime
from stream_read_xbrl import stream_read_xbrl_sync

with stream_read_xbrl_sync(datetime.date(2022, 12, 31)) as (columns, date_range_and_rows):
    for ((start_date, end_date), rows) in date_range_and_rows
       for row in rows:
           print(row)
```

The `end_date` can be passed to the next call of `stream_read_xbrl_sync`. The can be passed to the next call of `stream_read_xbrl_sync` in order skip data before this date. This can be used as part of a regular sync process from Companies House to a local store - hence the name of the function.

This function can take many hours, even days. To handle the case of the process being interrupted, once the inner `rows` iterable has iterated to completion, the `final_zip_date` can be saved, and used in the next call to `stream_read_xbrl_sync` to pick up close to where it left off.

It is possible that in such a process data will be repeated, especially if `stream_read_xbrl_sync` is called infrequently. Running the function approximately once a day would minimise the risk of this.


### Regularly syncing data to S3

A higher level utility function is provided that saves CSV data to under a prefix in a bucket in S3.

```python
import boto3
from stream_read_xbrl import stream_read_xbrl_sync_s3_csv

s3_client = boto3.client('s3', region_name='eu-west-2')
bucket_name = 'my-bucket'
key_prefix = 'my-folder/'  # Would usually end in a /

stream_read_xbrl_sync_s3_csv(s3_client, bucket_name, key_prefix)
```

This can be called regularly to keep the bucket updated with recent data. Under the hood, `stream_read_xbrl_sync` is used, and the same caveats apply. Specifically, data may be repeated in the bucket, especially if the function is called infrequently.
