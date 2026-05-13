from loguru import logger
from playwright.sync_api import Page, Dialog, TimeoutError as PWTimeout
import time
from resources.config import Config
from utils.dashboard_loaded_checker import check_dashboard_loaded


def click_home(page: Page, config: Config) -> None:
    "Clicks the home button and waits for the new dashboard page to load"
    popup_count = {"n": 0}
    def handle_popup(dialog: Dialog) -> None:
        popup_count["n"] += 1
        logger.warning(f"Page Unresponsive popup detected: [{dialog.type}]")
        logger.warning("Auto-clicking Wait...")
        dialog.dismiss()
        logger.info(f"Popup dismissed. Waiting {config.popup_recovery_ms}ms for page to recover...")
        page.wait_for_timeout(config.popup_recovery_ms)
        logger.info("Recovery wait done.")


    page.on("dialog", handle_popup)
    logger.debug("Popup handled...")

    #Record current URL before click
    url_before = page.url
    logger.info(f"Current URL before home click: {url_before}")

    #Click the home button
    try:
        home_btn = page.locator(config.sel_home_link)
        if home_btn.count() == 0:
            # Fallback to the span itself
            home_btn = page.locator(config.sel_home_btn)
        home_btn.first.wait_for(state="visible", timeout=config.timeout)
        logger.info("Home button found. Clicking...")
        home_btn.click()
        logger.debug("Home button clicked.")
    except PWTimeout:
        page.screenshot(path="logs/error_home_button.png", full_page=True)
        raise RuntimeError(
        "Home button not found.\n"
        "  Screenshot saved → logs/error_home_button.png"
    )

    #Wait for navigating to Dashboard
    logger.info("Waiting for redirect to new dashboard URL...")

    try:
        page.wait_for_url(
            lambda url: url.rstrip("/") != url_before.rstrip("/"),
            timeout=config.timeout,
        )
        logger.debug(f"Redirected to: {page.url}")
    except PWTimeout:
        logger.warning(
            "URL did not change after clicking home"
        )

    #Wait for page to fully load
    logger.info("Waiting for page to fully load...")

    #Wait for all requests to complete
    try:
        page.wait_for_load_state("networkidle", timeout=config.timeout)
        logger.debug("Page load state: networkidle")
    except PWTimeout:
        logger.warning("Network idle timed out — page may still be loading. Continuing.")

    #Waiting until data rows are populated
    max_wait_sec = 300
    poll_every_ms = 20000
    start_time = time.time()

    logger.info(f"Waiting for Knockout.js data to bind into tables "
        f"(up to {max_wait_sec // 60} min)...")
    
    logger.info("Popup handler is active — 'Page Unresponsive' dialogs will be auto-dismissed.")

    dashboard_loaded = False

    while True:
        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        if elapsed >= max_wait_sec:
            logger.warning(
                f"Reached {max_wait_sec // 60} min timeout. "
                "Saving screenshot and continuing..."
            )
            page.screenshot(path="logs/error_dashboard_load_timeout.png", full_page=True)
            logger.warning("Screenshot saved to logs/error_dashboard_load_timeout.png")
            break
        
        logger.info(f"  [{mins}m {secs}s] Checking dashboard... "
            f"| Popups dismissed: {popup_count['n']}")
        
        loaded = check_dashboard_loaded(page)

        if loaded:
            dashboard_loaded = True
            page.wait_for_timeout(10000)
            logger.success(
                f"Dashboard fully loaded! "
                f"Time: {mins}m {secs}s | "
                f"Popups handled: {popup_count['n']}"
            )
            break
        # Not ready yet waiting and trying again
        page.wait_for_timeout(poll_every_ms)

    elapsed_final = int(time.time() - start_time)
    mins, secs = divmod(elapsed_final, 60)

    
    logger.success(
        f"Home navigation complete.\n"
        f"  URL            : {page.url}\n"
        f"  Title          : {page.title()}\n"
        f"  Time taken     : {mins}m {secs}s\n"
        f"  Popups handled : {popup_count['n']}\n"
        f"  Data loaded    : {dashboard_loaded}"
    )


    






