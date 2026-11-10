"""원본 보존 JSON에 지역집계의 복합 인덱스·컬럼·미수록 사유를 연결한다."""
from pathlib import Path
import json
from preserve_workbooks import save_json
ROOT=Path(__file__).resolve().parents[1]
def finalize(root=ROOT):
    missing=json.loads((root/'공식표_미수록21칸.json').read_text(encoding='utf-8'))
    for path in (root/'json').glob('*.json'):
        o=json.loads(path.read_text(encoding='utf-8'));s=next(s for s in o['sheets'] if s['name']=='03_지역집계');v=lambda col,row:s['cells'].get(f'{col}{row}',{}).get('value')
        last=max(int(''.join(filter(str.isdigit,c))) for c in s['cells']);index=[];data=[]
        for row in range(3,last+1):
            if str(v('F',row)) in ['2024','2025']:
                index.append([int(v('F',row)),v('B',row),v('A',row)]);data.append([v('C',row),v('D',row),v('E',row)])
        o['regional_aggregation']={'index_names':['year','industry','brand'],'index':index,'columns':['seoul_franchise_stores','gyeonggi_franchise_stores','national_franchise_stores'],'data':data,'description':'원본 지역집계의 값 그대로. 기존 숫자는 수정하지 않음. 신규 공시값은 가맹점 수이며 직영 제외. null은 아래 missing에서 사유와 출처 확인','missing':[m for m in missing if m['filename']==o['source_filename']]}
        save_json(o,path)
if __name__=='__main__':finalize()
