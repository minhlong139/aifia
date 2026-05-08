"""AI-powered financial report analysis.

Analyzes financial statements to detect:
- Anomalies and red flags
- Transparency issues
- Inconsistencies between reports
- Overall financial health
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from .config import ProcessingConfig


class FinancialAnalyzer:
    """AI agent that analyzes financial reports using LLM."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self._llm_client = None
    
    def _get_llm(self):
        """Get LLM client (OpenAI or Anthropic)."""
        if self._llm_client:
            return self._llm_client
        
        if self.config.ai_provider == "openai" and self.config.openai_api_key:
            from openai import OpenAI
            self._llm_client = OpenAI(api_key=self.config.openai_api_key)
        elif self.config.ai_provider == "anthropic" and self.config.anthropic_api_key:
            from anthropic import Anthropic
            self._llm_client = Anthropic(api_key=self.config.anthropic_api_key)
        else:
            print("  [AI] No AI provider configured. Using mock analysis.")
            self._llm_client = "mock"
        
        return self._llm_client
    
    def _build_analysis_prompt(self, symbol: str, 
                               income_summary: str,
                               balance_summary: str,
                               cashflow_summary: str,
                               ratios_summary: str) -> str:
        """Build prompt for AI financial analysis."""
        return f"""Bạn là chuyên gia phân tích tài chính chứng khoán Việt Nam. Hãy phân tích báo cáo tài chính của mã cổ phiếu {symbol} và đưa ra đánh giá.

Dữ liệu tài chính:
--- KẾT QUẢ KINH DOANH (theo quý) ---
{income_summary}

--- CÂN ĐỐI KẾ TOÁN ---
{balance_summary}

--- LƯU CHUYỂN TIỀN TỆ ---
{cashflow_summary}

--- CHỈ SỐ TÀI CHÍNH ---
{ratios_summary}

Yêu cầu phân tích:
1. **PHÁT HIỆN BẤT THƯỜNG**: Doanh thu/lợi nhuận tăng giảm đột biến, biên lợi nhuận bất thường, nợ tăng đột biến
2. **TÍNH MINH BẠCH**: Đánh giá mức độ minh bạch, phát hiện dấu hiệu thiếu minh bạch
3. **MÂU THUẪN**: Dữ liệu giữa các báo cáo không nhất quán (VD: dòng tiền không khớp với lợi nhuận)
4. **ĐÁNH GIÁ TỔNG THỂ**: Sức khỏe tài chính, xu hướng, rủi ro

Trả về JSON với format:
{{
    "anomalies": [{{"type": "string", "severity": "high|medium|low", "description": "string", "detail": "string"}}],
    "transparency_score": 0-100,
    "health_score": 0-100,
    "summary": "Tổng quan ngắn gọn",
    "key_findings": ["finding1", "finding2"],
    "red_flags": ["flag1", "flag2"],
    "recommendations": ["rec1", "rec2"]
}}
"""
    
    def analyze(self, symbol: str,
                financial_data: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Analyze financial data for a company using AI.
        
        Args:
            symbol: Stock symbol
            financial_data: Dict with keys income_statement, balance_sheet, 
                           cash_flow, ratios
        
        Returns:
            Analysis result dict
        """
        client = self._get_llm()
        
        # Summarize financial data for the prompt
        income_summary = self._summarize_income(financial_data.get("income_statement", []))
        balance_summary = self._summarize_balance(financial_data.get("balance_sheet", []))
        cashflow_summary = self._summarize_cashflow(financial_data.get("cash_flow", []))
        ratios_summary = self._summarize_ratios(financial_data.get("ratios", []))
        
        if client == "mock":
            return self._mock_analysis(symbol, financial_data)
        
        prompt = self._build_analysis_prompt(
            symbol, income_summary, balance_summary, cashflow_summary, ratios_summary
        )
        
        try:
            if self.config.ai_provider == "openai":
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # cost-effective for structured analysis
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                result = json.loads(response.choices[0].message.content)
            
            elif self.config.ai_provider == "anthropic":
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = response.content[0].text
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                result = json.loads(json_match.group()) if json_match else {}
            
            result["model"] = f"{self.config.ai_provider}_financial_analyzer"
            return result
            
        except Exception as e:
            print(f"  [AI] Error analyzing {symbol}: {e}")
            return self._mock_analysis(symbol, financial_data)
    
    def _summarize_income(self, data: List[Dict]) -> str:
        """Summarize income statement for AI prompt."""
        if not data:
            return "Không có dữ liệu"
        
        # Get last 8 quarters for trend
        recent = sorted(data, key=lambda x: (x.get('year', 0), x.get('quarter', 0)), reverse=True)[:8]
        
        lines = []
        for r in reversed(recent):
            year = r.get('year', '?')
            q = r.get('quarter', '?')
            revenue = r.get('revenue', r.get('doanh_thuan', r.get('doanhthuthuan', 'N/A')))
            profit = r.get('net_profit', r.get('loi_nhuan', r.get('loinhuan', 'N/A')))
            gross_margin = r.get('gross_profit_margin', 'N/A')
            lines.append(f"  Q{q}/{year}: Revenue={revenue}, NetProfit={profit}, GrossMargin={gross_margin}%")
        
        return "\n".join(lines)
    
    def _summarize_balance(self, data: List[Dict]) -> str:
        """Summarize balance sheet for AI prompt."""
        if not data:
            return "Không có dữ liệu"
        
        recent = sorted(data, key=lambda x: (x.get('year', 0), x.get('quarter', 0)), reverse=True)[:4]
        
        lines = []
        for r in reversed(recent):
            year = r.get('year', '?')
            q = r.get('quarter', '?')
            total_assets = r.get('total_assets', r.get('tongsan', 'N/A'))
            equity = r.get('equity', r.get('vonchusohuu', 'N/A'))
            debt = r.get('total_debt', r.get('tongsong', 'N/A'))
            lines.append(f"  Q{q}/{year}: Assets={total_assets}, Equity={equity}, Debt={debt}")
        
        return "\n".join(lines)
    
    def _summarize_cashflow(self, data: List[Dict]) -> str:
        """Summarize cash flow for AI prompt."""
        if not data:
            return "Không có dữ liệu"
        
        recent = sorted(data, key=lambda x: (x.get('year', 0), x.get('quarter', 0)), reverse=True)[:8]
        
        lines = []
        for r in reversed(recent):
            year = r.get('year', '?')
            q = r.get('quarter', '?')
            operating = r.get('operating_cashflow', r.get('luuchuyenthuan', 'N/A'))
            free_cf = r.get('free_cash_flow', 'N/A')
            lines.append(f"  Q{q}/{year}: OperatingCF={operating}, FreeCF={free_cf}")
        
        return "\n".join(lines)
    
    def _summarize_ratios(self, data: List[Dict]) -> str:
        """Summarize financial ratios for AI prompt."""
        if not data:
            return "Không có dữ liệu"
        
        recent = sorted(data, key=lambda x: (x.get('year', 0), x.get('quarter', 0)), reverse=True)[:4]
        
        lines = []
        for r in reversed(recent):
            year = r.get('year', '?')
            q = r.get('quarter', '?')
            pe = r.get('pe', 'N/A')
            pb = r.get('pb', 'N/A')
            roe = r.get('roe', 'N/A')
            roa = r.get('roa', 'N/A')
            lines.append(f"  Q{q}/{year}: P/E={pe}, P/B={pb}, ROE={roe}%, ROA={roa}%")
        
        return "\n".join(lines)
    
    def _mock_analysis(self, symbol: str, financial_data: Dict) -> Dict:
        """Mock analysis when no AI provider is configured."""
        return {
            "anomalies": [],
            "transparency_score": 75,
            "health_score": 70,
            "summary": f"Phân tích cơ bản mã {symbol}. Vui lòng cấu hình API key (OpenAI/Anthropic) để có phân tích AI chi tiết.",
            "key_findings": [
                "Dữ liệu tài chính đã được thu thập",
                "Cần AI analysis để phát hiện bất thường"
            ],
            "red_flags": [],
            "recommendations": [
                "Cấu hình OpenAI hoặc Anthropic API để kích hoạt AI analysis"
            ],
            "model": "mock_analyzer",
            "note": "Mock mode - no AI API configured"
        }
