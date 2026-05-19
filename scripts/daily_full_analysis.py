#!/usr/bin/env python3
"""
AIFIA Daily Full Analysis — Data Preparation Script

Công việc:
1. Đọc toàn bộ 100 mã từ Supabase
2. Fetch BCTC + giá mới nhất từ vnstock API
3. Tính toán 30+ chỉ số tài chính/kỹ thuật cho mỗi mã
4. Phát hiện bất thường rule-based
5. Ghi metric lên Supabase (company_highlights + analysis_results)
6. Xuất file batch để OpenClaw sub-agent phân tích AI sâu

Usage:
    python scripts/daily_full_analysis.py --prepare       # Chỉ prep data
    python scripts/daily_full_analysis.py --batch N       # Xử lý batch N
    python scripts/daily_full_analysis.py --full           # Full pipeline
"""
import os, sys, json, math
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── Load .env ──────────────────────────────────────
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ[k.strip()] = v.strip()

from crawler.storage import SupabaseStorage
from crawler.config import CrawlerConfig
from crawler.pipeline import RateLimiter

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
HISTORY_DIR = os.path.join(DATA_DIR, "history")

# ─── Helpers ────────────────────────────────────────

def safe_float(v, default=None):
    if v is None: return default
    try:
        f = float(v)
        return f if not math.isnan(f) and not math.isinf(f) else default
    except: return default

def pick(d: dict, *keys):
    for k in keys:
        v = d.get(k)
        if v is not None:
            f = safe_float(v)
            if f is not None: return f
    return None

def fmt_t(v):
    f = safe_float(v)
    return round(f / 1_000_000_000, 2) if f else None

# ─── Daily Stock Analyzer ───────────────────────────

class DailyStockAnalyzer:
    """Phân tích toàn diện 1 mã cổ phiếu — rule-based metrics."""

    def __init__(self):
        self.rate_limiter = RateLimiter(max_per_minute=15)
        config = CrawlerConfig()
        self.storage = SupabaseStorage(config)
        # Pre-fetch company data
        self._companies = {}
        self._incomes = {}
        self._balances = {}
        self._cashflows = {}
        self._ratios = {}
        self._prices = {}

    def analyze_all(self) -> List[Dict]:
        if not self.storage.is_connected():
            print("❌ Supabase not connected")
            return []

        result = self.storage.client.table("companies").select("symbol, industry").execute()
        symbols = [r["symbol"] for r in result.data] if result.data else []
        print(f"📋 {len(symbols)} symbols loaded from Supabase")

        # Bulk fetch financial data (1 pass per table, not 100 queries)
        print("⏳ Bulk fetching financial data from Supabase...")
        self._bulk_fetch(symbols)

        results = []
        for i, sym in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] {sym}...", end=" ")
            try:
                analysis = self._analyze_stock(sym)
                results.append(analysis)
                print(f"✅ {analysis['score']}/100")
            except Exception as e:
                print(f"❌ {e}")
                results.append(self._empty_analysis(sym, str(e)))

        return results

    def _bulk_fetch(self, symbols: List[str]):
        """Fetch all data once for all symbols (avoid N+1 queries)."""
        for rtype in ["income_statement", "balance_sheet", "cash_flow", "ratio"]:
            try:
                data = self.storage.client.table("financial_reports") \
                    .select("symbol, report_type, quarter, year, report_data") \
                    .in_("symbol", symbols).eq("report_type", rtype) \
                    .order("year", desc=True).order("quarter", desc=True).execute().data
                cache = self._cache_for(rtype)
                for row in data:
                    sym = row["symbol"]
                    if sym not in cache:
                        cache[sym] = []
                    cache[sym].append(row)
                print(f"  📊 {rtype}: {len(data)} records cached")
            except Exception as e:
                print(f"  ⚠️ {rtype}: {e}")

        # Prices - by symbol to keep manageable
        for sym in symbols:
            try:
                data = self.storage.client.table("price_history") \
                    .select("date, close, high, low, volume") \
                    .eq("symbol", sym).order("date", desc=True).limit(365).execute().data
                self._prices[sym] = data
            except:
                self._prices[sym] = []

        # Companies
        try:
            data = self.storage.client.table("companies") \
                .select("symbol, industry, exchange, market_cap, outstanding_shares, name") \
                .in_("symbol", symbols).execute().data
            for row in data:
                self._companies[row["symbol"]] = row
        except:
            pass

        print("✅ Bulk fetch complete")

    def _cache_for(self, rtype: str) -> dict:
        if rtype == "income_statement": return self._incomes
        if rtype == "balance_sheet": return self._balances
        if rtype == "cash_flow": return self._cashflows
        if rtype == "ratio": return self._ratios
        return {}

    def _analyze_stock(self, symbol: str) -> Dict:
        today = date.today().isoformat()
        company = self._companies.get(symbol)
        incomes = self._incomes.get(symbol, [])
        balances = self._balances.get(symbol, [])
        cashflows = self._cashflows.get(symbol, [])
        ratios_list = self._ratios.get(symbol, [])
        prices = self._prices.get(symbol, [])

        latest_inc = self._latest_record(incomes)
        prev_inc = self._prev_record(incomes)
        latest_bal = self._latest_record(balances)
        latest_cf = self._latest_record(cashflows)
        latest_price = self._latest_price(prices, 0)
        month_ago_price = self._latest_price(prices, 20)
        year_ago_price = self._latest_price(prices, 252)

        metrics = self._compute_metrics(
            symbol, company, latest_inc, prev_inc, latest_bal,
            latest_cf, prices, latest_price,
            month_ago_price, year_ago_price
        )

        anomalies = self._detect_anomalies(metrics)
        score = self._compute_score(metrics, anomalies)
        verdict = self._verdict(score, metrics)

        return {
            "symbol": symbol,
            "report_date": today,
            "score": score,
            "verdict": verdict,
            "metrics": metrics,
            "anomalies": anomalies,
            "industry": company.get("industry") if company else None,
            "latest_price": latest_price,
            "generated_at": datetime.now().isoformat(),
            "model_version": "aifia_v2_daily_rule_analytics",
        }

    def _latest_record(self, records: List[Dict], offset: int = 0):
        return records[offset] if len(records) > offset else None

    def _prev_record(self, records: List[Dict]):
        return self._latest_record(records, 1)

    def _latest_price(self, prices: List[Dict], offset: int = 0):
        return safe_float(prices[offset].get("close")) if len(prices) > offset else None

    # ── Metric Engine ──

    def _compute_metrics(self, symbol: str, company: Optional[Dict],
                         inc: Optional[Dict], inc_prev: Optional[Dict],
                         bal: Optional[Dict], cf: Optional[Dict],
                         prices: List[Dict],
                         price_now, price_1m_ago, price_1y_ago) -> Dict:
        di = (inc or {}).get("report_data", {})
        dp = (inc_prev or {}).get("report_data", {})
        db = (bal or {}).get("report_data", {})
        dc = (cf or {}).get("report_data", {})

        # ── Số liệu cơ bản ──
        revenue = pick(di, "n_3.net_revenue", "n_1.revenue")
        revenue_prev = pick(dp, "n_3.net_revenue", "n_1.revenue")
        gross_profit = pick(di, "n_5.gross_profit")
        op_profit = pick(di, "n_11.operating_profit")
        net_profit_parent = pick(di, "profit_after_tax_for_shareholders_of_parent_company")
        net_profit = pick(di, "n_18.net_profit_after_tax")
        ebit = safe_float(op_profit)
        interest_expense = pick(di, "of_which_interest_expense")

        # ── Balance Sheet ──
        total_assets = pick(db, "total_assets")
        equity_val = pick(db, "d.owners_equity")
        cash = pick(db, "i.cash_and_cash_equivalents", "cash_and_cash_equivalents")
        short_invest = pick(db, "ii.short_term_financial_investments")
        receivables = pick(db, "iii.short_term_receivables")
        inventory = pick(db, "iv.inventories")
        short_debt = pick(db, "n_11.short_term_borrowings_and_financial_leases")
        long_debt = pick(db, "n_9.long_term_borrowings_and_financial_leases")
        current_assets = pick(db, "a.short_term_assets")
        current_liab = pick(db, "i.short_term_liabilities")

        # ── Cash Flow ──
        op_cf = pick(dc, "net_cash_flow_from_operating_activities",
                     "i.net_cash_flow_from_operating_activities")
        capex = pick(dc, "n_1.purchase_of_fixed_assets")

        # ── Shares Outstanding ──
        shares_count = safe_float(company.get("outstanding_shares")) if company else None
        if not shares_count:
            cap = pick(db, "n_1.owners_capital")
            shares_count = cap / 10000 if cap else None

        # ════════ TÍNH TOÁN CHỈ SỐ ════════

        rev_growth = round((revenue - revenue_prev) / revenue_prev * 100, 1) \
            if revenue and revenue_prev and revenue_prev > 0 else None
        gross_margin = round(gross_profit / revenue * 100, 1) if revenue and gross_profit else None
        net_margin = round(net_profit / revenue * 100, 1) if revenue and net_profit else None
        op_margin = round(op_profit / revenue * 100, 1) if revenue and op_profit else None

        eps_ttm = round(net_profit_parent / shares_count * 4, 0) \
            if net_profit_parent and shares_count else None
        bvps = round(equity_val / shares_count, 0) \
            if equity_val and shares_count else None
        # Adjust scale for VND
        if eps_ttm and eps_ttm < 100:
            eps_ttm = eps_ttm * 1000
        if bvps and bvps < 1000:
            bvps = bvps * 1000

        mcap = price_now * shares_count if price_now and shares_count else None

        pe = round(mcap / (eps_ttm * shares_count), 1) \
            if mcap and eps_ttm and shares_count and eps_ttm > 0 else None
        pb = round(mcap / equity_val, 1) \
            if mcap and equity_val and equity_val > 0 else None
        roe = round(net_profit_parent / equity_val * 100 * 4, 1) \
            if net_profit_parent and equity_val and equity_val > 0 else None
        roa = round(net_profit / total_assets * 100 * 4, 1) \
            if net_profit and total_assets and total_assets > 0 else None

        try:
            total_debt = (safe_float(short_debt, 0) or 0) + (safe_float(long_debt, 0) or 0)
            if total_debt == 0: total_debt = None
        except:
            total_debt = None
        de = round(total_debt / equity_val * 100, 1) \
            if total_debt and equity_val and equity_val > 0 and total_debt > 0 else None
        cr = round(current_assets / current_liab, 2) \
            if current_assets and current_liab else None
        qr = round((current_assets - (inventory or 0)) / current_liab, 2) \
            if current_assets and current_liab else None
        cash_ratio = round((cash + (short_invest or 0)) / total_assets * 100, 1) \
            if cash is not None and total_assets and total_assets > 0 else None
        ic = round(ebit / interest_expense, 1) \
            if ebit and interest_expense and interest_expense > 0 else None
        dso = round(receivables / revenue * 90, 1) \
            if receivables and revenue and revenue > 0 else None

        fcf = round(op_cf - abs(capex), 2) \
            if op_cf is not None and capex is not None else None
        cfo_np = round(op_cf / net_profit, 2) \
            if op_cf is not None and net_profit and net_profit > 0 else None

        ret_1m = round((price_now - price_1m_ago) / price_1m_ago * 100, 1) \
            if price_now and price_1m_ago else None
        ret_1y = round((price_now - price_1y_ago) / price_1y_ago * 100, 1) \
            if price_now and price_1y_ago else None

        # Technical
        n_30 = prices[:30]
        high_30 = max((safe_float(p.get("high")) or 0) for p in n_30) if n_30 else None
        low_30 = min((safe_float(p.get("low")) or 999999) for p in n_30) if n_30 else None
        avg_vol_20 = sum(safe_float(p.get("volume"), 0) for p in prices[:20]) / max(len(prices[:20]), 1) if prices else None
        latest_vol = safe_float(prices[0].get("volume")) if prices else None
        vol_ratio = round(latest_vol / avg_vol_20, 2) if latest_vol and avg_vol_20 else None
        from_high = round((price_now - high_30) / high_30 * 100, 1) if price_now and high_30 else None

        closes_50 = [safe_float(p.get("close")) for p in prices[:50] if safe_float(p.get("close")) is not None]
        closes_200 = [safe_float(p.get("close")) for p in prices[:200] if safe_float(p.get("close")) is not None]
        sma50 = sum(closes_50) / len(closes_50) if len(closes_50) >= 50 else None
        sma200 = sum(closes_200) / len(closes_200) if len(closes_200) >= 200 else None
        vs_sma50 = round((price_now - sma50) / sma50 * 100, 1) if price_now and sma50 else None
        vs_sma200 = round((price_now - sma200) / sma200 * 100, 1) if price_now and sma200 else None

        return {
            "revenue_t": fmt_t(revenue),
            "revenue_growth_qoq": rev_growth,
            "gross_profit_t": fmt_t(gross_profit),
            "gross_margin": gross_margin,
            "op_profit_t": fmt_t(op_profit),
            "op_margin": op_margin,
            "net_profit_parent_t": fmt_t(net_profit_parent),
            "net_profit_t": fmt_t(net_profit),
            "net_margin": net_margin,
            "eps_ttm_vnd": eps_ttm,
            "bvps_vnd": bvps,
            "market_cap_t": fmt_t(mcap),
            "pe": pe, "pb": pb,
            "roe": roe, "roa": roa,
            "de_ratio": de, "current_ratio": cr, "quick_ratio": qr,
            "cash_ratio": cash_ratio, "interest_coverage": ic, "dso_days": dso,
            "cfo_t": fmt_t(op_cf), "fcf_t": fmt_t(fcf), "cfo_np_ratio": cfo_np,
            "price": price_now,
            "price_change_1m": ret_1m, "price_change_1y": ret_1y,
            "from_52w_high": from_high,
            "vs_sma50": vs_sma50, "vs_sma200": vs_sma200,
            "volume_ratio": vol_ratio, "avg_volume_20": avg_vol_20,
        }

    def _detect_anomalies(self, m: Dict) -> List[Dict]:
        a = []
        rg = m.get("revenue_growth_qoq")
        if rg is not None:
            if rg > 50:
                a.append({"type":"revenue_spike","severity":"high",
                    "description":f"Doanh thu tăng {rg}% QoQ — bất thường"})
            elif rg > 30:
                a.append({"type":"revenue_growth_high","severity":"medium",
                    "description":f"Doanh thu tăng mạnh {rg}% QoQ"})
            elif rg < -20:
                a.append({"type":"revenue_decline","severity":"high",
                    "description":f"Doanh thu giảm {abs(rg)}% QoQ"})

        if m.get("net_margin") and m["net_margin"] > 90:
            a.append({"type":"margin_suspicious","severity":"medium",
                "description":f"Biên gộp {m['net_margin']}% — rất cao, cần kiểm tra"})

        cr = m.get("cfo_np_ratio")
        if cr is not None and cr < 0.3:
            a.append({"type":"cashflow_warning","severity":"high",
                "description":"Lợi nhuận dương nhưng dòng tiền hoạt động thấp"})

        d = m.get("de_ratio")
        if d and d > 150:
            a.append({"type":"high_debt","severity":"high","description":f"D/E {d}% — nợ cao"})
        elif d and d > 100:
            a.append({"type":"moderate_debt","severity":"low","description":f"D/E {d}%"})

        vr = m.get("volume_ratio")
        if vr and vr > 2.0:
            a.append({"type":"high_volume","severity":"medium",
                "description":f"Volume gấp {vr}x TB — giao dịch bất thường"})

        fh = m.get("from_52w_high")
        if fh and fh < -40:
            a.append({"type":"sharp_decline","severity":"high",
                "description":f"Giá giảm {abs(fh)}% từ đỉnh"})

        dso = m.get("dso_days")
        if dso and dso > 180:
            a.append({"type":"high_dso","severity":"medium",
                "description":f"DSO {dso} ngày — thu hồi công nợ chậm"})

        return a

    def _compute_score(self, metrics: Dict, anomalies: List[Dict]) -> float:
        score = 70.0
        rg = metrics.get("revenue_growth_qoq")
        if rg and rg > 10: score += 8
        elif rg and rg > 0: score += 3
        elif rg and rg < -10: score -= 8
        elif rg and rg < 0: score -= 3

        nm = metrics.get("net_margin")
        if nm and nm > 20: score += 6
        elif nm and nm > 10: score += 3
        elif nm and nm < 5: score -= 4

        roe = metrics.get("roe")
        if roe and roe > 25: score += 6
        elif roe and roe > 15: score += 3
        elif roe and roe < 10: score -= 3

        d = metrics.get("de_ratio")
        if d and d < 50: score += 4
        elif d and d > 100: score -= 5
        elif d and d > 200: score -= 8

        cr = metrics.get("current_ratio")
        if cr and cr > 1.5: score += 3
        elif cr and cr < 1.0: score -= 4

        ic = metrics.get("interest_coverage")
        if ic and ic > 10: score += 3
        elif ic and ic < 3: score -= 4

        cfo_np = metrics.get("cfo_np_ratio")
        if cfo_np and cfo_np >= 1: score += 4
        elif cfo_np and cfo_np < 0.5: score -= 4

        pe = metrics.get("pe")
        if pe and pe < 10: score += 5
        elif pe and pe < 15: score += 3
        elif pe and pe > 25: score -= 2
        elif pe and pe > 30: score -= 4

        vs200 = metrics.get("vs_sma200")
        if vs200 and vs200 > 5: score += 3
        elif vs200 and vs200 < -15: score -= 3
        elif vs200 and vs200 < -25: score -= 5

        for an in anomalies:
            if an["severity"] == "high": score -= 8
            elif an["severity"] == "medium": score -= 3
            elif an["severity"] == "low": score -= 1

        return max(0, min(100, round(score, 1)))

    def _verdict(self, score: float, m: Dict) -> str:
        if score >= 75: return "HẤP_DẪN"
        if score >= 60: return "TÍCH_CỰC"
        if score >= 45: return "TRUNG_LẬP"
        if score >= 30: return "THẬN_TRỌNG"
        return "RỦI_RO"

    def _empty_analysis(self, symbol: str, error: str) -> Dict:
        return {"symbol": symbol, "report_date": date.today().isoformat(),
                "score": 0, "verdict": "LỖI", "metrics": {},
                "anomalies": [{"type":"fetch_error","severity":"high",
                              "description":f"Lỗi: {error}"}],
                "industry": None, "latest_price": None,
                "generated_at": datetime.now().isoformat(),
                "model_version": "aifia_v2_daily_rule_analytics"}


# ─── Batch Export ───────────────────────────────────

def export_batches(analyses: List[Dict], batch_size: int = 10) -> List[str]:
    today = date.today().isoformat()
    daily_dir = os.path.join(HISTORY_DIR, today)
    os.makedirs(daily_dir, exist_ok=True)
    files = []

    for i in range(0, len(analyses), batch_size):
        batch = analyses[i:i + batch_size]
        bn = i // batch_size
        path = os.path.join(daily_dir, f"batch_{bn}.json")
        with open(path, "w") as f:
            json.dump({"batch": bn,
                       "total_batches": math.ceil(len(analyses)/batch_size),
                       "date": today, "stocks": batch},
                      f, indent=2, ensure_ascii=False)
        files.append(path)
        print(f"  📦 batch_{bn}.json: {len(batch)} stocks")

    scores = {a["symbol"]: a.get("score", 0) for a in analyses}
    sp = os.path.join(daily_dir, "_summary.json")
    with open(sp, "w") as f:
        json.dump({"date": today, "total_stocks": len(analyses),
                   "total_batches": math.ceil(len(analyses)/batch_size),
                   "avg_score": round(sum(scores.values())/len(scores),1) if scores else 0,
                   "top_stocks": sorted(scores.items(), key=lambda x:-x[1])[:10],
                   "bottom_stocks": sorted(scores.items(), key=lambda x:x[1])[:10]},
                  f, indent=2, ensure_ascii=False)
    files.append(sp)
    return files


# ─── Save to Supabase ──────────────────────────────

def save_to_supabase(analyses: List[Dict], storage: SupabaseStorage):
    today = date.today().isoformat()
    saved = 0
    for a in analyses:
        sym = a["symbol"]
        try:
            # 1. Analysis results
            analysis_row = {
                "symbol": sym,
                "analysis_type": "full_report",
                "result": json.dumps({
                    "score": a["score"], "verdict": a["verdict"],
                    "metrics": a["metrics"], "anomalies": a["anomalies"],
                    "model_version": a["model_version"],
                    "generated_at": a["generated_at"],
                    "report_date": today,
                }),
                "summary": _gen_summary(a),
                "score": float(a["score"]),
                "recommendations": _recs(a),
                "model_version": a["model_version"],
                "metadata": json.dumps({"report_date": today,
                    "industry": a.get("industry"), "price": a.get("latest_price")}),
            }
            storage.client.table("analysis_results").insert(analysis_row).execute()

            # 2. Company highlights (upsert) — convert to proper types
            m = a["metrics"]
            storage.client.table("company_highlights").upsert({
                "symbol": sym,
                "current_price": float(m.get("price") or 0),
                "price_change_1m": m.get("price_change_1m"),
                "price_change_1y": m.get("price_change_1y"),
                "pe_ratio": m.get("pe"),
                "pb_ratio": m.get("pb"),
                "eps": m.get("eps_ttm_vnd"),
                "roe": m.get("roe"),
                "roa": m.get("roa"),
                "market_cap": int(float(m.get("market_cap_t") or 0) * 1_000_000_000),
                "ai_rating": float(a["score"]),
                "ai_summary": _gen_summary_short(a),
                "anomalies": [an["description"] for an in a.get("anomalies", [])],
            }, on_conflict="symbol").execute()
            saved += 1
        except Exception as e:
            print(f"  ❌ {sym}: save error - {e}")
    print(f"\n✅ Saved {saved}/{len(analyses)} analyses to Supabase")


def _gen_summary(a: Dict) -> str:
    m = a["metrics"]
    parts = [f"Mã {a['symbol']} — Điểm {a['score']}/100 ({a['verdict']})."]
    if m.get("revenue_t"): parts.append(f"DT Q gần: {m['revenue_t']} tỷ")
    if m.get("net_margin"): parts.append(f"Biên LNST {m['net_margin']}%")
    if m.get("roe"): parts.append(f"ROE {m['roe']}%")
    if m.get("pe"): parts.append(f"P/E {m['pe']}x")
    an = [x["description"] for x in a.get("anomalies", [])]
    if an: parts.append("⚠️ " + "; ".join(an[:3]))
    return ". ".join(parts)

def _gen_summary_short(a: Dict) -> str:
    s = a["score"]
    tag = "🟢" if s >= 75 else "🔵" if s >= 60 else "🟡" if s >= 45 else "🔴"
    parts = [f"{tag} {s}/100"]
    if a["metrics"].get("pe"): parts.append(f"P/E {a['metrics']['pe']}x")
    if a["metrics"].get("roe"): parts.append(f"ROE {a['metrics']['roe']}%")
    return " | ".join(parts)

def _recs(a: Dict) -> List[str]:
    recs = []
    for an in a.get("anomalies", []):
        if an["severity"] == "high":
            recs.append(f"⚠️ {an['description']}")
    m = a["metrics"]
    if m.get("cfo_np_ratio") and m["cfo_np_ratio"] < 0.7:
        recs.append("Theo dõi dòng tiền — LN cao nhưng dòng tiền thấp")
    if m.get("de_ratio") and m["de_ratio"] > 100:
        recs.append("Giám sát đòn bẩy — nợ cao")
    if m.get("dso_days") and m["dso_days"] > 120:
        recs.append("Kiểm tra bán chịu — DSO cao")
    return recs or ["Tiếp tục theo dõi"]


# ─── Previous Day Comparison ───────────────────────

def load_previous_analysis(prev_date: str) -> Dict[str, Dict]:
    prev_dir = os.path.join(HISTORY_DIR, prev_date)
    if not os.path.isdir(prev_dir): return {}
    prev = {}
    for bf in os.listdir(prev_dir):
        if not bf.startswith("batch_") or not bf.endswith(".json"): continue
        with open(os.path.join(prev_dir, bf)) as f:
            for stock in json.load(f).get("stocks", []):
                prev[stock["symbol"]] = stock
    return prev


def compare_with_previous(current: List[Dict], prev: Dict[str, Dict]):
    today = date.today().isoformat()
    changes = []
    for a in current:
        sym = a["symbol"]
        if sym in prev:
            old = prev[sym].get("score", 0)
            new = a.get("score", 0)
            d = round(new - old, 1)
            if abs(d) >= 5:
                changes.append({"symbol": sym, "old": old, "new": new, "delta": d,
                                "reason": "Cập nhật dữ liệu mới"})

    lessons_dir = os.path.join(HISTORY_DIR, "_lessons")
    os.makedirs(lessons_dir, exist_ok=True)
    with open(os.path.join(lessons_dir, f"{today}.json"), "w") as f:
        json.dump({"date": today, "total_changes": len(changes),
                   "avg_delta": round(sum(c["delta"] for c in changes)/len(changes),1) if changes else 0,
                   "improved": len([c for c in changes if c["delta"]>0]),
                   "declined": len([c for c in changes if c["delta"]<0]),
                   "changes": changes[:20]}, f, indent=2, ensure_ascii=False)
    print(f"📚 Lessons saved: {len(changes)} score changes tracked")


# ─── Main ──────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--batch", type=int, help="Xử lý batch N (sub-agent)")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--skip-supabase", action="store_true")
    args = parser.parse_args()

    analyzer = DailyStockAnalyzer()
    today = date.today().isoformat()
    daily_dir = os.path.join(HISTORY_DIR, today)
    os.makedirs(daily_dir, exist_ok=True)

    if args.prepare or args.full:
        print(f"\n{'='*60}")
        print(f"🔬 AIFIA Daily Full Analysis — {today}")
        print(f"{'='*60}")

        analyses = analyzer.analyze_all()

        prev_date = (date.today() - timedelta(days=1)).isoformat()
        prev = load_previous_analysis(prev_date)
        if prev:
            compare_with_previous(analyses, prev)

        export_batches(analyses, args.batch_size)

        scores = [a["score"] for a in analyses if "score" in a]
        print(f"\n📊 Thống kê: {len(analyses)} mã, TB {round(sum(scores)/len(scores),1) if scores else 0}/100")
        print(f"   Hấp dẫn(≥75):{len([s for s in scores if s>=75])} Tích cực(60-74):{len([s for s in scores if 60<=s<75])} Trung lập(45-59):{len([s for s in scores if 45<=s<60])} Thận trọng(30-44):{len([s for s in scores if 30<=s<44])} Rủi ro(<30):{len([s for s in scores if s<30])}")

        if not args.skip_supabase and analyzer.storage.is_connected():
            save_to_supabase(analyses, analyzer.storage)
            print(f"\n✅ Done — dữ liệu tại {daily_dir}")
        else:
            print("\n⏭️ Skip Supabase save")

    elif args.batch is not None:
        batch_path = os.path.join(daily_dir, f"batch_{args.batch}.json")
        if not os.path.exists(batch_path):
            print(f"❌ Batch file not found: {batch_path}")
            sys.exit(1)
        with open(batch_path) as f:
            batch_data = json.load(f)
        print(f"📦 Batch {args.batch}/{batch_data.get('total_batches','?')}")
        for stock in batch_data["stocks"]:
            print(f"\n🔍 {stock['symbol']}: Score={stock['score']} Verdict={stock['verdict']}")
            for an in stock.get("anomalies", []):
                print(f"   ⚠️ [{an['severity'].upper()}] {an['description']}")
            m = stock.get("metrics", {})
            print(f"   📊 P/E={m.get('pe')} P/B={m.get('pb')} ROE={m.get('roe')}%")
        marker = {"processed_at": datetime.now().isoformat(),
                  "symbols": [s["symbol"] for s in batch_data["stocks"]]}
        with open(os.path.join(daily_dir, f"batch_{args.batch}_done.json"), "w") as f:
            json.dump(marker, f)
        print(f"\n✅ Batch {args.batch} done")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
