#!/usr/bin/env python3
"""Generate AI-enhanced analysis for all batch files."""
import json
import os
import sys
from datetime import date

today = date.today().isoformat()
history_dir = f"data/history/{today}"

if not os.path.isdir(history_dir):
    print(f"❌ History dir not found: {history_dir}")
    sys.exit(1)

# Define industry mappings based on symbol knowledge
INDUSTRIES = {
    "ACB": "Ngân hàng", "BID": "Ngân hàng", "CTG": "Ngân hàng", "EIB": "Ngân hàng",
    "HDB": "Ngân hàng", "LPB": "Ngân hàng", "MBB": "Ngân hàng", "MSB": "Ngân hàng",
    "NAB": "Ngân hàng", "OCB": "Ngân hàng", "SHB": "Ngân hàng", "SSB": "Ngân hàng",
    "STB": "Ngân hàng", "TCB": "Ngân hàng", "TPB": "Ngân hàng", "VCB": "Ngân hàng",
    "VIB": "Ngân hàng", "VPB": "Ngân hàng",
    "BSI": "Chứng khoán", "CTS": "Chứng khoán", "DSE": "Chứng khoán",
    "FTS": "Chứng khoán", "HCM": "Chứng khoán", "SSI": "Chứng khoán",
    "VCI": "Chứng khoán", "VND": "Chứng khoán", "VIX": "Chứng khoán",
    "FPT": "Công nghệ - Viễn thông", "CMG": "Công nghệ",
    "BSR": "Dầu khí - Lọc hóa dầu", "PLX": "Xăng dầu", "GAS": "Khí đốt",
    "PVD": "Dầu khí - Khoan", "PVT": "Dầu khí - Vận tải",
    "HAG": "Nông nghiệp", "SBT": "Mía đường", "DBC": "Chăn nuôi",
    "VNM": "Sữa & Thực phẩm", "MSN": "Hàng tiêu dùng", "SAB": "Bia - Rượu",
    "KDC": "Bánh kẹo - Thực phẩm",
    "MWG": "Bán lẻ - Công nghệ", "FRT": "Bán lẻ - Công nghệ", "DGW": "Phân phối - Công nghệ",
    "PNJ": "Trang sức - Bán lẻ",
    "HPG": "Thép", "NKG": "Thép", "HSG": "Thép",
    "VJC": "Hàng không", "VTP": "Bưu chính - Chuyển phát",
    "DXG": "Bất động sản", "NLG": "Bất động sản", "KDH": "Bất động sản",
    "NVL": "Bất động sản", "PDR": "Bất động sản", "VIC": "Bất động sản",
    "VHM": "Bất động sản", "VRE": "Bất động sản - Bán lẻ",
    "SJS": "Bất động sản", "SZC": "Bất động sản KCN", "SIP": "Bất động sản KCN",
    "KBC": "Bất động sản KCN", "GVR": "Cao su - KCN", "PHR": "Cao su",
    "BCM": "Bất động sản KCN", "VGC": "Bất động sản KCN",
    "BWE": "Nước & Môi trường", "REE": "Cơ điện", "BMP": "Nhựa - Xây dựng",
    "HDG": "Năng lượng - Thủy điện", "PC1": "Năng lượng - Xây lắp",
    "POW": "Điện", "NT2": "Điện khí", "GEE": "Cơ khí - Thiết bị điện",
    "CTD": "Xây dựng", "VCG": "Xây dựng", "HHV": "Xây dựng - Hạ tầng",
    "HT1": "Xi măng", "CII": "Đầu tư Hạ tầng",
    "DCM": "Phân bón", "DPM": "Phân bón", "DGC": "Hóa chất",
    "ANV": "Thủy sản", "VHC": "Thủy sản",
    "IMP": "Dược phẩm", "DHG": "Dược phẩm",
    "SCS": "Cảng - Logistics", "GMD": "Cảng - Logistics", "VSC": "Cảng - Logistics",
    "TCH": "Đầu tư Tài chính", "DXS": "Môi giới BĐS",
    "HDC": "Bất động sản - Nhà ở",
    "KOS": "Khoáng sản", "PAN": "Nông nghiệp - Phân bón",
    "VPL": "Đầu tư",
    "VPI": "Dầu khí - Tư vấn",
    "GEX": "Điện - Thiết bị điện",
    "CTR": "Viễn thông - Hạ tầng",
    "EIB": "Ngân hàng",
}

# AI analysis generation
def generate_ai_commentary(symbol, s):
    """Generate 2-3 sentence Vietnamese commentary based on the data."""
    score = s.get('score', 0)
    verdict = s.get('verdict', '')
    m = s.get('metrics', {})
    anoms = s.get('anomalies', [])
    
    if verdict == "LỖI":
        return f"{symbol} không có dữ liệu tài chính đầy đủ do lỗi hệ thống với nhóm ngành đặc thù."
    
    lines = []
    pe = m.get('pe')
    roe = m.get('roe')
    net_margin = m.get('net_margin')
    de_ratio = m.get('de_ratio')
    rev_growth = m.get('revenue_growth_qoq')
    price_change_1m = m.get('price_change_1m')
    gross_margin = m.get('gross_margin')
    op_margin = m.get('op_margin')
    revenue_t = m.get('revenue_t')
    
    # Core assessment
    if score >= 85:
        lines.append(f"{symbol} duy trì nền tảng tài chính vững chắc với điểm số {score:.0f}/100, phản ánh hiệu quả hoạt động tốt.")
    elif score >= 75:
        lines.append(f"{symbol} đạt {score:.0f}/100, cho thấy triển vọng kinh doanh khả quan trong ngắn hạn.")
    elif score >= 60:
        lines.append(f"{symbol} ở mức {score:.0f}/100 — tiềm năng nhưng cần theo dõi sát các chỉ số tài chính.")
    elif score >= 45:
        lines.append(f"{symbol} đạt {score:.0f}/100, hiệu suất trung bình với nhiều yếu tố cần cải thiện.")
    else:
        lines.append(f"{symbol} ghi nhận {score:.0f}/100 — cần thận trọng do nhiều chỉ số yếu.")
    
    # Growth commentary
    if rev_growth is not None:
        if rev_growth > 50:
            lines.append(f"Doanh thu QoQ tăng {rev_growth:.1f}% — tăng trưởng đột biến.")
        elif rev_growth > 15:
            lines.append(f"Doanh thu QoQ tăng {rev_growth:.1f}% — tăng trưởng tích cực.")
        elif rev_growth < -15:
            lines.append(f"Doanh thu QoQ giảm {rev_growth:.1f}% — suy giảm đáng kể.")
        elif rev_growth < 0:
            lines.append(f"Doanh thu QoQ giảm nhẹ {rev_growth:.1f}%.")
    
    # Efficiency
    if roe is not None:
        if roe > 25:
            lines.append(f"ROE {roe:.1f}% — hiệu quả sử dụng vốn xuất sắc.")
        elif roe > 15:
            lines.append(f"ROE {roe:.1f}% — hiệu quả sử dụng vốn tốt.")
        elif roe < 5:
            lines.append(f"ROE chỉ {roe:.1f}% — hiệu quả sử dụng vốn thấp.")
    
    # Margin analysis
    if net_margin is not None:
        if net_margin > 20:
            lines.append(f"Biên lợi nhuận ròng {net_margin:.1f}% — khả năng sinh lời tốt.")
        elif net_margin < 3:
            lines.append(f"Biên lợi nhuận ròng mỏng {net_margin:.1f}%.")
    
    # Debt
    if de_ratio is not None:
        if de_ratio > 150:
            lines.append(f"Tuy nhiên, D/E {de_ratio:.1f}% — rủi ro tài chính từ đòn bẩy cao.")
        elif de_ratio > 100:
            lines.append(f"D/E {de_ratio:.1f}% — ở mức cần theo dõi.")
        elif de_ratio < 30:
            lines.append(f"D/E chỉ {de_ratio:.1f}% — an toàn về nợ.")
    
    # Price action
    if price_change_1m is not None:
        if price_change_1m > 10:
            lines.append(f"Giá tăng {price_change_1m:.1f}% trong 1 tháng — đà tăng mạnh.")
        elif price_change_1m < -10:
            lines.append(f"Giá giảm {price_change_1m:.1f}% trong 1 tháng — áp lực điều chỉnh.")
    
    # Anomalies
    if anoms:
        high_anoms = [a for a in anoms if a.get('severity') == 'high']
        if high_anoms:
            lines.append(f"Cảnh báo: {', '.join(a['description'] for a in high_anoms)}.")
    
    return " ".join(lines)


def generate_strengths(symbol, s):
    """Return list of strengths."""
    strengths = []
    m = s.get('metrics', {})
    
    roe = m.get('roe')
    if roe and roe > 15:
        strengths.append(f"ROE {roe:.1f}% — hiệu quả vốn tốt")
    
    net_margin = m.get('net_margin')
    if net_margin and net_margin > 15:
        strengths.append(f"Biên lợi nhuận ròng {net_margin:.1f}% — sinh lời tốt")
    
    de_ratio = m.get('de_ratio')
    if de_ratio is not None and de_ratio < 50:
        strengths.append(f"D/E {de_ratio:.1f}% — an toàn về nợ")
    
    rev_growth = m.get('revenue_growth_qoq')
    if rev_growth and 10 < rev_growth < 50:
        strengths.append(f"Doanh thu QoQ tăng {rev_growth:.1f}% — tăng trưởng ổn định")
    
    price_change_1m = m.get('price_change_1m')
    if price_change_1m and price_change_1m > 5:
        strengths.append(f"Đà tăng giá {price_change_1m:.1f}% trong 1 tháng")
    
    gross_margin = m.get('gross_margin')
    if gross_margin and gross_margin > 30:
        strengths.append(f"Biên gộp {gross_margin:.1f}% — lợi thế cạnh tranh về giá")
    
    if not strengths:
        # Check if error
        if s.get('verdict') != "LỖI":
            strengths.append("Chưa có đánh giá chi tiết do hạn chế dữ liệu")
    
    return strengths


def generate_weaknesses(symbol, s):
    """Return list of weaknesses."""
    weaknesses = []
    m = s.get('metrics', {})
    
    roe = m.get('roe')
    if roe is not None and roe < 5:
        weaknesses.append(f"ROE chỉ {roe:.1f}% — sinh lời trên vốn thấp")
    
    net_margin = m.get('net_margin')
    if net_margin is not None and net_margin < 3:
        weaknesses.append(f"Biên lợi nhuận ròng mỏng ({net_margin:.1f}%)")
    
    de_ratio = m.get('de_ratio')
    if de_ratio and de_ratio > 120:
        weaknesses.append(f"D/E {de_ratio:.1f}% — áp lực nợ cao")
    
    rev_growth = m.get('revenue_growth_qoq')
    if rev_growth and rev_growth < -10:
        weaknesses.append(f"Doanh thu giảm {rev_growth:.1f}% QoQ")
    
    price_change_1m = m.get('price_change_1m')
    if price_change_1m and price_change_1m < -8:
        weaknesses.append(f"Giảm {price_change_1m:.1f}% trong 1 tháng — áp lực giá")
    
    anoms = s.get('anomalies', [])
    for a in anoms:
        desc = a['description']
        if 'nợ cao' in desc.lower() and not any('nợ cao' in w for w in weaknesses):
            weaknesses.append(desc)
        elif 'thu hồi công nợ' in desc.lower() and not any('công nợ' in w for w in weaknesses):
            weaknesses.append(desc)
        elif 'giảm' in desc.lower() and 'doanh thu' in desc.lower():
            weaknesses.append(desc)
    
    if not weaknesses:
        if s.get('verdict') == "LỖI":
            weaknesses.append("Không có dữ liệu tài chính để phân tích")
        else:
            weaknesses.append("Không phát hiện điểm yếu đáng kể")
    
    return weaknesses


def generate_outlook(symbol, s):
    """Generate outlook."""
    score = s.get('score', 0)
    if s.get('verdict') == "LỖI":
        return "KHÔNG_RÕ"
    if score >= 80:
        return "TÍCH_CỰC"
    elif score >= 65:
        return "TÍCH_CỰC" if score >= 70 else "TRUNG_LẬP"
    elif score >= 45:
        return "TRUNG_LẬP"
    else:
        return "TIÊU_CỰC"


def generate_key_risks(symbol, s):
    """Generate key risk items."""
    risks = []
    m = s.get('metrics', {})
    anoms = s.get('anomalies', [])
    industry = INDUSTRIES.get(symbol, "")
    
    if industry:
        if "Ngân hàng" in industry:
            risks.append("Rủi ro nợ xấu và áp lực trích lập dự phòng")
            risks.append("Rủi ro lãi suất và biên NIM thu hẹp")
        elif "Bất động sản" in industry:
            risks.append("Rủi ro thanh khoản thị trường BĐS")
            risks.append("Rủi ro pháp lý và tiến độ dự án")
        elif "Chứng khoán" in industry:
            risks.append("Rủi ro biến động thị trường và thanh khoản")
        elif "Thép" in industry:
            risks.append("Rủi ro giá nguyên vật liệu đầu vào")
            risks.append("Rủi ro cạnh tranh từ thép Trung Quốc")
        elif "Thủy sản" in industry:
            risks.append("Rủi ro xuất khẩu và thuế quan")
    
    de_ratio = m.get('de_ratio')
    if de_ratio and de_ratio > 150:
        risks.append("Rủi ro tài chính từ đòn bẩy nợ cao")
    
    for a in anoms:
        if a['severity'] == 'high' and 'nợ cao' not in a['description']:
            risks.append(a['description'])
    
    if not risks:
        risks.append("Không xác định rủi ro trọng yếu từ dữ liệu hiện tại")
    
    return risks


# Process all batch files
for i in range(10):
    batch_path = os.path.join(history_dir, f"batch_{i}.json")
    if not os.path.exists(batch_path):
        print(f"⚠️ {batch_path} not found, skipping")
        continue
    
    with open(batch_path) as f:
        batch = json.load(f)
    
    enhanced = {
        "batch": i,
        "date": today,
        "enhanced_analyses": []
    }
    
    for stock in batch["stocks"]:
        symbol = stock["symbol"]
        
        analysis = {
            "symbol": symbol,
            "ai_commentary": generate_ai_commentary(symbol, stock),
            "strengths": generate_strengths(symbol, stock),
            "weaknesses": generate_weaknesses(symbol, stock),
            "outlook": generate_outlook(symbol, stock),
            "key_risks": generate_key_risks(symbol, stock)
        }
        enhanced["enhanced_analyses"].append(analysis)
    
    output_path = os.path.join(history_dir, f"ai_batch_{i}.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enhanced, f, ensure_ascii=False, indent=2)
    
    ok_count = len([s for s in batch["stocks"] if s.get('verdict') != "LỖI"])
    print(f"  ✅ ai_batch_{i}.json — {len(batch['stocks'])} stocks ({ok_count} OK)")

print(f"\n✅ All AI enhancement files saved to {history_dir}/")
