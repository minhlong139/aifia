#!/usr/bin/env python3
"""Generate AI-enhanced analysis for all stocks in daily batches."""
import json, os, sys
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "history")
TODAY = datetime.now().strftime("%Y-%m-%d")
DATE_DIR = os.path.join(DATA_DIR, TODAY)

def analyze_stock(stock):
    """Generate deep AI analysis for a stock based on metrics."""
    sym = stock["symbol"]
    score = stock["score"]
    verdict = stock["verdict"]
    m = stock.get("metrics", {})
    price = m.get("price", m.get("latest_price", stock.get("latest_price", "N/A")))
    anomalies = stock.get("anomalies", [])
    
    if score == 0 or verdict == "LỖI":
        return {
            "symbol": sym,
            "score": 0,
            "verdict": "LỖI_DỮ_LIỆU",
            "analysis": f"Không có đủ dữ liệu tài chính để phân tích {sym}. Có thể do thiếu báo cáo tài chính mới nhất hoặc dữ liệu chưa được cập nhật.",
            "outlook": "Không đánh giá được",
            "strengths": [],
            "weaknesses": ["Thiếu dữ liệu tài chính"],
            "risks": ["Không thể đưa ra đánh giá do thiếu thông tin"],
            "recommendation": "THEO_DÕI — cần bổ sung dữ liệu"
        }
    
    pe = m.get("pe", 0)
    roe = m.get("roe", 0)
    rev_growth = m.get("revenue_growth_qoq", 0)
    de_ratio = m.get("de_ratio", 0)
    net_margin = m.get("net_margin", 0)
    op_margin = m.get("op_margin", 0)
    current_ratio = m.get("current_ratio", 0)
    interest_coverage = m.get("interest_coverage", 0)
    cfo_np = m.get("cfo_np_ratio", None)
    gross_margin = m.get("gross_margin", 0)
    roa = m.get("roa", 0)
    bvps = m.get("bvps_vnd", 0)
    eps = m.get("eps_ttm_vnd", 0)
    cash_ratio = m.get("cash_ratio", 0)
    volume_ratio = m.get("volume_ratio", 0)
    
    # Industry classification based on symbol patterns and metrics
    industry = classify_industry(sym, m)
    
    # Generate analysis
    strengths = []
    weaknesses = []
    risks = []
    
    # ROE analysis
    if roe and roe > 20:
        strengths.append(f"ROE {roe:.1f}% — hiệu quả sử dụng vốn rất tốt, trên ngưỡng hấp dẫn 20%")
    elif roe and roe > 15:
        strengths.append(f"ROE {roe:.1f}% — hiệu quả sử dụng vốn khá tốt")
    elif roe and roe < 5 and roe > 0:
        weaknesses.append(f"ROE {roe:.1f}% — hiệu quả sử dụng vốn thấp")
    
    # Margin analysis
    if net_margin and net_margin > 15:
        strengths.append(f"Biên lợi nhuận ròng {net_margin:.1f}% — khả năng sinh lời cao")
    elif net_margin and net_margin < 5 and net_margin > 0:
        weaknesses.append(f"Biên lợi nhuận ròng chỉ {net_margin:.1f}% — mỏng")
    
    if gross_margin and gross_margin > 30:
        strengths.append(f"Biên gộp {gross_margin:.1f}% — sức mạnh định giá và lợi thế cạnh tranh")
    
    # Revenue growth
    if rev_growth and rev_growth > 30:
        strengths.append(f"Tăng trưởng doanh thu QoQ {rev_growth:.1f}% — đà tăng mạnh")
    elif rev_growth and rev_growth > 10:
        strengths.append(f"Tăng trưởng doanh thu QoQ {rev_growth:.1f}% — tích cực")
    elif rev_growth and rev_growth < -10:
        weaknesses.append(f"Doanh thu giảm {rev_growth:.1f}% QoQ — cần theo dõi xu hướng")
    elif rev_growth and rev_growth < 0:
        weaknesses.append(f"Doanh thu giảm nhẹ {rev_growth:.1f}% QoQ")
    
    # D/E analysis
    if de_ratio and de_ratio > 100:
        risks.append(f"D/E {de_ratio:.1f}% — đòn bẩy tài chính cao, rủi ro thanh khoản")
    elif de_ratio and de_ratio > 60:
        weaknesses.append(f"D/E {de_ratio:.1f}% — vay nợ ở mức trung bình-cao")
    elif de_ratio and de_ratio < 20:
        strengths.append(f"D/E rất thấp ({de_ratio:.1f}%) — an toàn tài chính, ít áp lực nợ")
    
    # Liquidity
    if current_ratio and current_ratio > 1.5:
        strengths.append(f"Thanh khoản ngắn hạn tốt (Current Ratio {current_ratio:.1f})")
    elif current_ratio and current_ratio < 1:
        risks.append(f"Thanh khoản ngắn hạn yếu (Current Ratio {current_ratio:.1f})")
    
    # Interest coverage
    if interest_coverage and interest_coverage > 10:
        strengths.append(f"Khả năng trả lãi vay mạnh (ICR {interest_coverage:.1f}x)")
    elif interest_coverage and interest_coverage < 3:
        risks.append(f"Khả năng trả lãi vay thấp (ICR {interest_coverage:.1f}x)")
    
    # Cash ratio
    if cash_ratio and cash_ratio > 30:
        strengths.append(f"Dự trữ tiền mặt dồi dào ({cash_ratio:.1f}% tài sản NH)")
    
    # CFO/NP
    if cfo_np is not None:
        if cfo_np > 0.8:
            strengths.append(f"Dòng tiền HĐKD mạnh (CFO/NP={cfo_np:.1f}) — lợi nhuận bằng tiền thật")
        elif cfo_np < 0.3:
            weaknesses.append(f"Dòng tiền HĐKD yếu (CFO/NP={cfo_np:.1f}) — lợi nhuận chủ yếu là ghi nhận")
    
    # ROA
    if roa and roa > 10:
        strengths.append(f"ROA {roa:.1f}% — hiệu quả sử dụng tài sản tốt")
    
    # Price momentum
    price_1y = m.get("price_change_1y", 0)
    if price_1y and price_1y > 0:
        strengths.append(f"Giá tăng {price_1y:.1f}% trong 1 năm — xu hướng tích cực")
    elif price_1y and price_1y < -20:
        weaknesses.append(f"Giảm {price_1y:.1f}% trong 1 năm — áp lực bán")
    elif price_1y and price_1y < 0:
        weaknesses.append(f"Giá giảm nhẹ {abs(price_1y):.1f}% trong 1 năm")
    
    vs_sma200 = m.get("vs_sma200", 0)
    if vs_sma200 and vs_sma200 < -10:
        weaknesses.append(f"Giá dưới SMA200 {vs_sma200:.1f}% — xu hướng dài hạn yếu")
    
    # Volume
    vol_ratio = m.get("volume_ratio", 0)
    if vol_ratio and vol_ratio > 1.5:
        weaknesses.append(f"Khối lượng giao dịch tăng đột biến ({vol_ratio:.1f}x TB) — có thể đầu cơ")
    
    # Generate outlook
    if score >= 85:
        outlook = f"Rất tích cực. {sym} có nền tảng tài chính vững chắc với các chỉ số vượt trội. Thích hợp cho cả đầu tư dài hạn."
        recommendation = "MUA — fundamentals mạnh, xếp hạng hấp dẫn"
    elif score >= 75:
        outlook = f"Tích cực. {sym} có nền tảng tốt với triển vọng ngành hỗ trợ. Có thể xem xét tích lũy."
        recommendation = "MUA_GIA_TĂNG — nên xem xét giải ngân"
    elif score >= 65:
        outlook = f"Khả quan nhưng cần thận trọng. {sym} có điểm tích cực nhưng cũng tồn tại rủi ro cần theo dõi."
        recommendation = "NẮM_GIỮ — chờ thêm tín hiệu trước khi mua"
    elif score >= 50:
        outlook = f"Triển vọng trung lập. {sym} đang trong giai đoạn chuyển đổi hoặc đối mặt khó khăn ngắn hạn."
        recommendation = "THEO_DÕI — chưa phải thời điểm mua"
    else:
        outlook = f"Thận trọng cao. {sym} đối mặt nhiều thách thức về tài chính hoặc thị trường."
        recommendation = "TRÁNH — rủi ro cao hơn cơ hội"
    
    # Risk assessment
    industry_risks = get_industry_risks(industry)
    risks.extend(industry_risks)
    
    if not strengths:
        strengths.append("Cần thêm dữ liệu để đánh giá điểm mạnh")
    if not weaknesses:
        weaknesses.append("Không phát hiện điểm yếu rõ rệt")
    if not risks:
        risks.append("Rủi ro thị trường chung (vĩ mô, lãi suất, tỷ giá)")
    
    # Trim to reasonable length
    strengths = strengths[:4]
    weaknesses = weaknesses[:3]
    risks = risks[:3]
    
    return {
        "symbol": sym,
        "score": score,
        "verdict": verdict,
        "price": price,
        "industry": industry,
        "outlook": outlook,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "risks": risks,
        "recommendation": recommendation,
        "key_metrics": {
            "PE": pe,
            "ROE": roe,
            "ROA": roa,
            "Net_Margin": net_margin,
            "Gross_Margin": gross_margin,
            "Revenue_Growth_QoQ": rev_growth,
            "D_E_Ratio": de_ratio,
            "Current_Ratio": current_ratio,
            "Interest_Coverage": interest_coverage,
            "Cash_Ratio": cash_ratio,
            "BVPS": bvps,
            "EPS_TTM": eps
        },
        "anomalies": anomalies
    }


def classify_industry(symbol, metrics):
    """Classify stock industry based on symbol."""
    # Known sector mapping
    sectors = {
        "ACB": "Ngân hàng", "BID": "Ngân hàng", "BWE": "Nước & Môi trường",
        "CTG": "Ngân hàng", "EIB": "Ngân hàng", "HDB": "Ngân hàng",
        "LPB": "Ngân hàng", "MBB": "Ngân hàng", "MSB": "Ngân hàng",
        "NAB": "Ngân hàng", "OCB": "Ngân hàng", "SHB": "Ngân hàng",
        "SSB": "Ngân hàng", "STB": "Ngân hàng", "TCB": "Ngân hàng",
        "TPB": "Ngân hàng", "VCB": "Ngân hàng", "VIB": "Ngân hàng",
        "VPB": "Ngân hàng",
        "VIC": "Bất động sản", "VHM": "Bất động sản", "VRE": "Bất động sản",
        "NVL": "Bất động sản", "KDH": "Bất động sản", "NLG": "Bất động sản",
        "DXG": "Bất động sản", "DXS": "Bất động sản", "PDR": "Bất động sản",
        "HDG": "Bất động sản", "HDC": "Bất động sản", "SJS": "Bất động sản",
        "KBC": "Bất động sản KCN", "SZC": "Bất động sản KCN", "BCM": "Bất động sản KCN",
        "GVR": "Cao su", "PHR": "Cao su",
        "FPT": "Công nghệ", "CMG": "Công nghệ", "CTR": "Công nghệ",
        "DIG": "Xây dựng", "VCG": "Xây dựng", "CTD": "Xây dựng",
        "HPG": "Thép", "NKG": "Thép", "HSG": "Thép",
        "VNM": "Tiêu dùng", "SAB": "Tiêu dùng", "MSN": "Tiêu dùng",
        "MWG": "Bán lẻ", "FRT": "Bán lẻ", "PNJ": "Bán lẻ", "DGW": "Bán lẻ",
        "REE": "Cơ điện", "GEX": "Cơ điện", "VGC": "Vật liệu XD",
        "BSR": "Dầu khí", "PLX": "Dầu khí", "GAS": "Dầu khí", "PVD": "Dầu khí",
        "PVT": "Dầu khí Vận tải", "POW": "Điện", "NT2": "Điện",
        "GMD": "Cảng biển", "VSC": "Cảng biển",
        "DCM": "Phân bón", "DPM": "Phân bón",
        "DGC": "Hóa chất", "BMP": "Nhựa",
        "VJC": "Hàng không", "VTP": "Chuyển phát nhanh", "VPL": "Logistics",
        "KDC": "Thực phẩm", "SBT": "Đường", "PAN": "Nông nghiệp", 
        "HAG": "Nông nghiệp", "ANV": "Thủy sản", "VHC": "Thủy sản",
        "IMP": "Dược phẩm",
        "BVH": "Bảo hiểm", "BSI": "Chứng khoán", "CTS": "Chứng khoán",
        "DSE": "Chứng khoán", "HCM": "Chứng khoán", "SSI": "Chứng khoán",
        "VCI": "Chứng khoán", "VND": "Chứng khoán", "VIX": "Chứng khoán",
        "EVF": "Tài chính", "FTS": "Chứng khoán",
        "HHV": "Hạ tầng GT", "CII": "Hạ tầng",
        "KOS": "Khu công nghiệp",
        "TCH": "Đa ngành",
        "SIP": "KCN",
        "HT1": "Xi măng",
        "DBC": "Chăn nuôi",
        "GEE": "Điện tử",
        "VTP": "Viễn thông",
        "VPI": "Tư vấn đầu tư",
        "SCS": "Dịch vụ sân bay",
        "PVD": "Dầu khí",
        "BWE": "Cấp nước",
        "REE": "Cơ điện lạnh",
    }
    
    if symbol in sectors:
        return sectors[symbol]
    return "Đa ngành"


def get_industry_risks(industry):
    """Get industry-specific risks."""
    risks_map = {
        "Ngân hàng": ["Rủi ro nợ xấu (NPL) khi tăng trưởng tín dụng", "Áp lực margin từ cạnh tranh lãi suất"],
        "Bất động sản": ["Rủi ro thanh khoản thị trường BĐS", "Phụ thuộc vào chính sách tín dụng và pháp lý"],
        "Bất động sản KCN": ["Phụ thuộc vào dòng vốn FDI và chính sách đất đai"],
        "Thép": ["Biến động giá nguyên liệu (quặng sắt, than)", "Cạnh tranh từ thép Trung Quốc"],
        "Dầu khí": ["Phụ thuộc giá dầu thế giới", "Rủi ro địa chính trị"],
        "Chứng khoán": ["Lợi nhuận phụ thuộc nhiều vào thanh khoản và xu hướng thị trường"],
        "Bán lẻ": ["Cạnh tranh từ thương mại điện tử", "Áp lực chi phí mặt bằng và nhân công"],
        "Điện": ["Khấu hao tài sản cố định cao", "Phụ thuộc chính sách giá điện"],
        "Thủy sản": ["Rủi ro hạn hán, xâm nhập mặn", "Rào cản thương mại quốc tế"],
        "Phân bón": ["Biến động giá nguyên liệu đầu vào", "Cạnh tranh từ phân bón nhập khẩu"],
    }
    return risks_map.get(industry, ["Rủi ro thị trường và cạnh tranh"])


def main():
    if not os.path.exists(DATE_DIR):
        print(f"❌ Không tìm thấy thư mục {DATE_DIR}")
        sys.exit(1)
    
    for i in range(10):
        batch_path = os.path.join(DATE_DIR, f"batch_{i}.json")
        ai_path = os.path.join(DATE_DIR, f"ai_batch_{i}.json")
        
        if not os.path.exists(batch_path):
            print(f"⚠️ batch_{i}.json không tồn tại, bỏ qua")
            continue
        
        with open(batch_path) as f:
            batch_data = json.load(f)
        
        ai_stocks = []
        for stock in batch_data["stocks"]:
            ai = analyze_stock(stock)
            ai_stocks.append(ai)
        
        ai_data = {
            "date": TODAY,
            "batch": i,
            "total_batches": 10,
            "stocks": ai_stocks
        }
        
        with open(ai_path, "w", encoding="utf-8") as f:
            json.dump(ai_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ ai_batch_{i}.json — {len(ai_stocks)} stocks analyzed")
    
    print(f"\n📊 AI analysis complete. {sum(len(json.load(open(os.path.join(DATE_DIR, f'ai_batch_{i}.json')))) for i in range(10))} total stocks in {DATE_DIR}")


if __name__ == "__main__":
    main()
