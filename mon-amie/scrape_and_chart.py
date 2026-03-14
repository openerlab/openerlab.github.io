#!/usr/bin/env python3
"""Scrape sold 'Mon Amie kaffeburk' listings from Tradera and chart price trends."""

import argparse
import json
import os
import re
import time
import webbrowser
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.tradera.com/search"
PARAMS = {
    "q": "mon amie",
    "itemStatus": "Sold",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}
DATA_DIR = Path(__file__).parent / "data"
CHART_PATH = Path(__file__).parent / "chart.html"


def scrape_listings(max_pages=50):
    """Scrape all sold listings from Tradera search results."""
    all_items = []
    for page in range(1, max_pages + 1):
        params = {**PARAMS, "paging": page}
        print(f"Fetching page {page}...", end=" ")

        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script:
            print("no __NEXT_DATA__ found, stopping.")
            break

        data = json.loads(script.string)
        items = (
            data.get("props", {})
            .get("pageProps", {})
            .get("initialState", {})
            .get("discover", {})
            .get("items", [])
        )

        if not items:
            print("0 items, done.")
            break

        print(f"{len(items)} items")
        for item in items:
            all_items.append(
                {
                    "item_id": item.get("itemId"),
                    "title": item.get("shortDescription"),
                    "price": item.get("price"),
                    "end_date": item.get("endDate"),
                    "item_type": item.get("itemType"),
                    "total_bids": item.get("totalBids"),
                    "url": f"https://www.tradera.com{item['itemUrl']}" if item.get("itemUrl") else None,
                    "seller": item.get("sellerAlias"),
                }
            )

        time.sleep(1)

    # Deduplicate by item_id
    seen = set()
    unique = []
    for item in all_items:
        if item["item_id"] not in seen:
            seen.add(item["item_id"])
            unique.append(item)

    print(f"\nTotal unique listings: {len(unique)}")
    return unique


def save_data(listings):
    """Merge new listings with existing data and save to JSON and CSV."""
    DATA_DIR.mkdir(exist_ok=True)

    json_path = DATA_DIR / "listings.json"
    csv_path = DATA_DIR / "listings.csv"

    # Merge with existing data
    existing = []
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            existing = json.load(f)

    seen = {item["item_id"] for item in existing}
    new_count = 0
    for item in listings:
        if item["item_id"] not in seen:
            existing.append(item)
            seen.add(item["item_id"])
            new_count += 1

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    df = pd.DataFrame(existing)
    df["end_date"] = pd.to_datetime(df["end_date"])
    df.to_csv(csv_path, index=False)

    print(f"Added {new_count} new listings (total: {len(existing)}) to {json_path} and {csv_path}")
    return csv_path


def create_chart(csv_path=None):
    """Create an interactive Plotly chart from the scraped data."""
    if csv_path is None:
        csv_path = DATA_DIR / "listings.csv"

    df = pd.read_csv(csv_path)
    df["end_date"] = pd.to_datetime(df["end_date"], format="mixed", utc=True)
    df = df.sort_values("end_date")

    # Only include last month
    df = df[df["end_date"] >= (pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=1))]

    # Only include burk/förvaringsburk listings
    df = df[df["title"].str.contains(r"burk|förvar", case=False, regex=True)]

    # Exclude multi-item bundles
    bundle_pattern = re.compile(
        r"\b\d+\s*(?:st\b|stycken|×|x\s)"
        r"|\btre\b|\bfyra\b|\btvå\b"
        r"|\b\d+\s*(?:koppar|muggar|tallrikar|assietter|skålar|burkar|kaffeburkar)",
        re.IGNORECASE,
    )
    df = df[~df["title"].str.contains(bundle_pattern)]

    # Exclude price outliers (IQR method)
    q1, q3 = df["price"].quantile(0.25), df["price"].quantile(0.75)
    iqr = q3 - q1
    df = df[(df["price"] >= q1 - 1.5 * iqr) & (df["price"] <= q3 + 1.5 * iqr)]

    # Separate auction and buy-now items
    auctions = df[df["item_type"] == "Auction"]
    buynow = df[df["item_type"] != "Auction"]

    fig = go.Figure()

    # Auction scatter — marker size reflects bid count
    if not auctions.empty:
        min_size, max_size = 5, 25
        bids = auctions["total_bids"].clip(lower=1)
        sizes = min_size + (max_size - min_size) * (bids - bids.min()) / max(bids.max() - bids.min(), 1)
        fig.add_trace(
            go.Scatter(
                x=auctions["end_date"],
                y=auctions["price"],
                mode="markers",
                name="Auktion",
                marker=dict(size=sizes, color="#1f77b4", opacity=0.6),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Pris: %{y} kr<br>"
                    "Datum: %{x|%Y-%m-%d}<br>"
                    "Bud: %{customdata[1]}<br>"
                    "<extra></extra>"
                ),
                customdata=list(zip(auctions["title"], auctions["total_bids"])),
            )
        )

    # Buy-now scatter
    if not buynow.empty:
        fig.add_trace(
            go.Scatter(
                x=buynow["end_date"],
                y=buynow["price"],
                mode="markers",
                name="Köp nu",
                marker=dict(size=7, color="#ff7f0e", symbol="diamond", opacity=0.6),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Pris: %{y} kr<br>"
                    "Datum: %{x|%Y-%m-%d}<br>"
                    "<extra></extra>"
                ),
                customdata=list(zip(buynow["title"], buynow["total_bids"])),
            )
        )

    # Daily average trend lines per category
    categories = [
        (df, "Alla", "#2ca02c", "solid"),
        (auctions, "Auktion", "#1f77b4", "dot"),
        (buynow, "Köp nu", "#ff7f0e", "dot"),
    ]
    for cat_df, cat_label, color, dash in categories:
        if cat_df.empty:
            continue
        resampled = cat_df.set_index("end_date").resample("D")["price"].mean().dropna()
        if len(resampled) < 2:
            continue
        fig.add_trace(
            go.Scatter(
                x=resampled.index,
                y=resampled.values,
                mode="lines",
                name=f"Medel {cat_label} (Dag)",
                line=dict(color=color, width=3, dash=dash),
                hovertemplate=f"Medel {cat_label}: %{{y:.0f}} kr<br>%{{x|%Y-%m-%d}}<extra></extra>",
                visible=True if cat_label == "Alla" else "legendonly",
            )
        )

    fig.update_layout(
        title="Mon Amie — Sålda på Tradera",
        xaxis_title="Slutdatum",
        yaxis_title="Pris (SEK)",
        hovermode="closest",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        font=dict(size=14),
    )

    fig.write_html(str(CHART_PATH), include_plotlyjs="cdn")
    print(f"Chart saved to {CHART_PATH}")
    if os.environ.get("CI") is None:
        webbrowser.open(f"file://{CHART_PATH.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="Tradera Mon Amie Kaffeburk price tracker")
    parser.add_argument("--scrape-only", action="store_true", help="Only scrape, don't chart")
    parser.add_argument("--chart-only", action="store_true", help="Only chart from existing data")
    args = parser.parse_args()

    if not args.chart_only:
        listings = scrape_listings()
        if not listings:
            print("No listings found!")
            return
        save_data(listings)

    if not args.scrape_only:
        create_chart()


if __name__ == "__main__":
    main()
