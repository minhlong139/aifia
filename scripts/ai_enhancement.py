#!/usr/bin/env python3
"""
AIFIA AI Enhancement - Reads batch analysis files and adds deep AI analysis.
Outputs ai_batch_N.json for each batch.
"""
import json
import os
import sys
from datetime import datetime

DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-05-23"
INDIR = f"data/history/{DATE}"
OUTDIR = INDIR

if not os.path.isdir(INDIR):
    print(f"Directory not found: {INDIR}")
    sys.exit(1)

INDUSTRY_MAP = {
    'ACB':'Ngân hàng','BID':'Ngân hàng','CTG':'Ngân hàng','EIB':'Ngân hàng','HDB':'Ngân hàng',
    'LPB':'Ngân hàng','MBB':'Ngân hàng','MSB':'Ngân hàng','NAB':'Ngân hàng','OCB':'Ngân hàng',
    'SHB':'Ngân hàng','SSB':'Ngân hàng','STB':'Ngân hàng','TCB':'Ngân hàng','TPB':'Ngân hàng',
    'VCB':'Ngân hàng','VIB':'Ngân hàng','VPB':'Ngân hàng',
    'FPT':'Công nghệ & Viễn thông','CMG':'Công nghệ & Viễn thông','CTR':'Công nghệ & Viễn thông',
    'VTP':'Công nghệ & Viễn thông',
    'MWG':'Hàng tiêu dùng & Thực phẩm','DGW':'Hàng tiêu dùng & Thực phẩm','FRT':'Hàng tiêu dùng & Thực phẩm',
    'PNJ':'Hàng tiêu dùng & Thực phẩm','SAB':'Hàng tiêu dùng & Thực phẩm','MSN':'Hàng tiêu dùng & Thực phẩm',
    'VNM':'Hàng tiêu dùng & Thực phẩm','KDC':'Hàng tiêu dùng & Thực phẩm','DBC':'Hàng tiêu dùng & Thực phẩm',
    'PAN':'Hàng tiêu dùng & Thực phẩm','VHC':'Hàng tiêu dùng & Thực phẩm','ANV':'Hàng tiêu dùng & Thực phẩm',
    'IMP':'Dược phẩm & Y tế','DHG':'Dược phẩm & Y tế','TRA':'Dược phẩm & Y tế',
    'VIC':'Bất động sản','VHM':'Bất động sản','KDH':'Bất động sản','NLG':'Bất động sản',
    'PDR':'Bất động sản','DXG':'Bất động sản','DXS':'Bất động sản','HDC':'Bất động sản',
    'HDG':'Bất động sản','KBC':'Bất động sản','NVL':'Bất động sản','SJS':'Bất động sản',
    'SZC':'Bất động sản','VRE':'Bất động sản','VPL':'Bất động sản','CII':'Bất động sản',
    'DIG':'Bất động sản',
    'VJC':'Hàng không','HVN':'Hàng không','SCS':'Hàng không',
    'HPG':'Thép & Vật liệu','NKG':'Thép & Vật liệu','HSG':'Thép & Vật liệu',
    'GEE':'Thép & Vật liệu','VGC':'Thép & Vật liệu',
    'GAS':'Dầu khí & Năng lượng','PLX':'Dầu khí & Năng lượng','PVD':'Dầu khí & Năng lượng',
    'PVT':'Dầu khí & Năng lượng','BSR':'Dầu khí & Năng lượng','PC1':'Dầu khí & Năng lượng',
    'POW':'Điện & Năng lượng','NT2':'Điện & Năng lượng','REE':'Điện & Năng lượng',
    'GEX':'Dịch vụ tài chính','BWE':'Dịch vụ tài chính','BMP':'Vật liệu xây dựng',
    'SIP':'Khu công nghiệp','CTD':'Xây dựng','HT1':'Vật liệu xây dựng',
    'DCM':'Phân bón & Hóa chất','DPM':'Phân bón & Hóa chất','DGC':'Hóa chất',
    'DSE':'Chứng khoán','VCI':'Chứng khoán','VND':'Chứng khoán','VPI':'Chứng khoán',
    'BSI':'Chứng khoán','EVF':'Chứng khoán','SSI':'Chứng khoán','HCM':'Chứng khoán',
    'VDS':'Chứng khoán','ORS':'Chứng khoán','MBS':'Chứng khoán','TVS':'Chứng khoán',
    'CTS':'Chứng khoán','FTS':'Chứng khoán','VIX':'Chứng khoán',
    'BID':'Ngân hàng','BVH':'Bảo hiểm','VRE':'Bất động sản','SBT':'Mía đường',
    'PHR':'Cao su','GVR':'Cao su','GMD':'Cảng & Logistics','VSC':'Cảng & Logistics',
    'HHV':'Xây dựng hạ tầng','BWE':'Nước & Môi trường','REE':'Cơ điện lạnh',
    'VTP':'Bưu chính & Logistics',
}

def calc_pe(price_k, eps_vnd):
    if eps_vnd and eps_vnd > 0 and price_k and price_k > 0:
        return round(price_k * 1000 / eps_vnd, 2)
    return None

for i in range(10):
    fname = os.path.join(INDIR, f'batch_{i}.json')
    if not os.path.exists(fname):
        continue
    with open(fname) as f:
        batch = json.load(f)
    stocks = batch.get('stocks', [])
    enhanced = []
    for s in stocks:
        m = s.get('metrics', {})
        symbol = s.get('symbol', 'UNKNOWN')
        industry = INDUSTRY_MAP.get(symbol, 'Khác')
        score = s.get('score', 0)
        verdict = s.get('verdict', '')
        anomalies = s.get('anomalies', [])
        
        eps = m.get('eps_ttm_vnd') or 0
        price = m.get('price') or 0
        roe = m.get('roe') or 0
        de = m.get('de_ratio') or 0
        growth = m.get('revenue_growth_qoq') or 0
        margin = m.get('net_margin') or 0
        gross_margin = m.get('gross_margin') or 0
        current_ratio = m.get('current_ratio') or 0
        price_change_1y = m.get('price_change_1y') or 0
        pe_val = calc_pe(price, eps)
        
        # Industry outlook
        outlooks = {
            'Ngân hàng': 'Ngành ngân hàng 2026 duy trì tăng trưởng tín dụng ~15%, NIM dần phục hồi. Áp lực nợ xấu vẫn hiện hữu nhưng đã qua đỉnh.',
            'Công nghệ & Viễn thông': 'Ngành CNTT tăng trưởng mạnh nhờ chuyển đổi số quốc gia, xuất khẩu phần mềm và dịch vụ IT. FPT là đầu tàu với các đơn hàng AI, chuyển đổi số quy mô lớn.',
            'Bất động sản': 'Thị trường phục hồi chậm nhưng tích cực. Luật Đất đai, Nhà ở, Kinh doanh BĐS mới tạo khung pháp lý rõ ràng. Nguồn cung mới vẫn hạn chế.',
            'Hàng tiêu dùng & Thực phẩm': 'Tiêu dùng nội địa phục hồi ổn định. Công ty có thương hiệu mạnh và mạng lưới phân phối rộng vẫn giữ lợi thế cạnh tranh.',
            'Thép & Vật liệu': 'Ngành thép hưởng lợi từ đầu tư công và hạ tầng. Cạnh tranh từ thép Trung Quốc và biến động nguyên vật liệu là rủi ro ngắn hạn.',
            'Dầu khí & Năng lượng': 'Giá dầu thế giới neo cao hỗ trợ doanh thu. LNG và chuyển dịch điện khí là xu hướng trong 3-5 năm tới.',
            'Điện & Năng lượng': 'Nhu cầu điện tăng ~10%/năm. Năng lượng tái tạo được ưu đãi nhưng còn vướng mắc về cơ chế giá và giải phóng mặt bằng.',
            'Chứng khoán': 'Thị trường chứng khoán phục hồi, thanh khoản cải thiện. Hưởng lợi từ nâng hạng thị trường và dòng vốn ngoại.',
            'Hàng không': 'Phục hồi du lịch mạnh mẽ. Giá nhiên liệu là biến số chính ảnh hưởng lợi nhuận. Cạnh tranh đường bay nội địa gay gắt.',
            'Dược phẩm & Y tế': 'Ngành dược tăng trưởng ổn định 8-12%/năm nhờ già hóa dân số và chi tiêu y tế tăng. Cạnh tranh từ thuốc ngoại nhập.',
            'Phân bón & Hóa chất': 'Hưởng lợi từ giá phân bón thế giới và nhu cầu nông nghiệp. Cạnh tranh từ hàng nhập khẩu.',
            'Bảo hiểm': 'Tăng trưởng phí bảo hiểm 10-15%/năm. Kênh bancassurance phục hồi sau giai đoạn tái cấu trúc.',
            'Cao su': 'Giá cao su thế giới neo ở mức hỗ trợ. Nhu cầu từ sản xuất lốp xe và công nghiệp phục hồi.',
            'Cảng & Logistics': 'Hưởng lợi từ thương mại quốc tế phục hồi và đầu tư hạ tầng cảng biển. Cạnh tranh giá cước vận tải.',
            'Vật liệu xây dựng': 'Nhu cầu vật liệu tăng nhờ đẩy mạnh đầu tư công và hạ tầng. Xi măng, đá, gạch có lợi thế chi phí.',
            'Khu công nghiệp': 'Dòng vốn FDI mạnh, giá thuê đất KCN tăng. Hạ tầng giao thông kết nối được đầu tư đồng bộ.',
            'Xây dựng': 'Ngành xây dựng hồi phục nhờ dự án hạ tầng và đầu tư công. Biên lợi nhuận mỏng là thách thức dai dẳng.',
            'Mía đường': 'Ngành đường hưởng lợi từ thuế chống bán phá giá và nhu cầu tiêu thụ ổn định. Biến động giá đường thế giới là rủi ro.',
            'Xây dựng hạ tầng': 'Đầu tư công là động lực chính. Các dự án cao tốc Bắc-Nam, sân bay Long Thành thúc đẩy tăng trưởng.',
            'Bưu chính & Logistics': 'Thương mại điện tử tăng trưởng mạnh kéo theo nhu cầu logistics. Cạnh tranh giá khốc liệt.',
            'Nước & Môi trường': 'Nhu cầu nước sạch và xử lý môi trường tăng đều. Chính sách xã hội hóa và cổ phần hóa tạo cơ hội.',
            'Cơ điện lạnh': 'Mảng M&E và BĐS công nghiệp tăng trưởng tốt. Năng lượng tái tạo tạo thêm động lực.',
            'Hóa chất': 'Hóa chất cơ bản phục hồi theo chu kỳ kinh tế. Hóa chất đặc thù và phân bón có biên lợi nhuận tốt hơn.',
        }
        outlook = outlooks.get(industry, 'Thị trường phục hồi từng bước, doanh nghiệp nền tảng tốt có dư địa tăng trưởng trong dài hạn.')

        # Key metrics analysis
        pe_str = f'P/E: {pe_val}' if pe_val else 'P/E: N/A (chua du lieu gia/eps)'
        if pe_val:
            if pe_val < 8:
                pe_str += ' — dinh gia re, kiem tra chat luong tai san'
            elif pe_val < 15:
                pe_str += ' — dinh gia hop ly'
            elif pe_val < 25:
                pe_str += ' — cao hon trung binh, ky vong tang truong tot'
            else:
                pe_str += ' — rat cao, can trong dinh gia'
        
        roe_str = f'ROE: {roe}%'
        if roe >= 25:
            roe_str += ' — xuat sac'
        elif roe >= 20:
            roe_str += ' — rat tot'
        elif roe >= 15:
            roe_str += ' — tot'
        elif roe >= 12:
            roe_str += ' — kha'
        elif roe >= 8:
            roe_str += ' — trung binh'
        else:
            roe_str += ' — thap'
        
        de_str = f'D/E: {de}%'
        if de < 20:
            de_str += ' — rat an toan, it su dung don bay'
        elif de < 50:
            de_str += ' — an toan'
        elif de < 80:
            de_str += ' — trung binh, can theo doi'
        elif de < 120:
            de_str += ' — cao'
        else:
            de_str += ' — rat cao, rui ro tai chinh'
        
        growth_str = f'Doanh thu QoQ'
        if growth > 0:
            growth_str += f' +{growth}% — tang truong duong'
        else:
            growth_str += f' {growth}% — suy giam'
        
        margin_str = f'Bien LN rong: {margin}%'
        if margin >= 20:
            margin_str += ' — xuat sac'
        elif margin >= 15:
            margin_str += ' — rat tot'
        elif margin >= 10:
            margin_str += ' — tot'
        elif margin >= 5:
            margin_str += ' — kha'
        else:
            margin_str += ' — thap'
        
        liquid_str = f'Current ratio: {current_ratio}'
        if current_ratio >= 2:
            liquid_str += ' — rat tot'
        elif current_ratio >= 1.5:
            liquid_str += ' — tot'
        elif current_ratio >= 1:
            liquid_str += ' — dat yeu cau'
        else:
            liquid_str += ' — yeu, thieu thanh khoan ngan han'

        # Price trend
        trend_str = f'Gia {price}k VND'
        if price_change_1y is not None:
            trend_str += f', 1 nam: {price_change_1y}%'
        
        # Build strengths, weaknesses, risks
        strengths = []
        weaknesses = []
        risks = []
        
        if roe >= 15:
            strengths.append(f'Hieu qua su dung von tot: ROE {roe}%')
        if pe_val and pe_val < 12:
            strengths.append(f'Dinh gia hap dan: P/E {pe_val}')
        if de < 30:
            strengths.append(f'Don bay thap, an toan tai chinh: D/E {de}%')
        if margin >= 10:
            strengths.append(f'Bien loi nhuan tot: {margin}%')
        if growth > 10:
            strengths.append(f'Tang truong doanh thu QoQ manh: +{growth}%')
        if current_ratio > 1.5:
            strengths.append(f'Thanh khoan tot, kha nang tra no ngan han tot')
        if gross_margin and gross_margin > 40:
            strengths.append(f'Bien lai gop cao: {gross_margin}%')
        if pe_val is not None and pe_val > roe and roe > 0:
            try:
                peg = pe_val / roe
                if peg < 1:
                    strengths.append(f'PEG ratio < 1')
            except: pass

        if roe < 10:
            weaknesses.append(f'ROE thap ({roe}%) — kha nang sinh loi kem')
        if pe_val and pe_val > 20:
            weaknesses.append(f'P/E cao ({pe_val}) — dinh gia khong re')
        if de > 80:
            weaknesses.append(f'No cao ({de}%) — ap luc tra lai dang ke')
        if growth < 0:
            weaknesses.append(f'Doanh thu giam {growth}% so voi quy truoc')
        if margin < 5 and margin > 0:
            weaknesses.append(f'Bien loi nhuan mong ({margin}%)')
        if price_change_1y and price_change_1y < -20:
            weaknesses.append(f'Hieu suat gia kem: giam {price_change_1y}% trong 1 nam')
        if current_ratio < 1:
            weaknesses.append(f'Mat kha nang thanh toan ngan han')
        
        if de > 100:
            risks.append('Rui ro vo no / tai cau truc no khi lai suat tang')
        if growth < -10:
            risks.append('Tang truong am manh — suy giam cau thi truong')
        if margin < 3:
            risks.append('Bien mong — de ton thuong truoc bien dong chi phi')
        if industry == 'Bất động sản' and de > 60:
            risks.append('Rui ro thanh khoan dac thu BDS voi don bay cao')
        if industry == 'Ngân hàng' and de > 90:
            risks.append('Ap luc no xau khi kinh te suy giam')
        for a in anomalies[:3]:
            risks.append(f'Bat thuong: {a}')
        risks.append('Rui ro thi truong chung (vĩ mo, lai suat, ty gia)')

        if not strengths:
            strengths.append('Can them du lieu de danh gia')
        if not weaknesses:
            weaknesses.append('Chua phat hiem diem yeu dang ke')
        if not risks:
            risks.append('Rui ro thi truong chung')

        # Score classification recommendation
        if score >= 85:
            rec = 'Rat hap dan — co ky vong tang truong tot, phu hop voi nha dau tu co kha nang cham soc'
        elif score >= 75:
            rec = 'Hap dan — trien vong tot, co the tich luy khi gia dieu chinh'
        elif score >= 60:
            rec = 'Tich cuc — nam giu hoac mua them voi gia tot'
        elif score >= 45:
            rec = 'Trung lap — cho tin hieu ro rang hon'
        elif score >= 30:
            rec = 'Than trong — rui ro cao, han che giai ngan moi'
        else:
            rec = 'Rui ro cao — khong khuyen nghi nam giu'

        analysis = {
            'symbol': symbol,
            'score': score,
            'verdict': verdict,
            'industry': industry,
            'key_metrics': {
                'pe': pe_str,
                'roe': roe_str,
                'debt': de_str,
                'growth_qoq': growth_str,
                'net_margin': margin_str,
                'liquidity': liquid_str,
                'price_trend': trend_str,
                'price_vs_52w_high': f'Cach dinh: {m.get("from_52w_high", 0)}%',
                'volume_ratio': f'Volume ratio: {m.get("volume_ratio", 0)}',
            },
            'industry_outlook': outlook,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'risks': risks,
            'recommendation': rec,
            'watch_points': [
                'Bao cao KQKD quy toi',
                'Bien dong lai suat / ty gia',
                'Tang truong nganh',
            ],
            'anomalies': anomalies,
        }
        enhanced.append(analysis)
    
    outname = os.path.join(OUTDIR, f'ai_batch_{i}.json')
    with open(outname, 'w') as f:
        json.dump({
            'batch': i,
            'count': len(enhanced),
            'stocks': enhanced,
            'generated_at': f'{DATE}T16:00:00+07:00'
        }, f, indent=2, ensure_ascii=False)
    print(f'Done ai_batch_{i}.json: {len(enhanced)} stocks')

print('\nAI Enhancement complete for all batches')
