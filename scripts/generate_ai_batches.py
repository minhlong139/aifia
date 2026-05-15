#!/usr/bin/env python3
"""
AI Enhancement Pipeline for AIFIA — generates per-stock AI commentary,
strengths, weaknesses, outlook, and risks based on financial metrics.
"""

import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'history', '2026-05-13')
DATA_DIR = os.path.abspath(DATA_DIR)

def load_batch(n):
    path = os.path.join(DATA_DIR, f'batch_{n}.json')
    with open(path) as f:
        return json.load(f)

def analyze_stock(stock, batch_num):
    """Generate AI enhancement for a single stock."""
    symbol = stock['symbol']
    score = stock['score']
    verdict = stock['verdict']
    m = stock.get('metrics', {})
    anomalies = stock.get('anomalies', [])

    # Handle error stocks
    if verdict == 'LỖI' or score == 0:
        return {
            "symbol": symbol,
            "ai_commentary": f"Dữ liệu tài chính của {symbol} không khả dụng do lỗi fetch dữ liệu. Hệ thống ghi nhận lỗi: {anomalies[0]['description'] if anomalies else 'không xác định'}. Không thể đưa ra phân tích cho mã này.",
            "strengths": [],
            "weaknesses": [],
            "outlook": "TIÊU_CỰC",
            "key_risks": ["Dữ liệu tài chính không khả dụng"]
        }

    # Extract key metrics with defaults
    rev_growth = m.get('revenue_growth_qoq')
    gross_margin = m.get('gross_margin')
    net_margin = m.get('net_margin')
    roe = m.get('roe')
    roa = m.get('roa')
    de_ratio = m.get('de_ratio')
    current_ratio = m.get('current_ratio')
    eps = m.get('eps_ttm_vnd')
    bvps = m.get('bvps_vnd')
    price_change_1y = m.get('price_change_1y')
    price_change_1m = m.get('price_change_1m')
    dso = m.get('dso_days')
    interest_cov = m.get('interest_coverage')
    cash_ratio = m.get('cash_ratio')
    revenue_t = m.get('revenue_t')
    net_profit_t = m.get('net_profit_t')

    strengths = []
    weaknesses = []
    key_risks = []

    # --- Analysis based on metrics ---

    # Commentary generation
    commentary_parts = []

    # Revenue analysis
    if rev_growth is not None:
        if rev_growth > 50:
            commentary_parts.append(f"Doanh thu tăng trưởng mạnh {rev_growth:.1f}% so với quý trước")
            key_risks.append("Tăng trưởng doanh thu đột biến cần được xác nhận xu hướng bền vững")
        elif rev_growth > 20:
            commentary_parts.append(f"Doanh thu tăng {rev_growth:.1f}% QoQ, cho thấy đà tăng trưởng khả quan")
        elif rev_growth > 0:
            commentary_parts.append(f"Doanh thu tăng nhẹ {rev_growth:.1f}% QoQ, duy trì ổn định")
        elif rev_growth > -15:
            commentary_parts.append(f"Doanh thu giảm {rev_growth:.1f}% QoQ, cần theo dõi diễn biến")
        else:
            commentary_parts.append(f"Doanh thu giảm mạnh {rev_growth:.1f}% QoQ, đây là tín hiệu đáng lo ngại")

    # Profitability
    if roe is not None and roe > 0:
        if roe > 25:
            strengths.append(f"ROE {roe:.1f}% — hiệu quả sử dụng vốn xuất sắc")
            commentary_parts.append(f"ROE đạt {roe:.1f}%, cho thấy doanh nghiệp sử dụng vôn hiệu quả")
        elif roe > 15:
            strengths.append(f"ROE {roe:.1f}% — hiệu quả sử dụng vốn tốt")
            commentary_parts.append(f"ROE {roe:.1f}% ở mức khá, phản ánh năng lực sinh lời trên vốn chủ sở hữu")
        elif roe > 8:
            commentary_parts.append(f"ROE {roe:.1f}% ở mức trung bình")
        else:
            weaknesses.append(f"ROE chỉ {roe:.1f}% — hiệu quả sử dụng vốn thấp")
    elif roe == 0:
        weaknesses.append("Không có dữ liệu ROE hoặc ROE bằng 0")

    if net_margin is not None:
        if net_margin > 20:
            strengths.append(f"Biên lợi nhuận ròng {net_margin:.1f}% — ấn tượng")
        elif net_margin > 10:
            strengths.append(f"Biên lợi nhuận ròng {net_margin:.1f}% — khả quan")
        elif net_margin > 0:
            pass
        elif net_margin < 0:
            weaknesses.append(f"Biên lợi nhuận ròng âm {net_margin:.1f}% — doanh nghiệp đang lỗ")

    if roa is not None and roa > 0:
        if roa > 10:
            commentary_parts.append(f"ROA {roa:.1f}% — doanh nghiệp sử dụng tài sản sinh lời hiệu quả")

    # Debt / Leverage
    if de_ratio is not None:
        if de_ratio < 20:
            strengths.append(f"D/E {de_ratio:.1f}% — ít phụ thuộc vào vốn vay, an toàn về mặt tài chính")
        elif de_ratio < 50:
            strengths.append(f"D/E {de_ratio:.1f}% — cấu trúc vốn lành mạnh")
        elif de_ratio < 100:
            key_risks.append(f"D/E {de_ratio:.1f}% ở mức trung bình, cần theo dõi đòn bẩy")
        elif de_ratio < 150:
            weaknesses.append(f"D/E {de_ratio:.1f}% — nợ tương đối cao, tiềm ẩn rủi ro thanh khoản")
            key_risks.append("Áp lực trả nợ và chi phí lãi vay có thể ảnh hưởng lợi nhuận")
        else:
            weaknesses.append(f"D/E {de_ratio:.1f}% — nợ cao, rủi ro tài chính đáng kể")
            key_risks.append("Rủi ro mất khả năng thanh toán nếu dòng tiền suy yếu")

    # Liquidity
    if current_ratio is not None:
        if current_ratio < 1:
            weaknesses.append(f"Thanh khoản ngắn hạn yếu (current ratio {current_ratio:.2f}) — dưới ngưỡng an toàn")
            key_risks.append("Rủi ro thanh khoản ngắn hạn khi current ratio dưới 1")
        elif current_ratio < 1.5:
            key_risks.append("Thanh khoản ngắn hạn ở mức thấp, cần theo dõi")

    # Cash position
    if cash_ratio is not None and cash_ratio > 30:
        strengths.append(f"Tiền mặt dồi dào ({cash_ratio:.1f}% tài sản ngắn hạn) — đệm thanh khoản tốt")

    # Interest coverage
    if interest_cov is not None:
        if interest_cov > 10:
            strengths.append(f"Khả năng trả lãi {interest_cov:.1f}x — rất an toàn")
        elif interest_cov > 3:
            pass  # acceptable
        elif interest_cov > 0:
            key_risks.append(f"Interest coverage {interest_cov:.1f}x thấp, nguy cơ không trả được nợ")
        elif interest_cov < 0:
            key_risks.append("Lợi nhuận hoạt động âm, không đủ trả lãi vay")

    # DSO
    if dso is not None and dso > 200:
        weaknesses.append(f"DSO {dso:.0f} ngày — thu hồi công nợ quá chậm, tiềm ẩn rủi ro nợ xấu")
        key_risks.append("Rủi ro nợ xấu do thời gian thu hồi công nợ kéo dài")
    elif dso is not None and dso > 100:
        key_risks.append(f"DSO {dso:.0f} ngày — thu hồi công nợ tương đối chậm")

    # EPS / BVPS
    if eps is not None and eps > 5000:
        strengths.append(f'EPS {eps:,.0f} VNĐ — lợi nhuận trên mỗi cổ phiếu hấp dẫn')
    if bvps is not None and bvps > 30000:
        strengths.append(f'BVPS {bvps:,.0f} VNĐ — giá trị sổ sách trên mỗi cổ phiếu tốt')

    # Price performance
    if price_change_1y is not None:
        if price_change_1y > 50:
            commentary_parts.append(f"Giá cổ phiếu tăng {price_change_1y:.1f}% trong 1 năm qua, phản ánh kỳ vọng tích cực của thị trường")
        elif price_change_1y > 20:
            commentary_parts.append(f"Giá tăng {price_change_1y:.1f}% trong 1 năm, duy trì xu hướng tích cực")
        elif price_change_1y < -20:
            commentary_parts.append(f"Giá giảm {price_change_1y:.1f}% trong 1 năm, thị trường đang khá thận trọng với cổ phiếu này")
            key_risks.append("Xu hướng giá giảm kéo dài, tâm lý thị trường tiêu cực")

    # Revenue size context
    if revenue_t is not None and net_profit_t is not None:
        if revenue_t > 10:
            commentary_parts.append(f"Quy mô doanh thu {revenue_t:.2f} nghìn tỷ, cho thấy vị thế vững chắc của doanh nghiệp")
        if net_profit_t > 1:
            commentary_parts.append(f"Lợi nhuận {net_profit_t:.2f} nghìn tỷ, nền tảng tài chính tốt để tăng trưởng")

    # Volume anomaly
    vol_anomaly = [a for a in anomalies if a['type'] == 'high_volume']
    if vol_anomaly:
        key_risks.append("Khối lượng giao dịch bất thường có thể gây biến động giá ngắn hạn")

    # Determine outlook
    if score >= 80 and verdict in ('HẤP_DẪN',):
        outlook = "TÍCH_CỰC"
    elif score >= 60:
        outlook = "TÍCH_CỰC"
    elif score >= 40:
        outlook = "TRUNG_LẬP"
    else:
        outlook = "TIÊU_CỰC"

    # If many high severity anomalies, downgrade outlook
    high_sev = [a for a in anomalies if a.get('severity') == 'high']
    if len(high_sev) >= 2 and outlook == "TÍCH_CỰC":
        outlook = "TRUNG_LẬP"

    # If there are no data points at all (many null metrics)
    non_null_metrics = {k: v for k, v in m.items() if v is not None}
    if len(non_null_metrics) < 5:
        if not strengths and not weaknesses:
            commentary_parts = [f"Dữ liệu tài chính của {symbol} còn hạn chế, chủ yếu dựa trên chỉ số thị trường và thanh khoản. Cần thêm thông tin từ báo cáo tài chính để đánh giá toàn diện."]
        outlook = "TRUNG_LẬP"

    ai_commentary = ". ".join(filter(None, commentary_parts))
    if ai_commentary:
        ai_commentary += ". "
    if score is not None:
        ai_commentary += f"Mã {symbol} đạt tổng điểm {score:.0f}/100 với nhận định {verdict}."
    if not ai_commentary:
        ai_commentary = f"Mã {symbol} đạt {score:.0f}/100 — {verdict}. Cần thêm dữ liệu tài chính chi tiết để phân tích sâu hơn."

    return {
        "symbol": symbol,
        "ai_commentary": ai_commentary.strip(),
        "strengths": strengths[:4],
        "weaknesses": weaknesses[:4],
        "outlook": outlook,
        "key_risks": key_risks[:5]
    }


def main():
    # Load the _summary to know what exists
    summary_path = os.path.join(DATA_DIR, '_summary.json')
    with open(summary_path) as f:
        summary = json.load(f)

    total_batches = summary['total_batches']
    total_enhanced = 0

    for n in range(total_batches):
        try:
            batch = load_batch(n)
        except FileNotFoundError:
            continue

        stocks = batch['stocks']
        enhanced_analyses = []
        for stock in stocks:
            analysis = analyze_stock(stock, n)
            enhanced_analyses.append(analysis)
            total_enhanced += 1

        output = {
            "batch": n,
            "total_batches": total_batches,
            "date": "2026-05-13",
            "enhanced_analyses": enhanced_analyses
        }

        out_path = os.path.join(DATA_DIR, f'ai_batch_{n}.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"  Batch {n}: {len(stocks)} stocks → ai_batch_{n}.json")

    print(f"\n✅ Tổng cộng: {total_enhanced} stocks enhanced across {total_batches} batches")

    # Count by outlook
    outlooks = {}
    errors = 0
    for n in range(total_batches):
        try:
            with open(os.path.join(DATA_DIR, f'ai_batch_{n}.json')) as f:
                data = json.load(f)
            for a in data['enhanced_analyses']:
                o = a['outlook']
                outlooks[o] = outlooks.get(o, 0) + 1
        except FileNotFoundError:
            errors += 1

    print(f"  Phân bổ outlook: {outlooks}")
    if errors:
        print(f"  Errors: {errors}")


if __name__ == '__main__':
    main()
