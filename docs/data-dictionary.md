# Data dictionary

stream-read-xbrl converts Companies House accounts data into a single data frame of 37 columns. Each row corresponds to a single period for a single company. However, periods may be repeated corresponding to multiple submissions to Companies House.

The 37 columns can be interpreted as denormalised data of 3 source data frames - "Runs", "Companies at date in run", and "Periods for company at date in run".


## Runs

**run_code**

:   str


## Companies at date in run

**company_id**

:   str


**date**

:   date


**file_type**

:   str


**taxonomy**

:   str


**balance_sheet_date**

:   date


**companies_house_registered_number**

:   text


**entity_current_legal_name**

:   str


**company_dormant**

:   bool


**average_number_employees_during_period**

:   Decimal


## Periods for company in run

It is possible for stream-read-xbrl to not find any for a company at date in a run. If this is the case, all these values are `None`.

**period_start**

:   date


**period_end**

:   date


**tangible_fixed_assets**

:   Decimal


**debtors**

:   Decimal


**cash_bank_in_hand**

:   Decimal


**current_assets**

:   Decimal


**creditors_due_within_one_year**

:   Decimal


**creditors_due_after_one_year**

:   Decimal


**net_current_assets_liabilities**

:   Decimal


**total_assets_less_current_liabilities**

:   Decimal


**net_assets_liabilities_including_pension_asset_liability**

:   Decimal


**called_up_share_capital**

:   Decimal


**profit_loss_account_reserve**

:   Decimal


**shareholder_funds**

:   Decimal


**turnover_gross_operating_revenue**

:   Decimal


**other_operating_income**

:   Decimal


**cost_sales**

:   Decimal


**gross_profit_loss**

:   Decimal


**administrative_expenses**

:   Decimal


**raw_materials_consumables**

:   Decimal


**staff_costs**

:   Decimal


**depreciation_other_amounts_written_off_tangible_intangible_fixed**

:   Decimal


**other_operating_charges_format2**

:   Decimal


**operating_profit_loss**

:   Decimal


**profit_loss_on_ordinary_activities_before_tax**

:   Decimal


**tax_on_profit_or_loss_on_ordinary_activities**

:   Decimal


**profit_loss_for_period**

:   Decimal
