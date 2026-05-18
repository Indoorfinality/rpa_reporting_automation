import csv
import os
import shutil
from loguru import logger
from resources.config import Config


try:
    import xlwings as xw
except Exception:  
    xw = None


def _read_csv(file_path: str) -> list:
    """Return all rows from a UTF-8-BOM-safe CSV as a list of lists."""
    with open(file_path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.reader(fh))


def _coerce(value: str):
    """Convert a string to int or float where possible, else keep as str."""
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _clear_range(ws, cell_range: str) -> None:
    """Blank every cell in the given A1-notation range."""
    for row in ws[cell_range]:
        for cell in row:
            cell.value = None


def _write_rows(ws, start_row: int, start_col: int, rows: list) -> None:
    """Write a list-of-lists into the sheet starting at (start_row, start_col)."""
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            ws.cell(row=start_row + i, column=start_col + j, value=_coerce(value))


def update_master_from_csvs(config: Config, date_str: str) -> str:
    """Update the master template using CSVs for the given date and save a dated copy.
    The output file is created by copying the template first, then editing the copy in Excel 
    """
    dated_output_dir = os.path.join(config.output_dir, date_str)
    collections_csv = os.path.join(dated_output_dir, f"{date_str}_collections.csv")
    registrations_csv = os.path.join(dated_output_dir, f"{date_str}_registrations_state_wise.csv")
    claim_csv = os.path.join(dated_output_dir, f"{date_str}_claim_status.csv")

    if not os.path.exists(dated_output_dir):
        raise FileNotFoundError(f"Output folder not found: {dated_output_dir}")

    missing = [
        path for path in [collections_csv, registrations_csv, claim_csv] if not os.path.exists(path)
    ]
    if missing:
        missing_list = "\n".join(missing)
        raise FileNotFoundError(f"Missing CSV files:\n{missing_list}")

    if not os.path.exists(config.master_template):
        raise FileNotFoundError(f"Master template not found: {config.master_template}")

    output_file = os.path.join(dated_output_dir, f"{date_str}_master.xlsx")
    shutil.copy2(config.master_template, output_file)

    collections_rows = _read_csv(collections_csv)[1:]
    all_reg_rows = _read_csv(registrations_csv)
    reg_data_rows = all_reg_rows[2:-1]
    claim_rows = _read_csv(claim_csv)

    if xw is None:
        raise RuntimeError(
            "xlwings is required to preserve images when updating the master. "
            "Install it and ensure Microsoft Excel is available."
        )

    app = None
    try:
        app = xw.App(visible=False)
        wb = app.books.open(output_file)
        try:
            ws = wb.sheets["Sheet1"]

            ws.range("V1:Y36").clear_contents()
            if collections_rows:
                ws.range("V1").value = [[_coerce(v) for v in row] for row in collections_rows]
            logger.info(f"Collections: {len(collections_rows)} rows written to V1:Y36")

            ws.range("K2:T15").clear_contents()
            if reg_data_rows:
                ws.range("K2").value = [[_coerce(v) for v in row] for row in reg_data_rows]
            logger.info(f"Registrations: {len(reg_data_rows)} rows written to K2:T15")

            ws.range("V37:AA47").clear_contents()
            if claim_rows:
                ws.range("V37").value = [[_coerce(v) for v in row] for row in claim_rows]
            logger.info(f"Claim status: {len(claim_rows)} rows written to V37:AA47")

            wb.save()
        finally:
            wb.close()
    finally:
        if app is not None:
            app.quit()

    logger.success(f"Master updated: {output_file}")
    return output_file
