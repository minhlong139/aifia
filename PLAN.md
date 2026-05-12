# AIFIA — Kế hoạch phát triển (cập nhật 12/05/2026)

## ✅ Đã hoàn thành

### Crawler & Data Pipeline
- [x] Khảo sát dữ liệu: vnstock (OHLCV, BCTC, company info) + Kronos (price prediction)
- [x] Xác định kiến trúc: Crawler → Supabase → Processing → Frontend
- [x] Xây dựng Supabase schema (7 tables: companies, financial_reports, price_history, 
      macro_data, analysis_results, kronos_predictions, company_highlights)
- [x] Crawler vnstock_source: lấy danh sách VN100 + company info
- [x] Crawler lấy báo cáo tài chính (income_statement, balance_sheet, cash_flow, ratio)
- [x] Crawler lấy dữ liệu giá OHLCV (incremental, ~2018→nay)
- [x] Lưu trữ: local JSON + Supabase (dual storage)
- [x] Rate limiter tự động + retry mechanism
- [x] Kiểm thử pipeline crawl (100 symbols)

### OS Cron Scheduling (độc lập với OpenClaw)
- [x] `daily_price` — 15:30 T2-T6, crawl incremental giá mới nhất
- [x] `daily_price_and_upload` — crawl + upload lên Supabase (recommended)
- [x] `weekly_financial` — cuối tuần, refresh BCTC 2 năm gần nhất
- [x] `full_vn100` — đầu tháng, full crawl toàn bộ
- [x] `kronos_prediction` — 16:30 T2-T6, chạy dự báo Kronos
- [x] Fix: `set -a` khi source .env để truyền biến sang Python (env vars export)
- [x] Script `upload_prices.py` — upload incremental lên Supabase

### Supabase Data (hiện tại)
- [x] 100 companies: metadata đầy đủ (ngành, vốn hóa, lịch sử, website...)
- [x] Giá OHLCV: 197,417 records (~2,081 records/symbol, 2018→12/05/2026)
- [x] BCTC: income_statement, balance_sheet, cash_flow, ratio (Q3/2025→Q1/2026)
- [x] Dữ liệu cập nhật realtime sau mỗi phiên

### AI Processing & Kronos
- [x] Tích hợp Kronos model (price forecasting via cron)
- [x] AI financial report analyzer (OpenAI/Claude integration, scripts)
- [x] Phát hiện bất thường trong BCTC (anomaly detection)
- [x] Pipeline phân tích 100 mã (daily_full_analysis.py)
- [x] Ai upload script (ai_upload.py)
- [x] Report generator

### Frontend (Vercel — `aifia-wdpk.vercel.app`)
- [x] Next.js project setup (App Router, TypeScript, Tailwind v4)
- [x] Dashboard A-Z: danh sách 100 mã, search + filter theo ngành
- [x] Badge data coverage: BCTC, Kronos signal (🔥⚡⚠️💀)
- [x] Trang chi tiết công ty: `/company/[symbol]`
  - [x] Tổng quan: vốn hóa, P/E, P/B, EPS, ROE
  - [x] Biểu đồ giá OHLCV (recharts)
  - [x] KQKD comparison table (QoQ/YoY)
  - [x] Chỉ số tài chính (ROE, biên lợi nhuận, D/E...)
  - [x] AI Analysis score card (color-coded)
  - [x] Kronos predictions display
  - [x] Prev/Next navigation giữa các mã
  - [x] Format VND: toLocaleString('vi-VN')
- [x] API proxy `/api/db` (bypass RLS với service key)
- [x] Fix deployment (PostCSS, webpack alias, edge runtime)

### OpenClaw Automation
- [x] Workflow: daily_crawl (15:35 T2-T6)
- [x] Workflow: daily_summary (báo cáo cuối ngày)
- [x] Workflow: analyze_symbol (phân tích theo yêu cầu)
- [x] Workflow: daily_full_analysis (18:30 T2-T6) — phân tích 100 mã + AI enhancement

### Infrastructure
- [x] OS cron độc lập (không phụ thuộc OpenClaw)
- [x] GitHub repo: `minhlong139/aifia`
- [x] Vercel auto-deploy từ branch `main`
- [x] Supabase project live
- [x] Telegram notification channel

---

## 📋 Kế hoạch tới

### Ngắn hạn
- [ ] Hoàn thiện báo giá sáng/chiều (bao-gia-morning, bao-gia-afternoon đang chạy từ web)
- [ ] Cập nhật dữ liệu realtime/intraday (nếu có nguồn)
- [ ] Dashboard thị trường tổng quan (VN-Index, VN30)
- [ ] Fix production domain `aifia.vercel.app` (hiện đang bị project khác chiếm)

### Trung hạn
- [ ] Thêm bộ lọc nâng cao (P/E range, ngành, vốn hóa...)
- [ ] So sánh multiple stocks
- [ ] Portfolio tracking
- [ ] Alert/notification khi có bất thường

### Dài hạn
- [ ] User accounts & authentication
- [ ] Premium features (nếu có insiders API vnstock)
- [ ] Mobile app
