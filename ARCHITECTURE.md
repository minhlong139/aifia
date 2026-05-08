# AIFIA Architecture

## 1. Kiến trúc tổng thể

```
                                  ┌──────────────────────────┐
                                  │      OpenClaw            │
                                  │  (Orchestrator)          │
                                  │  - Cron scheduling       │
                                  │  - Webhook triggers      │
                                  │  - Query interface       │
                                  └──────┬──────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────┐
              │                          │                      │
    ┌─────────▼────────┐   ┌────────────▼────────┐  ┌─────────▼────────┐
    │  Crawler (Py)    │   │  Processing (Py)     │  │  Frontend        │
    │  - Vnstock API   │   │  - Kronos model      │  │ (Next.js/Vercel) │
    │  - Company sites │   │  - AI analysis       │  │  - Dashboard     │
    │  - Data ingestion│   │  - Insight gen       │  │  - Reports       │
    └─────────┬────────┘   └────────────┬────────┘  └─────────┬────────┘
              │                          │                      │
              └────────────────┬─────────┼──────────────────────┘
                               │         │
                    ┌──────────▼─────────▼──────────┐
                    │        Supabase                │
                    │  - Companies                   │
                    │  - Financial Reports           │
                    │  - Price History               │
                    │  - Analysis Results            │
                    │  - Macro Data                  │
                    │  - Kronos Predictions          │
                    └────────────────────────────────┘
```

## 2. Layer 1: Crawler (Python)

### 2.1 Vnstock Source
**Library:** `vnstock` (pip install vnstock)

**Dữ liệu crawl:**
- **Danh sách công ty:** `all_symbols()`, `symbols_by_group('VN100')`
- **Thông tin công ty:** `overview(symbol)`, `profile(symbol)`
- **BCTC (Quý):**
  - `income_statement(symbol)` — KQKD
  - `balance_sheet(symbol)` — CĐKT
  - `cash_flow(symbol)` — LCTT
  - `ratio(symbol)` — Chỉ số tài chính
- **Giá cổ phiếu:** `history(symbol, start, end)` — OHLCV historical
- **Cổ đông:** `shareholders(symbol)`
- **Lãnh đạo:** `officers(symbol)`

### 2.2 Company Website Scraper
**Fallback:** Crawl trực tiếp từ website doanh nghiệp nếu thiếu dữ liệu từ vnstock.

- URL pattern: `https://ir.{company}.vn/` hoặc các site công bố thông tin
- Parse PDF báo cáo tài chính
- Lưu raw text + metadata

### 2.3 Pipeline
```python
CrawlPipeline:
  Step 1: Fetch VN100 symbol list
  Step 2: For each symbol -> get company info -> store to Supabase
  Step 3: For each symbol -> get financial reports -> store to Supabase
  Step 4: For each symbol -> get price history -> store to Supabase
  Step 5: Get macro data -> store to Supabase
  Step 6: Trigger processing pipeline
```

## 3. Layer 2: Supabase Storage

### Tables

```sql
-- Companies / Metadata
companies (id, symbol, name, exchange, industry, icb_code,
           established_date, listed_date, website, profile_text,
           market_cap, shares_outstanding, updated_at)

-- Financial Reports (Quaterly)
financial_reports (id, company_id, symbol, quarter, year,
                   report_type, -- income/balance/cashflow/ratios
                   report_data JSONB, -- full data as JSON
                   source, raw_text, ingested_at)

-- Price History
price_history (id, symbol, date, open, high, low, close,
               volume, adjusted_close, source, ingested_at)

-- Macro Data
macro_data (id, indicator, value, unit, period, source)

-- Analysis Results
analysis_results (id, company_id, symbol, analysis_type,
                  -- anomaly/insight/rating
                  result JSONB, summary text, score float,
                  model_version, created_at)

-- Kronos Predictions
kronos_predictions (id, symbol, prediction_date,
                    lookback_start, prediction_end,
                    predicted_ohlcv JSONB, metrics JSONB,
                    model_version, created_at)
```

## 4. Layer 3: Processing

### 4.1 Kronos Integration
- Sử dụng pre-trained model từ HuggingFace
- Input: OHLCV data (512 token window)
- Output: Price forecast
- Frequency: Daily batch prediction

### 4.2 AI Financial Analysis
- Sử dụng LLM (OpenAI/Claude) để phân tích BCTC
- **Anomaly Detection:** Phát hiện bất thường (revenue jump, margin inconsistency...)
- **Transparency Assessment:** Đánh giá mức minh bạch
- **Contradiction Detection:** Phát hiện mâu thuẫn giữa các báo cáo
- **Insight Summary:** Tổng hợp đánh giá doanh nghiệp

### 4.3 Report Generator
- Kết hợp Kronos forecast + AI analysis + macro data
- Đưa ra nhận định sơ bộ về mức độ hấp dẫn đầu tư
- Score tổng hợp (1-100)

## 5. Layer 4: Presentation

### 5.1 Vercel Frontend
- **Market Dashboard:** Tổng quan thị trường (VN-Index, VN30, VN100)
- **Company Detail:** BCTC, biểu đồ, Kronos forecast, AI insights
- **Screener:** Filter cổ phiếu theo chỉ số
- **Alerts:** Cảnh báo bất thường

### 5.2 OpenClaw Query Interface
- Telegram query: `@aifia [mã cổ phiếu]`
- Response: Company overview + AI rating + recent anomalies
- Cron: Daily market summary report

## 6. Data Flow

```
Vnstock API ──► Crawler Pipeline ──► Supabase
                                           │
                    ┌──────────────────────┘
                    ▼
            Kronos Analyzer ──► Predictions ──► Supabase
            AI Analyzer ──► Insights ──► Supabase
                                           │
                    ┌──────────────────────┘
                    ▼
            Vercel Dashboard ◄── Query ──► OpenClaw
```

## 7. Deployment

| Component | Host | Tech |
|-----------|------|------|
| Crawler | OpenClaw host / GitHub Actions | Python |
| Database | Supabase Cloud | PostgreSQL + pgvector |
| Processing | OpenClaw / Serverless | Python + Torch |
| Frontend | Vercel | Next.js + Tailwind |
| Query Interface | Telegram (via OpenClaw) | OpenAI/Claude |
