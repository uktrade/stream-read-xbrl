<!-- --8<-- [start:intro] -->
# stream-read-xbrl

[![PyPI package](https://img.shields.io/pypi/v/stream-read-xbrl?label=PyPI%20package&color=%234c1)](https://pypi.org/project/stream-read-xbrl/) [![Test suite](https://img.shields.io/github/actions/workflow/status/uktrade/stream-read-xbrl/tests.yml?label=Test%20suite)](https://github.com/uktrade/stream-read-xbrl/actions/workflows/tests.yml) [![Code coverage](https://img.shields.io/codecov/c/github/uktrade/stream-read-xbrl?label=Code%20coverage)](https://app.codecov.io/gh/uktrade/stream-read-xbrl)


Python package to parse [Companies House accounts data](http://download.companieshouse.gov.uk/en_accountsdata.html) in a streaming way. It converts the zipped XBRL format that Companies House supplies into a single data frame of 38 columns.

On a standard laptop with 8 CPU cores it takes approximately 10 seconds to convert a single day of Companies House accounts data. This does not include the time to transfer the data from Companies House.
<!-- --8<-- [end:intro] -->


<!-- --8<-- [start:features] -->
<!-- --8<-- [end:features] -->

---

Visit the [stream-read-xbrl documentation](https://stream-read-xbrl.docs.trade.gov.uk/) for usage instructions.