import datetime
import os

import pandas as pd
from openpyxl.utils import get_column_letter

# reports/ folder in the project root (git-ignored)
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")

RISK_ORDER = {"High": 0, "Medium": 1, "Low": 2}  # alphabetical order would put Low before Medium


def _format_sheet(worksheet, header_row=1):
    """Make a sheet auditor-friendly: frozen header, filter arrows, readable column widths."""
    worksheet.freeze_panes = worksheet.cell(row=header_row + 1, column=1)  # keep the header visible
    worksheet.auto_filter.ref = (f"A{header_row}:{get_column_letter(worksheet.max_column)}"
                                 f"{worksheet.max_row}")
    _set_widths(worksheet, first_row=header_row)


def _set_widths(worksheet, first_row=1):
    """Column width = longest value from the header down (ignores the title row), max 60."""
    for column in worksheet.iter_cols(min_row=first_row):
        longest = max((len(str(cell.value)) for cell in column if cell.value is not None), default=8)
        worksheet.column_dimensions[column[0].column_letter].width = min(longest + 2, 60)


def write_excel_report(summary, exceptions, seller_risk, benford_results, statistical_tests):
    """Write the audit results to reports/audit_report_<date>.xlsx and return the file path.

    Sheets: Summary, one sheet per test (T01-T06), Seller risk (top 50), Statistics.
    """
    run_date = datetime.date.today().isoformat()
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, f"audit_report_{run_date}.xlsx")

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # 1. Summary: a title row (when and on what data), then the table from row 3
        summary.to_excel(writer, sheet_name="Summary", index=False, startrow=2)
        sheet = writer.sheets["Summary"]
        sheet["A1"] = f"Audit run on {run_date} - data source: olist.db"
        _format_sheet(sheet, header_row=3)

        # 2. One sheet per test: High risk first, then the largest amounts
        for test_id, df in exceptions.groupby("test_id"):
            df = (df.assign(_risk_order=df["risk_level"].map(RISK_ORDER))
                    .sort_values(["_risk_order", "amount"], ascending=[True, False])
                    .drop(columns="_risk_order"))
            df.round({"amount": 2}).to_excel(writer, sheet_name=test_id, index=False)
            _format_sheet(writer.sheets[test_id])

        # 3. Seller risk: the 50 highest-ranked sellers, with the reasons
        top_sellers = seller_risk.sort_values("risk_rank").head(50).round(3)  # rounded for readability only
        top_sellers.to_excel(writer, sheet_name="Seller risk", index=False)
        _format_sheet(writer.sheets["Seller risk"])

        # 4. Statistics: the 2 test results, then the Benford table 3 rows below
        statistical_tests.to_excel(writer, sheet_name="Statistics", index=False)
        benford_start = len(statistical_tests) + 3
        benford_results.to_excel(writer, sheet_name="Statistics", index=False, startrow=benford_start)
        sheet = writer.sheets["Statistics"]
        sheet.freeze_panes = "A2"
        _set_widths(sheet)

    return path
