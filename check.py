"""
keywords/calendar.py
======================
Exactly what a user does:
  1. Click the "To Date" input  →  its calendar opens
  2. Find today (yellow cell = ndp-selected)
  3. Click the cell just before it  →  that is yesterday
  4. Click the Search button (btnView)
  5. Wait for results to load

Two #ndp-nepali-box divs exist on the page — one for txtFromDate,
one for txtToDate. We identify the correct one using the hidden
<span id="ndp-target-id"> inside each box which contains the
input's id ("txtToDate").
"""

import time
from loguru import logger
from playwright.sync_api import Page, Dialog, TimeoutError as PWTimeout

from resources.config import Config
from utils.page_utils import check_dashboard_loaded


def select_yesterday_and_search(page: Page, config: Config) -> None:

    # ── Step 1: Click To Date input → its calendar opens ──
    logger.info("Clicking 'To Date' input...")
    try:
        to_date = page.locator("#txtToDate")
        to_date.wait_for(state="visible", timeout=config.timeout)
        to_date.click()

        # Wait for the ToDate calendar box to become visible.
        # There are 2 #ndp-nepali-box divs. The right one has
        # <span id="ndp-target-id">txtToDate</span> inside it.
        # We wait for it to become visible using JS.
        page.wait_for_function("""
            () => {
                const boxes = document.querySelectorAll('#ndp-nepali-box');
                for (const box of boxes) {
                    const target = box.querySelector('#ndp-target-id');
                    if (target && target.innerText.trim() === 'txtToDate') {
                        const s = window.getComputedStyle(box);
                        return s.display !== 'none' && s.visibility !== 'hidden';
                    }
                }
                return false;
            }
        """, timeout=5000)
        logger.info("To Date calendar opened.")

    except Exception as e:
        page.screenshot(path="logs/error_calendar_open.png", full_page=True)
        raise RuntimeError(
            f"Could not open To Date calendar: {e}\n"
            "Screenshot → logs/error_calendar_open.png"
        )

    # ── Step 2 & 3: Find today (yellow) → click yesterday ─
    logger.info("Finding today's highlighted cell and clicking yesterday...")
    _click_yesterday(page)

    # ── Step 4: Click Search ───────────────────────────────
    logger.info("Clicking Search button (btnView)...")
    try:
        search_btn = page.locator("#btnView")
        search_btn.wait_for(state="visible", timeout=config.timeout)
        search_btn.click()
        logger.info("Search clicked.")
    except PWTimeout:
        page.screenshot(path="logs/error_search_btn.png", full_page=True)
        raise RuntimeError(
            "Search button (#btnView) not found.\n"
            "Screenshot → logs/error_search_btn.png"
        )

    # ── Step 5: Wait for results to load ──────────────────
    _wait_for_results(page, config)


# ── Helpers ───────────────────────────────────────────────────

def _click_yesterday(page: Page) -> None:
    """
    Inside the VISIBLE ToDate calendar:
      - Find ndp-selected (today, yellow)
      - Walk backwards through all td cells
      - Click the first one that has a setSelectedDay link = yesterday
    """
    try:
        result = page.evaluate("""
            () => {
                // Find the ToDate calendar box specifically
                const boxes = document.querySelectorAll('#ndp-nepali-box');
                let calBox = null;
                for (const box of boxes) {
                    const target = box.querySelector('#ndp-target-id');
                    if (target && target.innerText.trim() === 'txtToDate') {
                        const s = window.getComputedStyle(box);
                        if (s.display !== 'none' && s.visibility !== 'hidden') {
                            calBox = box;
                            break;
                        }
                    }
                }
                if (!calBox) {
                    return { success: false, reason: 'ToDate calendar box not visible' };
                }

                // Find today cell (yellow highlight)
                const todayCell = calBox.querySelector('.ndp-selected')
                                || calBox.querySelector('td.ndp-selected');
                if (!todayCell) {
                    return { success: false, reason: 'ndp-selected (today) cell not found' };
                }

                // All td cells in this calendar
                const allCells = Array.from(calBox.querySelectorAll('td'));
                const todayIndex = allCells.indexOf(todayCell);
                if (todayIndex < 0) {
                    return { success: false, reason: 'today cell index not found' };
                }

                // Walk backwards — first cell with a date link is yesterday
                for (let i = todayIndex - 1; i >= 0; i--) {
                    const link = allCells[i].querySelector('a[onclick*="setSelectedDay"]');
                    if (link) {
                        const val = link.getAttribute('onclick');
                        link.click();
                        return { success: true, reason: val };
                    }
                }

                return { success: false, reason: 'No date cell found before today' };
            }
        """)

        if result["success"]:
            logger.info(f"Yesterday selected — {result['reason']}")
            page.wait_for_timeout(500)  # let calendar close and input fill
        else:
            raise RuntimeError(f"Could not click yesterday: {result['reason']}")

    except RuntimeError:
        raise
    except Exception as e:
        page.screenshot(path="logs/error_yesterday_click.png", full_page=True)
        raise RuntimeError(
            f"Error clicking yesterday: {e}\n"
            "Screenshot → logs/error_yesterday_click.png"
        )


def _wait_for_results(page: Page, config: Config) -> None:
    """
    After Search is clicked the page re-runs all AJAX calls.
    Reuses check_dashboard_loaded() — same pattern as initial load.
    Popup handler fires every time Page Unresponsive appears.
    """
    popup_count = {"n": 0}

    def handle_popup(dialog: Dialog) -> None:
        popup_count["n"] += 1
        logger.warning(
            f"[Search Popup #{popup_count['n']}] Page Unresponsive — auto-clicking Wait..."
        )
        try:
            dialog.dismiss()
            logger.info(f"[Search Popup #{popup_count['n']}] Dismissed.")
        except Exception as e:
            logger.debug(f"Dismiss error: {e}")

    page.on("dialog", handle_popup)

    try:
        page.locator("#loader").wait_for(state="visible", timeout=10000)
        logger.info("#loader visible — search results loading...")
    except PWTimeout:
        logger.debug("#loader did not appear — continuing.")

    max_wait_sec  = 600
    poll_every_ms = 20000
    start_time    = time.time()
    logger.info(f"Waiting for search results (up to {max_wait_sec // 60} min)...")

    while True:
        elapsed    = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)

        if elapsed >= max_wait_sec:
            logger.warning("Search result timeout. Saving screenshot and continuing.")
            page.screenshot(path="logs/search_timeout.png", full_page=True)
            break

        logger.info(
            f"  [{mins}m {secs}s] Checking results... | "
            f"Popups dismissed: {popup_count['n']}"
        )

        if check_dashboard_loaded(page):
            elapsed    = int(time.time() - start_time)
            mins, secs = divmod(elapsed, 60)
            logger.success(
                f"Search results loaded in {mins}m {secs}s | "
                f"Popups: {popup_count['n']}"
            )
            break

        page.wait_for_timeout(poll_every_ms)