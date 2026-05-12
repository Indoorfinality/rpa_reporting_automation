"""
robot.py
Run with:  python robot.py

Current steps:
  1. Login  (username + password → redirects to dashboard)
  2. Click Home button (glyphicon-home → redirects to new dashboard)
"""

import sys
import os
from loguru import logger
from playwright.sync_api import sync_playwright

from resources.config import Config
from keywords.login import do_login
from keywords.navigation import click_home


def main():
    # ── Logging setup ──────────────────────────────────────
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

    # ── Validate config ────────────────────────────────────
    config = Config()

    if not config.login_url or "yourwebsite" in config.login_url:
        logger.error("LOGIN_URL not set. Open .env and fill it in.")
        sys.exit(1)
    if not config.username:
        logger.error("USERNAME not set in .env")
        sys.exit(1)
    if not config.password:
        logger.error("PASSWORD not set in .env")
        sys.exit(1)

    logger.info("=" * 45)
    logger.info("RPA BOT — STARTING")
    logger.info("=" * 45)
    logger.info(f"URL      : {config.login_url}")
    logger.info(f"Headless : {config.headless}  |  Slow mo : {config.slow_mo}ms")

    # ── Launch browser ─────────────────────────────────────
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=config.headless,
            slow_mo=config.slow_mo,
            channel="chrome",       # uses your installed Chrome
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
        )
        context.set_default_timeout(config.timeout)
        page = context.new_page()

        try:
            # ── STEP 1: Login ──────────────────────────────
            logger.info("─" * 45)
            logger.info("STEP 1 — LOGIN")
            logger.info("─" * 45)
            do_login(page, config)

            # ── STEP 2: Click Home ─────────────────────────
            logger.info("─" * 45)
            logger.info("STEP 2 — CLICK HOME BUTTON")
            logger.info("─" * 45)
            click_home(page, config)

            logger.success("=" * 45)
            logger.success("ALL STEPS COMPLETE")
            logger.success("=" * 45)

            # Pause so you can verify the dashboard in browser
            logger.info("Pausing 5 seconds — check the browser window...")
            page.wait_for_timeout(5000)

        except Exception as exc:
            logger.error(f"Bot failed: {exc}")
        finally:
            context.close()
            browser.close()
            logger.info("Browser closed.")


if __name__ == "__main__":
    main()