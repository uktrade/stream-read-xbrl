import csv
import datetime
import hashlib
import logging
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass
from collections import defaultdict, deque
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from decimal import Decimal
from itertools import chain
from io import BytesIO, IOBase
from pathlib import Path, PurePosixPath
from typing import Optional, Callable

import dateutil
import dateutil.parser
from bs4 import BeautifulSoup
import httpx
from lxml import etree
from lxml.etree import XMLSyntaxError
from stream_unzip import stream_unzip

_COLUMNS = (
    'run_code',
    'company_id',
    'date',
    'file_type',
    'taxonomy',
    'balance_sheet_date',
    'companies_house_registered_number',
    'entity_current_legal_name',
    'company_dormant',
    'average_number_employees_during_period',
    'period_start',
    'period_end',
    'tangible_fixed_assets',
    'debtors',
    'cash_bank_in_hand',
    'current_assets',
    'creditors_due_within_one_year',
    'creditors_due_after_one_year',
    'net_current_assets_liabilities',
    'total_assets_less_current_liabilities',
    'net_assets_liabilities_including_pension_asset_liability',
    'called_up_share_capital',
    'profit_loss_account_reserve',
    'shareholder_funds',
    'turnover_gross_operating_revenue',
    'other_operating_income',
    'cost_sales',
    'gross_profit_loss',
    'administrative_expenses',
    'raw_materials_consumables',
    'staff_costs',
    'depreciation_other_amounts_written_off_tangible_intangible_fixed_assets',
    'other_operating_charges_format2',
    'operating_profit_loss',
    'profit_loss_on_ordinary_activities_before_tax',
    'tax_on_profit_or_loss_on_ordinary_activities',
    'profit_loss_for_period',
    'error',
    'zip_url',
)

logger = logging.getLogger(__name__)


def _xbrl_to_rows(name_xbrl_xml_str_orig):
    name, xbrl_xml_str_orig = name_xbrl_xml_str_orig

    # Slightly hacky way to remove BOM, which is present in some older data
    xbrl_xml_str = BytesIO(xbrl_xml_str_orig[xbrl_xml_str_orig.find(b'<'):])

    # Low level value parsers

    def _date(text):
        return dateutil.parser.parse(text).date()

    def _parse(element, text, parser):
        return \
            parser(element, text.strip()) if text and text.strip() not in ['', '-'] else \
            None

    def _parse_str(element, text):
        return str(text).replace('\n', ' ').replace('"', '')
    
    def _parse_absolute(element, text):
        # Some cases where employee numbers have a negative sign attached,
        # seemingly indicating negative employee numbers
        return abs(_parse_decimal_with_colon_or_dash(element, text))

    def _parse_decimal(element, text):
        sign = -1 if element.get('sign', '') == '-' else +1
        text_without_thousands_separator = \
            text.replace('.', '').replace(',', '.') if element.get('format', '').rpartition(':')[2] == 'numdotcomma' else \
            text.replace(' ', '') if element.get('format', '').rpartition(':')[2] == 'numspacedot' else \
            text.replace(',', '')
        if ' ' in text_without_thousands_separator:
            text_without_thousands_separator = sum(map(Decimal, text_without_thousands_separator.split(" ")))
        return sign * Decimal(text_without_thousands_separator) * Decimal(10) ** Decimal(element.get('scale', '0'))

    def _parse_decimal_with_colon_or_dash(element, text):
        # Values seem to have a human readble prefix that isn't part of the value,
        # like "2017 - 2" to mean 2 employees. So we strip the prefix.
        return _parse(element, re.sub(r'(.*:)|(.+- )', '', text), _parse_decimal)

    def _parse_date(element, text):
        format = element.get('format','').rpartition(':')[2].lower()
        day_first = format in ('datedaymonthyear', 'dateslasheu', 'datedoteu')
        if format == 'datedaymonthyearen':
            text = text.replace(' ','')
        text = re.sub(r"(?i)(\d)((st)|(nd)|(rd)|(th))", r"\1", text)
        try:
            return dateutil.parser.parse(text, dayfirst=day_first).date()
        except dateutil.parser.ParserError:
            # Try to parse mis-spellings that still have the first 3 characters right
            return dateutil.parser.parse(re.sub(r'([a-zA-Z]+)', lambda m: m.group(0)[:3], text), dayfirst=day_first).date()

    def _parse_bool(element, text):
        return False if text == 'false' else True if text == 'true' else None

    def _parse_reversed_bool(element, text):
        return False if text == 'true' else True if text == 'false' else None

    # Parsing strategy
    #
    # The XBRL format is a "tagging" format that can tag elements in any order with machine readable metadata.
    # While flexible, this means that it's difficult to efficiently convert to a dataframe.
    #
    # The simplest way to do this would XPath repeatedly to find extract the data for each columnn. This was
    # done in previous versions, but took about 3 times as long as the current solution. The current solution
    # leverages the fact that dictionary lookups are fast, and so constructs dictionaries that can be looked up
    # while iterating through all the elements in the document.

    # Although in some cases a dictionary lookup doesn't seem possible, and so a custom matcher can be defined

    @dataclass
    class _test():
        name: Optional[str]
        search: Callable = lambda element, local_name, attribute_name, context_ref: (element,)

    @dataclass
    class _tn(_test):
        # (Local) Tag name, i.e. withoout namespace
        pass

    @dataclass
    class _av(_test):
        # Attribute value. Matches on the "name" attribute, but stripping off the namespace prefix
        pass

    @dataclass
    class _custom(_test):
        # Custom test when matching on tag name or name attribute isn't enought
        pass

    GENERAL_XPATH_MAPPINGS = {
        'balance_sheet_date': (
            [
                (_av('BalanceSheetDate'), _parse_date),
                (_tn('BalanceSheetDate'), _parse_date),
            ]
        ),
        'companies_house_registered_number': (
            [
                (_av('UKCompaniesHouseRegisteredNumber'), _parse_str),
                (_tn('CompaniesHouseRegisteredNumber'), _parse_str),
            ]
        ),
        'entity_current_legal_name': (
            [
                (_av('EntityCurrentLegalOrRegisteredName', lambda element, local_name, attribute_name, context_ref: chain((element,), element.xpath("./*[local-name()='span'][1]"),)), _parse_str),
                (_tn('EntityCurrentLegalName', lambda element, local_name, attribute_name, context_ref: chain((element,), element.xpath("./*[local-name()='span'][1]"),)), _parse_str),
            ]
        ),
        'company_dormant': (
            [
                (_av('EntityDormantTruefalse'), _parse_bool),
                (_av('EntityDormant'), _parse_bool),
                (_tn('CompanyDormant'), _parse_bool),
                (_tn('CompanyNotDormant'), _parse_reversed_bool),
            ]
        ),
        'average_number_employees_during_period': (
            [
                (_av('AverageNumberEmployeesDuringPeriod'), _parse_absolute),
                (_av('EmployeesTotal'), _parse_absolute),
                (_tn('AverageNumberEmployeesDuringPeriod'), _parse_absolute),
                (_tn('EmployeesTotal'), _parse_absolute),
            ]
        ),
    }

    PERIODICAL_XPATH_MAPPINGS = {
        # balance sheet
        'tangible_fixed_assets': (
            [
                (_tn('FixedAssets'), _parse_decimal),
                (_av('FixedAssets'), _parse_decimal),
                (_tn('TangibleFixedAssets'), _parse_decimal),
                (_av('TangibleFixedAssets'), _parse_decimal),
                (_av('PropertyPlantEquipment'), _parse_decimal),
            ]
        ),
        'debtors': (
            [
                (_tn('Debtors'), _parse_decimal),
                (_av('Debtors'), _parse_decimal),
            ]
        ),
        'cash_bank_in_hand': (
            [
                (_tn('CashBankInHand'), _parse_decimal),
                (_av('CashBankInHand'), _parse_decimal),
                (_av('CashBankOnHand'), _parse_decimal),
            ]
        ),
        'current_assets': (
            [
                (_tn('CurrentAssets'), _parse_decimal),
                (_av('CurrentAssets'), _parse_decimal),
            ]
        ),
        'creditors_due_within_one_year': (
            [
                (_av('CreditorsDueWithinOneYear'), _parse_decimal),
                (_av('Creditors', lambda element, local_name, attribute_name, context_ref: (element,) if 'WithinOneYear' in element.get('contextRef') else ()), _parse_decimal),
            ]
        ),
        'creditors_due_after_one_year': (
            [
                (_av('CreditorsDueAfterOneYear'), _parse_decimal),
                (_custom(None, lambda element, local_name, attribute_name, context_ref: (element,) if 'Creditors' == local_name and 'AfterOneYear' in context_ref else ()), _parse_decimal)
            ]
        ),
        'net_current_assets_liabilities': (
            [
                (_tn('NetCurrentAssetsLiabilities'), _parse_decimal),
                (_av('NetCurrentAssetsLiabilities'), _parse_decimal),
            ]
        ),
        'total_assets_less_current_liabilities': (
            [
                (_tn('TotalAssetsLessCurrentLiabilities'), _parse_decimal),
                (_av('TotalAssetsLessCurrentLiabilities'), _parse_decimal),
            ]
        ),
        'net_assets_liabilities_including_pension_asset_liability': (
            [
                (_tn('NetAssetsLiabilitiesIncludingPensionAssetLiability'), _parse_decimal),
                (_av('NetAssetsLiabilitiesIncludingPensionAssetLiability'), _parse_decimal),
                (_tn('NetAssetsLiabilities'), _parse_decimal),
                (_av('NetAssetsLiabilities'), _parse_decimal),
            ]
        ),
        'called_up_share_capital': (
            [
                (_tn('CalledUpShareCapital'), _parse_decimal),
                (_av('CalledUpShareCapital'), _parse_decimal),
                (_custom(None, lambda element, local_name, attribute_name, context_ref: (element,) if 'Equity' == attribute_name and 'ShareCapital' in element.get('contextRef', '') else ()), _parse_decimal),
            ]
        ),
        'profit_loss_account_reserve': (
            [
                (_tn('ProfitLossAccountReserve'), _parse_decimal),
                (_av('ProfitLossAccountReserve'), _parse_decimal),
                (_custom(None, lambda element, local_name, attribute_name, context_ref: (element,) if 'Equity' == attribute_name and 'RetainedEarningsAccumulatedLosses' in element.get('contextRef', '') else ()), _parse_decimal),
            ]
        ),
        'shareholder_funds': (
            [
                (_tn('ShareholderFunds'), _parse_decimal),
                (_av('ShareholderFunds'), _parse_decimal),
                (_custom(None,  lambda element, local_name, attribute_name, context_ref: (element,) if 'Equity' == attribute_name and 'segment' not in context_ref else ()), _parse_decimal),
            ]
        ),
        # income statement
        'turnover_gross_operating_revenue': (
            [
                (_tn('TurnoverGrossOperatingRevenue'), _parse_decimal),
                (_av('TurnoverGrossOperatingRevenue'), _parse_decimal),
                (_tn('TurnoverRevenue'), _parse_decimal),
                (_av('TurnoverRevenue'), _parse_decimal),
            ]
        ),
        'other_operating_income': (
            [
                (_tn('OtherOperatingIncome'), _parse_decimal),
                (_av('OtherOperatingIncome'), _parse_decimal),
                (_tn('OtherOperatingIncomeFormat2'), _parse_decimal),
                (_av('OtherOperatingIncomeFormat2'), _parse_decimal),
            ]
        ),
        'cost_sales': (
            [
                (_tn('CostSales'), _parse_decimal),
                (_av('CostSales'), _parse_decimal),
            ]
        ),
        'gross_profit_loss': (
            [
                (_tn('GrossProfitLoss'), _parse_decimal),
                (_av('GrossProfitLoss'), _parse_decimal),
            ]
        ),
        'administrative_expenses': (
            [
                (_tn('AdministrativeExpenses'), _parse_decimal),
                (_av('AdministrativeExpenses'), _parse_decimal),
            ]
        ),
        'raw_materials_consumables': (
            [
                (_tn('RawMaterialsConsumables'), _parse_decimal),
                (_av('RawMaterialsConsumables'), _parse_decimal),
                (_tn('RawMaterialsConsumablesUsed'), _parse_decimal),
                (_av('RawMaterialsConsumablesUsed'), _parse_decimal),
            ]
        ),
        'staff_costs': (
            [
                (_tn('StaffCosts'), _parse_decimal),
                (_av('StaffCosts'), _parse_decimal),
                (_tn('StaffCostsEmployeeBenefitsExpense'), _parse_decimal),
                (_av('StaffCostsEmployeeBenefitsExpense'), _parse_decimal),
            ]
        ),
        'depreciation_other_amounts_written_off_tangible_intangible_fixed_assets': (
            [
                (_tn('DepreciationOtherAmountsWrittenOffTangibleIntangibleFixedAssets'), _parse_decimal),
                (_av('DepreciationOtherAmountsWrittenOffTangibleIntangibleFixedAssets'), _parse_decimal),
                (_tn('DepreciationAmortisationImpairmentExpense'), _parse_decimal),
                (_av('DepreciationAmortisationImpairmentExpense'), _parse_decimal),
            ]
        ),
        'other_operating_charges_format2': (
            [
                (_tn('OtherOperatingChargesFormat2'), _parse_decimal),
                (_av('OtherOperatingChargesFormat2'), _parse_decimal),
                (_tn('OtherOperatingExpensesFormat2'), _parse_decimal),
                (_av('OtherOperatingExpensesFormat2'), _parse_decimal),
            ]
        ),
        'operating_profit_loss': (
            [
                (_tn('OperatingProfitLoss'), _parse_decimal),
                (_av('OperatingProfitLoss'), _parse_decimal),
            ]
        ),
        'profit_loss_on_ordinary_activities_before_tax': (
            [
                (_tn('ProfitLossOnOrdinaryActivitiesBeforeTax'), _parse_decimal),
                (_av('ProfitLossOnOrdinaryActivitiesBeforeTax'), _parse_decimal),
            ]
        ),
        'tax_on_profit_or_loss_on_ordinary_activities': (
            [
                (_tn('TaxOnProfitOrLossOnOrdinaryActivities'), _parse_decimal),
                (_av('TaxOnProfitOrLossOnOrdinaryActivities'), _parse_decimal),
                (_tn('TaxTaxCreditOnProfitOrLossOnOrdinaryActivities'), _parse_decimal),
                (_av('TaxTaxCreditOnProfitOrLossOnOrdinaryActivities'), _parse_decimal),
            ]
        ),
        'profit_loss_for_period': (
            [
                (_tn('ProfitLoss'), _parse_decimal),
                (_av('ProfitLoss'), _parse_decimal),
                (_tn('ProfitLossForPeriod'), _parse_decimal),
                (_av('ProfitLossForPeriod'), _parse_decimal),
            ]
        ),
    }

    ALL_MAPPINGS = dict(**GENERAL_XPATH_MAPPINGS, **PERIODICAL_XPATH_MAPPINGS)

    TAG_NAME_TESTS = {
        test.name: (name, priority, test, parser)
        for (name, tests) in ALL_MAPPINGS.items()
        for (priority, (test, parser)) in enumerate(tests)
        if isinstance(test, _tn)
    }

    ATTRIBUTE_VALUE_TESTS = {
        test.name: (name, priority, test, parser)
        for (name, tests) in ALL_MAPPINGS.items()
        for (priority, (test, parser)) in enumerate(tests)
        if isinstance(test, _av)
    }

    CUSTOM_TESTS = tuple(
        (name, priority, test, parser)
        for (name, tests) in ALL_MAPPINGS.items()
        for (priority, (test, parser)) in enumerate(tests)
        if isinstance(test, _custom)
    )

    def _get_dates(context):
        instant_elements = context.xpath("./*[local-name()='instant']")
        start_date_text_nodes = context.xpath("./*[local-name()='startDate']/text()")
        end_date_text_nodes = context.xpath("./*[local-name()='endDate']/text()")
        return \
            (None, None) if context is None else \
            (instant_elements[0].text.strip(), instant_elements[0].text.strip()) if instant_elements else \
            (None, None) if start_date_text_nodes[0] is None or end_date_text_nodes[0] is None else \
            (start_date_text_nodes[0].strip(), end_date_text_nodes[0].strip())

    try:
        document = etree.parse(xbrl_xml_str, etree.XMLParser(ns_clean=True, recover=True))
        root = document.getroot()
        document.xpath("//*[0]")
    except:
        # In at least one case - Prod224_9956_04944372_20100331.xml, the XML seems very badly formed.
        # Suspect this is before Companies House had better validation. The best we can do is log and
        # carry on. We can at least still get a row in the data
        logger.warning("Bad XML. Name: %s XML: %s", name, xbrl_xml_str_orig)
        document = etree.parse(BytesIO(b'<?xml version="1.0" encoding="UTF-8"?><root></root>'), etree.XMLParser(ns_clean=True, recover=True))
        root = document.getroot()

    context_dates = {
        e.get('id'): _get_dates(period)
        for e in document.xpath("//*[local-name()='context']")
        for period in e.xpath("./*[local-name()='period']")[:1]
    }

    fn = os.path.basename(name)
    # Some April 2021 data files end in .zip, but seem to really be html
    mo = re.match(r'^(Prod\d+_\d+)_([^_]+)_(\d\d\d\d\d\d\d\d)\.(html|xml|zip)', fn)
    run_code, company_id, date, filetype = mo.groups()
    allowed_taxonomies = [
        'http://www.xbrl.org/uk/fr/gaap/pt/2004-12-01',
        'http://www.xbrl.org/uk/gaap/core/2009-09-01',
        'http://xbrl.frc.org.uk/fr/2014-09-01/core',
    ]

    core_attributes = (
        run_code,
        company_id,
        _date(date),
        filetype,
        ';'.join(set(allowed_taxonomies) & set(root.nsmap.values())),
    )

    # Mutable dictionaries to store the "priority" (lower is better) of a found value
    general_attributes_with_priorities = {
        name: (10, None)
        for name in GENERAL_XPATH_MAPPINGS.keys()
    }
    periodic_attributes_with_priorities = defaultdict(lambda: {
        name: (10, None)
        for name in PERIODICAL_XPATH_MAPPINGS.keys()
    })

    def tag_name_tests(local_name):
        try:
            yield from (TAG_NAME_TESTS[local_name],)
        except KeyError:
            pass

    def attribute_value_tests(attribute_value):
        try:
            yield from (ATTRIBUTE_VALUE_TESTS[attribute_value],)
        except KeyError:
            pass

    def handle_general(element, local_name, attribute_value, context_ref, name, priority, test, parse):
        best_priority, best_value = general_attributes_with_priorities[name]

        if priority > best_priority:
            return

        for element in test.search(element, local_name, attribute_value, context_ref):
            filtered = ((e.text or '') for e in element.iter() if e.tag.rpartition('}')[2] != "exclude")
            value = _parse(element, ''.join(filtered), parse)
            if value is not None:
                general_attributes_with_priorities[name] = (priority, value)
                break

    def handle_periodic(element, local_name, attribute_value, context_ref, name, priority, test, parse):
        if not context_ref:
            return
        dates = context_dates.get(context_ref)
        if not dates:
            return

        for element in test.search(element, local_name, attribute_value, context_ref):
            best_priority, best_value = periodic_attributes_with_priorities[dates][name]

            if priority >= best_priority:
                return

            filtered = ((e.text or '') for e in element.iter() if etree.QName(e).localname != "exclude")
            value = _parse(element, ''.join(filtered), parse)
            if value is not None:
                periodic_attributes_with_priorities[dates][name] = (priority, value)
                break

    error = None
    try:          
        for element in document.xpath('//*'):
            _, _, local_name = element.tag.rpartition('}')
            _, _, attribute_value = element.get('name', '').rpartition(':')
            context_ref = element.get('contextRef', '')

            for name, priority, test, parse in chain(tag_name_tests(local_name), attribute_value_tests(attribute_value), CUSTOM_TESTS):
                handler = \
                    handle_general if name in general_attributes_with_priorities else \
                    handle_periodic

                handler(element, local_name, attribute_value, context_ref, name, priority, test, parse)

        general_attributes = tuple(
            general_attributes_with_priorities[name][1]
            for name in GENERAL_XPATH_MAPPINGS.keys()
        )

        periods = tuple(
            (datetime.date.fromisoformat(period_start_end[0]), datetime.date.fromisoformat(period_start_end[1]))
            + tuple(
                periodic_attributes[name][1]
                for name in PERIODICAL_XPATH_MAPPINGS.keys()
            )
            for period_start_end, periodic_attributes in periodic_attributes_with_priorities.items()
        )
        sorted_periods = sorted(periods, key=lambda period: (period[0], period[1]), reverse=True)
    except ValueError as e:
        error = str(e)

    return \
        ((core_attributes + (None,) * (2 + len(GENERAL_XPATH_MAPPINGS) + len(PERIODICAL_XPATH_MAPPINGS)) + (error,)),) if error is not None else \
        tuple((core_attributes + general_attributes + period + (None,)) for period in sorted_periods) if sorted_periods else \
        ((core_attributes + general_attributes + (None,) * (3 + len(PERIODICAL_XPATH_MAPPINGS))),)


@contextmanager
def stream_read_xbrl_zip(
    zip_bytes_iter,
    zip_url=None,
):
    queue = deque()
    num_workers = max(os.cpu_count() - 1, 1)

    def imap(executor, func, param_iterables):
        for params in param_iterables:
            if len(queue) == num_workers:
                yield queue.popleft().result()

            queue.append(executor.submit(func, params))

        while queue:
            yield queue.popleft().result()

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        yield _COLUMNS, (
            row + (zip_url,)
            for results in imap(executor, _xbrl_to_rows, ((name.decode(), b''.join(chunks)) for name, _, chunks in stream_unzip(zip_bytes_iter)))
            for row in results
        )


@contextmanager
def stream_read_xbrl_sync(
    ingest_data_after_date=datetime.date(datetime.MINYEAR, 1, 1),
    data_urls=(
        'https://download.companieshouse.gov.uk/en_accountsdata.html',
        'https://download.companieshouse.gov.uk/en_monthlyaccountsdata.html',
        'https://download.companieshouse.gov.uk/historicmonthlyaccountsdata.html',
    ),
    get_client = lambda: httpx.Client(timeout=60.0, transport=httpx.HTTPTransport(retries=3)),
    chunk_size = 100 * 1048576  # 100 MiB
):
    def extract_start_end_dates(url):
        file_basename = os.path.basename(url)
        file_name_no_ext = os.path.splitext(file_basename)[0]

        if 'JanToDec' in file_name_no_ext or 'JanuaryToDecember' in file_name_no_ext:
            file_name_no_ext = os.path.splitext(url)[0]
            year = file_name_no_ext[-4:]
            return datetime.date(int(year), 1, 1), datetime.date(int(year), 12, 31)
        elif 'Accounts_Monthly_Data' in file_name_no_ext and file_name_no_ext[-4:].isnumeric():
            year = int(file_name_no_ext[-4:])
            month_name = file_name_no_ext.split('-')[1][:-4]
            # Convert the month name to a month number
            month_num = datetime.datetime.strptime(month_name, '%B').month
            # Calculate the last date of the month
            first_day_of_month = datetime.date(year, month_num, 1)
            next_month = datetime.date(year, month_num, 28) + datetime.timedelta(days=4)
            last_day_of_month = next_month - datetime.timedelta(days=next_month.day)
            return (first_day_of_month, last_day_of_month)
        elif 'Accounts_Bulk_Data' in file_name_no_ext:
            date_str = file_name_no_ext.split('-', 1)[1]
            day = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            return (day, day)
        else:
            return (None, None)

    def get_content(client, url):
        r = client.get(url)
        r.raise_for_status()
        return r.content

    @contextmanager
    def get_content_streamed(client, url):

        def get_chunks():
            start = 0
            end = chunk_size - 1
            etag = None
            remaining = None

            while remaining is None or remaining > 0:
                with client.stream('GET', url, headers={
                    'range': f'bytes={start}-{end}'
                }) as r:
                    r.raise_for_status()
                    if etag is None:
                        etag = r.headers['etag']
                    else:
                        if etag != r.headers['etag']:
                            raise Exception('etag has changed since beginning requests')     
                    if remaining is None:
                        remaining = int(r.headers['content-range'].split('/')[1])
                    content_length =int(r.headers['content-length'])
                    assert content_length > 0
                    remaining -= content_length
                    yield from r.iter_bytes(chunk_size=65536)
                start += chunk_size
                end += chunk_size

        chunks = get_chunks()
        try:
            yield chunks
        finally:
            # This is for the case of unfinished iteration. It raises a GeneratorExit in get_chunks, so any
            # open context in "get_chunks" gets properly closed, i.e. to close its open HTTP connection
            chunks.close()

    dummy_list_to_ingest = [
        (datetime.date(2021, 5, 2), (('1', '2'), ('3', '4'))),
        (datetime.date(2022, 2, 8), (('5', '6'), ('7', '8'))),
    ]

    with get_client() as client:
        pages_of_links = [
            (data_url, BeautifulSoup(get_content(client, data_url), 'html.parser').find_all('a'))
            for data_url in data_urls
        ]

        all_zip_urls = [
            link.attrs['href'].strip() if link.attrs['href'].strip().startswith('http://') or link.attrs['href'].strip().startswith('https://') else
            urllib.parse.urljoin(data_url, link.attrs['href'].strip())
            for (data_url, page_of_links) in pages_of_links
            for link in page_of_links
            if link.attrs.get('href', '').endswith('.zip')
        ]

        all_zip_urls_with_dates = [
            (zip_url, extract_start_end_dates(zip_url))
            for zip_url in all_zip_urls
        ]

        all_zip_urls_with_parseable_dates = [
            (zip_url, dates)
            for (zip_url, dates) in all_zip_urls_with_dates
            if dates != (None, None)
        ]

        all_zip_urls_with_dates_oldest_first = sorted(
            all_zip_urls_with_parseable_dates, key=lambda zip_start_end: (zip_start_end[1][0], zip_start_end[1][1])
        )

        zip_urls_with_date_in_range_to_ingest = [
            (zip_url, (start_date, end_date))
            for (zip_url, (start_date, end_date)) in all_zip_urls_with_dates_oldest_first
            if (start_date, end_date) != (None, None) and end_date > ingest_data_after_date
        ]

        def _final_date_and_rows():
            for zip_url, (start_date, end_date) in zip_urls_with_date_in_range_to_ingest:
                with get_content_streamed(client, zip_url) as chunks:
                    with stream_read_xbrl_zip(chunks, zip_url=zip_url) as (_, rows):
                        yield (start_date, end_date), rows

        yield (_COLUMNS, _final_date_and_rows())


def stream_read_xbrl_sync_s3_csv(s3_client, bucket_name, key_prefix):

    def _to_file_like_obj(iterable):
        chunk = b''
        offset = 0
        it = iter(iterable)

        def up_to_iter(size):
            nonlocal chunk, offset

            while size:
                if offset == len(chunk):
                    try:
                        chunk = next(it)
                    except StopIteration:
                        break
                    else:
                        offset = 0
                to_yield = min(size, len(chunk) - offset)
                offset = offset + to_yield
                size -= to_yield
                yield chunk[offset - to_yield : offset]

        class FileLikeObj(IOBase):
            def readable(self):
                return True

            def read(self, size=-1):
                return b''.join(
                    up_to_iter(float('inf') if size is None or size < 0 else size)
                )

        return FileLikeObj()

    def _convert_to_csv(columns, rows):
        class PseudoBuffer:
            def write(self, value):
                return value.encode("utf-8")

        pseudo_buffer = PseudoBuffer()
        csv_writer = csv.writer(pseudo_buffer, quoting=csv.QUOTE_NONNUMERIC)
        yield csv_writer.writerow(columns)
        yield from (csv_writer.writerow(row) for row in rows)

    s3_paginator = s3_client.get_paginator('list_objects_v2')
    dates = (
        # The -10: is to support older versions where only the end date was in the file name
        datetime.date.fromisoformat(PurePosixPath(content['Key']).stem[-10:])
        for page in s3_paginator.paginate(Bucket=bucket_name, Prefix=key_prefix)
        for content in page.get('Contents', ())
    )
    latest_completed_date = max(dates, default=datetime.date(datetime.MINYEAR, 1, 1))

    with stream_read_xbrl_sync(latest_completed_date) as (columns, final_date_and_rows):
        for ((start_date, final_date), rows) in final_date_and_rows:
            key = f'{key_prefix}{start_date}--{final_date}.csv'
            logger.info('Saving Companies House accounts data to %s/%s ...', bucket_name, key)
            csv_file = _to_file_like_obj(_convert_to_csv(columns, rows))
            s3_client.upload_fileobj(Bucket=bucket_name, Key=key, Fileobj=csv_file)
            logger.info('Saving Companies House accounts data to %s/%s (done)', bucket_name, key)


def stream_read_xbrl_debug(zip_url, run_code, company_id, date, debug_cache_folder=".debug-cache"):
    Path(debug_cache_folder).mkdir(parents=True, exist_ok=True)

    # Hashing so we have a filesystem-safe URL
    hashed_zip_url = hashlib.sha256(zip_url.encode('utf-8')).hexdigest()
    local_zip_file = Path(debug_cache_folder).joinpath(hashed_zip_url)

    if not local_zip_file.exists():
        print('The ZIP', zip_url, 'does not exist in local cache. Downloading...', file=sys.stderr)
        done = False
        try:
            with \
                    httpx.stream('GET', zip_url) as r, \
                    open(local_zip_file, 'wb') as f:
                r.raise_for_status()
                for chunk in r.iter_bytes():
                    f.write(chunk)
            done = True
        finally:
            if not done:
                local_zip_file.unlink(missing_ok=True)
        print('Downloaded', file=sys.stderr)
    else:
        print('Found', zip_url, 'in local cache', file=sys.stderr)

    def local_chunks():
        with open(local_zip_file, 'rb') as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                yield chunk

    print('Searching ZIP for member file matching', run_code, company_id, date, file=sys.stderr)
    found = False
    for name, _, chunks in stream_unzip(local_chunks()):
        fn = os.path.basename(name.decode('utf-8'))
        mo = re.match(r'^(Prod\d+_\d+)_([^_]+)_(\d\d\d\d\d\d\d\d)\.(html|xml)', fn)
        _run_code, _company_id, _date, _ = mo.groups()
        # print(_run_code, _company_id, _date)

        if _run_code == run_code and _company_id == company_id and _date == date.isoformat().replace('-', ''):
            print('Found matching file', name, file=sys.stderr)
            found = True
            for chunk in chunks:
                sys.stdout.buffer.write(chunk)
        else:
            for chunk in chunks:
                pass

    if not found:
        print('No matching member file found', file=sys.stderr)

    print('Finished', file=sys.stderr)
