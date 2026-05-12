import sys
import os
from loguru import logger
from playwright.sync_api import sync_playwright

from resources.config import Config
from actions.login import do_login

def main():
    #Logging setup
    os.makedirs("logs", exist_ok=True)
    logger.remove()
    logger.add(
        "logs/robot_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="1 day",
        format="{time:HH:mm:ss} | {level:<8} | {message}",
    )
    logger.add(
        sys.stdout,
        level="INFO",
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
    )

    #Load and validate config
    config = Config()
    if not config.login_url in config.login_url:
        logger.error("LOGIN_URL not set.")
        sys.exit(1)
    if not config.username:
        logger.error("USERNAME not set.")
        sys.exit(1)
    if not config.password:
        logger.error("PASSWORD not set.")
        sys.exit(1)

    
    logger.info("=" * 45)
    logger.info("RPA LOGIN BOT STARTING")
    logger.info("=" * 45)
    logger.info(f"URL      : {config.login_url}")
    logger.info(f"User     : {config.username}")
    logger.info(f"Headless : {config.headless}")
    logger.info(f"Slow mo  : {config.slow_mo}ms")

    #Launch browser and run login
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=config.headless, slow_mo=config.slow_mo, channel="chrome")
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
        )
        context.set_default_timeout(config.timeout)
        page = context.new_page()

        try:
            do_login(page, config)

            logger.info("Login successful! Closing browser.")
            logger.info("Pausing 5 seconds to check the browser window...")
            page.wait_for_timeout(5000)
        except Exception as exc:
            logger.error(f"Login failed: {exc}")
        finally:
            context.close()
            browser.close()
            logger.info("Browser closed.")

if __name__ == "__main__":
    main()

