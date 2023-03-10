# How data is extracted

Each row of the data frame returned by stream-read-xbrl has data extracted from 3 sources.


## 1. HTML

When using the `stream_read_xbrl_sync` or `stream_read_xbrl_sync_s3_csv` functions, the HTML from 3 Companies House pages are fetched and parsed to find the URLs of all the ZIP files that have the published accounts data. The pages that contain the URLs of the ZIP files are:

- [https://download.companieshouse.gov.uk/en_accountsdata.html](https://download.companieshouse.gov.uk/en_accountsdata.html)
- [https://download.companieshouse.gov.uk/en_monthlyaccountsdata.html](https://download.companieshouse.gov.uk/en_monthlyaccountsdata.html)
- [https://download.companieshouse.gov.uk/historicmonthlyaccountsdata.html](https://download.companieshouse.gov.uk/historicmonthlyaccountsdata.html)

Each row of data has the URL of the ZIP file used to populate it as its `zip_url` column.

When using `stream_read_xbrl_zip` directly, by default the `zip_url` column is `None`.


## 2. Names of the member files inside each ZIP

Each ZIP file is a container of many member files, and each has its own file name. 4 columns are extracted from each file name:

- **run_code**

- **company_id**

- **date**

- **file_type**


## 3. HTML or XML inside each member file

The remaining columns are all extracted from the HTML or XML inside each member file.

How data is found for each column is a complex process. However in general, data for each column is found by either by tag name, or by name attribute value.

What this means is described below using an example column, `balance_sheet_date`.

### Tag name

The column `balance_sheet_date` can be extracted from the `BalanceSheetDate` name attribute. What this means in terms of the source data can be seen in the following example.

```xml
<any-namespace:any-tag name="bus:BalanceSheetDate">
	31 May 2022
</any-namespace:any-tag>
```

In this case, the `balance_sheet_date` column will have a Python date object corresponding to 31 May 2022.

### Name attribute value

The column `balance_sheet_date` can alternatively be extracted from `BalanceSheetDate` tags. For example.

```xml
<bus:BalanceSheetDate>
	31 May 2022
</bus:BalanceSheetDate>
```

In this case, the `balance_sheet_name` column will also be a Python date object corresponding to 31 May 2022.
