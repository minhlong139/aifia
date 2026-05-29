#!/usr/bin/env python3
"""
Generate AI-enhanced analysis for all stocks in data/history/YYYY-MM-DD/
"""
import json, glob, os, sys
from datetime import date

today = date.today().isoformat() if len(sys.argv) < 2 else sys.argv[1]
base = os.path.join(os.path.dirname(__file__), '..', 'data', 'history', today)
base = os.path.abspath(base)

if not os.path.isdir(base):
    print(f"❌ Data dir not found: {base}")
    sys.exit(1)

batch_files = sorted(glob.glob(os.path.join(base, 'batch_*.json')))
if not batch_files:
    print(f"❌ No batch files in {base}")
    sys.exit(1)

print(f"✅ Processing {len(batch_files)} batch files in {base}")

INDUSTRY_MAP = {
    'ACB': 'Ngân hàng', 'BID': 'Ngân hàng', 'CTG': 'Ngân hàng', 'EIB': 'Ngân hàng',
    'HDB': 'Ngân hàng', 'LPB': 'Ngân hàng', 'MBB': 'Ngân hàng', 'MSB': 'Ngân hàng',
    'NAB': 'Ngân hàng', 'OCB': 'Ngân hàng', 'SHB': 'Ngân hàng', 'SSB': 'Ngân hàng',
    'STB': 'Ngân hàng', 'TCB': 'Ngân hàng', 'TPB': 'Ngân hàng', 'VCB': 'Ngân hàng',
    'VIB': 'Ngân hàng', 'VPB': 'Ngân hàng',
    'BSI': 'Chứng khoán', 'CTS': 'Chứng khoán', 'DSE': 'Chứng khoán', 'EVF': 'Chứng khoán',
    'HCM': 'Chứng khoán', 'SSI': 'Chứng khoán', 'VCI': 'Chứng khoán', 'VIX': 'Chứng khoán',
    'VND': 'Chứng khoán', 'VPI': 'Chứng khoán',
    'DXG': 'Bất động sản', 'DXS': 'Bất động sản', 'HDC': 'Bất động sản', 'KDH': 'Bất động sản',
    'KOS': 'Bất động sản', 'NLG': 'Bất động sản', 'NVL': 'Bất động sản', 'PDR': 'Bất động sản',
    'SJS': 'Bất động sản', 'SZC': 'Bất động sản', 'TCH': 'Bất động sản', 'VHM': 'Bất động sản',
    'VIC': 'Bất động sản', 'VPL': 'Bất động sản',
    'CTD': 'Xây dựng', 'HT1': 'Vật liệu xây dựng', 'PC1': 'Xây dựng/Năng lượng',
    'VCG': 'Xây dựng', 'VGC': 'Vật liệu xây dựng',
    'HPG': 'Thép', 'HSG': 'Thép', 'NKG': 'Thép',
    'CMG': 'Công nghệ', 'FPT': 'Công nghệ', 'CTR': 'Viễn thông/Công nghệ',
    'DGW': 'Phân phối', 'FRT': 'Bán lẻ', 'MWG': 'Bán lẻ', 'PNJ': 'Bán lẻ vàng bạc',
    'VRE': 'Bán lẻ (cho thuê mặt bằng)',
    'BSR': 'Lọc hóa dầu', 'GAS': 'Khí đốt', 'PLX': 'Xăng dầu',
    'POW': 'Nhiệt điện', 'PVD': 'Dầu khí (khoan)', 'PVT': 'Vận tải dầu khí', 'NT2': 'Nhiệt điện',
    'KDC': 'Thực phẩm', 'MSN': 'Thực phẩm/Đầu tư', 'SAB': 'Bia', 'VNM': 'Sữa', 'PAN': 'Nông nghiệp/Thực phẩm',
    'ANV': 'Thủy sản', 'VHC': 'Thủy sản',
    'DPM': 'Phân bón', 'DCM': 'Phân bón', 'DGC': 'Hóa chất', 'GVR': 'Cao su', 'PHR': 'Cao su',
    'BCM': 'Khu công nghiệp', 'BWE': 'Nước/Môi trường', 'CII': 'Hạ tầng',
    'GMD': 'Cảng biển', 'HHV': 'Hạ tầng', 'KBC': 'Khu công nghiệp',
    'REE': 'Cơ điện/Năng lượng', 'SIP': 'Khu công nghiệp', 'SBT': 'Mía đường',
    'SCS': 'Cảng biển', 'VSC': 'Cảng biển', 'VTP': 'Chuyển phát nhanh', 'GEE': 'Cơ điện',
    'BMP': 'Nhựa', 'BVH': 'Bảo hiểm', 'DIG': 'Đầu tư/Phát triển hạ tầng',
    'FTS': 'Tài chính', 'GEX': 'Điện/Xây dựng', 'HAG': 'Nông nghiệp',
    'HDG': 'Năng lượng/Nhiệt điện', 'IMP': 'Dược phẩm', 'VJC': 'Hàng không',
}

def safe_num(v):
    if v is None: return None
    try: return float(v)
    except: return None

def nz(v):
    """Return 0 if None"""
    return 0 if v is None else v

for bf in batch_files:
    data = json.load(open(bf))
    batch_num = data['batch']
    enhanced = {'batch': batch_num, 'date': data['date'], 'stocks': []}
    
    for stock in data['stocks']:
        s = stock['symbol']
        m = stock.get('metrics', {}) or {}
        score = stock['score']
        verdict = stock.get('verdict', '')
        anomalies = stock.get('anomalies', [])
        industry = INDUSTRY_MAP.get(s, stock.get('industry', 'Không xác định'))
        price = stock.get('latest_price') or m.get('price', 'N/A')
        
        analysis = {
            'symbol': s,
            'industry': industry,
            'score': score,
            'verdict': verdict,
            'price': price,
            'metrics_summary': {},
            'ai_assessment': '',
            'strengths': [],
            'weaknesses': [],
            'risks': [],
            'outlook': '',
            'recommendation': ''
        }
        
        pe = safe_num(m.get('pe'))
        pb = safe_num(m.get('pb'))
        roe = safe_num(m.get('roe'))
        de = safe_num(m.get('de_ratio'))
        rev_growth = safe_num(m.get('revenue_growth_qoq'))
        net_margin = safe_num(m.get('net_margin'))
        op_margin = safe_num(m.get('op_margin'))
        gross_margin = safe_num(m.get('gross_margin'))
        current_ratio = safe_num(m.get('current_ratio'))
        dso = safe_num(m.get('dso_days'))
        cash_ratio = safe_num(m.get('cash_ratio'))
        eps = safe_num(m.get('eps_ttm_vnd'))
        bvps = safe_num(m.get('bvps_vnd'))
        price_1y = safe_num(m.get('price_change_1y'))
        from_high = safe_num(m.get('from_52w_high'))
        
        # Display P/E specially — score shows 0 for all
        pe_display = pe if (pe is not None and pe > 0) else 'N/A'
        
        analysis['metrics_summary'] = {
            'price': price,
            'P/E': pe_display, 'P/B': pb if pb is not None else 'N/A',
            'ROE': f'{roe}%' if roe is not None else 'N/A',
            'D/E': f'{de}%' if de is not None else 'N/A',
            'Revenue Growth QoQ': f'{rev_growth}%' if rev_growth is not None else 'N/A',
            'Net Margin': f'{net_margin}%' if net_margin is not None else 'N/A',
            'Op Margin': f'{op_margin}%' if op_margin is not None else 'N/A',
            'Gross Margin': f'{gross_margin}%' if gross_margin is not None else 'N/A',
            'Current Ratio': current_ratio,
            'Cash Ratio': f'{cash_ratio}%' if cash_ratio is not None else 'N/A',
            'DSO (days)': dso,
            'EPS (VND)': eps,
            'BVPS (VND)': bvps,
            'Price Change 1Y': f'{price_1y}%' if price_1y is not None else 'N/A',
            'From 52w High': f'{from_high}%' if from_high is not None else 'N/A'
        }
        
        strengths = []
        weaknesses = []
        risks = []
        
        is_bank = (industry == 'Ngân hàng')
        is_securities = (industry == 'Chứng khoán')
        
        if verdict == 'LỖI':
            analysis['ai_assessment'] = f'{s} bị lỗi khi fetch dữ liệu tài chính. Cần kiểm tra lại nguồn dữ liệu Supabase.'
            analysis['outlook'] = 'Không thể đánh giá do thiếu dữ liệu.'
            analysis['recommendation'] = 'Chờ xử lý lỗi dữ liệu.'
            enhanced['stocks'].append(analysis)
            continue
        
        verdict_map = {'HẤP_DẪN': 'rất tích cực', 'TÍCH_CỰC': 'tích cực', 'TRUNG_LẬP': 'trung lập',
                       'THẬN_TRỌNG': 'thận trọng', 'RỦI_RO': 'rủi ro'}
        abs_verdict = verdict_map.get(verdict, 'chưa xác định')
        
        if is_bank:
            analysis['ai_assessment'] = (
                f'{s} là cổ phiếu ngân hàng với điểm {score}/100 (mức {abs_verdict}). '
                f'Giá hiện tại {price}. ROE {roe}%' if roe is not None else 'Chưa có ROE'
            )
            if roe is not None and roe > 15:
                strengths.append(f'ROE {roe}% — hiệu quả sử dụng vốn tốt')
            if de is not None and de < 30:
                strengths.append(f'Tỷ lệ nợ thấp (D/E {de}%)')
        elif is_securities:
            analysis['ai_assessment'] = (
                f'{s} là cổ phiếu chứng khoán với điểm {score}/100 (mức {abs_verdict}). '
                f'Giá hiện tại {price}.'
            )
            if price_1y is not None and price_1y > 0:
                strengths.append(f'Giá tăng {price_1y}% trong 1 năm')
        else:
            analysis['ai_assessment'] = (
                f'{s} thuộc ngành {industry}, điểm {score}/100 (mức {abs_verdict}). '
                f'Giá hiện tại {price}.'
            )
        
        # Strengths
        if roe is not None and roe > 15:
            strengths.append(f'ROE {roe}% — hiệu quả sử dụng vốn tốt')
        elif roe is not None and roe > 10:
            strengths.append(f'ROE {roe}% — hiệu quả sử dụng vốn khá')
        
        if net_margin is not None and net_margin > 15:
            strengths.append(f'Biên lợi nhuận ròng {net_margin}% — ấn tượng')
        elif net_margin is not None and net_margin > 10:
            strengths.append(f'Biên lợi nhuận ròng {net_margin}% — tốt')
        
        if op_margin is not None and op_margin > 15:
            strengths.append(f'Biên lợi nhuận hoạt động {op_margin}% — hiệu quả vận hành cao')
        
        if de is not None and de >= 0 and de < 30:
            strengths.append(f'D/E thấp ({de}%) — an toàn tài chính tốt')
        elif de is not None and 30 <= de < 80:
            strengths.append(f'Đòn bẩy tài chính hợp lý (D/E {de}%)')
        
        if current_ratio is not None and current_ratio > 2:
            strengths.append(f'Khả năng thanh khoản tốt (Current Ratio {current_ratio})')
        
        if cash_ratio is not None and cash_ratio > 20:
            strengths.append(f'Lượng tiền mặt dồi dào ({cash_ratio}%)')
        
        if rev_growth is not None and rev_growth > 15:
            strengths.append(f'Tăng trưởng doanh thu QoQ {rev_growth}%')
        
        if from_high is not None and from_high > -10:
            strengths.append(f'Cách đỉnh 52 tuần chỉ {abs(from_high)}% — gần vùng kháng cự')
        
        # Weaknesses
        negative_anomaly_types = [a.get('type','') for a in anomalies]
        
        if roe is not None and roe < 8:
            weaknesses.append(f'ROE {roe}% — thấp, hiệu quả sử dụng vốn kém')
        
        if net_margin is not None and net_margin < 5:
            weaknesses.append(f'Biên lợi nhuận ròng {net_margin}% — rất mỏng')
        elif net_margin is not None and net_margin < 10:
            weaknesses.append(f'Biên lợi nhuận ròng {net_margin}% — khá thấp')
        
        if op_margin is not None and op_margin < 5:
            weaknesses.append(f'Biên lợi nhuận hoạt động {op_margin}% — thấp')
        
        if de is not None and de > 100:
            weaknesses.append(f'Đòn bẩy cao (D/E {de}%)')
        if de is not None and de > 200:
            weaknesses.append(f'Rủi ro vỡ nợ cao — D/E {de}%')
        
        if current_ratio is not None and current_ratio < 0.8:
            weaknesses.append(f'Thanh khoản yếu (Current Ratio {current_ratio})')
        
        if dso is not None and dso > 200:
            weaknesses.append(f'DSO {dso} ngày — thu hồi công nợ rất chậm')
        elif dso is not None and dso > 90:
            weaknesses.append(f'DSO {dso} ngày — thu hồi công nợ chậm')
        
        if rev_growth is not None and rev_growth < -10:
            weaknesses.append(f'Doanh thu giảm {abs(rev_growth)}% QoQ')
        
        if 'revenue_spike' in negative_anomaly_types:
            weaknesses.append(f'Doanh thu tăng đột biến QoQ — cần kiểm tra tính bền vững')
        
        if from_high is not None and from_high < -20:
            weaknesses.append(f'Giảm {abs(from_high)}% từ đỉnh 52 tuần — xu hướng yếu')
        
        if price_1y is not None and price_1y < 0:
            weaknesses.append(f'Giá giảm {abs(price_1y)}% trong 1 năm')
        
        # Risks
        if 'high_debt' in negative_anomaly_types or (de is not None and de > 100):
            risks.append(f'Rủi ro tài chính từ đòn bẩy cao (D/E {de}%)')
        
        if dso is not None and dso > 300:
            risks.append(f'Rủi ro thanh khoản từ công nợ phải thu kéo dài (DSO {dso} ngày)')
        
        if 'margin_suspicious' in negative_anomaly_types:
            risks.append(f'Biên lợi nhuận bất thường — rủi ro gian lận/thiếu minh bạch')
        
        if 'revenue_spike' in negative_anomaly_types:
            risks.append(f'Rủi ro doanh thu tăng đột biến không bền vững')
        
        if 'revenue_decline' in negative_anomaly_types:
            risks.append(f'Suy giảm doanh thu — rủi ro kinh doanh')
        
        if de is not None and de > 150:
            risks.append(f'Rủi ro phá sản nếu lãi suất tăng hoặc kinh doanh suy giảm')
        
        if from_high is not None and from_high < -30:
            risks.append(f'Rủi ro xu hướng giảm dài hạn')
        
        # Outlook & recommendation
        if score >= 80:
            outlook = f'{s} có nền tảng tài chính vững chắc và triển vọng tích cực.'
            if industry:
                outlook += f' Ngành {industry} duy trì đà tăng trưởng ổn định.'
            if from_high is not None and from_high < -10:
                outlook += ' Có thể tận dụng vùng giá thấp để tích lũy.'
            analysis['recommendation'] = 'MUA — nền tảng tài chính tốt, triển vọng tích cực'
        elif score >= 70:
            outlook = f'{s} có nền tảng ổn định nhưng tiềm năng tăng trưởng ở mức vừa phải.'
            if risks:
                outlook += ' Cần theo dõi các rủi ro đã nêu.'
            analysis['recommendation'] = 'NẮM GIỮ — nền tảng tốt nhưng chờ điểm vào hợp lý'
        elif score >= 60:
            outlook = f'{s} có tín hiệu trái chiều.'
            if strengths:
                outlook += f' Điểm mạnh: {strengths[0].lower()}.'
            if weaknesses:
                outlook += f' Điểm yếu: {weaknesses[0].lower()}.'
            analysis['recommendation'] = 'THEO DÕI — chờ thêm tín hiệu xác nhận'
        elif score >= 40:
            outlook = f'{s} đang đối diện nhiều thách thức. Cần thận trọng.'
            analysis['recommendation'] = 'THẬN TRỌNG — rủi ro cao hơn cơ hội'
        else:
            outlook = f'{s} ở trạng thái yếu kém, nhiều rủi ro.'
            analysis['recommendation'] = 'TRÁNH — nhiều yếu tố bất lợi'
        
        analysis['strengths'] = strengths
        analysis['weaknesses'] = weaknesses
        analysis['risks'] = risks
        analysis['outlook'] = outlook
        
        enhanced['stocks'].append(analysis)
    
    outfile = os.path.join(base, f'ai_batch_{batch_num}.json')
    with open(outfile, 'w') as f:
        json.dump(enhanced, f, indent=2, ensure_ascii=False)
    print(f"  ✅ ai_batch_{batch_num}.json ({len(enhanced['stocks'])} stocks)")

print(f"✅ AI enhancement complete for {len(batch_files)} batches → {base}")
