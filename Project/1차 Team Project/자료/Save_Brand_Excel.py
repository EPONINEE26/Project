# -*- coding: utf-8 -*-
"""검증·정리된 출처 데이터 JSON에서 브랜드별 기본 형식 엑셀 5개를 생성합니다.

실행:
    pip install pandas openpyxl
    python 02_엑셀저장_브랜드별.py

이 코드는 사이트 구조의 변화로 인한 잘못된 숫자 자동 추출을 막기 위해, 동봉된
JSON의 수치를 사용합니다. 원문 HTML을 다시 스크래핑하려면 01번 스크립트를 실행하세요.
"""
import json
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / '미용실_브랜드별_2024-2025_출처자료.json'
data = json.loads(DATA_PATH.read_text(encoding='utf-8'))
FTC_URL = 'https://franchise.ftc.go.kr/'

for brand, info in data['brands'].items():
    rows = []
    for year in (2024, 2025):
        a = info['annual'][str(year)] if str(year) in info['annual'] else info['annual'][year]
        end = a.get('end')
        cancel = a.get('cancel')
        closed = None if end is None or cancel is None else end + cancel
        rows.append({
            '실적연도': year,
            '연말 총 점포 수(가맹+직영)': a.get('total'),
            '연말 가맹점 수': a.get('franchise'),
            '연말 직영점 수': a.get('direct'),
            '신규 개점 수': a.get('new'),
            '계약 종료 수': end,
            '계약 해지 수': cancel,
            '폐업·해지 합계(종료+해지)': closed,
            '가맹점 평균 월매출(만원)': a.get('monthly'),
            '신규 창업점 첫 달 월매출(만원)': None,
            '데이터 확인/공란 사유': a.get('note', ''),
            '프차몰 브랜드 페이지 URL': info['frchamall_url'],
            '점포가이드 보조 페이지 URL': info['jumpo_url'],
        })
    summary = pd.DataFrame(rows)

    regional_rows = []
    blank_reasons = info.get('blank_reasons', {})
    for year in (2024, 2025):
        for region in ('서울', '경기'):
            val = info.get('regions', {}).get(str(year), info.get('regions', {}).get(year, {})).get(region)
            reason = ''
            if val is None:
                reason = blank_reasons.get(str(year), blank_reasons.get(year, ''))
                if not reason:
                    reason = f'{year}년 {region} 점포 수를 확인 가능한 연도별 공개 표에서 찾지 못해 공란(0이 아님).'
            regional_rows.append({
                '실적연도': year, '지역': region,
                '연말 점포 수(가맹+직영)': val,
                '출처 사이트': '점포가이드(JUMPO.SHOP; 공정위 정보공개서 기반 요약)',
                '출처 URL': info['jumpo_url'], '공란 사유/기준': reason
            })
    regions = pd.DataFrame(regional_rows)

    sources = pd.DataFrame([
        {'자료 유형':'주요 브랜드 출처','사이트명':'프차몰 (FCHAMALL)','페이지/공시 기준':'각 브랜드 상세 페이지; 2025년 정보공개서 요약',
         '사용 목적':'브랜드 요약, 2024년 수치 교차 확인','정확한 URL':info['frchamall_url'],
         '한계/메모':'브랜드 페이지는 공정위 정보공개서 기반 수치를 요약하며, 지역별 연도별 시계열 전체를 제공하지 않음.'},
        {'자료 유형':'보조 출처','사이트명':'점포가이드 (JUMPO.SHOP)','페이지/공시 기준':info['jumpo_date'],
         '사용 목적':'연도별 신규 개점·계약 종료·해지, 서울/경기 연말 점포 수 확인','정확한 URL':info['jumpo_url'],
         '한계/메모':'공정위 정보공개서 원자료를 재정리한 2차 요약 사이트. 링크된 해당 브랜드 페이지에 실제로 표시된 연도/수치만 사용.'},
        {'자료 유형':'원자료 검색 포털','사이트명':'공정거래위원회 가맹사업거래 정보공개서','페이지/공시 기준':'공식 일반 검색 포털',
         '사용 목적':'보조 사이트가 출처로 밝히는 원자료 기관','정확한 URL':FTC_URL,
         '한계/메모':'일반 포털 링크이며 브랜드·연도 개별 문서로 직접 연결되는 주소가 아님. 원문은 브랜드명/등록번호로 검색 필요.'},
        {'자료 유형':'산정 기준','사이트명':'신규 개점 수','페이지/공시 기준':'해당 실적연도','사용 목적':'새로 개점한 가맹점 수(누적이 아님)','정확한 URL':'','한계/메모':'연말 전체 점포 수와 별도 지표.'},
        {'자료 유형':'산정 기준','사이트명':'폐업·해지 합계','페이지/공시 기준':'계약 종료 + 계약 해지','사용 목적':'공시상 계약 종료/해지 합계','정확한 URL':'','한계/메모':'물리적 폐점과 항상 동일하지 않으므로 각각의 세부 항목도 별도 표기.'},
        {'자료 유형':'산정 기준','사이트명':'가맹점 평균 월매출','페이지/공시 기준':'공시된 가맹점 평균','사용 목적':'만원 단위 평균 월매출','정확한 URL':'','한계/메모':'신규 창업 첫 달 매출/순이익이 아님. 첫 달 매출은 공개자료 미확인으로 공란.'},
        {'자료 유형':'자료 공란','사이트명':'미확인 연도/지역 값','페이지/공시 기준':'2024-2025','사용 목적':'수치가 공개표에서 확인되지 않은 항목','정확한 URL':'','한계/메모':'공란은 0이 아님. 공란 사유는 해당 시트에 기재.'},
    ])

    path = BASE / info['filename']
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        summary.to_excel(writer, sheet_name='연도별 요약', index=False)
        regions.to_excel(writer, sheet_name='서울경기 점포수', index=False)
        sources.to_excel(writer, sheet_name='출처와 기준', index=False)
        for sheet in writer.book.worksheets:
            sheet.freeze_panes = 'A2'
            sheet.auto_filter.ref = sheet.dimensions
            for cell in sheet[1]:
                cell.font = cell.font.copy(bold=True)
            for column_cells in sheet.columns:
                max_len = max(len(str(c.value or '')) for c in column_cells)
                col_letter = column_cells[0].column_letter
                sheet.column_dimensions[col_letter].width = min(max(max_len + 2, 12), 60)
            for row in sheet.iter_rows():
                for cell in row:
                    cell.alignment = cell.alignment.copy(vertical='top', wrap_text=True)
    print(f'저장: {path.name}')
