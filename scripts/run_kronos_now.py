#!/usr/bin/env python3
"""Run Kronos prediction immediately on selected stocks."""
import sys
import os
import json
import pandas as pd

# Add Kronos repo to path (try permanent location first, then /tmp)
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


def load_price_data(symbol: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, f"price_{symbol}.json")
    if not os.path.exists(path):
        print(f"  ❌ No price data for {symbol}")
        return None
    
    with open(path) as f:
        records = json.load(f)
    
    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    required = ['open', 'high', 'low', 'close', 'volume']
    for col in required:
        if col not in df.columns:
            print(f"  ❌ Missing column {col} in {symbol} data")
            return None
    
    print(f"  📊 {symbol}: {len(df)} records ({df['date'].iloc[0].date()} → {df['date'].iloc[-1].date()})")
    print(f"  💰 Latest close: {df['close'].iloc[-1]:.2f}")
    return df


def run_kronos(symbol: str, price_df: pd.DataFrame, predictor):
    """Run Kronos prediction on a single symbol."""
    print(f"\n  🔮 Kronos predicting {symbol}...")
    
    df = price_df.copy()
    
    # Prepare input: timestamps + OHLCV
    df['timestamps'] = df['date']
    
    # Ensure enough data
    lookback = min(len(df), 512)
    pred_len = min(30, len(df) // 4)
    
    if lookback < 50:
        print(f"  ⚠️  Not enough data ({lookback} periods), need >= 50")
        return None
    
    x_df = df.iloc[-lookback:][['open', 'high', 'low', 'close', 'volume']]
    x_ts = df.iloc[-lookback:]['timestamps']
    
    # Future dates
    from datetime import timedelta
    last_ts = df.iloc[-1]['date']
    future_dates = pd.bdate_range(
        start=last_ts + timedelta(days=1),
        periods=pred_len
    )
    y_ts = pd.Series(future_dates)
    
    print(f"  🔄 Predicting {pred_len} periods from {lookback} lookback...")
    
    try:
        pred_df = predictor.predict(
            df=x_df,
            x_timestamp=x_ts,
            y_timestamp=y_ts,
            pred_len=pred_len,
            T=1.0,
            top_p=0.9,
            sample_count=5
        )
        
        if pred_df is None or len(pred_df) == 0:
            print(f"  ❌ No predictions returned")
            return None
        
        print(f"  ✅ Prediction complete: {len(pred_df)} periods")
        return pred_df
        
    except Exception as e:
        print(f"  ❌ Prediction error: {e}")
        import traceback
        traceback.print_exc()
        return None


def format_results(symbol: str, price_df: pd.DataFrame, pred_df: pd.DataFrame):
    """Format and display prediction results."""
    last_close = price_df['close'].iloc[-1]
    
    if isinstance(pred_df.index, pd.DatetimeIndex):
        pred_dates = pred_df.index
    elif 'date' in pred_df.columns or 'timestamps' in pred_df.columns:
        ts_col = 'date' if 'date' in pred_df.columns else 'timestamps'
        pred_dates = pd.to_datetime(pred_df[ts_col])
    else:
        pred_dates = pd.RangeIndex(len(pred_df))
    
    pred_close = pred_df['close'].values if 'close' in pred_df.columns else None
    
    if pred_close is not None:
        final_pred = pred_close[-1]
        change_pct = ((final_pred - last_close) / last_close) * 100
        max_pred = max(pred_close)
        min_pred = min(pred_close)
        upside = (pred_close > last_close).mean() * 100
        volatility = float(pd.Series(pred_close).std() / pd.Series(pred_close).mean() * 100)
        
        print(f"\n{'='*60}")
        print(f"📊 KRONOS PREDICTION: {symbol}")
        print(f"{'='*60}")
        print(f"  Current price : {last_close:>8.2f}")
        print(f"  Predicted end : {final_pred:>8.2f} ({change_pct:+.2f}%)")
        print(f"  Range         : {min_pred:.2f} → {max_pred:.2f}")
        print(f"  Upside prob   : {upside:.1f}%")
        print(f"  Volatility    : {volatility:.1f}%")
        print(f"{'─'*60}")
        
        if change_pct > 5:
            signal = "🟢 STRONG BUY"
        elif change_pct > 2:
            signal = "🟢 BUY"
        elif change_pct > -2:
            signal = "🟡 HOLD/NEUTRAL"
        elif change_pct > -5:
            signal = "🔴 SELL"
        else:
            signal = "🔴 STRONG SELL"
        
        print(f"  Signal : {signal}")
        print(f"{'─'*60}")
        
        print(f"\n  📅 Projected prices (next {len(pred_df)} periods):")
        for i in range(len(pred_df)):
            d = pred_dates[i] if isinstance(pred_dates, pd.DatetimeIndex) else pred_dates.iloc[i]
            if hasattr(d, 'strftime'):
                d_str = d.strftime('%Y-%m-%d')
            else:
                d_str = str(d)
            o = pred_df['open'].values[i] if 'open' in pred_df.columns else 0
            h = pred_df['high'].values[i] if 'high' in pred_df.columns else 0
            l = pred_df['low'].values[i] if 'low' in pred_df.columns else 0
            c = pred_df['close'].values[i] if 'close' in pred_df.columns else 0
            v = pred_df['volume'].values[i] if 'volume' in pred_df.columns else 0
            print(f"    {d_str}: O={o:>8.2f} H={h:>8.2f} L={l:>8.2f} C={c:>8.2f} V={int(v):>10,}")
        
        return {
            "symbol": symbol,
            "current_price": float(last_close),
            "predicted_price": float(final_pred),
            "change_pct": round(change_pct, 2),
            "upside_prob": round(upside, 1),
            "volatility": round(volatility, 1),
            "signal": signal,
            "prediction_periods": len(pred_df),
        }
    
    return None


def main():
    # Symbols to analyze
    symbols = ["FPT", "ACB", "VNM"]
    
    print(f"{'='*60}")
    print(f"🔮 AIFIA KRONOS PREDICTION ENGINE")
    print(f"{'='*60}")
    print(f"\nLoading Kronos model (24.7M params)...")
    
    tokenizer = KronosTokenizer.from_pretrained('NeoQuasar/Kronos-Tokenizer-base')
    model = Kronos.from_pretrained('NeoQuasar/Kronos-small')
    predictor = KronosPredictor(model, tokenizer, max_context=512)
    print(f"✅ Model loaded\n")
    
    results = []
    for symbol in symbols:
        print(f"\n{'─'*60}")
        price_df = load_price_data(symbol)
        if price_df is None:
            continue
        
        pred_df = run_kronos(symbol, price_df, predictor)
        if pred_df is None:
            continue
        
        result = format_results(symbol, price_df, pred_df)
        if result:
            results.append(result)
        
        print(f"{'─'*60}\n")
    
    # Summary
    if results:
        print(f"\n{'='*60}")
        print(f"📈 KRONOS MARKET SUMMARY")
        print(f"{'='*60}")
        for r in results:
            print(f"  {r['symbol']:>5}: {r['signal']:>15} | "
                  f"Δ {r['change_pct']:+.2f}% | "
                  f"Current: {r['current_price']:>8.2f} → {r['predicted_price']:>8.2f}")
        print(f"{'='*60}")
    else:
        print(f"\n❌ No predictions generated")


if __name__ == "__main__":
    main()
