# Data dictionary

stream-read-xbrl converts Companies House accounts data into a single data frame of 38 columns. The 38 columns can be interpreted as a denormalised data frame of 3 source data frames - "Run", "Companies at date in run", and "Periods for company at date in run".

For further details on the extraction of data, please see the [How Data Is Extracted](https://stream-read-xbrl.docs.trade.gov.uk/how-data-is-extracted/) page


## Run

**run_code**

:   str

:   Internal run processes. It is formed from the file name in Companies House, and is prefixed with 'Prod'.

**zip_url**

:   str

:   Populated by stream_read_xbrl_sync and stream_read_xbrl_sync_s3_csv, None otherwise.

:   Original URL of zip. 


## Companies at date in run

For each Run, there would be one or more "Companies at date in a run".

**company_id**

:   str

:   The unique identifier for the company that filed the account. Use this to join onto the company_number in the companieshouse.companies table.

:   Extracted from the member file name in the zip.

**date**

:   date

:   The date on which the account was filed, drawn from the balance sheet date. This is known as the accounting reference date.

:   Extracted from the member file name in the zip. 


**file_type**

:   str

:   The file format that the account document was uploaded in. This is either XML or HTML. 

:   Extracted from the member file name in the zip. 


**taxonomy**

:   str

:   The account record's taxonomy, which is the specific set of hierarchical XBRL tags designed to help organize and tag documents related to the account.


**balance_sheet_date**

:   date

:   The date that the company's balance sheet was submitted. This shows the value of everything the company owns, owes and is owed on the last day of the financial year.

:   Extracted from BalanceSheetDate XBRL field


**companies_house_registered_number**

:   text

:   The company's registration number, assigned to a company during the incorporation process to identify the company. This is a unique string of 8 characters.

:   Extracted from CompaniesHouseRegisteredNumber or UKCompaniesHouseRegisteredNumber XBRL fields


**entity_current_legal_name**

:   str

:   The official name of the company that filed the account, as it appears on the Companies House register.

:   Extracted from EntityCurrentLegalOrRegisteredName or EntityCurrentLegalName XBRL fields

**company_dormant**

:   bool

:	Indicates whether or not the company is dormant. The company is called dormant by Companies House if it had no 'significant' transactions in the financial year.

:   Extracted from EntityDormantTruefalse or EntityDormant or CompanyDormant or CompanyNotDormant XBRL fields


**average_number_employees_during_period**

:   Decimal

:	The average number of employees employed under a contract of service by the company that filed the account for the financial year.

:   Extracted from AverageNumberEmployeesDuringPeriod or EmployeesTotal or AverageNumberEmployeesDuringPeriod or EmployeesTotal XBRL fields


## Periods for company in run

For each "Company at a date in a run" there can be zero or more "Periods for company in run". In the case of zero, all the following values are `None`.

A period for a company, defined by `company_id`, `period_start` and `period_end`, may be repeated. This is because they are contained in multiple submissions of accounts data to Companies House.

**period_start**

:   date

: 	The date on which the account is made up to. This is also known as the 'accounting reference date'.

:   Extracted from the startDate XBRL field, contained within the period and context tags of the html member file


**period_end**

:   date

:   The account referencing date. This is the same as the period_start field.

:   Extracted from the endDate XBRL field, contained within the period and context tags of the html member file


**tangible_fixed_assets**

:   Decimal

:   The total value of assets that have been acquired for long term use in the company's business, and will be retained for a year or more.

:   Extracted from FixedAssets or TangibleFixedAssets or PropertyPlantEquipment XBRL fields for the period indicated by period_start and period_end


**debtors**

:   Decimal

: 	The total amount owed to the company as a result of trading activity, measured in British sterling (£).

:   Extracted from Debtors XBRL field for the period indicated by period_start and period_end


**cash_bank_in_hand**

:   Decimal

: 	The total value (in £) of any positive bank account balance plus any cash held as at the balance sheet date.

:   Extracted from CashBankInHand or CashBankOnHand XBRL fields for the period indicated by period_start and period_end


**current_assets**

:   Decimal

:   The total value (in £) of current assets owned by the company. Current assets will convert into cash quicker than fixed assets.

:   Extracted from CurrentAssets XBRL field for the period indicated by period_start and period_end


**creditors_due_within_one_year**

:   Decimal

:   The total value (in £) of goods, services or payments received by the company which are not yet paid as at the balance sheet date, but due within 1 financial year.

:   Extracted from CreditorsDueWithinOneYear or Creditors (if withinOneYear in contextRef) XBRL fields for the period indicated by period_start and period_end


**creditors_due_after_one_year**

:   Decimal

:   The total value (in £) of goods, services or payments received by the company which are not yet paid as at the balance sheet date, and due beyond 1 financial year.

:   Extracted from CreditorsDueAfterOneYear XBRL field for the period indicated by period_start and period_end

**net_current_assets_liabilities**

:   Decimal

:   The net worth (in £) of a company's current liabilities. These are amounts owing that the company expects to settle within 12 months of the balance sheet date.

:   Extracted from NetCurrentAssetsLiabilities XBRL field for the period indicated by period_start and period_end


**total_assets_less_current_liabilities**

:   Decimal

:   The net worth (in £) of a company's long term liabilities. These are amounts that the company expects to repay more than 12 months after the balance sheet date.

:   Extracted from TotalAssetsLessCurrentLiabilities XBRL field for the period indicated by period_start and period_end


**net_assets_liabilities_including_pension_asset_liability**

:   Decimal

:   The total value (in £) of fixed and current assets less minus the total value of current and long term liabilities, including the pension asset liability.

:   Extracted from NetAssetsLiabilitiesIncludingPensionAssetLiability or NetAssetsLiabilities XBRL fields for the period indicated by period_start and period_end


**called_up_share_capital**

:   Decimal

:   The total nominal or face value (in £) of shares that the company has issued to shareholders.

:   Extracted from CalledUpShareCapital XBRL field for the period indicated by period_start and period_end


**profit_loss_account_reserve**

:   Decimal

:   The total value (in £) of any other reserves not included in the profit and loss account.

:   Extracted from ProfitLossAccountReserve XBRL field for the period indicated by period_start and period_end


**shareholder_funds**

:   Decimal

:   The total value (in £) of equity in the company which belongs to the company's stakeholders.

:   Extracted from ShareholderFunds XBRL field for the period indicated by period_start and period_end


**turnover_gross_operating_revenue**

:   Decimal

:   The total income (in £) after subtracting operating expenses and other costs from total revenue.

:   Extracted from TurnoverGrossOperatingRevenue or TurnoverRevenue XBRL fields for the period indicated by period_start and period_end


**other_operating_income**

:   Decimal

:   The total income (in £) from all other operating activities which are not related to the principal activities of the company, such as gains/losses from disposals.

:   Extracted from OtherOperatingIncome or OtherOperatingIncomeFormat2 XBRL fields for the period indicated by period_start and period_end

**cost_sales**

:   Decimal

:   The total value (in £) of merchandise sold by the company in the stated period.

:   Extracted from CostSales XBRL field for the period indicated by period_start and period_end


**gross_profit_loss**

:   Decimal

:   The total value (in £) of the accumulated profits or earnings of the company over its lifetime.

:   Extracted from GrossProfitLoss XBRL field for the period indicated by period_start and period_end


**administrative_expenses**

:   Decimal

:   The total cost (in £) the company has incurred not directly tied to a specific function, such as rent and insurance.

:   Extracted from AdministrativeExpenses XBRL field for the period indicated by period_start and period_end


**raw_materials_consumables**

:   Decimal

:   The total cost (in £) of all commodities that are directly attributable to the production of a good or a service.

:   Extracted from RawMaterialsConsumables or RawMaterialsConsumablesUsed XBRL fields for the period indicated by period_start and period_end


**staff_costs**

:   Decimal

:   The total staff costs (in £) of the company relating to the financial year. This includes wages, salaries, social security costs and pension costs.

:   Extracted from StaffCosts or StaffCostsEmployeeBenefitsExpense XBRL fields for the period indicated by period_start and period_end


**depreciation_other_amounts_written_off_tangible_intangible_fixed**

:   Decimal

:   The total value (in £) written off by the company to account for the decrease in value of capital assets over time.
    
:   Extracted from DepreciationOtherAmountsWrittenOffTangibleIntangibleFixedAssets or DepreciationAmortisationImpairmentExpense XBRL fields for the period indicated by period_start and period_end


**other_operating_charges_format2**

:   Decimal

:   The total cost (in £) the company has incurred due to other operating income not arising from turnover or the company's principal activities.

:   Extracted from OperatingProfitLoss or OtherOperatingExpensesFormat2 XBRL fields for the period indicated by period_start and period_end


**operating_profit_loss**

:   Decimal

:   The company's total profit (in £) from business operations before deduction of interest and taxes. This is the gross profit minus operating expenses.

:   Extracted from OtherOperatingChargesFormat2 XBRL field for the period indicated by period_start and period_end


**profit_loss_on_ordinary_activities_before_tax**

:   Decimal

:   The company's total profit (in £) from both operating and financial activities carried out, before the deduction of taxes.

:   Extracted from ProfitLossOnOrdinaryActivitiesBeforeTax XBRL field for the period indicated by period_start and period_end


**tax_on_profit_or_loss_on_ordinary_activities**

:   Decimal

:   The total tax amount applied (in £) to a company's total profit from both operating and financial activities.

:   Extracted from TaxOnProfitOrLossOnOrdinaryActivities or TaxTaxCreditOnProfitOrLossOnOrdinaryActivities XBRL fields for the period indicated by period_start and period_end


**profit_loss_for_period**

:   Decimal

:   The total value (in £) of the accumulated profits or earnings of the company for the stated accounting reference period.

:   Extracted from ProfitLoss or ProfitLossForPeriod XBRL fields for the period indicated by period_start and period_end