"""엑셀 읽기 전용 JSON 변환. 수식 문자열과 저장 계산값을 따로 보존한다.
실행: python convert_excel.py 엑셀파일.xlsx 출력.json
필요 패키지: openpyxl
"""
import json,hashlib,sys,datetime
from pathlib import Path
import openpyxl
from openpyxl.utils import get_column_letter

def convert(source,target):
    source=Path(source);formula=openpyxl.load_workbook(source,data_only=False);cached=openpyxl.load_workbook(source,data_only=True)
    out={'schema_version':'excel-exact-1.0','source_filename':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'description':{'data':'각 시트의 index는 엑셀 행번호, columns는 엑셀 열문자. data에는 기존 숫자·문자·수식을 그대로 저장','formula_results':'수식 셀의 저장 계산 결과. null은 엑셀에 저장 계산값이 없는 상태이며0으로 대체하지 않음','preservation':'첨부의 excel/ 안 최신 엑셀을 읽기만 함. 원본 파일 및 기존값을 수정하지 않음','blank':'빈칸은null, 원본0은숫자0, 오류값은원본오류문자열 유지'},'sheets':[]}
    def value(v):
        if isinstance(v,(datetime.datetime,datetime.date,datetime.time)):return v.isoformat()
        if isinstance(v,datetime.timedelta):return {'type':'timedelta','seconds':v.total_seconds()}
        return v
    for s in formula:
        rows=list(range(1,s.max_row+1));cols=[get_column_letter(c) for c in range(1,s.max_column+1)];data=[];results={};types={}
        for row in s.iter_rows():
            data.append([value(c.value) for c in row])
            for c in row:
                if c.data_type=='f':results[c.coordinate]=value(cached[s.title][c.coordinate].value)
                if c.value is not None:types[c.coordinate]=c.data_type
        out['sheets'].append({'name':s.title,'index':rows,'columns':cols,'data':data,'formula_results':results,'cell_types':types,'merged_ranges':[str(m) for m in s.merged_cells.ranges]})
    target=Path(target);target.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    # 저장한JSON을 다시 읽어 전체 셀의 값·수식·저장 계산결과를 대조한다.
    saved=json.loads(target.read_text(encoding='utf-8'))
    assert [s['name'] for s in saved['sheets']]==formula.sheetnames
    for ss in saved['sheets']:
        s=formula[ss['name']]
        for r,row in enumerate(ss['data'],1):
            for c,v in enumerate(row,1):assert v==value(s.cell(r,c).value)
        for coord,v in ss['formula_results'].items():assert v==value(cached[ss['name']][coord].value)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==out['source_sha256']
    return {'file':source.name,'sheets':len(out['sheets']),'cells':sum(len(s['index'])*len(s['columns']) for s in out['sheets']),'formulas':sum(len(s['formula_results']) for s in out['sheets']),'all_cells_verified':True,'original_changed':False}
if __name__=='__main__':print(convert(sys.argv[1],sys.argv[2]))
