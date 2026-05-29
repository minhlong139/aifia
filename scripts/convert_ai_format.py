#!/usr/bin/env python3
"""
Convert ai_batch files to format expected by ai_upload.py
"""
import json, os, sys, glob

DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-05-23"
INDIR = f"data/history/{DATE}"

for i in range(10):
    fpath = os.path.join(INDIR, f'ai_batch_{i}.json')
    if not os.path.exists(fpath):
        continue
    
    with open(fpath) as f:
        data = json.load(f)
    
    stocks = data.get('stocks', [])
    converted = []
    for s in stocks:
        km = s.get('key_metrics', {})
        
        # Build commentary from our analysis
        parts = [
            f"Ngành: {s.get('industry', 'Khác')}.",
            f"Điểm mạnh: {'; '.join(s.get('strengths', []))}.",
            f"Điểm yếu: {'; '.join(s.get('weaknesses', []))}.",
            f"{s.get('outlook', '')}",
            f"Khuyến nghị: {s.get('recommendation', '')}."
        ]
        commentary = ' '.join(parts)
        
        converted.append({
            'symbol': s.get('symbol', ''),
            'ai_commentary': commentary,
            'strengths': s.get('strengths', []),
            'weaknesses': s.get('weaknesses', []),
            'outlook': s.get('outlook', ''),
            'key_risks': s.get('risks', []),
            'score': s.get('score', 0),
            'verdict': s.get('verdict', ''),
            'industry': s.get('industry', ''),
            'recommendation': s.get('recommendation', ''),
            'watch_points': s.get('watch_points', []),
        })
    
    # Rewrite with correct format
    with open(fpath, 'w') as f:
        json.dump({
            'batch': i,
            'count': len(converted),
            'enhanced_analyses': converted
        }, f, indent=2, ensure_ascii=False)
    print(f'Converted ai_batch_{i}.json: {len(converted)} stocks')

print('Done')
