import os
import json
import time
import logging
from typing import Dict, List

import pandas as pd
import yfinance as yf
from colorama import Fore, Style

# -----------------------------
# Configuration
# -----------------------------
TICKERS: List[str] = [
    # ETFs
    "SPY",
    "QQQ",
    # Consumer Defensive
    "PEP",
    "KO",
    "COST",
    "WMT",
    # Consumer Cyclical
    "AMZN",
    "BABA",
    "F",
    "TSLA",
    "NIO",
    "MCD",
    "DKNG",
    "MELI",
    "SE",
    "EBAY",
    "BKNG",
    "DASH",
    "WEN",
    # Communication Services
    "PINS",
    "SNAP",
    "RDDT",
    "META",
    "GOOG",
    "T",
    "AMC",
    "TTWO",
    "NFLX",
    "VZ",
    "BIDU",
    "ROKU",
    "DIS",
    "SONY",
    "SPOT",
    "MTCH",
    # Technology
    "DELL",
    "NVDA",
    "AMD",
    "AVGO",
    "TSM",
    "MU",
    "ORCL",
    "AAPL",
    "PLTR",
    "INTC",
    "QUBT",
    "MSFT",
    "ADBE",
    "QCOM",
    "ASML",
    "AMAT",
    "ADP",
    "IBM",
    "CRM",
    "NOW",
    "SHOP",
    "PANW",
    "CRWD",
    "MDB",
    "ZS",
    "DDOG",
    "ARM",
    "LRCX",
    "KLAC",
    "NXPI",
    "ON",
    "MRVL",
    "UBER",
    # Financial Services
    "PYPL",
    "HOOD",
    "V",
    "JPM",
    "AXP",
    "GS",
    "MA",
    "SQ",
    "COIN",
    "C",
    "BAC",
    "MS",
    # Healthcare
    "LLY",
    "UNH",
    "JNJ",
    "AMGN",
    "PFE",
    "MRK",
    "ABBV",
    "REGN",
    "BMY",
    # Industrials
    "CTAS",
    "BA",
    "CAT",
    "GE",
    "HON",
    "LMT",
    "RTX",
    # Energy
    "XOM",
    "CVX",
]


SECTOR_CACHE_FILE = "sectors.json"
REFRESH_SECONDS = 10
DOWNLOAD_PERIOD = "5d"
DOWNLOAD_INTERVAL = "1d"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)


# -----------------------------
# Sector mapping (cached)
# -----------------------------
def load_sector_cache(path: str) -> Dict[str, str]:
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            if isinstance(data, dict):
                logging.info("Loaded sector cache from %s", path)
                return data
        except Exception as exc:
            logging.warning("Failed to read sector cache: %s", exc)
    return {}


def build_sector_cache(tickers: List[str]) -> Dict[str, str]:
    """Fetch sector info once (best effort)."""
    sectors: Dict[str, str] = {}
    logging.info("Building sector cache (one-time fetch)...")
    for tk in tickers:
        try:
            info = yf.Ticker(tk).info  # yfinance still exposes sector here
            sectors[tk] = info.get("sector", "Unknown")
        except Exception as exc:
            sectors[tk] = "Unknown"
            logging.debug("Sector fetch failed for %s: %s", tk, exc)
        time.sleep(0.2)  # gentle pacing to avoid rate-limiting
    return sectors


def ensure_sector_cache(path: str, tickers: List[str]) -> Dict[str, str]:
    sectors = load_sector_cache(path)
    missing = [tk for tk in tickers if tk not in sectors]
    if missing:
        fetched = build_sector_cache(missing)
        sectors.update(fetched)
        try:
            with open(path, "w") as f:
                json.dump(sectors, f)
            logging.info("Sector cache updated: %s", path)
        except Exception as exc:
            logging.warning("Failed to write sector cache: %s", exc)
    return sectors


# -----------------------------
# Display helpers
# -----------------------------
def print_sector_block(df: pd.DataFrame, sector: str) -> None:
    print(f"\nSector: {sector}")
    print(f"{'Ticker':<6} {'Prev':>10} {'Cur':>10} {'%Chg':>8}")
    for _, r in df.iterrows():
        color = (
            Fore.GREEN
            if r["% Change"] > 0
            else Fore.RED if r["% Change"] < 0 else Fore.LIGHTBLACK_EX
        )
        print(
            f"{r['Ticker']:<6} "
            f"{r['Previous']:>10.2f} "
            f"{r['Current']:>10.2f} "
            f"{color}{r['% Change']:>7.2f}%{Style.RESET_ALL}"
        )


# -----------------------------
# Main loop
# -----------------------------
def main() -> None:
    sectors = ensure_sector_cache(SECTOR_CACHE_FILE, TICKERS)

    while True:
        logging.info("Fetching price data...")
        try:
            data = yf.download(
                TICKERS,
                period=DOWNLOAD_PERIOD,
                interval=DOWNLOAD_INTERVAL,
                threads=True,
                progress=False,
            )

            if data is None or data.empty:
                raise ValueError("No data returned from Yahoo Finance")

            # Build results
            results = []
            for tk in TICKERS:
                try:
                    s = data["Close"][tk].dropna()
                    if len(s) < 2:
                        raise ValueError("Insufficient history")
                    prev, current = s.iloc[-2], s.iloc[-1]
                    change = (current - prev) / prev * 100.0
                    results.append(
                        {
                            "Ticker": tk,
                            "Sector": sectors.get(tk, "Unknown"),
                            "Previous": prev,
                            "Current": current,
                            "% Change": change,
                        }
                    )
                except Exception as exc:
                    results.append(
                        {
                            "Ticker": tk,
                            "Sector": sectors.get(tk, "Unknown"),
                            "Previous": None,
                            "Current": None,
                            "% Change": None,
                            "Error": str(exc),
                        }
                    )

            # Display
            valid = pd.DataFrame(results).dropna(subset=["% Change"])
            if valid.empty:
                logging.warning("No valid symbols to display.")
            else:
                valid = valid.sort_values(by="% Change", ascending=False)
                print("\nPrice Change — Close vs Previous Close")
                for sector in sorted(valid["Sector"].unique()):
                    print_sector_block(valid[valid["Sector"] == sector], sector)

            # Errors (if any)
            errs = [r for r in results if r.get("Error")]
            if errs:
                print("\nErrors:")
                for r in errs:
                    print(f"{r['Ticker']:<6} - {r['Error']}")

        except Exception as exc:
            logging.error("Fetch/display error: %s", exc)

        logging.info("Sleeping %s seconds...", REFRESH_SECONDS)
        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    main()
