"""AIFIA Processing Configuration."""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProcessingConfig:
    # AI Provider
    ai_provider: str = field(default_factory=lambda: os.getenv("AI_PROVIDER", "openai"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    
    # Kronos Model
    kronos_model: str = "NeoQuasar/Kronos-small"  # 24.7M params, context 512
    kronos_tokenizer: str = "NeoQuasar/Kronos-Tokenizer-base"
    kronos_max_context: int = 512
    kronos_pred_len: int = 60  # number of periods to predict
    
    # Analysis settings
    anomaly_sensitivity: str = "medium"  # low, medium, high
    enable_ai_analysis: bool = True
    enable_kronos: bool = True
    
    # Supabase
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_key: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_KEY", ""))
    
    # Scheduling
    analysis_interval_hours: int = 24
    
    # Device
    device: str = "cpu"  # cpu or cuda
