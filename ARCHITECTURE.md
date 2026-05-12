# AIFIA Architecture

## 1. Kiến trúc tổng thể

```
                                  ┌──────────────────────────┐
                                  │      OS Cron             │
                                  │  (Scheduler độc lập)     │
                                  │  - 15:30 daily_price     │
                                  │  - 16:30 kronos_pred     │
                                  │  - 17:00 thứ 7 financial │
                                  │  - 08:00 CN full_vn100   │
                                  └──────────┬───────────────┘
                                             │
              ┌──────────────────────────────┼──────────────────────┐
              │                              │                      │
    ┌─────────▼────────┐         ┌───────────▼────────┐  ┌─────────▼────────┐
    │  Crawler (Py)    │         │  Processing (Py)    │  │  Frontend        │
    │  - Vnstock API   │         │  - Kronos model     │  │ (Next.js/Vercel) │
    │  - Data ingestion│         │  - AI analysis      │  │  - Dashboard A-Z │
    │  - Local JSON    │         │  - Anomaly detect   │  │  - Company page  │
    │    backup        │         │  - Report gen       │  │  - API proxy     │
    └─────────┬────────┘         └───────────┬────────┘  └─────────┬────────┘
              │                              │                      │
              └────────────────┬──────────────┼──────────────────────┘
                               │              │
                    ┌──────────▼──────────────▼──────────┐
                    │        Supabase (7 tables)          │
                    │  - companies                        │
                    │  - financial_reports                │
                    │  - price_history (~197K records)    │
                    │  - analysis_results                 │
                    │  - macro_data                       │
                    │  - kronos_predictions               │
                    │  - company_highlights               │
                    └────────────────────────────────────┘
                               │
                    ┌──────────▼──────────────┐
                    │  OpenClaw (Telegram)    │
                    │  - Tra cứu CK           │
                    │  - Báo cáo cuối ngày    │
                    │  - Full analysis 18:30  │
                    └─────────────────────────┘
```

> **Lưu ý:** Scheduling crawl được thực hiện qua **OS cron**, không qua OpenClaw.
> OpenClaw chỉ phụ trách: (1) phân tích nâng cao (AI enhancement), (2) tra cứu Telegram.
> Điều này đảm bảo crawl hoạt động độc lập, kể cả khi OpenClaw tắt.

---

## 2. Layer 1: Crawler (Python)

### 2.1 Vnstock Source
**Library:** `vnstock` ^4.0 (source='KBS')

**Dữ liệu crawl:**
- **Danh sách công ty:** `symbols_by_group('VN100')`
- **Thông tin công ty:** `profile(symbol)` + `overview(symbol)`
- **BCTC (Quý):**
  - `income_statement(symbol)` — KQKD
  - `balance_sheet(symbol)` — CĐKT
  - `cash_flow(symbol)` — LCTT
  - `ratio(symbol)` — Chỉ số tài chính
- **Giá cổ phiếu:** `history(symbol, start, end)` — OHLCV từ 2018

### 2.2 Pipeline
```python
CrawlPipeline:
  Step 1: Fetch VN100 symbol list
  Step 2: For each symbol -> get company info -> local JSON + Supabase
  Step 3: For each symbol -> get financial reports -> local JSON + Supabase
  Step 4: For each symbol -> get price history -> local JSON + Supabase
  Step 5: Save crawl summary
```

Dữ liệu luôn được lưu dual: local JSON (backup) + Supabase (primary).
Nếu Supabase offline, crawl vẫn chạy và ghi file.

---

## 3. Layer 2: Supabase Storage

### Tables

| Table | Mục đích | Primary Key | Records |
|---|---|---|---|
| **companies** | Thông tin doanh nghiệp | symbol | ~100 |
| **financial_reports** | BCTC (income/balance/cashflow/ratio) | symbol + quarter + year + report_type | ~500 |
| **price_history** | Giá OHLCV hàng ngày | symbol + date | ~197,000 |
| **macro_data** | Dữ liệu vĩ mô (GDP, CPI, ...) | indicator + period | — |
| **analysis_results** | Kết quả phân tích AI | id | — |
| **kronos_predictions** | Dự báo giá từ Kronos | id | ~97 |
| **company_highlights** | Điểm nổi bật doanh nghiệp | id | — |

### Security
- Frontend (Vercel) gọi Supabase qua **API proxy** (`/api/db` route)
- Proxy dùng **service key** (server-side only, không lộ ra client)
- Client-side không access Supabase trực tiếp (tránh RLS issues)

---

## 4. Layer 3: Processing

### 4.1 Kronos Integration
- Pre-trained model cho OHLCV prediction
- Input: 512 token window price history
- Output: Price forecast (next N days)
- Frequency: Daily batch (16:30, sau khi có giá mới)

### 4.2 AI Financial Analysis
- Sử dụng LLM (OpenAI/Claude) để phân tích BCTC
- **Anomaly Detection:** Phát hiện bất thường (revenue jump, margin inconsistency...)
- **Transparency Assessment:** Đánh giá mức minh bạch
- **Insight Summary:** Tổng hợp đánh giá doanh nghiệp
- Kết quả lưu vào `analysis_results` + `company_highlights`

### 4.3 Report Generator
- Kết hợp Kronos forecast + AI analysis
- Score tổng hợp (1-100)
- Daily summary cho Telegram

---

## 5. Layer 4: Presentation

### 5.1 Vercel Frontend (`aifia-wdpk.vercel.app`)
- **Dashboard A-Z:** Danh sách 100 mã (search/filter theo ngành, mã)
- **Data Coverage Badges:** Hiển thị trạng thái BCTC + Kronos signal
- **Company Detail:** BCTC, biểu đồ giá, Kronos forecast, AI insights
- **API Proxy:** `/api/db` route — edge runtime, gọi Supabase với service key

### 5.2 OpenClaw Telegram
- Tra cứu mã CK: phân tích nhanh qua Telegram
- Daily summary: báo cáo cuối ngày
- Full analysis: phân tích 100 mã (18:30 T2-T6)

---

## 6. Data Flow

```
Vnstock API ──► CrawlPipeline ──► Local JSON + Supabase
                                          │
                    ┌─────────────────────┘
                    ▼
            Kronos Analyzer ──► Predictions ──► Supabase
            AI Analyzer ──► Insights ──► Supabase
                                          │
                    ┌─────────────────────┘
                    ▼
            Vercel Dashboard ◄── API Proxy ──► OpenClaw
```

---

## 7. Deployment

| Component | Host | Tech | Scheduling |
|---|---|---|---|
| Crawler | OS cron | Python, vnstock | **OS cron** (15:30 daily) |
| Database | Supabase Cloud | PostgreSQL | — |
| Processing | OS cron / OpenClaw | Python, Torch | OS cron (16:30) / OpenClaw (18:30) |
| Frontend | Vercel | Next.js, Tailwind | Auto-deploy từ GitHub main |
| Telegram Bot | OpenClaw | — | 18:30 T2-T6 (full analysis) |
