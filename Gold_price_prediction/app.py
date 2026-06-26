from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yfinance as yf
import pandas as pd

app = FastAPI(title="Gold Signals Dashboard")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def fetch_gold_df(period="6mo", interval="1d"):
    df = yf.download("XAUUSD=X", period=period, interval=interval, auto_adjust=True)
    df = df.rename(columns={"Close": "close"})
    return df.dropna()

def compute_signals(df: pd.DataFrame):
    df = df.copy()
    df["sma_20"] = df["close"].rolling(20).mean()
    df["sma_50"] = df["close"].rolling(50).mean()
    df["signal"] = "HOLD"
    df.loc[(df["sma_20"] > df["sma_50"]) & (df["sma_20"].shift() <= df["sma_50"].shift()), "signal"] = "BUY"
    df.loc[(df["sma_20"] < df["sma_50"]) & (df["sma_20"].shift() >= df["sma_50"].shift()), "signal"] = "SELL"

    last = df.iloc[-1]
    if last["signal"] == "BUY":
        reason = f"20-day SMA {last['sma_20']:.2f} crossed above 50-day SMA {last['sma_50']:.2f}. Momentum up."
    elif last["signal"] == "SELL":
        reason = f"20-day SMA {last['sma_20']:.2f} crossed below 50-day SMA {last['sma_50']:.2f}. Momentum down."
    else:
        reason = f"Price {last['close']:.2f} is between SMAs. No clear trend."
    return df, reason, last["close"]

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/data")
async def data():
    df = fetch_gold_df()
    df, reason, last_price = compute_signals(df)
    chart_data = df.tail(100).reset_index()
    chart_data["Date"] = chart_data["Date"].dt.strftime("%Y-%m-%d")
    return {
        "labels": chart_data["Date"].tolist(),
        "price": chart_data["close"].tolist(),
        "sma20": chart_data["sma_20"].fillna(0).tolist(),
        "sma50": chart_data["sma_50"].fillna(0).tolist(),
        "signal": df["signal"].iloc[-1],
        "reason": reason,
        "last_price": round(last_price, 2)
    }