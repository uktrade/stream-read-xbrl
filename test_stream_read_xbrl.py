import re

import httpx

from stream_read_xbrl import stream_read_xbrl_zip


def test_stream_read_xbrl_zip():
    with httpx.stream('GET', 'http://download.companieshouse.gov.uk/Accounts_Bulk_Data-2023-03-02.zip') as r:
        columns, rows = stream_read_xbrl_zip(r.iter_bytes(chunk_size=65536))
        assert columns == (
            'run_code',
            'company_id',
            'date',
            'file_type',
            'taxonomy',
            'period_start',
            'period_end',
            'balance_sheet_date',
            'companies_house_registered_number',
            'entity_current_legal_name',
            'company_dormant',
            'average_number_employees_during_period',
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
        )
        count = 0
        for row in rows:
            count += 1
            assert len(row) == len(columns)
            row_dict = dict(zip(columns, row))
            assert re.match(r'(\d{8})|([A-Z]{2}\d{6})', row_dict['company_id'])

        assert count > 1
