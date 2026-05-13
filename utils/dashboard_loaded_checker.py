
from loguru import logger
from playwright.sync_api import Page


def check_dashboard_loaded(page: Page) -> bool:

    try:
        result = page.evaluate("""
            () => {
                // Check 1: #loader hidden
                const loader = document.getElementById('loader');
                if (loader) {
                    const s = window.getComputedStyle(loader);
                    if (s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0') {
                        return { loaded: false, reason: '#loader still visible (Please Wait...)' };
                    }
                }

                // Check 2: #outerLoader hidden
                const outerLoader = document.getElementById('outerLoader');
                if (outerLoader && outerLoader.children.length > 0) {
                    const s = window.getComputedStyle(outerLoader);
                    if (s.display !== 'none') {
                        return { loaded: false, reason: '#outerLoader still visible' };
                    }
                }

                // Check 3: Knockout data bound (tbody rows have text)
                const tbodies = document.querySelectorAll('table tbody');
                let totalRows = 0;
                let populatedRows = 0;
                for (const tbody of tbodies) {
                    const rows = tbody.querySelectorAll('tr');
                    totalRows += rows.length;
                    for (const row of rows) {
                        if (row.innerText.trim().length > 0) populatedRows++;
                    }
                }
                if (totalRows === 0)    return { loaded: false, reason: 'No table rows found yet' };
                if (populatedRows === 0) return { loaded: false, reason: `${totalRows} rows found but all empty — Knockout still binding` };

                // Check 4: jQuery AJAX idle
                if (typeof window.jQuery !== 'undefined' && jQuery.active > 0) {
                    return { loaded: false, reason: `jQuery AJAX active (${jQuery.active} pending)` };
                }

                return { loaded: true, reason: `${populatedRows}/${totalRows} rows populated` };
            }
        """)
        logger.debug(f"Load check: {result['reason']}")
        return result["loaded"]

    except Exception as e:
        logger.debug(f"Load check error (page navigating?): {e}")
        return False