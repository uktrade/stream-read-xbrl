# Data dictionary

stream-read-xbrl converts Companies House accounts data into a single data frame of 37 columns. The 37 columns can be interpreted as a denormalised data frame of 3 source data frames - "Runs", "Companies at date in run", and "Periods for company at date in run".


## Runs

There should be one or more runs in all data extracted by stream-read-xbrl.

**run_code**

:   str


## Companies at date in run

For each Run, there would be one or more "Companies at date in a run".

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

For each "Company at a date in a run" there can be zero or more "Periods for company in run". In the case of zero, all the following values are `None`.

A period for a company, defined by `company_id`, `period_start` and `period_end`, may be repeated. This is because they are contained in multiple submissions of accounts data to Companies House.

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
