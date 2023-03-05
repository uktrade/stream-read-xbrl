import datetime
import os
import re
import urllib.parse
from collections import OrderedDict
from contextlib import contextmanager
from decimal import Decimal
from itertools import chain
from io import BytesIO

import dateutil
import dateutil.parser
from bs4 import BeautifulSoup
import httpx
from lxml import etree
from lxml.etree import XMLSyntaxError
from stream_unzip import stream_unzip


def stream_read_xbrl_zip(zip_bytes_iter):

    # Low level value parsers

    def _date(text):
        return dateutil.parser.parse(text).date()

    def _parse(element, text, parser):
        return \
            parser(element, text.strip()) if text and text.strip() not in ['', '-'] else \
            None

    def _parse_str(element, text):
        return str(text).replace('\n', ' ').replace('"', '')

    def _parse_decimal(element, text):
        sign = -1 if element.get('sign', '') == '-' else +1
        return sign * Decimal(re.sub(r',', '', text)) * Decimal(10) ** Decimal(element.get('scale', '0'))

    def _parse_decimal_with_colon(element, text):
        return _parse(element, re.sub(r'.*: ', '', text), _parse_decimal)

    def _parse_date(element, text):
        return _date(text)

    def _parse_bool(element, text):
        return False if text == 'false' else True if text == 'true' else None

    def _parse_reversed_bool(element, text):
        return False if text == 'true' else True if text == 'false' else None

    # XPATH helpers
    # XML element syntax: <ns:name attribute='value'>content</ns:name>
    def _element_has_tag_name(name):
        return f"//*[local-name()='{name}']"

    def _element_has_name_attr_value(attr_value):
        return (
            f"//*[contains(@name, ':{attr_value}') "
            f"and substring-after(@name, ':{attr_value}') = '']"
        )

    def _element_has_tag_name_or_name_attr_value(value):
        return (
            f"//*[local-name()='{value}' or (contains(@name, ':{value}') "
            f"and substring-after(@name, ':{value}') = '')]"
        )

    # aliases
    _tn = _element_has_tag_name
    _av = _element_has_name_attr_value
    _tn_av = _element_has_tag_name_or_name_attr_value

    # {attribute: ([xpath_expressions], attribute_type)}
    #   attribute: identifier for financial attribute
    #   xpath_expressions: xpaths that will be tried to locate
    #   financial attribute in XBRL tree (until a value is found)
    #   attribute_type: type used to parse the attribute value
    GENERAL_XPATH_MAPPINGS = {
        'balance_sheet_date': (
            [
                _av('BalanceSheetDate'),
                _tn('BalanceSheetDate'),
            ],
            _parse_date,
        ),
        'companies_house_registered_number': (
            [
                _av('UKCompaniesHouseRegisteredNumber'),
                _tn('CompaniesHouseRegisteredNumber'),
            ],
            _parse_str,
        ),
        'entity_current_legal_name': (
            [
                _av('EntityCurrentLegalOrRegisteredName'),
                _tn('EntityCurrentLegalName'),
                (
                    "(//*[contains(@name, ':EntityCurrentLegalOrRegisteredName') "
                    "and substring-after(@name, ':EntityCurrentLegalOrRegisteredName') = '']"
                    "//*[local-name()='span'])[1]"
                ),
            ],
            _parse_str,
        ),
        'company_dormant': (
            [
                _av('EntityDormantTruefalse'),
                _av('EntityDormant'),
                _tn('CompanyDormant'),
                _tn('CompanyNotDormant'),
            ],
            [_parse_bool, _parse_bool, _parse_bool, _parse_reversed_bool],
        ),
        'average_number_employees_during_period': (
            [
                _av('AverageNumberEmployeesDuringPeriod'),
                _av('EmployeesTotal'),
                _tn('AverageNumberEmployeesDuringPeriod'),
                _tn('EmployeesTotal'),
            ],
            _parse_decimal_with_colon,
        ),
    }

    PERIODICAL_XPATH_MAPPINGS = {
        # balance sheet
        'tangible_fixed_assets': (
            [
                _tn_av('FixedAssets'),
                _tn_av('TangibleFixedAssets'),
                _av('PropertyPlantEquipment'),
            ],
            _parse_decimal,
        ),
        'debtors': (
            [
                _tn_av('Debtors'),
            ],
            _parse_decimal,
        ),
        'cash_bank_in_hand': (
            [
                _tn_av('CashBankInHand'),
                _av('CashBankOnHand'),
            ],
            _parse_decimal,
        ),
        'current_assets': (
            [
                _tn_av('CurrentAssets'),
            ],
            _parse_decimal,
        ),
        'creditors_due_within_one_year': (
            [
                _av('CreditorsDueWithinOneYear'),
                (
                    "//*[contains(@name, ':Creditors') and substring-after(@name, ':Creditors')"
                    " = '' and contains(@contextRef, 'WithinOneYear')]"
                ),
            ],
            _parse_decimal,
        ),
        'creditors_due_after_one_year': (
            [
                _av('CreditorsDueAfterOneYear'),
                (
                    "//*[contains(@name, ':Creditors') and substring-after(@name, ':Creditors')"
                    " = '' and contains(@contextRef, 'AfterOneYear')]"
                ),
            ],
            _parse_decimal,
        ),
        'net_current_assets_liabilities': (
            [
                _tn_av('NetCurrentAssetsLiabilities'),
            ],
            _parse_decimal,
        ),
        'total_assets_less_current_liabilities': (
            [
                _tn_av('TotalAssetsLessCurrentLiabilities'),
            ],
            _parse_decimal,
        ),
        'net_assets_liabilities_including_pension_asset_liability': (
            [
                _tn_av('NetAssetsLiabilitiesIncludingPensionAssetLiability'),
                _tn_av('NetAssetsLiabilities'),
            ],
            _parse_decimal,
        ),
        'called_up_share_capital': (
            [
                _tn_av('CalledUpShareCapital'),
                (
                    "//*[contains(@name, ':Equity') and substring-after(@name, ':Equity') = '' "
                    "and contains(@contextRef, 'ShareCapital')]"
                ),
            ],
            _parse_decimal,
        ),
        'profit_loss_account_reserve': (
            [
                _tn_av('ProfitLossAccountReserve'),
                (
                    "//*[contains(@name, ':Equity') and substring-after(@name, ':Equity') = '' "
                    "and contains(@contextRef, 'RetainedEarningsAccumulatedLosses')]"
                ),
            ],
            _parse_decimal,
        ),
        'shareholder_funds': (
            [
                _tn_av('ShareholderFunds'),
                (
                    "//*[contains(@name, ':Equity') and substring-after(@name, ':Equity') = '' "
                    "and not(contains(@contextRef, 'segment'))]"
                ),
            ],
            _parse_decimal,
        ),
        # income statement
        'turnover_gross_operating_revenue': (
            [
                _tn_av('TurnoverGrossOperatingRevenue'),
                _tn_av('TurnoverRevenue'),
            ],
            _parse_decimal,
        ),
        'other_operating_income': (
            [
                _tn_av('OtherOperatingIncome'),
                _tn_av('OtherOperatingIncomeFormat2'),
            ],
            _parse_decimal,
        ),
        'cost_sales': (
            [
                _tn_av('CostSales'),
            ],
            _parse_decimal,
        ),
        'gross_profit_loss': (
            [
                _tn_av('GrossProfitLoss'),
            ],
            _parse_decimal,
        ),
        'administrative_expenses': (
            [
                _tn_av('AdministrativeExpenses'),
            ],
            _parse_decimal,
        ),
        'raw_materials_consumables': (
            [
                _tn_av('RawMaterialsConsumables'),
                _tn_av('RawMaterialsConsumablesUsed'),
            ],
            _parse_decimal,
        ),
        'staff_costs': (
            [
                _tn_av('StaffCosts'),
                _tn_av('StaffCostsEmployeeBenefitsExpense'),
            ],
            _parse_decimal,
        ),
        'depreciation_other_amounts_written_off_tangible_intangible_fixed_assets': (
            [
                _tn_av('DepreciationOtherAmountsWrittenOffTangibleIntangibleFixedAssets'),
                _tn_av('DepreciationAmortisationImpairmentExpense'),
            ],
            _parse_decimal,
        ),
        'other_operating_charges_format2': (
            [
                _tn_av('OtherOperatingChargesFormat2'),
                _tn_av('OtherOperatingExpensesFormat2'),
            ],
            _parse_decimal,
        ),
        'operating_profit_loss': (
            [
                _tn_av('OperatingProfitLoss'),
            ],
            _parse_decimal,
        ),
        'profit_loss_on_ordinary_activities_before_tax': (
            [
                _tn_av('ProfitLossOnOrdinaryActivitiesBeforeTax'),
            ],
            _parse_decimal,
        ),
        'tax_on_profit_or_loss_on_ordinary_activities': (
            [
                _tn_av('TaxOnProfitOrLossOnOrdinaryActivities'),
                _tn_av('TaxTaxCreditOnProfitOrLossOnOrdinaryActivities'),
            ],
            _parse_decimal,
        ),
        'profit_loss_for_period': (
            [
                _tn_av('ProfitLoss'),
                _tn_av('ProfitLossForPeriod'),
            ],
            _parse_decimal,
        ),
    }

    # columns names used to store the companies financial attributes
    columns = (
        ['run_code', 'company_id', 'date', 'file_type', 'taxonomy']
        + [key for key in GENERAL_XPATH_MAPPINGS.keys()]
        + ['period_start', 'period_end'] + [key for key in PERIODICAL_XPATH_MAPPINGS.keys()]
    )

    def xbrl_to_rows(name, xbrl_xml_str):

        def _general_attributes(xpath_expressions, attr_type_maybe_list):
            for i, xpath in enumerate(xpath_expressions):
                attr_type = \
                    attr_type_maybe_list[i] if isinstance(attr_type_maybe_list, list) else \
                    attr_type_maybe_list
                # Reversed so we choose the last non None in the document, which stands the best
                # chance of being for the most recent period, so the current state of the company
                for e in reversed(document.xpath(xpath)):
                    yield _parse(e, e.text, attr_type)

        def _periodical_attributes(xpath_expressions, attr_type_maybe_list):
            for i, xpath in reversed(list(enumerate(xpath_expressions))):
                attr_type = \
                    attr_type_maybe_list[i] if isinstance(attr_type_maybe_list, list) else \
                    attr_type_maybe_list
                for e in reversed(document.xpath(xpath)):
                    context_ref_attr = e.xpath('@contextRef')
                    if not context_ref_attr:
                        continue
                    dates = context_dates[context_ref_attr[0]]
                    if not dates:
                        continue
                    value = _parse(e, e.text, attr_type)
                    yield (dates, value)

        def _get_dates(context):
            instant_elements = context.xpath("./*[local-name()='instant']")
            start_date_text_nodes = context.xpath("./*[local-name()='startDate']/text()")
            end_date_text_nodes = context.xpath("./*[local-name()='endDate']/text()")
            return \
                (None, None) if context is None else \
                (instant_elements[0].text.strip(), instant_elements[0].text.strip()) if instant_elements else \
                (None, None) if start_date_text_nodes[0] is None or end_date_text_nodes[0] is None else \
                (start_date_text_nodes[0].strip(), end_date_text_nodes[0].strip())

        document = etree.parse(xbrl_xml_str, etree.XMLParser(ns_clean=True))
        context_dates = {
            e.get('id'): _get_dates(e.xpath("./*[local-name()='period']")[0])
            for e in document.xpath("//*[local-name()='context']")
        }

        fn = os.path.basename(name)
        mo = re.match(r'^(Prod\d+_\d+)_([^_]+)_(\d\d\d\d\d\d\d\d)\.(html|xml)', fn)
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
            ';'.join(set(allowed_taxonomies) & set(document.getroot().nsmap.values())),
        )
        general_attributes = tuple(
            next((value for value in _general_attributes(xpath_expressions, attribute) if value is not None), None)
            for (name, (xpath_expressions, attribute)) in GENERAL_XPATH_MAPPINGS.items()
        )

        periodical_attributes_by_date_and_name = {
            (dates, name): value
            for (name, (xpath_expressions, attribute)) in PERIODICAL_XPATH_MAPPINGS.items()
            for (dates, value) in _periodical_attributes(xpath_expressions, attribute)
        }
        period_dates = reversed(sorted(list(set(dates for (dates, _) in periodical_attributes_by_date_and_name.keys()))))
        periods = tuple((
            (datetime.date.fromisoformat(period_start_end[0]), datetime.date.fromisoformat(period_start_end[1]))
            + tuple((
                periodical_attributes_by_date_and_name.get((period_start_end, name))
                for name, _ in PERIODICAL_XPATH_MAPPINGS.items()
            ))
            for period_start_end in period_dates
        ))

        yield from \
            ((core_attributes + general_attributes + period) for period in periods) if periods else \
            ((core_attributes + general_attributes + (None,) * (2 + len(PERIODICAL_XPATH_MAPPINGS))),)

    return tuple(columns), (
        row
        for name, _, chunks in stream_unzip(zip_bytes_iter)
        for row in xbrl_to_rows(name.decode(), BytesIO(b''.join(chunks)))
    )


@contextmanager
def stream_read_xbrl_daily_all(
    url='http://download.companieshouse.gov.uk/en_accountsdata.html',
    get_client=lambda: httpx.Client(transport=httpx.HTTPTransport(retries=3)),
):
    with get_client() as client:
        all_links = BeautifulSoup(httpx.get(url).content, "html.parser").find_all('a')
        zip_urls = [
            link.attrs['href'] if link.attrs['href'].strip().startswith('http://') or link.attrs['href'].strip().startswith('https://') else
            urllib.parse.urljoin(url, link.attrs['href'])
            for link in all_links
            if link.attrs.get('href', '').endswith('.zip')
        ]

        def rows():
            for zip_url in zip_urls:
                with client.stream('GET', zip_url) as r:
                    _, rows = stream_read_xbrl_zip(r.iter_bytes(chunk_size=65536))
                    yield from rows

        # Allows us to get the columns before actually iterating the real data
        columns, _ = stream_read_xbrl_zip(())

        yield columns, rows()
