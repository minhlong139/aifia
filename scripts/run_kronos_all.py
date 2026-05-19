#!/usr/bin/env python3
"""Run Kronos prediction on ALL VN100 stocks, save results to JSON."""
import sys
import os
import json
import time
from datetime import datetime, timedelta
import pandas as pd

AIFIA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KRONOS_PATHS = [
    os.path.join(AIFIA_DIR, 'kronos_repo'),
    '/tmp/kronos_repo',
]
for kp in KRONOS_PATHS:
    if os.path.isdir(kp):
        sys.path.insert(0, kp)
        break
from model import Kronos, KronosTokenizer, KronosPredictor

AIFIA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(AIFIA_DIR, "data")
OUT_DIR = os.path.join(AIFIA_DIR, "data", "predictions")
os.makedirs(OUT_DIR, exist_ok=True)


def get_vn100_symbols():
    """Get VN100 symbol list from existing data."""
    path = os.path.join(DATA_DIR, "vn100_symbols.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f).get("symbols", [])
    
    # Fallback: price files
    return sorted(set(
        f.split("price_")[1].split(".json")[0]
        for f in os.listdir(DATA_DIR) if f.startswith("price_")
    ))


def load_price_data(symbol: str):
    path = os.path.join(DATA_DIR, f"price_{symbol}.json")
    if not os.path.exists(path):
        return None
    
    with open(path) as f:
        records = json.load(f)
    
    if not records:
        return None
    
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    
    required = ["open", "high", "low", "close", "volume"]
    if not all(c in df.columns for c in required):
        return None
    
    return df


def predict_symbol(symbol: str, price_df: pd.DataFrame, predictor):
    """Single Kronos prediction."""
    df = price_df.copy()
    df["timestamps"] = df["date"]
    
    lookback = min(len(df), 512)
    pred_len = min(20, len(df) // 4)  # 20 periods prediction
    
    if lookback < 50:
        return None
    
    x_df = df.iloc[-lookback:][["open", "high", "low", "close", "volume"]]
    x_ts = df.iloc[-lookback:]["timestamps"]
    
    last_ts = df.iloc[-1]["date"]
    future_dates = pd.bdate_range(
        start=last_ts + timedelta(days=1), periods=pred_len
    )
    y_ts = pd.Series(future_dates)
    
    pred_df = predictor.predict(
        df=x_df, x_timestamp=x_ts, y_timestamp=y_ts,
        pred_len=pred_len, T=1.0, top_p=0.9, sample_count=5
    )
    return pred_df


def compute_metrics(symbol: str, price_df: pd.DataFrame, pred_df: pd.DataFrame):
    """Compute tradeable metrics from prediction."""
    last = price_df["close"].iloc[-1]
    
    if pred_df is None or len(pred_df) == 0:
        return None
    
    closes = pred_df["close"].values if "close" in pred_df.columns else None
    if closes is None:
        return None
    
    final_close = closes[-1]
    change_pct = ((final_close - last) / last) * 100
    max_pred = max(closes)
    min_pred = min(closes)
    upside_prob = (closes > last).mean() * 100
    volatility = float(pd.Series(closes).std() / pd.Series(closes).mean() * 100)
    
    if change_pct > 5:
        signal = "STRONG_BUY"
    elif change_pct > 2:
        signal = "BUY"
    elif change_pct > -2:
        signal = "NEUTRAL"
    elif change_pct > -5:
        signal = "SELL"
    else:
        signal = "STRONG_SELL"
    
    # Last 5 predictions for snapshot
    ohlcv_snapshot = []
    if hasattr(pred_df, "index"):
        for i in range(len(pred_df)):
            d = pred_df.index[i] if isinstance(pred_df.index, pd.DatetimeIndex) else i
            if hasattr(d, "strftime"):
                d = d.strftime("%Y-%m-%d")
            ohlcv_snapshot.append({
                "date": str(d),
                "open": float(pred_df["open"].values[i]) if "open" in pred_df.columns else 0,
                "high": float(pred_df["high"].values[i]) if "high" in pred_df.columns else 0,
                "low": float(pred_df["low"].values[i]) if "low" in pred_df.columns else 0,
                "close": float(closes[i]),
                "volume": int(pred_df["volume"].values[i]) if "volume" in pred_df.columns else 0,
            })
    
    return {
        "symbol": symbol.upper(),
        "current_price": float(last),
        "predicted_price": float(final_close),
        "change_pct": round(change_pct, 2),
        "upside_prob": round(upside_prob, 1),
        "volatility": round(volatility, 1),
        "signal": signal,
        "prediction_periods": len(pred_df),
        "predicted_high": float(max_pred),
        "predicted_low": float(min_pred),
        "ohclv_snapshot": ohlcv_snapshot,
        "generated_at": datetime.now().isoformat(),
    }


def main():
    print("=" * 60)
    print("🔮 AIFIA KRONOS - VN100 FULL PREDICTION")
    print("=" * 60)
    
    # Get symbols
    all_symbols = get_vn100_symbols()
    print(f"\n📋 {len(all_symbols)} VN100 symbols available")
    
    # Load available price data
    available = []
    for sym in all_symbols:
        df = load_price_data(sym)
        if df is not None and len(df) >= 50:
            available.append((sym, df))
    
    print(f"   {len(available)} have sufficient price data (≥50 periods)")
    
    if not available:
        print("❌ No symbols with adequate data!")
        return
    
    # Load model
    print(f"\n🧠 Loading Kronos model (24.7M params)...")
    t0 = time.time()
    tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
    model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
    predictor = KronosPredictor(model, tokenizer, max_context=512)
    print(f"   ✅ {time.time()-t0:.1f}s\n")
    
    # Predict all symbols
    results = []
    errors = []
    
    for i, (symbol, df) in enumerate(available, 1):
        print(f"[{i:>3}/{len(available)}] {symbol:>5} ({len(df):>5} records, latest: {df['close'].iloc[-1]:>8.2f})...", end=" ")
        sys.stdout.flush()
        
        try:
            pred_df = predict_symbol(symbol, df, predictor)
            if pred_df is not None:
                metrics = compute_metrics(symbol, df, pred_df)
                if metrics:
                    results.append(metrics)
                    print(f"▶ ${metrics['predicted_price']:>8.2f} ({metrics['change_pct']:+.2f}%) {metrics['signal']}")
                    continue
            print("⚠️  no pred")
        except Exception as e:
            print(f"❌ {str(e)[:50]}")
            errors.append({"symbol": symbol, "error": str(e)})
    
    # Save all results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(OUT_DIR, f"kronos_vn100_{timestamp}.json")
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "total_symbols": len(available),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }
    
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n{'='*60}")
    print(f"📈 KRONOS VN100 SUMMARY")
    print(f"{'='*60}")
    
    # Sort by predicted change
    sorted_results = sorted(results, key=lambda r: r["change_pct"], reverse=True)
    
    print(f"\n🔥 TOP 10 GAINERS:")
    for r in sorted_results[:10]:
        print(f"   {r['symbol']:>5}: {r['change_pct']:+.2f}% → ${r['predicted_price']:.2f} | Vol: {r['volatility']:.1f}% | {r['signal']}")
    
    print(f"\n💀 BOTTOM 10 LOSERS:")
    for r in sorted_results[-10:]:
        print(f"   {r['symbol']:>5}: {r['change_pct']:+.2f}% → ${r['predicted_price']:.2f} | Vol: {r['volatility']:.1f}% | {r['signal']}")
    
    print(f"\n📊 BY SIGNAL:")
    signals = {}
    for r in results:
        signals.setdefault(r["signal"], []).append(r["symbol"])
    for sig, syms in sorted(signals.items(), reverse=True):
        print(f"   {sig:>15}: {len(syms)} stocks")
    
    print(f"\n{'─'*60}")
    print(f"✅ {len(results)}/{len(available)} predictions saved to {out_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
