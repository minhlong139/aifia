"""Supabase storage client for AIFIA."""
from typing import Optional, Any, Dict, List
from datetime import datetime
import json

from supabase import create_client, Client
from ..config import CrawlerConfig


class SupabaseStorage:
    """Handles all data persistence to Supabase."""
    
    def __init__(self, config: CrawlerConfig):
        self.url = config.supabase_url
        self.key = config.supabase_key
        self.client: Optional[Client] = None
        
        if self.url and self.key:
            self.client = create_client(self.url, self.key)
    
    def is_connected(self) -> bool:
        return self.client is not None
    
    # ──────────────────────────────────────────────
    # Companies
    # ──────────────────────────────────────────────
    
    def upsert_company(self, data: Dict[str, Any]) -> bool:
        """Insert or update company info."""
        try:
            self.client.table("companies").upsert(data, on_conflict="symbol").execute()
            return True
        except Exception as e:
            print(f"  [Supabase] Error upserting company {data.get('symbol')}: {e}")
            return False
    
    def upsert_companies_batch(self, companies: List[Dict]) -> bool:
        """Batch upsert companies."""
        try:
            self.client.table("companies").upsert(companies, on_conflict="symbol").execute()
            return True
        except Exception as e:
            print(f"  [Supabase] Error batch upserting companies: {e}")
            return False
    
    # ──────────────────────────────────────────────
    # Financial Reports
    # ──────────────────────────────────────────────
    
    def upsert_financial_report(self, report: Dict[str, Any]) -> bool:
        """Insert or update a financial report."""
        try:
            # Convert complex types to JSON
            if isinstance(report.get("report_data"), dict):
                report["report_data"] = json.dumps(report["report_data"])
            
            self.client.table("financial_reports").upsert(
                report, 
                on_conflict="symbol,quarter,year,report_type"
            ).execute()
            return True
        except Exception as e:
            print(f"  [Supabase] Error upserting report: {e}")
            return False
    
    def upsert_financial_reports_batch(self, reports: List[Dict]) -> bool:
        """Batch upsert financial reports."""
        try:
            for r in reports:
                if isinstance(r.get("report_data"), dict):
                    r["report_data"] = json.dumps(r["report_data"])
            
            self.client.table("financial_reports").upsert(
                reports, 
                on_conflict="symbol,quarter,year,report_type"
            ).execute()
            return True
        except Exception as e:
            print(f"  [Supabase] Error batch upserting reports: {e}")
            return False
    
    # ──────────────────────────────────────────────
    # Price History
    # ──────────────────────────────────────────────
    
    def upsert_price_data(self, prices: List[Dict]) -> bool:
        """Batch upsert price history data."""
        try:
            self.client.table("price_history").upsert(
                prices, 
                on_conflict="symbol,date"
            ).execute()
            return True
        except Exception as e:
            print(f"  [Supabase] Error upserting prices: {e}")
            return False
    
    def get_latest_price_date(self, symbol: str) -> Optional[str]:
        """Get the most recent price date for a symbol (for incremental crawl)."""
        try:
            result = self.client.table("price_history")\
                .select("date")\
                .eq("symbol", symbol)\
                .order("date", desc=True)\
                .limit(1)\
                .execute()
            if result.data:
                return result.data[0]["date"]
            return None
        except Exception:
            return None
    
    # ──────────────────────────────────────────────
    # Macro Data
    # ──────────────────────────────────────────────
    
    def upsert_macro_data(self, data: List[Dict]) -> bool:
        """Batch upsert macro economic data."""
        try:
            self.client.table("macro_data").upsert(
                data,
                on_conflict="indicator,period"
            ).execute()
            return True
        except Exception as e:
            print(f"  [Supabase] Error upserting macro data: {e}")
            return False
    
    # ──────────────────────────────────────────────
    # Analysis Results
    # ──────────────────────────────────────────────
    
    def upsert_analysis(self, analysis: Dict[str, Any]) -> bool:
        """Insert an analysis result."""
        try:
            if isinstance(analysis.get("result"), (dict, list)):
                analysis["result"] = json.dumps(analysis["result"])
            
            self.client.table("analysis_results").insert(analysis).execute()
            return True
        except Exception as e:
            print(f"  [Supabase] Error upserting analysis: {e}")
            return False
    
    # ──────────────────────────────────────────────
    # Kronos Predictions
    # ──────────────────────────────────────────────
    
    def upsert_kronos_prediction(self, pred: Dict[str, Any]) -> bool:
        """Insert a Kronos prediction."""
        try:
            if isinstance(pred.get("predicted_ohlcv"), (dict, list)):
                pred["predicted_ohlcv"] = json.dumps(pred["predicted_ohlcv"])
            if isinstance(pred.get("metrics"), dict):
                pred["metrics"] = json.dumps(pred["metrics"])
            
            self.client.table("kronos_predictions").insert(pred).execute()
            return True
        except Exception as e:
            print(f"  [Supabase] Error upserting Kronos prediction: {e}")
            return False
    
    # ──────────────────────────────────────────────
    # Query Helpers
    # ──────────────────────────────────────────────
    
    def get_company(self, symbol: str) -> Optional[Dict]:
        """Get company by symbol."""
        result = self.client.table("companies")\
            .select("*")\
            .eq("symbol", symbol.upper())\
            .limit(1)\
            .execute()
        return result.data[0] if result.data else None
    
    def get_financial_reports(self, symbol: str, limit: int = 20) -> List[Dict]:
        """Get financial reports for a symbol."""
        result = self.client.table("financial_reports")\
            .select("*")\
            .eq("symbol", symbol.upper())\
            .order("year", desc=True)\
            .order("quarter", desc=True)\
            .limit(limit)\
            .execute()
        return result.data
    
    def get_price_history(self, symbol: str, days: int = 365) -> List[Dict]:
        """Get recent price history for a symbol."""
        result = self.client.table("price_history")\
            .select("*")\
            .eq("symbol", symbol.upper())\
            .order("date", desc=True)\
            .limit(days)\
            .execute()
        return result.data
    
    def get_latest_analysis(self, symbol: str) -> Optional[Dict]:
        """Get the latest analysis result for a symbol."""
        result = self.client.table("analysis_results")\
            .select("*")\
            .eq("symbol", symbol.upper())\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        return result.data[0] if result.data else None
