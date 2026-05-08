-- ==============================================================
-- AIFIA - AI Financial Intelligence Assistant
-- Supabase Database Schema
-- ==============================================================

-- Enable pgvector for AI embeddings (future use)
CREATE EXTENSION IF NOT EXISTS vector;

-- ==============================================================
-- 1. Companies
-- ==============================================================
CREATE TABLE IF NOT EXISTS companies (
    id          BIGSERIAL PRIMARY KEY,
    symbol      VARCHAR(20) UNIQUE NOT NULL,
    name        TEXT,
    name_en     TEXT,
    exchange    VARCHAR(10),        -- HOSE, HNX, UPCOM
    industry    TEXT,               -- ICB industry name (VN)
    industry_en TEXT,               -- ICB industry name (EN)
    icb_code    INTEGER,            -- ICB industry code
    established_date DATE,
    listed_date DATE,
    website     TEXT,
    profile_text TEXT,              -- Concise profile for AI
    market_cap  BIGINT,             -- VND
    shares_outstanding BIGINT,
    foreign_ownership_limit REAL,
    
    -- Additional metadata
    status      VARCHAR(20) DEFAULT 'active',
    raw_data    JSONB,              -- Full response from vnstock
    
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_companies_symbol ON companies(symbol);
CREATE INDEX idx_companies_industry ON companies(industry);
CREATE INDEX idx_companies_exchange ON companies(exchange);

-- ==============================================================
-- 2. Financial Reports
-- ==============================================================
CREATE TABLE IF NOT EXISTS financial_reports (
    id          BIGSERIAL PRIMARY KEY,
    symbol      VARCHAR(20) NOT NULL,
    quarter     INTEGER NOT NULL,   -- 1-4
    year        INTEGER NOT NULL,
    report_type VARCHAR(50) NOT NULL, -- income_statement, balance_sheet, cash_flow, ratios
    report_data JSONB NOT NULL,      -- Full report data
    
    -- Metadata
    source      VARCHAR(50) DEFAULT 'vnstock',
    currency    VARCHAR(10) DEFAULT 'VND',
    raw_text    TEXT,                -- For AI analysis
    
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (symbol, quarter, year, report_type)
);

CREATE INDEX idx_financial_reports_symbol ON financial_reports(symbol);
CREATE INDEX idx_financial_reports_time ON financial_reports(symbol, year DESC, quarter DESC);

-- ==============================================================
-- 3. Price History
-- ==============================================================
CREATE TABLE IF NOT EXISTS price_history (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL,
    date            DATE NOT NULL,
    open            DOUBLE PRECISION,
    high            DOUBLE PRECISION,
    low             DOUBLE PRECISION,
    close           DOUBLE PRECISION,
    volume          BIGINT,
    adjusted_close  DOUBLE PRECISION,
    
    source          VARCHAR(50) DEFAULT 'vnstock',
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (symbol, date)
);

CREATE INDEX idx_price_history_symbol ON price_history(symbol);
CREATE INDEX idx_price_history_date ON price_history(date DESC);
CREATE INDEX idx_price_history_symbol_date ON price_history(symbol, date DESC);

-- ==============================================================
-- 4. Macro Economic Data
-- ==============================================================
CREATE TABLE IF NOT EXISTS macro_data (
    id          BIGSERIAL PRIMARY KEY,
    indicator   VARCHAR(100) NOT NULL,  -- GDP, CPI, interest_rate, etc.
    value       DOUBLE PRECISION,
    unit        VARCHAR(50),
    period      VARCHAR(20) NOT NULL,   -- e.g. "2024-Q1", "2024"
    source      VARCHAR(50) DEFAULT 'vnstock',
    
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (indicator, period)
);

CREATE INDEX idx_macro_indicator ON macro_data(indicator);

-- ==============================================================
-- 5. Analysis Results
-- ==============================================================
CREATE TABLE IF NOT EXISTS analysis_results (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL,
    analysis_type   VARCHAR(50) NOT NULL, -- anomaly, insight, rating, full_report
    
    result          JSONB NOT NULL,       -- Structured analysis result
    summary         TEXT,                 -- Human-readable summary
    score           REAL,                -- 0-100 overall score
    recommendations TEXT[],              -- Actionable recommendations
    
    model_version   VARCHAR(50),
    metadata        JSONB,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analysis_symbol ON analysis_results(symbol);
CREATE INDEX idx_analysis_type ON analysis_results(analysis_type);
CREATE INDEX idx_analysis_created ON analysis_results(created_at DESC);

-- ==============================================================
-- 6. Kronos Predictions
-- ==============================================================
CREATE TABLE IF NOT EXISTS kronos_predictions (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL,
    
    -- Prediction window
    prediction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    lookback_start  TIMESTAMPTZ,
    prediction_end  TIMESTAMPTZ,
    
    -- Data
    predicted_ohlcv JSONB,        -- [{date, open, high, low, close, volume}]
    metrics         JSONB,        -- {accuracy, confidence, upsdie_prob, ...}
    
    model_version   VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kronos_symbol ON kronos_predictions(symbol);
CREATE INDEX idx_kronos_date ON kronos_predictions(prediction_date DESC);

-- ==============================================================
-- 7. Crawl Log (tracking what was crawled when)
-- ==============================================================
CREATE TABLE IF NOT EXISTS crawl_log (
    id          BIGSERIAL PRIMARY KEY,
    pipeline    VARCHAR(100) NOT NULL,  -- full, incremental, company
    status      VARCHAR(20) NOT NULL,   -- running, success, failed, partial
    symbols_count INTEGER,
    reports_count INTEGER,
    price_count INTEGER,
    error_count INTEGER,
    
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    error_log   JSONB,
    metadata    JSONB
);

-- ==============================================================
-- 8. Company Financial Highlights (materialized for quick queries)
-- ==============================================================
CREATE TABLE IF NOT EXISTS company_highlights (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(20) UNIQUE NOT NULL,
    
    -- Current metrics
    current_price   DOUBLE PRECISION,
    price_change_1m REAL,      -- % change 1 month
    price_change_3m REAL,      -- % change 3 months
    price_change_1y REAL,      -- % change 1 year
    
    pe_ratio        REAL,
    pb_ratio        REAL,
    eps             REAL,
    roe             REAL,
    roa             REAL,
    dividend_yield  REAL,
    market_cap      BIGINT,
    
    -- AI summary
    ai_rating       REAL,       -- 0-100
    ai_summary      TEXT,
    anomalies       TEXT[],     -- List of detected anomalies
    
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_highlights_symbol ON company_highlights(symbol);
CREATE INDEX idx_highlights_rating ON company_highlights(ai_rating DESC);

-- ==============================================================
-- Trigger: auto-update updated_at
-- ==============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_highlights_updated_at
    BEFORE UPDATE ON company_highlights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
