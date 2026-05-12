from loguru import logger
from playwright.sync_api import Page, TimeoutError as PWTimeout
from resources.config import Config

def do_login(page: Page, config: Config) -> None:
    """
    Login flow for: Username and Password form → redirects to home.


    """

    #Open login page
    logger.info(f"Opening: {config.login_url}")

    try:
        page.goto(config.login_url, wait_until="domcontentloaded", timeout=config.timeout)
    except PWTimeout:
        logger.warning("Page took long to load — continuing anyway.")
    
    logger.debug(f"Page title: {page.title()}")

    #Fill username
    logger.info("Filling username...")
    try:
        username_field = page.locator(config.sel_username)
        username_field.wait_for(state="visible", timeout=config.timeout)
        username_field.click()
        username_field.fill(config.username)
        logger.debug("Username filled.")

    except PWTimeout:
        page.screenshot(path="logs/error_username_field.png", full_page=True)
        raise RuntimeError(
            f"Username field not found using selector: '{config.sel_username}'\n"
            f"  Screenshot saved in logs/error_username_field.png\n"
            f"  Fix: update sel_username in resources/config.py"
        )
    
    #Fill password
    logger.info("Filling password...")
    try:
        password_field = page.locator(config.sel_password)
        password_field.wait_for(state="visible", timeout=config.timeout)
        password_field.click()
        password_field.fill(config.password)
        logger.debug("Password filled.")

    except PWTimeout:
        page.screenshot(path="logs/error_password_field.png", full_page=True)
        raise RuntimeError(
            f"Password field not found using selector: '{config.sel_password}'\n"
            f"  Screenshot saved in logs/error_password_field.png\n"
            f"  Fix: update sel_password in resources/config.py"
        )
    
    #Click login button
    logger.info("Clicking login button...")
    try:
        login_btn = page.locator(config.sel_login_btn)
        login_btn.wait_for(state="visible", timeout=config.timeout)
        login_btn.click()
        logger.debug("Login button clicked.")
    except PWTimeout:
        page.screenshot(path="logs/error_login_button.png", full_page=True)
        raise RuntimeError(
            f"Login button not found using selector: '{config.sel_login_btn}'\n"
            f"  Screenshot saved in logs/error_login_button.png\n"
            f"  Fix: update sel_login_btn in resources/config.py"
        )
    
    #Wait for home to load
    logger.info("Waiting for home to load...")
    try:
       page.wait_for_url( lambda url: url.rstrip("/") != config.login_url.rstrip("/"),
            timeout=config.timeout,)
       logger.debug("URL changed after login.")
    except PWTimeout:
        page.screenshot(path="logs/error_no_redirect.png", full_page=True)
        raise RuntimeError(
            "Page did not redirect after login within the timeout.\n"
            f"  Screenshot saved in logs/error_no_redirect.png\n"
            "  Fix: check if login was successful and if sel_logged_in selector is correct."
        )
    
    try:
        page.wait_for_load_state("networkidle", timeout=config.timeout)
    except PWTimeout:
        logger.warning("Network did not fully settle — continuing anyway.")

    # Give the home page extra time to fully stabilize after login
    page.wait_for_timeout(10000)

    # confirm login
    current_url = page.url
    logger.debug(f"Home URL: {current_url}")
    logger.debug(f"Home title: {page.title()}")

    # Verify URL matches home page
    if current_url.rstrip("/") != config.home_url.rstrip("/"):
        page.screenshot(path="logs/error_url_mismatch.png", full_page=True)
        raise RuntimeError(
            f"URL mismatch after login.\n"
            f"  Expected: {config.home_url}\n"
            f"  Got: {current_url}\n"
            f"  Screenshot saved in logs/error_url_mismatch.png"
        )
    logger.info("URL verified: on home page.")

    if config.sel_logged_in:
        try:
            page.locator(config.sel_logged_in).wait_for(state="visible", timeout=config.timeout)
            logger.info("Login confirmed by sel_logged_in element.")
        except PWTimeout:
            page.screenshot(path="logs/error_login_confirmation.png", full_page=True)
            raise RuntimeError(
                f"Login confirmation element not found using selector: '{config.sel_logged_in}'\n"
                f"  Screenshot saved in logs/error_login_confirmation.png\n"
                "  Fix: update sel_logged_in in resources/config.py or check if login was successful."
            )
    logger.success(f"Login successful! Navigated to {current_url}!")
    
