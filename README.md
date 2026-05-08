# AIFIA - AI Financial Intelligence Assistant 🏦🤖

Hệ thống AI hỗ trợ phân tích báo cáo tài chính doanh nghiệp niêm yết trên thị trường chứng khoán Việt Nam.

## Kiến trúc tổng quan

```
┌─────────────────────────────────────────────┐
│           Layer 1: Crawler (Python)          │
│  ┌──────────┐  ┌────────────┐  ┌──────────┐ │
│  │ Vnstock  │  │ Company    │  │ VnDirect │ │
│  │ API      │  │ Websites   │  │ API      │ │
│  └────┬─────┘  └─────┬──────┘  └────┬─────┘ │
│       │              │              │        │
│  ┌────▼──────────────▼──────────────▼────┐   │
│  │        Data Ingestion Pipeline         │   │
│  └────────────────┬──────────────────────┘   │
└───────────────────┼──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│          Layer 2: Storage (Supabase)          │
│  ┌─────────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Companies    │ │ Financial│ │ Price     │  │
│  │ Metadata    │ │ Reports  │ │ History   │  │
│  └─────────────┘ └──────────┘ └───────────┘  │
│  ┌─────────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Macro       │ │ Analysis │ │ Kronos    │  │
│  │ Data        │ │ Results  │ │ Predictions│ │
│  └─────────────┘ └──────────┘ └───────────┘  │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│      Layer 3: Processing                      │
│  ┌────────────────────────┐ ┌──────────────┐  │
│  │ Kronos (Price Fore-    │ │ AI Financial │  │
│  │ cast & Analysis)      │ │ Report       │  │
│  │                        │ │ Analysis     │  │
│  └────────────────────────┘ └──────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │ Insight Aggregator & Report Generator    │  │
│  └──────────────────┬───────────────────────┘  │
└─────────────────────┼──────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────┐
│      Layer 4: Presentation                      │
│  ┌─────────────────┐  ┌──────────────────────┐  │
│  │ Vercel Frontend  │  │ OpenClaw (Telegram)  │  │
│  │ (Dashboard)      │  │ (Query Interface)    │  │
│  └─────────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## Cấu trúc project

```
aifia/
├── README.md               # Giới thiệu project
├── ARCHITECTURE.md         # Kiến trúc chi tiết
├── PLAN.md                 # Kế hoạch phát triển theo tuần
├── requirements.txt        # Python dependencies
├── .env.example            # Mẫu biến môi trường
├── .gitignore
│
├── crawler/                # Layer 1: Data Crawler
│   ├── pipeline.py         # Pipeline orchestrator
│   ├── config.py           # Crawler config
│   ├── sources/
│   │   ├── vnstock_source.py     # Vnstock API integration
│   │   └── company_sites.py      # Corporate website scraper
│   ├── extractors/
│   │   ├── financial_reports.py  # Financial report parsing
│   │   └── stock_prices.py       # Stock price extractor
│   └── storage/
│       └── supabase_client.py    # Supabase storage layer
│
├── processing/             # Layer 3: AI & Analysis
│   ├── config.py           # Processing config
│   ├── kronos_analyzer.py  # Kronos price analysis
│   ├── financial_analyzer.py  # AI financial report analysis
│   ├── macro_analyzer.py     # Macro data analysis
│   └── report_generator.py   # Insight aggregation
│
├── supabase/               # Layer 2: Database
│   ├── schema.sql          # Full Supabase schema
│   └── migrations/         # Incremental migrations
│
├── vercel-frontend/        # Layer 4: Frontend (placeholder)
├── scripts/                # Entry point scripts
│   ├── run_crawler.py
│   └── run_analysis.py
└── openclaw/               # OpenClaw workflow scripts
    └── workflows/
```

## Tech Stack

| Layer | Công nghệ |
|-------|----------|
| Crawler | Python, vnstock, BeautifulSoup, httpx |
| Storage | Supabase (PostgreSQL + pgvector) |
| Processing | Kronos (OHLCV foundation model), OpenAI/Claude API |
| Frontend | Next.js + Tailwind + Recharts (Vercel) |
| Orchestration | OpenClaw cron + webhook |
| Monitoring | OpenClaw + Supabase logs |
