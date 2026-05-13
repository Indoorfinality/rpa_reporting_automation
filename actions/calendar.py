import time
from loguru import logger
from playwright.sync_api import Page, Dialog, TimeoutError as PWTimeout

from resources.config import Config
from utils.dashboard_loaded_checker import check_dashboard_loaded


def calender_search(page: Page, config: Config) -> None:
    logger.info("Clicking To Date...")

    #Open To Date calendar 
    try:
        to_date = page.locator("#txtToDate")
        to_date.wait_for(state="visible", timeout=config.timeout)
        to_date.click()

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
        raise RuntimeError(f"Could not open To Date calendar: {e}")

    #  Click yesterday
    logger.info("Finding today's cell and clicking the day before it...")
    _click_yesterday(page)

# Register popup handler BEFORE clicking search
    
    popup_count = {"n": 0}

    def handle_popup(dialog: Dialog) -> None:
        popup_count["n"] += 1
        logger.warning(f"[Popup #{popup_count['n']}] Page Unresponsive — auto-clicking Wait...")
        try:
            dialog.dismiss()
            logger.info(f"[Popup #{popup_count['n']}] Dismissed.")
        except Exception as e:
            logger.debug(f"Dismiss error: {e}")

    page.on("dialog", handle_popup)
    logger.debug("Popup handler registered before search click.")

    #  Click Search
    logger.info("Clicking Search button...")
    search_btn = page.locator("#btnView")
    search_btn.wait_for(state="visible", timeout=config.timeout)
    with page.expect_response(
        lambda response: "Report.ashx" in response.url,
        timeout=300000,
    ) as report_response:
        search_btn.click(timeout=300000, no_wait_after=True)
    logger.info(f"Search clicked. Waiting for Report.ashx response... ({report_response.value.status})")

    #  Wait for results
    _wait_for_results(page, config, popup_count)


def _click_yesterday(page: Page) -> None:
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

                // Find today (yellow cell)
                const todayCell = calBox.querySelector('.ndp-selected')
                                || calBox.querySelector('td.ndp-selected');
                if (!todayCell) {
                    return { success: false, reason: 'ndp-selected (today) not found' };
                }

                // All cells in this calendar
                const allCells = Array.from(calBox.querySelectorAll('td'));
                const todayIndex = allCells.indexOf(todayCell);
                if (todayIndex < 0) {
                    return { success: false, reason: 'today index not found' };
                }

                // Walk backwards — first cell with a date link = yesterday
                for (let i = todayIndex - 1; i >= 0; i--) {
                    const link = allCells[i].querySelector('a[onclick*="setSelectedDay"]');
                    if (link) {
                        link.click();
                        return { success: true, reason: link.getAttribute('onclick') };
                    }
                }
                return { success: false, reason: 'No date cell found before today' };
            }
        """)

        if result["success"]:
            logger.info(f"Yesterday selected — {result['reason']}")
            page.wait_for_timeout(500)
        else:
            raise RuntimeError(f"Could not click yesterday: {result['reason']}")

    except RuntimeError:
        raise
    except Exception as e:
        page.screenshot(path="logs/error_yesterday_click.png", full_page=True)
        raise RuntimeError(f"Error clicking yesterday: {e}")


def _wait_for_results(page: Page, config: Config, popup_count: dict) -> None:
    """
    Polls frequently for up to 5 minutes.
    Popup handler is already registered — passed in from caller.
    """
    max_wait_sec  = 300
    poll_every_ms = 5000
    start_time    = time.time()

    logger.info(f"Waiting for search results (up to {max_wait_sec // 60} min, checking every {poll_every_ms // 1000}s)...")

    while True:
        elapsed    = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)

        if elapsed >= max_wait_sec:
            logger.warning("Search timeout. Continuing anyway.")
            try:
                page.screenshot(path="logs/search_timeout.png", full_page=True)
            except Exception:
                pass
            break

        logger.info(f"  [{mins}m {secs}s] Search still running... | Popups dismissed: {popup_count['n']}")

        if check_dashboard_loaded(page):
            elapsed    = int(time.time() - start_time)
            mins, secs = divmod(elapsed, 60)
            logger.success(
                f"Search results loaded in {mins}m {secs}s | "
                f"Popups: {popup_count['n']}"
            )
            logger.info("Pausing 10 seconds so the report stays visible...")
            page.wait_for_timeout(10000)
            break

        page.wait_for_timeout(poll_every_ms)