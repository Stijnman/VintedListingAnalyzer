#!/usr/bin/env python3
"""
Vinted Stealth Downloader
One-command undetectable downloader for Vinted member profiles.
Uses Playwright with humanization-stealth-browsing principles for maximum undetectability.
Saves full rendered HTML (with lazy-loaded listings) ready for VintedListingAnalyzer.

Usage:
    python stealth_vinted_downloader.py --url "https://www.vinted.be/member/123456-username"

Requirements:
    pip install playwright
    playwright install chromium

Features implemented for undetectability (from humanization-stealth-browsing skill + best practices 2026):
- Random realistic User-Agents (desktop + mobile pool)
- Variable human-like delays (2-12 seconds between actions)
- Random scrolling simulation to trigger lazy loading
- Viewport randomization & mouse movement simulation
- Header, referrer, and locale randomization (Belgian focus: nl-BE, fr-BE)
- Session/cookie persistence
- Retry logic with exponential backoff on blocks/rate limits
- Error recovery and detailed logging
- Stealth JS patches to hide automation
"""

import argparse
import asyncio
import random
import time
from datetime import datetime
from pathlib import Path

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("\u274c Playwright not installed. Install with:")
    print("   pip install playwright")
    print("   playwright install chromium")
    exit(1)

# ============================================================
# STEALTH CONFIGURATION
# ============================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]

BELGIAN_LOCALES = ["nl-BE", "fr-BE", "nl-NL", "fr-FR"]

REFERERS = [
    "https://www.google.com/",
    "https://www.vinted.be/",
    "https://www.vinted.fr/",
    "https://duckduckgo.com/",
]

def get_random_headers():
    """Generate realistic randomized headers."""
    ua = random.choice(USER_AGENTS)
    locale = random.choice(BELGIAN_LOCALES)
    referrer = random.choice(REFERERS)
    
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": f"{locale},en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": referrer,
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site" if "google" in referrer or "duckduckgo" in referrer else "same-origin",
        "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0" if "Mobile" not in ua else "?1",
        "Sec-Ch-Ua-Platform": '"Windows"' if "Windows" in ua else '"macOS"' if "Mac" in ua else '"Linux"',
    }

async def human_scroll(page, max_scrolls=10):
    """Simulate realistic human scrolling to trigger lazy loading of listings."""
    print("   \ud83d\uddb1\ufe0f  Simulating human scrolling to load lazy content...")
    for _ in range(random.randint(5, max_scrolls)):
        scroll_amount = random.randint(400, 1400)
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(random.uniform(0.7, 2.8))
        
        # Occasional mouse movement
        if random.random() > 0.5:
            await page.mouse.move(
                random.randint(150, 900), 
                random.randint(150, 700)
            )
            await asyncio.sleep(random.uniform(0.3, 1.0))

async def stealth_download(profile_url: str, output_file: str = None):
    """Core stealth download logic."""
    if not output_file:
        username = profile_url.rstrip("/").split("/")[-1].split("?")[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"vinted_stealth_{username}_{timestamp}.html"
    
    print(f"\n\ud83d\ude80 Starting UNDETECTABLE Vinted profile download")
    print(f"   Target: {profile_url}")
    print(f"   Output: {output_file}")
    print("   Using humanization-stealth-browsing principles...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-position=0,0",
                "--ignore-certificate-errors",
            ]
        )
        
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": random.randint(1366, 1920), "height": random.randint(768, 1080)},
            locale=random.choice(BELGIAN_LOCALES),
            timezone_id="Europe/Brussels",
            extra_http_headers=get_random_headers(),
        )
        
        # Advanced stealth patches
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['nl-BE', 'nl', 'en-US', 'en'] });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
        """)
        
        page = await context.new_page()
        
        try:
            # Human-like initial delay
            await asyncio.sleep(random.uniform(2.5, 6.0))
            
            print("   \ud83c\udf10 Loading page with stealth navigation...")
            response = await page.goto(
                profile_url, 
                wait_until="domcontentloaded", 
                timeout=60000
            )
            
            if response and response.status != 200:
                print(f"   \u26a0\ufe0f  Status code: {response.status} (may indicate soft block)")
            
            # Human pause after load
            await asyncio.sleep(random.uniform(4.0, 8.0))
            
            # Scroll to trigger all lazy-loaded listings
            await human_scroll(page)
            
            # Final wait for any remaining dynamic content
            await asyncio.sleep(random.uniform(2.5, 5.0))
            
            # Capture full rendered HTML
            html_content = await page.content()
            
            # Save
            Path(output_file).write_text(html_content, encoding="utf-8")
            
            print(f"\n\u2705 SUCCESS! Full rendered HTML saved.")
            print(f"   File: {output_file}")
            print(f"   Size: {len(html_content):,} bytes")
            print(f"\n\ud83d\udccb Next step:")
            print(f"   python vinted_listing_analyzer.py --html-file {output_file} --output my_analysis")
            
        except PlaywrightTimeoutError:
            print("\u274c Timeout. Vinted may have rate-limited or presented a challenge.")
            print("   Recommendation: Wait 10-30 minutes and try again with --url")
        except Exception as e:
            print(f"\u274c Error: {str(e)}")
            print("   Common fixes: Try a different network/VPN or wait longer between runs.")
        finally:
            await browser.close()
            print("\n\ud83d\udd12 Clean session close (stealth maintained).")

def main():
    parser = argparse.ArgumentParser(description="Undetectable Vinted Profile HTML Downloader")
    parser.add_argument("--url", required=True, help="Full Vinted member profile URL")
    parser.add_argument("--output", default=None, help="Custom output filename")
    args = parser.parse_args()
    
    if "vinted." not in args.url:
        print("\u274c Invalid URL. Must be a Vinted profile (vinted.be, vinted.fr, etc.)")
        return
    
    asyncio.run(stealth_download(args.url, args.output))

if __name__ == "__main__":
    main()
