import yfinance as yf
import pandas as pd
import time
import json
import os
from colorama import Fore, Style

# Define your full list of tickers
tickers = [
    "SPY","PEP","PINS","DELL","KO","NVDA","AMD","AVGO","TSM","PYPL","UBER","SNAP","RDDT",
    "META","GOOG","AMZN","LLY","MU","BIDU","BABA","T","F","TSLA","NIO","AMC",
    "TTWO","ORCL","NFLX","COST","VZ","AAPL","PLTR","INTC","QUBT","HOOD",
    "MSFT","V","UNH","WMT","JNJ","JPM","ADBE","AMGN","QCOM","ASML","AMAT",
    "ADP","CTAS","BA","CAT","IBM","MCD","AXP","GS","DKNG", "QQQ"
]

# Cache sector info in a local file
sector_file = "sectors.json"
sectors = {}

if os.path.exists(sector_file):
    with open(sector_file, "r") as f:
        sectors = json.load(f)
    print("📂 Loaded cached sector data.\n")
else:
    print("📡 Fetching sector info (one-time)...")
    for i, ticker in enumerate(tickers):
        try:
            info = yf.Ticker(ticker).info
            sectors[ticker] = info.get("sector", "Unknown")
            print(f"✅ {ticker} → {sectors[ticker]}")
            time.sleep(0.5)  # Avoid rate-limiting
        except Exception as e:
            sectors[ticker] = "Unknown"
            print(f"⚠️ {ticker}: {e}")
    with open(sector_file, "w") as f:
        json.dump(sectors, f)
    print("✅ Sector mapping complete and saved.\n")

# Live loop
while True:
    print("\n📊 Stock Price % Change (Updated every minute)\n")
    try:
        data = yf.download(tickers, period="5d", interval="1d", threads=True, progress=False)

        if data.empty:
            raise ValueError("No data returned from Yahoo Finance")

        results = []
        for ticker in tickers:
            try:
                close_prices = data["Close"][ticker].dropna()
                if len(close_prices) < 2:
                    raise ValueError("Not enough data")
                prev = close_prices.iloc[-2]
                current = close_prices.iloc[-1]
                change = (current - prev) / prev * 100

                results.append({
                    "Ticker": ticker,
                    "Sector": sectors.get(ticker, "Unknown"),
                    "Previous": prev,
                    "Current": current,
                    "% Change": change
                })
            except Exception as e:
                results.append({
                    "Ticker": ticker,
                    "Sector": sectors.get(ticker, "Unknown"),
                    "Previous": None,
                    "Current": None,
                    "% Change": None,
                    "Error": str(e)
                })

        # Display
        df = pd.DataFrame(results).dropna(subset=["% Change"])
        df = df.sort_values(by="% Change", ascending=False)

        for sector in sorted(df["Sector"].unique()):
            print(f"\n🔹 Sector: {sector}")
            df_sector = df[df["Sector"] == sector]
            print(f"{'Ticker':<6} {'Prev':>10} {'Cur':>10} {'%Chg':>8}")
            for _, r in df_sector.iterrows():
                c = Fore.GREEN if r["% Change"] > 0 else Fore.RED if r["% Change"] < 0 else Fore.LIGHTBLACK_EX
                print(f"{r['Ticker']:<6} {r['Previous']:>10.2f} {r['Current']:>10.2f} {c}{r['% Change']:>7.2f}%{Style.RESET_ALL}")

        # Show errors
        errors = pd.DataFrame([r for r in results if r.get("Error")])
        if not errors.empty:
            print("\n⚠️ Errors:")
            for _, r in errors.iterrows():
                print(f"{r['Ticker']:<6} - {Fore.YELLOW}{r['Error']}{Style.RESET_ALL}")

    except Exception as e:
        print(Fore.RED + f"\n💥 Error during fetch: {e}" + Style.RESET_ALL)

    print("\n🔁 Waiting 10 seconds...\n")
    time.sleep(10)





