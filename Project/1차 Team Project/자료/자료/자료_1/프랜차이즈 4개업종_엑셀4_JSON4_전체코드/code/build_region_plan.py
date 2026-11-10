"""2024·2025 지역집계에서 원본 빈칸만 공정위 같은 실적연도의 가맹점 수로 연결한다.
실행: python code/build_region_plan.py --original original --evidence evidence --output 보완계획.json
공시 연도와 실적 연도를 혼동하지 않으며, 2025 표가 없으면 2024를 복사하지 않는다.
"""
from pathlib import Path
import json,argparse
from zipfile import ZipFile
from preserve_workbooks import read_cells,save_json

def build(original,evidence):
    plan=[];missing=[];conflicts=[]
    for path in sorted(Path(original).glob('*.xlsx')):
        industry=path.name.split('_')[1];patches=[]
        with ZipFile(path) as z:s=next(s for s in read_cells(z) if s['name']=='03_지역집계')
        cells=s['cells'];v=lambda col,row:cells.get(f'{col}{row}',{}).get('value')
        last=max(int(''.join(filter(str.isdigit,c))) for c in cells)
        if industry in ['이미용','커피','편의점']:
            for row in range(3,last+1):
                if str(v('F',row)) not in ['2024','2025']:continue
                year=int(v('F',row));brand=v('A',row);p=json.loads((Path(evidence)/(brand+'.json')).read_text(encoding='utf-8'))
                t=p['latest_tables'][6]['rows'];years=[int(x.replace('년','')) for x in t[0][1:]];j=years.index(year) if year in years else None
                for col,region in [('C','서울'),('D','경기'),('E','전체')]:
                    r=next(r for r in t[2:] if r[0]==region);raw=r[2+3*j] if j is not None and len(r)>2+3*j else ''
                    value=int(raw.replace(',','')) if raw.strip() else None
                    if v(col,row) is not None:
                        if value is not None and value!=v(col,row):conflicts.append({'file':path.name,'cell':col+str(row),'year':year,'brand':brand,'original_value':v(col,row),'official_value':value,'action':'기존값 보존, 수정 안 함','source_url':p['latest_url']})
                        continue
                    item={'sheet':'03_지역집계','cell':col+str(row),'brand':brand,'year':year,'source':{'publisher':'공정거래위원회','url':p['latest_url'],'section':f'가맹점 및 직영점 현황 / {year}년 / {region} / 가맹점수','retrieved_date':'2026-10-22'}}
                    if value is None:
                        missing.append({'filename':path.name,**item,'region':'전국' if region=='전체' else region,'reason':f'확인한 최신 공시의 {year}년 가맹점수 표가 없거나 해당 값이 비어 있음. 직영 포함 현재 매장 수·2024 수치로 대체하지 않음','latest_store_table_year':max(years)})
                    else:patches.append({**item,'value':value,'basis':f'{year}년 말 가맹점 수. 직영점 제외. 기존 원본 설명문은 수정하지 않음'})
        plan.append({'filename':path.name,'industry':industry,'patches':patches})
    return plan,missing,conflicts
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--original',default='original');p.add_argument('--evidence',default='evidence');p.add_argument('--output',default='보완계획.json');a=p.parse_args()
    plan,missing,conflicts=build(a.original,a.evidence);save_json(plan,a.output);save_json(missing,Path(a.output).parent/'공식표_미수록21칸.json');save_json(conflicts,Path(a.output).parent/'기존입력값_공시차이_보존.json')
    print('빈칸 보완',sum(len(i['patches']) for i in plan),'공식표 미수록',len(missing),'기존입력 공시차이',len(conflicts))
