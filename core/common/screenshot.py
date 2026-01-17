from typing import Optional
from pathlib import Path
import sys

try:
    from playwright.async_api import async_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    print("Playwright not installed. Please install it with `pip install playwright && playwright install chromium`")
    _PLAYWRIGHT_AVAILABLE = False
except Exception as e:
    import traceback
    print("Playwright import failed:")
    traceback.print_exc()
    _PLAYWRIGHT_AVAILABLE = False


async def html_to_image_bytes(html: str, width: int = 900, height: int = 600, timeout: int = 30000, base_path: Optional[Path] = None) -> Optional[bytes]:
    """Render given HTML to PNG bytes using Playwright (Async) if available.
    Returns None on failure.
    """
    if not _PLAYWRIGHT_AVAILABLE:
        print("Playwright unavailable, cannot render image.", file=sys.stderr)
        return None
    try:
        async with async_playwright() as p:
            # 在 Docker/Linux 环境中需要添加额外参数
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--single-process'
                ]
            )
            page = await browser.new_page(viewport={"width": width, "height": height})
            
            # Workaround: Inject <base href="...">
            if base_path:
                base_href = base_path.as_uri() + "/"
                if "<head>" in html:
                    html = html.replace("<head>", f'<head><base href="{base_href}">')
                else:
                    html = f'<base href="{base_href}">' + html

            await page.set_content(html, wait_until="networkidle", timeout=timeout)
            # Use full_page=True to capture the entire scrollable content
            img = await page.screenshot(type="png", full_page=True)
            await browser.close()
            return img
    except Exception as e:
        import traceback
        print(f"Detailed Playwright Error: {e}", file=sys.stderr)
        traceback.print_exc()
        err_str = str(e)
        if "Executable doesn't exist" in err_str:
            print("Tip: Run `playwright install chromium` in your console.", file=sys.stderr)
        elif "browser has been closed" in err_str.lower() or "Target page, context or browser has been closed" in err_str:
            print("Tip: Browser crashed, possibly missing system dependencies.", file=sys.stderr)
            print("For Docker/Linux, try: apt-get install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2", file=sys.stderr)
        return None


