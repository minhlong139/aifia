"""AIFIA Crawler Configuration"""
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Auto-load .env from project root at import time
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_project_root, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path, override=False)


@dataclass
class CrawlerConfig:
    # VN100 config
    vn100_file: str = "data/vn100_symbols.json"
    
    # Time range for data collection
    price_start_date: str = "2018-01-01"
    financial_years_back: int = 10  # crawl 10 years of financial data
    
    # Batch settings
    batch_size: int = 10  # companies per batch
    delay_between_requests: float = 0.5  # seconds
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 2.0
    
    # Supabase
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_key: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_KEY", ""))
    vnstock_api_key: str = field(default_factory=lambda: os.getenv("VNSTOCK_API_KEY", ""))
    
    # Enable/disable sources
    enable_vnstock: bool = True
    enable_company_sites: bool = False  # TBD for Phase 2
    
    # Cron schedule
    crawl_interval_hours: int = 24  # daily crawl
    
    # Logging
    log_level: str = "INFO"
