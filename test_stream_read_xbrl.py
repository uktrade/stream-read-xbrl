import re

import httpx

from stream_read_xbrl import stream_read_xbrl_zip


def test_stream_read_xbrl_zip():
    with httpx.stream('GET', 'http://download.companieshouse.gov.uk/Accounts_Bulk_Data-2023-03-02.zip') as r:
        columns, rows = stream_read_xbrl_zip(r.iter_bytes(chunk_size=65536))
        assert columns == ('company_id',)
        count = 0
        for row in rows:
            count += 1
            assert len(row) == len(columns)
            row_dict = dict(zip(columns, row))
            assert re.match(r'(\d{8})|([A-Z]{2}\d{6})', row_dict['company_id'])

        assert count > 1
