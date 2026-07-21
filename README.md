# VintedListingAnalyzer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)


This Python tool is designed to parse and analyze downloaded Vinted listing data to help users evaluate the competitiveness of the prices.

## Features

The script evaluates listings based on numerous criteria including:
 * Brand tier classification
 * Seller reputation analysis
 * Image quality assessment (heuristic based on photo count)
 * Authenticity checks
 * SEO and tag optimization (title-focused)
 * Presence of measurements
 * Material descriptions and background quality notes
 * Estimated shipping costs notes and price drop trends

## Installation

```bash
pip install beautifulsoup4 lxml playwright
playwright install chromium
```

## Usage

### Basic usage with sample data (for testing)
```bash
python vinted_listing_analyzer.py
```

### Analyze your own Vinted profile HTML
1. Go to the Vinted member profile page you want to analyze.
2. Right-click → "View Page Source" or use DevTools (F12) → Elements tab → right-click the main listings container or `<body>` → Copy → Copy outerHTML / Copy element.
3. Save it to a file, e.g. `my_profile.html`
4. Run:
```bash
python vinted_listing_analyzer.py --html-file my_profile.html --output my_vinted_analysis
```

The tool will generate:
- Console report with scores and actionable recommendations
- `my_vinted_analysis.json` — full structured data
- `my_vinted_analysis.csv` — tabular export for further analysis (Excel/Google Sheets)

## Undetectable Way to Download Profile HTML (Recommended)

For the most reliable and stealthy results, use the included `stealth_vinted_downloader.py`:

```bash
python stealth_vinted_downloader.py --url "https://www.vinted.be/member/YOUR-USERNAME"
```

This script:
- Uses Playwright with advanced stealth patches
- Simulates human scrolling to load all lazy content
- Rotates User-Agents, locales (nl-BE/fr-BE), referrers, and headers
- Adds realistic random delays and mouse movements
- Is designed following the humanization-stealth-browsing skill principles

**Requirements for stealth downloader:**
```bash
pip install playwright
playwright install chromium
```

## Output Example

The analyzer produces per-listing scores (0-10) across all criteria + an overall competitiveness score + specific recommendations to improve the listing or identify good deals.

## Scope & Limitations (MVP)

- Works best with HTML containing visible item cards from the profile grid.
- Detailed descriptions, multiple photos count, and measurements are best captured when the HTML includes expanded info or you analyze individual item pages.
- Image quality is currently a simple heuristic (photo count). Full computer vision analysis can be added in future versions.
- Price competitiveness uses internal heuristics + discount detection. For true market comparison, integrate live Vinted search or price databases in a future iteration.
- No live scraping included in the core analyzer (by design — you provide the HTML to respect Vinted's ToS and avoid blocks). The stealth downloader is an optional helper.

## Roadmap / Future Enhancements

- Per-item page fetching (with stealth headers)
- Computer vision for background cleanliness, photo quality scoring, logo detection
- Real-time price comparison against similar sold items
- Dutch/French localization of recommendations
- Integration with user's inventory for "my listings health check"

## License

MIT — feel free to adapt for your own Vinted flipping or reselling workflow.

---

*Created as part of the ODBE Autonomous Hierarchical Orchestrator v2 project workflow.*