from stream_unzip import stream_unzip


def stream_read_xbrl_zip(zip_bytes_iter):
    def rows():
        for name, _, chunks in stream_unzip(zip_bytes_iter):
            parts = name.decode().split('_')
            company_id = parts[2]
            yield (company_id,)

            for chunk in chunks:
                pass
    return ('company_id',), rows()
