"""Report Generator - Aggregates analysis into comprehensive reports."""
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from .config import ProcessingConfig
from .financial_analyzer import FinancialAnalyzer
from .kronos_analyzer import KronosAnalyzer


class ReportGenerator:
    """Generates comprehensive company analysis reports by combining
    AI financial analysis, Kronos price predictions, and macro context."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.financial_analyzer = FinancialAnalyzer(config)
        self.kronos = KronosAnalyzer(config)
    
    def generate_company_report(self, 
                                symbol: str,
                                financial_data: Dict,
                                price_data: Optional[List[Dict]] = None,
                                macro_data: Optional[List[Dict]] = None) -> Dict:
        """Generate a complete analysis report for a single company.
        
        Args:
            symbol: Stock symbol
            financial_data: Dict of financial reports
            price_data: Optional price history
            macro_data: Optional macro economic data
        
        Returns:
            Complete report dict
        """
        print(f"\n📊 Generating report for {symbol}...")
        
        # 1. AI Financial Analysis
        print(f"  🔬 Running AI financial analysis...")
        ai_analysis = self.financial_analyzer.analyze(symbol, financial_data)
        
        # 2. Kronos Price Prediction (if price data available)
        kronos_prediction = None
        if price_data and self.config.enable_kronos:
            print(f"  📈 Running Kronos price prediction...")
            try:
                import pandas as pd
                price_df = pd.DataFrame(price_data)
                if not price_df.empty:
                    preds = self.kronos.analyze_batch({symbol: price_df})
                    kronos_prediction = preds[0] if preds else None
            except Exception as e:
                print(f"  ⚠️ Kronos prediction skipped: {e}")
        
        # 3. Compile Report
        report = self._compile_report(
            symbol, ai_analysis, kronos_prediction, macro_data
        )
        
        return report
    
    def _compile_report(self, symbol: str,
                        ai_analysis: Dict,
                        kronos_prediction: Optional[Dict],
                        macro_data: Optional[List]) -> Dict:
        """Compile all analysis into a structured report."""
        
        # Compute overall rating
        health = ai_analysis.get("health_score", 50)
        transparency = ai_analysis.get("transparency_score", 50)
        
        # Adjust with Kronos signal if available
        kronos_signal = 0
        if kronos_prediction:
            metrics = kronos_prediction.get("metrics", {})
            if metrics.get("signal") == "BUY":
                kronos_signal = 10
            elif metrics.get("signal") == "SELL":
                kronos_signal = -10
        
        overall_score = min(100, max(0, 
            health * 0.4 + 
            transparency * 0.3 + 
            (50 + kronos_signal) * 0.3
        ))
        
        anomalies = ai_analysis.get("anomalies", [])
        red_flags = ai_analysis.get("red_flags", [])
        
        # Risk level
        if len([a for a in anomalies if a.get("severity") == "high"]) > 2:
            risk_level = "CAO"
        elif len(anomalies) > 3 or len(red_flags) > 2:
            risk_level = "TRUNG_BÌNH"
        else:
            risk_level = "THẤP"
        
        # Investment verdict
        if overall_score >= 70 and risk_level != "CAO":
            verdict = "HẤP_DẪN"
        elif overall_score >= 50:
            verdict = "TRUNG_LẬP"
        else:
            verdict = "KHÔNG_HẤP_DẪN"
        
        report = {
            "symbol": symbol.upper(),
            "analysis_type": "full_report",
            "generated_at": datetime.now().isoformat(),
            
            "result": {
                "overall_score": round(overall_score, 1),
                "health_score": health,
                "transparency_score": transparency,
                "risk_level": risk_level,
                "verdict": verdict,
                "anomalies": anomalies,
                "red_flags": red_flags,
                "key_findings": ai_analysis.get("key_findings", []),
                "recommendations": ai_analysis.get("recommendations", []),
                "kronos_signal": kronos_prediction["metrics"] if kronos_prediction else None,
                "macro_context": macro_data[:5] if macro_data else None,
            },
            
            "score": round(overall_score, 1),
            "summary": ai_analysis.get("summary", ""),
            "recommendations": ai_analysis.get("recommendations", []),
            "model_version": f"aifia_v1_{self.config.kronos_model.replace('/', '_')}",
        }
        
        return report
