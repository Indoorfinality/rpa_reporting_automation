import os
import csv
from datetime import date, timedelta
from loguru import logger
from playwright.sync_api import Page
from bs4 import BeautifulSoup
from typing import List
from resources.config import Config

def extract_tables(page: Page, config: Config) -> None:
    os.makedirs(config.output_dir, exist_ok=True)

    previous_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d") 

    #get full page HTML at once
    logger.info("Reading page HTML...")
    html = page.content()
    soup = BeautifulSoup(html, "lxml")

    #Claim Status

    logger.info("Extracting: Claim Status...")
    claim_rows = _extract_by_tbody_bind(soup, "ClaimStatusSummaries")
    _save_csv(
        claim_rows,
        os.path.join(config.output_dir, f"{previous_date}_claim_status.csv"),
        "Claim Status")
    
    #Registrations State Wise
    logger.info("Extracting: Registrations State Wise...")

    registration_rows = _extract_by_id(soup, "stateWiseReg")
    _save_csv(
        registration_rows,
        os.path.join(config.output_dir, f"{previous_date}_registrations_state_wise.csv"),
        "Registrations State Wise"
    )

    #Collections
    logger.info("Extracting: Collections...")
    collection_rows = _extract_by_tbody_bind(soup, "Collections")
    _save_csv(
        collection_rows,
        os.path.join(config.output_dir, f"{previous_date}_collections.csv"),
        "Collections"
    )

    logger.success(f"All 3 CSVs saved in: {config.output_dir}/")





    ######Extractors


def _extract_by_id(soup: BeautifulSoup, table_id: str)-> list:
    """Finds a table by its HTML id, extracts all rows from thead, tbody, and tfoot"""
    table = soup.find("table", {"id":table_id})
    if not table:
            raise RuntimeError(f"Table with id='{table_id}' not found on page.")
    return _get_all_rows(table)
    

def _extract_by_tbody_bind(soup: BeautifulSoup, bind_name: str) -> list:
    """  Finds a table whose <tbody> has a data-bind attribute containing the given keyword, then extracts all rows. """

    tbody = soup.find("tbody", attrs={"data-bind": lambda v: v and bind_name in v})
    if not tbody:
        raise RuntimeError(f"Table with data-bind containing '{bind_name}' not found.")
    table = tbody.find_parent("table")
    if not table:
        raise RuntimeError(f"Could not find parent <table> for '{bind_name}'.")
    
    return _get_all_rows(table)


def _get_all_rows(table) -> List:
    """
    Extracts every row from a BeautifulSoup table element.

    """

    rows = []

    #thead rows
    thead = table.find("thead")
    if thead:
        for tr in thead.find_all("tr"):
            cells = [cell.get_text(strip=True) for cell in tr.find_all(["th","td"])]
            if any(cells):
                rows.append(cells)

    #tbody rows, where there can be multiple tbodies
    for tbody in table.find_all("tbody"):
        for tr in tbody.find_all("tr"):
            cells = [cell.get_text(strip=True) for cell in tr.find_all(["th","td"])]
            if any(cells):
                rows.append(cells)

    #tfoot rows(total rows)
    tfoot = table.find("tfoot")
    if tfoot:
        for tr in tfoot.find_all("tr"):
            cells = [cell.get_text(strip=True) for cell in tr.find_all(["th", "td"])]
        if any(cells):
            rows.append(cells) 
    return rows



def _save_csv(rows: list, filepath: str, label: str) -> None:
    """
    Saves a list of rows to a CSV file
    """
    if not rows:
        logger.warning(f"No data found for '{label}' — CSV not saved.")
        return
    
    with open (filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
        logger.success(f"Saved '{label}': {filepath}  ({len(rows)} rows)")



                
    


