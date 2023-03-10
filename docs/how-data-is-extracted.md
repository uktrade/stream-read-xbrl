# How data is extracted

Each row of the data frame returned by stream-read-xbrl has data extracted from 3 sources.


## 1. HTML

When using the `stream_read_xbrl_sync` or `stream_read_xbrl_sync_s3_csv` functions, the HTML from 3 Companies House pages are fetched and parsed to find the URLs of all the ZIP files that have the published accounts data. The pages that contain the URLs of the ZIP files are:

- [https://download.companieshouse.gov.uk/en_accountsdata.html](https://download.companieshouse.gov.uk/en_accountsdata.html)
- [https://download.companieshouse.gov.uk/en_monthlyaccountsdata.html](https://download.companieshouse.gov.uk/en_monthlyaccountsdata.html)
- [https://download.companieshouse.gov.uk/historicmonthlyaccountsdata.html](https://download.companieshouse.gov.uk/historicmonthlyaccountsdata.html)

Each row of data has the URL of the ZIP file used to populate it as its `zip_url` field.

When using `stream_read_xbrl_zip` directly, by default the `zip_url` field is `None`.


## 2. Names of the member files inside each ZIP

Each ZIP file is a container of many member files, and each has its own file name. 4 fields are extracted from each file name:

- **run_code**

- **company_id**

- **date**

- **file_type**


## 3. HTML or XML inside each member file

The remaining fields are all extracted from the HTML or XML inside each member file.
