"""Kronos integration for price forecasting and analysis.

Kronos is a foundation model for financial K-line (OHLCV) data.
It treats candlestick sequences as a language for autoregressive prediction.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json

import pandas as pd

from .config import ProcessingConfig


class KronosAnalyzer:
    """Wrapper around Kronos model for stock price prediction."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self._model = None
        self._tokenizer = None
        self._predictor = None
    
    def _load_model(self):
        """Lazy load Kronos model from HuggingFace."""
        if self._model is not None:
            return
        
        try:
            from model import Kronos, KronosTokenizer, KronosPredictor
            
            model_name = self.config.kronos_model
            tokenizer_name = self.config.kronos_tokenizer
            
            print(f"  [Kronos] Loading model: {model_name}")
            self._tokenizer = KronosTokenizer.from_pretrained(tokenizer_name)
            self._model = Kronos.from_pretrained(model_name)
            self._predictor = KronosPredictor(
                self._model, 
                self._tokenizer, 
                max_context=self.config.kronos_max_context
            )
            print(f"  [Kronos] Model loaded successfully")
            
        except ImportError as e:
            raise ImportError(
                "Kronos not installed. Clone from: "
                "https://github.com/shiyu-coder/Kronos\n"
                f"Error: {e}"
            )
    
    def predict(self, price_df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Generate price prediction using Kronos.
        
        Args:
            price_df: DataFrame with columns ['open','high','low','close','volume']
                      and a 'timestamp' or 'date' column
        
        Returns:
            DataFrame with predicted OHLCV values
        """
        self._load_model()
        
        if self._predictor is None:
            print("  [Kronos] Model not loaded")
            return None
        
        try:
            # Prepare input data
            df = price_df.copy()
            
            # Ensure timestamps column
            if 'date' in df.columns and 'timestamps' not in df.columns:
                df['timestamps'] = pd.to_datetime(df['date'])
            elif 'timestamps' not in df.columns:
                print("  [Kronos] No timestamp/date column found")
                return None
            
            # Ensure required columns
            required = ['open', 'high', 'low', 'close']
            for col in required:
                if col not in df.columns:
                    print(f"  [Kronos] Missing required column: {col}")
                    return None
            
            # Limit to max context
            max_ctx = self.config.kronos_max_context
            lookback = min(len(df), max_ctx)
            pred_len = min(self.config.kronos_pred_len, len(df) // 2)
            pred_len = min(pred_len, 120)  # Kronos max prediction
            
            if lookback < 50:
                print(f"  [Kronos] Not enough data ({lookback} periods), need >= 50")
                return None
            
            x_df = df.iloc[-lookback:][['open', 'high', 'low', 'close', 'volume']]
            x_ts = df.iloc[-lookback:]['timestamps']
            
            # Generate future timestamps
            last_ts = df.iloc[-1]['timestamps']
            if isinstance(last_ts, pd.Timestamp):
                # Assume daily data, generate next pred_len business days
                future_dates = pd.bdate_range(
                    start=last_ts + timedelta(days=1),
                    periods=pred_len
                )
            else:
                future_dates = [last_ts + timedelta(days=i) for i in range(1, pred_len + 1)]
                future_dates = pd.Series(future_dates)
            y_ts = pd.Series(future_dates)
            
            print(f"  [Kronos] Predicting {pred_len} periods from {lookback} lookback...")
            
            pred_df = self._predictor.predict(
                df=x_df,
                x_timestamp=x_ts,
                y_timestamp=y_ts,
                pred_len=pred_len,
                T=1.0,
                top_p=0.9,
                sample_count=5
            )
            
            print(f"  [Kronos] Prediction complete ({len(pred_df)} rows)")
            return pred_df
            
        except Exception as e:
            print(f"  [Kronos] Prediction error: {e}")
            return None
    
    def analyze_batch(self, symbols_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """Run Kronos analysis on multiple symbols.
        
        Args:
            symbols_data: Dict of {symbol: price_df}
        
        Returns:
            List of prediction results ready for Supabase
        """
        results = []
        
        for symbol, df in symbols_data.items():
            print(f"\n  [Kronos] Analyzing {symbol}...")
            
            pred_df = self.predict(df)
            if pred_df is None:
                continue
            
            # Calculate basic metrics
            try:
                last_close = df['close'].iloc[-1]
                predicted_close = pred_df['close'].iloc[-1]
                price_change_pct = ((predicted_close - last_close) / last_close) * 100
                
                upside_prob = (pred_df['close'] > last_close).mean() * 100
                volatility = pred_df['close'].std() / pred_df['close'].mean() * 100
                
                result = {
                    "symbol": symbol.upper(),
                    "prediction_date": datetime.now().date().isoformat(),
                    "lookback_start": pd.Timestamp(df.index[-self.config.kronos_max_context]).isoformat() if hasattr(df, 'index') else None,
                    "prediction_end": pred_df.index[-1].isoformat() if hasattr(pred_df, 'index') else None,
                    "predicted_ohlcv": pred_df.to_dict('records'),
                    "metrics": {
                        "price_change_pct": round(price_change_pct, 2),
                        "upside_prob": round(upside_prob, 2),
                        "volatility": round(volatility, 2),
                        "last_close": float(last_close),
                        "predicted_close": float(predicted_close),
                        "signal": "BUY" if price_change_pct > 3 else ("SELL" if price_change_pct < -3 else "NEUTRAL"),
                    },
                    "model_version": self.config.kronos_model,
                    "created_at": datetime.now().isoformat(),
                }
                
                results.append(result)
                print(f"  [Kronos] {symbol}: Signal={result['metrics']['signal']}, "
                      f"Δ={price_change_pct:+.2f}%, "
                      f"Upside={upside_prob:.1f}%")
                
            except Exception as e:
                print(f"  [Kronos] Error computing metrics for {symbol}: {e}")
        
        return results
