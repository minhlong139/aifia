#!/usr/bin/env python3
"""AI Enhancement: phân tích sâu từng cổ phiếu và ghi vào ai_batch_N.json"""

import json, os, sys
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

def get_date_dir():
    """Lấy thư mục ngày hiện tại hoặc từ argument"""
    if len(sys.argv) > 1:
        return sys.argv[1]
    return datetime.now().strftime("%Y-%m-%d")

def analyze_stock(stock):
    """Phân tích sâu một cổ phiếu dựa trên dữ liệu có sẵn"""
    s = stock["symbol"]
    m = stock.get("metrics", {})
    score = stock.get("score", 0)
    verdict = stock.get("verdict", "N/A")
    price = m.get("price", 0)
    pe = m.get("pe", 0)
    roe = m.get("roe", 0)
    de_ratio = m.get("de_ratio", 0)
    rev_growth = m.get("revenue_growth_qoq", 0)
    gross_margin = m.get("gross_margin", 0)
    net_margin = m.get("net_margin", 0)
    current_ratio = m.get("current_ratio", 0)
    interest_cov = m.get("interest_coverage", 0)
    anomalies = stock.get("anomalies", [])
    
    analysis = {}
    analysis["symbol"] = s
    analysis["score"] = score
    analysis["verdict"] = verdict
    analysis["price"] = price
    
    # Đánh giá triển vọng ngành
    industry_outlook = []
    if de_ratio < 30:
        industry_outlook.append("Nợ thấp, an toàn tài chính")
    elif de_ratio < 60:
        industry_outlook.append("Đòn bẩy vừa phải, chấp nhận được")
    else:
        industry_outlook.append("Đòn bẩy cao, cần theo dõi")
    
    if rev_growth > 15:
        industry_outlook.append("Tăng trưởng doanh thu mạnh (>15% QoQ)")
    elif rev_growth > 5:
        industry_outlook.append("Tăng trưởng doanh thu ổn định")
    else:
        industry_outlook.append("Tăng trưởng doanh thu chậm")
    
    # Chất lượng tài chính
    fin_quality = []
    if roe >= 20:
        fin_quality.append("ROE xuất sắc (>=20%)")
    elif roe >= 15:
        fin_quality.append("ROE tốt (15-20%)")
    elif roe >= 10:
        fin_quality.append("ROE trung bình (10-15%)")
    else:
        fin_quality.append("ROE thấp (<10%)")
    
    if gross_margin >= 30:
        fin_quality.append("Biên lợi nhuận gộp cao")
    elif gross_margin >= 15:
        fin_quality.append("Biên lợi nhuận gộp trung bình")
    else:
        fin_quality.append("Biên lợi nhuận gộp thấp")
    
    if net_margin >= 10:
        fin_quality.append("Biên lợi nhuận ròng tốt")
    elif net_margin >= 5:
        fin_quality.append("Biên lợi nhuận ròng khá")
    else:
        fin_quality.append("Biên lợi nhuận ròng thấp")
    
    if current_ratio >= 2:
        fin_quality.append("Thanh khoản ngắn hạn tốt")
    elif current_ratio >= 1:
        fin_quality.append("Thanh khoản ngắn hạn ổn")
    else:
        fin_quality.append("Thanh khoản ngắn hạn yếu")
    
    # Điểm mạnh
    strengths = []
    if score >= 80:
        strengths.append("Tổng điểm cao (>=80) phản ánh nền tảng vững chắc")
    if roe >= 20:
        strengths.append("ROE cao cho thấy hiệu quả sử dụng vốn tốt")
    if rev_growth > 10:
        strengths.append("Tăng trưởng doanh thu tích cực")
    if de_ratio < 40:
        strengths.append("Ít phụ thuộc vào nợ vay")
    if gross_margin > 25:
        strengths.append("Biên lợi nhuận gộp cạnh tranh")
    if current_ratio > 1.5:
        strengths.append("Khả năng thanh toán ngắn hạn tốt")
    if interest_cov > 10:
        strengths.append("Khả năng trả lãi vay rất tốt")
    
    # Điểm yếu
    weaknesses = []
    if score < 60:
        weaknesses.append("Tổng điểm thấp cần cải thiện nhiều mặt")
    if roe < 10:
        weaknesses.append("ROE thấp, hiệu quả sử dụng vốn kém")
    if rev_growth < 0:
        weaknesses.append("Doanh thu tăng trưởng âm")
    if de_ratio > 60:
        weaknesses.append("Nợ cao so với vốn chủ sở hữu")
    if current_ratio < 1:
        weaknesses.append("Thanh khoản ngắn hạn yếu, rủi ro mất khả năng thanh toán")
    if m.get("cfo_t") is not None and m.get("cfo_np_ratio", 1) < 0.5:
        weaknesses.append("Dòng tiền hoạt động thấp hơn lợi nhuận")
    if score == 0:
        weaknesses.append("Không có dữ liệu hoặc lỗi trong quá trình phân tích")
    
    # Rủi ro
    risks = []
    if de_ratio > 70:
        risks.append("Rủi ro đòn bẩy tài chính cao")
    if price <= 0 or pe <= 0:
        risks.append("Thiếu dữ liệu giá/P/E để đánh giá định giá")
    if m.get("price_change_1y", 0) < -20:
        risks.append("Giá giảm mạnh trong 1 năm (>20%)")
    if m.get("vs_sma200", 0) and m["vs_sma200"] < -15:
        risks.append("Xu hướng giảm dài hạn (dưới SMA200 >15%)")
    if m.get("volume_ratio", 1) < 0.5:
        risks.append("Thanh khoản thấp so với trung bình")
    if current_ratio < 0.8:
        risks.append("Rủi ro thanh khoản ngắn hạn")
    
    if not strengths:
        strengths.append("Không có điểm mạnh nổi bật")
    if not weaknesses:
        weaknesses.append("Không phát hiện điểm yếu lớn")
    if not risks:
        risks.append("Không phát hiện rủi ro lớn")
    
    analysis["industry_outlook"] = industry_outlook
    analysis["financial_quality"] = fin_quality
    analysis["strengths"] = strengths
    analysis["weaknesses"] = weaknesses
    analysis["risks"] = risks
    analysis["anomalies"] = [a if isinstance(a, str) else str(a) for a in anomalies]
    
    # Tổng quan
    if score >= 80:
        overall = "Tích cực - Cổ phiếu có nền tảng tài chính tốt, triển vọng khả quan."
    elif score >= 60:
        overall = "Trung lập - Cổ phiếu ổn định nhưng cần theo dõi thêm các yếu tố tăng trưởng."
    elif score >= 40:
        overall = "Thận trọng - Cổ phiếu đối mặt nhiều thách thức, cần đánh giá kỹ trước khi đầu tư."
    else:
        overall = "Rủi ro - Cổ phiếu có nhiều vấn đề về tài chính hoặc thiếu dữ liệu."
    analysis["overall_assessment"] = overall
    
    return analysis

def process_all():
    date_str = get_date_dir()
    history_dir = os.path.join(DATA_DIR, "history", date_str)
    
    if not os.path.exists(history_dir):
        print("Không tìm thấy thư mục: %s" % history_dir)
        sys.exit(1)
    
    for i in range(10):
        batch_file = os.path.join(history_dir, "batch_%d.json" % i)
        ai_file = os.path.join(history_dir, "ai_batch_%d.json" % i)
        
        if not os.path.exists(batch_file):
            print("Bỏ qua batch_%d - không tìm thấy file" % i)
            continue
        
        with open(batch_file) as f:
            data = json.load(f)
        
        stocks = data.get("stocks", [])
        ai_stocks = []
        
        for stock in stocks:
            analysis = analyze_stock(stock)
            ai_stocks.append(analysis)
        
        output = {
            "batch": i,
            "total_batches": 10,
            "date": date_str,
            "ai_enhanced": True,
            "stocks": ai_stocks
        }
        
        with open(ai_file, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print("✅ ai_batch_%d.json: %d stocks" % (i, len(ai_stocks)))
    
    print("\n✅ AI Enhancement hoàn tất cho ngày %s" % date_str)

if __name__ == "__main__":
    process_all()
