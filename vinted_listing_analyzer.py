#!/usr/bin/env python3
"""
VintedListingAnalyzer
A tool to parse downloaded Vinted member profile HTML and evaluate listing competitiveness.
"""

import argparse
import re
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup, Tag

# ============================================================
# BRAND TIER CONFIGURATION (easily extensible)
# ============================================================
BRAND_TIERS: Dict[str, List[str]] = {
    "luxury": [
        "louis vuitton", "gucci", "chanel", "dior", "hermes", "prada", "fendi",
        "balenciaga", "saint laurent", "celine", "bottega veneta", "givenchy",
        "valentino", "versace", "burberry"
    ],
    "premium": [
        "ralph lauren", "tommy hilfiger", "levi's", "calvin klein", "michael kors",
        "adidas originals", "nike", "puma", "under armour", "the north face",
        "patagonia", "scotch & soda", "g-star raw", "jack & jones", "selected homme",
        "boss", "hugo boss", "lacoste", "fred perry"
    ],
    "mid": [
        "zara", "h&m", "mango", "pull&bear", "bershka", "massimo dutti",
        "uniqlo", "cos", "armani exchange", "guess", "esprit", "only", "veromoda"
    ],
    "fast_fashion": [
        "shein", "romwe", "fashion nova", "boohoo", "pretty little thing",
        "missguided", "nastygal", "forever 21"
    ]
}

def get_brand_tier(brand: str) -> str:
    """Classify brand into tier for value/retention scoring."""
    if not brand or not isinstance(brand, str):
        return "unknown"
    b = brand.lower().strip()
    for tier, brands in BRAND_TIERS.items():
        if any(bb in b for bb in brands):
            return tier
    return "unknown"


# ============================================================
# SAMPLE HTML (realistic Vinted-like structure for demo)
# ============================================================
SAMPLE_HTML = """<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <title>Vinted - fashionflipper92</title>
</head>
<body>
<div class="profile-header">
    <h1 class="username">fashionflipper92</h1>
    <div class="reputation">
        <span class="rating">4.8</span>
        <span class="ratings-count">(1,234 ratings)</span>
        <span class="location">Ghent, Belgium</span>
    </div>
    <div class="stats">Member since 2021 • 892 items sold • Excellent seller</div>
</div>

<div class="listings-grid">
    <!-- Listing 1: Good Nike example -->
    <div class="item-card" data-item-id="9876543210" data-photos="6">
        <a href="/items/9876543210-nike-air-force-1-07" class="item-link">
            <img src="https://images.vinted.net/..." alt="Nike Air Force 1" class="item-photo">
            <div class="item-details">
                <span class="brand">Nike</span>
                <h3 class="item-title">Air Force 1 '07 White</h3>
                <div class="item-meta">
                    <span class="size">EU 42</span>
                    <span class="condition">Very good</span>
                </div>
                <div class="price-container">
                    <span class="current-price">€52</span>
                    <span class="original-price">€65</span>
                    <span class="discount">-20%</span>
                </div>
            </div>
        </a>
        <div class="item-description-snippet">
            Classic Nike Air Force 1 in white. Worn only a few times, no major flaws.
            Insole length: 27.5 cm. 100% leather upper with rubber sole.
            measurements available upon request. Clean and ready to wear.
        </div>
    </div>

    <!-- Listing 2: Luxury with authenticity proof -->
    <div class="item-card" data-item-id="1122334455" data-photos="5">
        <a href="/items/1122334455-louis-vuitton-speedy" class="item-link">
            <img src="https://images.vinted.net/..." alt="Louis Vuitton Speedy" class="item-photo">
            <div class="item-details">
                <span class="brand">Louis Vuitton</span>
                <h3 class="item-title">Speedy 30 Monogram Canvas</h3>
                <div class="item-meta">
                    <span class="size">One size</span>
                    <span class="condition">Good</span>
                </div>
                <div class="price-container">
                    <span class="current-price">€890</span>
                </div>
            </div>
        </a>
        <div class="item-description-snippet">
            Authentic Louis Vuitton Speedy 30 in monogram canvas. Comes with original dustbag and box.
            Receipt and certificate of authenticity available. Serial number visible.
            Very good condition with normal signs of use. measurements: 30x21x17 cm.
        </div>
    </div>

    <!-- Listing 3: Poorly optimized fast fashion -->
    <div class="item-card" data-item-id="5566778899" data-photos="2">
        <a href="/items/5566778899-shein-dress" class="item-link">
            <img src="https://images.vinted.net/..." alt="Shein dress" class="item-photo">
            <div class="item-details">
                <span class="brand">Shein</span>
                <h3 class="item-title">Summer dress floral</h3>
                <div class="item-meta">
                    <span class="size">M</span>
                    <span class="condition">New with tags</span>
                </div>
                <div class="price-container">
                    <span class="current-price">€18</span>
                </div>
            </div>
        </a>
        <div class="item-description-snippet">
            Nice dress. Good quality.
        </div>
    </div>

    <!-- Listing 4: Mid brand with measurements but high price -->
    <div class="item-card" data-item-id="7788990011" data-photos="4">
        <a href="/items/7788990011-zara-jeans" class="item-link">
            <img src="https://images.vinted.net/..." alt="Zara jeans" class="item-photo">
            <div class="item-details">
                <span class="brand">Zara</span>
                <h3 class="item-title">High waisted mom jeans blue</h3>
                <div class="item-meta">
                    <span class="size">EU 38 / 28</span>
                    <span class="condition">Good</span>
                </div>
                <div class="price-container">
                    <span class="current-price">€35</span>
                    <span class="original-price">€45</span>
                </div>
            </div>
        </a>
        <div class="item-description-snippet">
            Zara high waisted mom fit jeans. Worn a couple of times.
            Waist: 72 cm, inseam: 78 cm, rise: 28 cm. 98% cotton 2% elastane.
        </div>
    </div>
</div>
</body>
</html>
"""


# ============================================================
# PARSING FUNCTIONS
# ============================================================
def extract_seller_info(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract seller profile information using heuristics and regex."""
    info: Dict[str, Any] = {
        "username": "Unknown Seller",
        "rating": None,
        "num_ratings": 0,
        "location": "",
        "member_since": "",
        "items_sold": 0,
        "raw_text_sample": ""
    }

    # Username
    user_el = soup.select_one('.username, h1, .profile-name, [class*="user-name"], [class*="profile-header"] h1')
    if user_el:
        info["username"] = user_el.get_text(strip=True)
    else:
        # Fallback: first h1 or strong text that looks like username
        for el in soup.find_all(['h1', 'h2', 'strong']):
            txt = el.get_text(strip=True)
            if len(txt) > 3 and len(txt) < 30 and not any(c.isdigit() for c in txt[:3]):
                info["username"] = txt
                break

    full_text = soup.get_text(separator=" ", strip=True)
    info["raw_text_sample"] = full_text[:500]

    # Rating: 4.8 / 5 or 4.8 (1234 ratings)
    rating_match = re.search(r'(\d\.\d)\s*[/•]?\s*5?\s*[\(\[]?\s*(\d[\d\s,.k]+)', full_text, re.IGNORECASE)
    if rating_match:
        try:
            info["rating"] = float(rating_match.group(1))
            num_str = rating_match.group(2).replace(" ", "").replace(",", "").replace("k", "000").replace(".", "")
            info["num_ratings"] = int(float(num_str))
        except (ValueError, TypeError):
            pass

    # Location (common Belgian/Dutch cities)
    loc_match = re.search(r'\b(Ghent|Gent|Brussels|Bruxelles|Antwerp|Antwerpen|Amsterdam|Rotterdam|Leuven|Bruges|Brugge|Belgium|België|Nederland)\b', full_text, re.IGNORECASE)
    if loc_match:
        info["location"] = loc_match.group(1)

    # Member since
    since_match = re.search(r'member since\s*(\d{4})|lid sinds\s*(\d{4})', full_text, re.IGNORECASE)
    if since_match:
        info["member_since"] = since_match.group(1) or since_match.group(2)

    # Items sold
    sold_match = re.search(r'(\d[\d\s,.k]+)\s*(items sold|verkocht|items verkocht)', full_text, re.IGNORECASE)
    if sold_match:
        try:
            num_str = sold_match.group(1).replace(" ", "").replace(",", "").replace("k", "000")
            info["items_sold"] = int(float(num_str))
        except (ValueError, TypeError):
            pass

    return info


def extract_listings(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract individual listings from profile grid. Robust multi-strategy approach."""
    listings: List[Dict[str, Any]] = []

    # Strategy 1: Known Vinted-like classes
    cards: List[Tag] = soup.select(
        '.item-card, .feed-grid__item, article[class*="item"], '
        'div[class*="ItemCard"], div[class*="item-card"], div[class*="listing"]'
    )

    # Strategy 2: Broader fallback
    if not cards:
        cards = soup.find_all(
            ['div', 'article', 'li'],
            class_=lambda c: bool(c and any(kw in str(c).lower() for kw in ['item', 'card', 'listing', 'product', 'feed']))
        )

    for card in cards:
        if not isinstance(card, Tag):
            continue

        listing: Dict[str, Any] = {
            "title": "",
            "brand": "",
            "price": None,
            "original_price": None,
            "discount_percent": 0.0,
            "size": "",
            "condition": "",
            "description": "",
            "url": "",
            "photo_count": 1,
            "raw_card_text": card.get_text(separator=" ", strip=True)[:300]
        }

        # Title
        title_el = card.select_one('.item-title, h3, h4, .title, a[href*="/items/"]')
        if title_el:
            listing["title"] = title_el.get_text(strip=True)

        # Brand
        brand_el = card.select_one('.brand, [class*="brand"], [class*="designer"]')
        if brand_el:
            listing["brand"] = brand_el.get_text(strip=True)
        elif listing["title"]:
            # Fallback: first word often brand
            parts = listing["title"].split(maxsplit=1)
            listing["brand"] = parts[0] if parts else ""

        # Price (current)
        price_el = card.select_one('.current-price, .price, [class*="price"]:not([class*="original"])')
        if price_el:
            price_text = price_el.get_text(strip=True)
            match = re.search(r'€?\s*([\d.,]+)', price_text.replace(" ", ""))
            if match:
                try:
                    listing["price"] = float(match.group(1).replace(",", "."))
                except ValueError:
                    pass

        # Original price & discount
        orig_el = card.select_one('.original-price, [class*="original-price"], [class*="was-price"]')
        if orig_el:
            orig_text = orig_el.get_text(strip=True)
            match = re.search(r'€?\s*([\d.,]+)', orig_text.replace(" ", ""))
            if match:
                try:
                    listing["original_price"] = float(match.group(1).replace(",", "."))
                    if listing["price"] and listing["original_price"] > listing["price"]:
                        listing["discount_percent"] = round(
                            ((listing["original_price"] - listing["price"]) / listing["original_price"]) * 100, 1
                        )
                except ValueError:
                    pass

        # Size
        size_el = card.select_one('.size, [class*="size"], [class*="maat"]')
        if size_el:
            listing["size"] = size_el.get_text(strip=True)

        # Condition
        cond_el = card.select_one('.condition, [class*="condition"], [class*="staat"]')
        if cond_el:
            listing["condition"] = cond_el.get_text(strip=True)

        # URL
        link_el = card.select_one('a[href*="/items/"]')
        if link_el and link_el.get("href"):
            href = link_el["href"]
            listing["url"] = f"https://www.vinted.be{href}" if href.startswith("/") else href

        # Description snippet
        desc_el = card.select_one('.item-description-snippet, [class*="description"], [class*="desc"]')
        if desc_el:
            listing["description"] = desc_el.get_text(strip=True)

        # Photo count
        imgs = card.find_all("img")
        listing["photo_count"] = max(len(imgs), 1)
        if card.get("data-photos"):
            try:
                listing["photo_count"] = int(card["data-photos"])
            except (ValueError, TypeError):
                pass

        # Only keep if we have at least title + price
        if listing["title"] and listing["price"] is not None:
            listings.append(listing)

    # Deduplicate by title + price (common in scraped HTML)
    seen = set()
    unique_listings = []
    for l in listings:
        key = (l["title"][:50], l["price"])
        if key not in seen:
            seen.add(key)
            unique_listings.append(l)
    return unique_listings


# ============================================================
# ANALYSIS ENGINE
# ============================================================
def analyze_listing(listing: Dict[str, Any], seller_info: Dict[str, Any]) -> Dict[str, Any]:
    """Score a single listing across all competitiveness dimensions."""
    analysis = listing.copy()
    analysis["scores"] = {}
    analysis["recommendations"] = []
    analysis["brand_tier"] = get_brand_tier(analysis.get("brand", ""))

    tier = analysis["brand_tier"]
    tier_score_map = {
        "luxury": 9.5,
        "premium": 7.8,
        "mid": 5.8,
        "fast_fashion": 4.2,
        "unknown": 3.8
    }
    analysis["scores"]["brand"] = tier_score_map.get(tier, 5.0)

    if tier == "unknown" and analysis.get("brand"):
        analysis["recommendations"].append(
            "Brand name is unclear. Add brand logo in photos or spell it clearly in title/description for better SEO and buyer trust."
        )

    # Seller reputation (applied per listing but global)
    seller_score = 5.0
    if seller_info.get("rating"):
        seller_score = min(10.0, seller_info["rating"] * 2.0)
    if seller_info.get("num_ratings", 0) > 300:
        seller_score = min(10.0, seller_score + 0.7)
    if seller_info.get("num_ratings", 0) > 1000:
        seller_score = min(10.0, seller_score + 0.5)
    analysis["scores"]["seller_reputation"] = round(seller_score, 1)

    # Description quality + measurements + materials
    desc = (analysis.get("description") or "").lower()
    desc_len = len(analysis.get("description") or "")
    desc_score = min(10.0, 3.0 + (desc_len / 45.0))

    has_measurements = bool(re.search(r'\b(\d{2,3}\s*cm|measurements?|maatvoering|insole|waist|inseam|length)\b', desc, re.IGNORECASE))
    analysis["has_measurements"] = has_measurements
    if has_measurements:
        desc_score = min(10.0, desc_score + 2.8)
    else:
        analysis["recommendations"].append(
            "Add precise measurements (e.g. 'Insole 27.5 cm', 'Waist 72 cm, Inseam 78 cm'). This dramatically reduces questions and returns."
        )

    has_materials = bool(re.search(r'\b(100%|leather|cotton|denim|wool|polyester|viscose|silk|cashmere|organic|elastane)\b', desc, re.IGNORECASE))
    analysis["has_material_info"] = has_materials
    if has_materials:
        desc_score = min(10.0, desc_score + 1.8)
    elif tier in ["luxury", "premium"]:
        analysis["recommendations"].append(
            "Premium/luxury items sell better with explicit material composition (e.g. '100% leather', '98% cotton 2% elastane')."
        )

    analysis["scores"]["description"] = round(desc_score, 1)

    # SEO & Title optimization
    title = analysis.get("title", "")
    title_lower = title.lower()
    seo_score = 5.0

    brand_in_title = analysis.get("brand", "").lower() in title_lower if analysis.get("brand") else False
    if brand_in_title:
        seo_score += 1.8
    if analysis.get("size") and analysis.get("size").lower() in title_lower:
        seo_score += 1.2
    if 45 <= len(title) <= 85:
        seo_score += 1.5
    if any(kw in title_lower for kw in ["new", "never worn", "limited", "rare", "vintage", "like new", "deadstock"]):
        seo_score += 1.2
    if any(kw in title_lower for kw in ["original", "authentic", "box", "dustbag"]):
        seo_score += 0.8

    analysis["scores"]["seo_title"] = min(10.0, round(seo_score, 1))
    if analysis["scores"]["seo_title"] < 7.0:
        analysis["recommendations"].append(
            "Improve title for SEO: 'Brand + Model + Size + Key Feature' (e.g. 'Nike Air Force 1 White EU42 - Like New'). Keep 50-80 characters."
        )

    # Image / visual quality (heuristic)
    photo_count = analysis.get("photo_count", 1)
    photo_score = min(10.0, 4.0 + (photo_count * 1.1))
    analysis["scores"]["images"] = round(photo_score, 1)
    if photo_count < 4:
        analysis["recommendations"].append(
            f"Only ~{photo_count} photo(s) detected. Add at least 5-7 clear photos: front, back, sides, details, flaws, measurements, brand tags."
        )

    # Authenticity (critical for luxury)
    auth_keywords = ["authentic", "original", "certificate", "receipt", "proof", "authenticity", "echt", "origineel", "serial", "dustbag", "box"]
    is_authentic = any(kw in desc for kw in auth_keywords)
    analysis["authenticity_checked"] = is_authentic

    if tier == "luxury":
        auth_score = 9.2 if is_authentic else 4.5
        if not is_authentic:
            analysis["recommendations"].append(
                "LUXURY ITEM: Add clear proof of authenticity (certificate, receipt photo, serial number visible, original box/dustbag mention). Buyers are very cautious."
            )
    else:
        auth_score = 7.5 if is_authentic else 6.5
    analysis["scores"]["authenticity"] = auth_score

    # Price competitiveness & drop trends
    price = analysis.get("price") or 0
    discount = analysis.get("discount_percent", 0)
    price_score = 6.0

    if discount >= 35:
        price_score = 9.3
        analysis["recommendations"].append("Excellent price drop — this is a strong competitive signal for buyers.")
    elif discount >= 20:
        price_score = 8.0
    elif discount >= 10:
        price_score = 7.0
    elif discount == 0 and tier == "luxury":
        price_score = 5.8  # Luxury holds value; small drops are normal

    # Condition boost
    cond_lower = (analysis.get("condition") or "").lower()
    if any(x in cond_lower for x in ["new with tags", "new", "never worn", "deadstock"]):
        price_score = min(10.0, price_score + 1.2)
    elif any(x in cond_lower for x in ["very good", "excellent"]):
        price_score = min(10.0, price_score + 0.6)

    analysis["scores"]["price_competitiveness"] = round(price_score, 1)

    # Weighted overall score
    weights = {
        "brand": 0.14,
        "seller_reputation": 0.10,
        "description": 0.22,
        "seo_title": 0.14,
        "images": 0.14,
        "authenticity": 0.12,
        "price_competitiveness": 0.14
    }
    overall = sum(analysis["scores"].get(k, 5.0) * w for k, w in weights.items())
    analysis["overall_score"] = round(overall, 1)

    # Verdict
    if analysis["overall_score"] >= 8.7:
        analysis["verdict"] = "Excellent — highly competitive listing"
    elif analysis["overall_score"] >= 7.3:
        analysis["verdict"] = "Good — competitive with small optimizations"
    elif analysis["overall_score"] >= 5.8:
        analysis["verdict"] = "Average — needs work to stand out"
    else:
        analysis["verdict"] = "Below average — major improvements required for good visibility/sales"

    return analysis


# ============================================================
# REPORTING
# ============================================================
def generate_report(seller_info: Dict[str, Any], analyzed_listings: List[Dict[str, Any]], output_base: str) -> None:
    """Print human-readable report + save JSON and CSV."""
    print("\n" + "=" * 70)
    print(f"VINTED LISTING ANALYZER REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    print(f"\n👤 SELLER: {seller_info.get('username', 'Unknown')}")
    if seller_info.get("rating"):
        print(f"   ⭐ Rating: {seller_info['rating']}/5  ({seller_info.get('num_ratings', 0):,} ratings)")
    if seller_info.get("location"):
        print(f"   📍 Location: {seller_info['location']}")
    if seller_info.get("member_since"):
        print(f"   📅 Member since: {seller_info['member_since']}")
    if seller_info.get("items_sold"):
        print(f"   📦 Items sold: {seller_info['items_sold']:,}")

    if not analyzed_listings:
        print("\n⚠️  No listings could be extracted from the provided HTML.")
        print("   Tip: Make sure the HTML contains visible item cards from the profile grid.")
        return

    print(f"\n📊 ANALYZED LISTINGS: {len(analyzed_listings)}")
    avg_score = sum(l["overall_score"] for l in analyzed_listings) / len(analyzed_listings)
    print(f"   Average Overall Score: {avg_score:.1f}/10")

    # Sort by overall score desc
    sorted_listings = sorted(analyzed_listings, key=lambda x: x["overall_score"], reverse=True)

    print("\n" + "-" * 70)
    print("TOP PERFORMING / MOST COMPETITIVE LISTINGS")
    print("-" * 70)

    for i, item in enumerate(sorted_listings[:5], 1):
        print(f"\n{i}. {item['title'][:65]}")
        print(f"   Brand: {item.get('brand', 'N/A')} ({item.get('brand_tier', 'unknown')}) | Size: {item.get('size', 'N/A')}")
        price_str = f"€{item['price']:.2f}"
        if item.get("discount_percent"):
            price_str += f" (was €{item.get('original_price'):.2f}, -{item['discount_percent']}%)")
        print(f"   Price: {price_str} | Condition: {item.get('condition', 'N/A')}")
        print(f"   Overall Score: {item['overall_score']}/10 → {item['verdict']}")
        print(f"   Key Scores → Brand: {item['scores']['brand']:.1f} | Desc: {item['scores']['description']:.1f} | "
              f"Photos: {item['scores']['images']:.1f} | Price Comp: {item['scores']['price_competitiveness']:.1f}")
        if item.get("recommendations"):
            print("   💡 Recommendations:")
            for rec in item["recommendations"][:3]:
                print(f"      • {rec}")

    # Bottom performers
    if len(sorted_listings) > 3:
        print("\n" + "-" * 70)
        print("LISTINGS NEEDING IMPROVEMENT (lowest scores)")
        print("-" * 70)
        for item in sorted_listings[-3:]:
            print(f"\n• {item['title'][:60]} — Score: {item['overall_score']}/10")
            if item.get("recommendations"):
                print(f"  Top fix: {item['recommendations'][0]}")

    # Summary stats
    print("\n" + "=" * 70)
    print("SUMMARY INSIGHTS")
    print("=" * 70)
    luxury_count = sum(1 for l in analyzed_listings if l.get("brand_tier") == "luxury")
    has_meas_count = sum(1 for l in analyzed_listings if l.get("has_measurements"))
    print(f"• Luxury items found: {luxury_count}")
    print(f"• Listings with measurements: {has_meas_count} / {len(analyzed_listings)}")
    print(f"• Average photo count: {sum(l.get('photo_count', 1) for l in analyzed_listings) / len(analyzed_listings):.1f}")
    print(f"• Items with significant price drops (>15%): {sum(1 for l in analyzed_listings if l.get('discount_percent', 0) > 15)}")

    print("\n💡 GENERAL TIPS FOR BETTER COMPETITIVENESS ON VINTED:")
    print("   • Always include measurements for clothing/shoes")
    print("   • 6+ high-quality photos from multiple angles win more sales")
    print("   • Clear brand + descriptive title = better search ranking")
    print("   • For luxury: authenticity proof is non-negotiable")
    print("   • Price drops of 15-25% often trigger buyer interest")

    # Save JSON
    json_path = f"{output_base}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "seller_info": seller_info,
            "analyzed_listings": analyzed_listings,
            "summary": {
                "total_listings": len(analyzed_listings),
                "average_overall_score": round(avg_score, 2),
                "luxury_items": luxury_count
            }
        }, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Full structured data saved to: {json_path}")

    # Save CSV (flattened scores)
    csv_path = f"{output_base}.csv"
    fieldnames = [
        "title", "brand", "brand_tier", "price", "original_price", "discount_percent",
        "size", "condition", "photo_count", "overall_score", "verdict",
        "score_brand", "score_description", "score_images", "score_price_competitiveness",
        "has_measurements", "has_material_info", "authenticity_checked", "url"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in analyzed_listings:
            row = {
                "title": item.get("title", ""),
                "brand": item.get("brand", ""),
                "brand_tier": item.get("brand_tier", ""),
                "price": item.get("price"),
                "original_price": item.get("original_price"),
                "discount_percent": item.get("discount_percent"),
                "size": item.get("size", ""),
                "condition": item.get("condition", ""),
                "photo_count": item.get("photo_count", 1),
                "overall_score": item.get("overall_score"),
                "verdict": item.get("verdict", ""),
                "score_brand": item.get("scores", {}).get("brand"),
                "score_description": item.get("scores", {}).get("description"),
                "score_images": item.get("scores", {}).get("images"),
                "score_price_competitiveness": item.get("scores", {}).get("price_competitiveness"),
                "has_measurements": item.get("has_measurements"),
                "has_material_info": item.get("has_material_info"),
                "authenticity_checked": item.get("authenticity_checked"),
                "url": item.get("url", "")
            }
            writer.writerow(row)
    print(f"✅ Tabular export saved to: {csv_path} (open in Excel/Google Sheets)")


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="VintedListingAnalyzer — Evaluate price competitiveness and listing quality from Vinted profile HTML"
    )
    parser.add_argument(
        "--html-file",
        type=str,
        help="Path to saved HTML file of a Vinted member profile page (recommended)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="vinted_analysis",
        help="Base filename for output JSON/CSV (default: vinted_analysis)"
    )
    args = parser.parse_args()

    if args.html_file:
        html_path = Path(args.html_file)
        if not html_path.exists():
            print(f"❌ Error: File not found: {html_path}")
            return
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()
        print(f"📥 Loaded HTML from: {html_path}")
    else:
        html_content = SAMPLE_HTML
        print("⚠️  No --html-file provided. Running with built-in SAMPLE_HTML for demonstration.")
        print("    Replace with real Vinted profile HTML using --html-file for accurate results.")

    soup = BeautifulSoup(html_content, "lxml")

    seller_info = extract_seller_info(soup)
    raw_listings = extract_listings(soup)
    analyzed_listings = [analyze_listing(l, seller_info) for l in raw_listings]

    generate_report(seller_info, analyzed_listings, args.output)

    print("\n" + "=" * 70)
    print("Analysis complete. Thank you for using VintedListingAnalyzer!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
