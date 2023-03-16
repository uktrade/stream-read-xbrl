# Investigating data issues

To help identify the root cause of a data issue, a utiliy function is provided, `stream_read_xbrl_debug`.

To use it, pass it 4 values from the single row of data in question:

- **zip_url**
- **run_code**
- **company_id**
- **date**

The function then:

- If necessary, downloads the source ZIP file from Companies House, and stores in a local cache.
- Finds the maching file of original member XML or HTML file that matches the 4 values.
- Prints out this original data from which this data was derived.

For example, save the below Python code to a file `debug.py`.

```python
from stream_read_xbrl import stream_read_xbrl_debug

stream_read_xbrl_debug(
    zip_url='https://download.companieshouse.gov.uk/archive/Accounts_Monthly_Data-February2019.zip',
    run_code='Prod224_0063',
    company_id='00024001',
    date=datetime.date(2018, 6, 30),
)
```

And run it using
```shell
python debug.py
```

This should print the untransformed source data to the console.

To save the source data to a file the following command can be used:

```shell
python debug.py > out.html
```

This allows you to use another program to view the source data. For example a web browser can be used to investigate .html files.
