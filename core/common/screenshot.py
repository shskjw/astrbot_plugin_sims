from typing import Optional
from pathlib import Path

try:
    from playwright.async_api import async_playwright
    _PLAYWRIGHT_AVAILABLE = True
except Exception as e:
    import traceback
    print("Playwright import failed:")
    traceback.print_exc()
    _PLAYWRIGHT_AVAILABLE = False


async def html_to_image_bytes(html: str, width: int = 900, height: int = 600, timeout: int = 10000, base_path: Optional[Path] = None) -> Optional[bytes]:
    """Render given HTML to PNG bytes using Playwright (Async) if available.
    Returns None on failure.
    """
    if not _PLAYWRIGHT_AVAILABLE:
        return None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": width, "height": height})
            
            # Workaround: Inject <base href="...">
            if base_path:
                base_href = base_path.as_uri() + "/"
                if "<head>" in html:
                    html = html.replace("<head>", f"<head><base href=""{base_href}"">")
                else:
                    html = f"<base href=""{base_href}"">" + html

            await page.set_content(html, wait_until="networkidle", timeout=timeout)
            # Use full_page=True to capture the entire scrollable content
            img = await page.screenshot(type="png", full_page=True)
            await browser.close()
            return img
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None

