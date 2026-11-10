# -*- coding: utf-8 -*-
"""두 작업을 순서대로 실행합니다.
1) 브랜드별 출처 페이지의 원문 HTML/텍스트 스크래핑
2) 제공된 검증 데이터 JSON으로 브랜드별 엑셀 5개 저장

주의: 1번 스크래핑은 원문 저장용입니다. 연도별 값을 새로 자동추정하지 않으며,
엑셀은 검토된 JSON 데이터로 생성됩니다. 페이지 변경 시 값을 검토한 뒤 JSON을 수정해야 합니다.
"""
import subprocess, sys
from pathlib import Path
base = Path(__file__).resolve().parent
for script in ('01_웹스크래핑_원문수집.py', '02_엑셀저장_브랜드별.py'):
    print(f'실행: {script}')
    subprocess.run([sys.executable, str(base / script)], check=True)
print('완료: 원문 HTML 수집 및 브랜드별 엑셀 5개 저장')
