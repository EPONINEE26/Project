"""원본의 빈 셀만 입력한다. 기존 상수·수식·서식·ZIP 부품을 재작성하지 않는다.

표준라이브러리만 사용한다. pandas/openpyxl로 파일 전체를 저장하지 않으므로
원본의 차트·필터·인쇄 설정·시트 구조 등도 그대로 유지된다.
실행: python code/preserve_workbooks.py --original 원본 --plan 보완계획.json --output 엑셀 --json-output JSON
"""
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
import argparse,hashlib,json,re,shutil,posixpath
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
CELL=re.compile(r'<c\b[^>]*?(?:/>|>[\s\S]*?</c>)')

def save_json(value,path):
    """한글 UTF-8 및 엄격한 JSON으로 저장한다. NaN/Infinity를 허용하지 않는다."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def sheet_paths(z):
    """표시 시트명을 실제 worksheet XML 경로에 연결한다. 시트 순서를 유지한다."""
    rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    targets={r.attrib['Id']:r.attrib['Target'] for r in rels}
    result={}
    for s in ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets',NS):
        target=targets[s.attrib['{'+REL+'}id']]
        result[s.attrib['name']]=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
    return result

def read_cells(z):
    """수식은 수식 문자열 그대로, 숫자는 숫자 그대로 읽는다. 캐시는 별도로 보존한다."""
    shared=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        shared=[''.join(t.text or '' for t in si.iter('{'+NS['s']+'}t')) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
    sheets=[]
    for name,path in sheet_paths(z).items():
        root=ET.fromstring(z.read(path));cells={}
        for c in root.findall('.//s:sheetData/s:row/s:c',NS):
            coord=c.attrib['r'];v=c.find('s:v',NS);f=c.find('s:f',NS);kind=c.attrib.get('t','n')
            raw=v.text if v is not None else None
            if kind=='s' and raw is not None:value=shared[int(raw)]
            elif kind=='inlineStr':value=''.join(t.text or '' for t in c.findall('.//s:t',NS))
            elif raw is None:value=None
            elif kind=='b':value=raw=='1'
            elif kind in ('str','e'):value=raw
            else:
                try:value=int(raw)
                except ValueError:value=float(raw)
            cell={'value':'='+ (f.text or '') if f is not None else value,'type':'formula' if f is not None else kind,'style_id':c.attrib.get('s','0')}
            if f is not None:cell['original_cached_value']=value
            cells[coord]=cell
        dim=root.find('s:dimension',NS)
        sheets.append({'name':name,'dimension':dim.attrib['ref'] if dim is not None else None,'cells':cells})
    return sheets

def _raw_cells(text):
    return {re.search(r'\br="([A-Z]+\d+)"',m.group()).group(1):m.group() for m in CELL.finditer(text)}

def _blank(cell_xml):
    node=ET.fromstring('<root xmlns="'+NS['s']+'">'+cell_xml+'</root>')[0]
    return node.find('s:f',NS) is None and node.find('s:v',NS) is None and not ''.join(node.itertext()).strip()

def fill_only_blanks(original,output,patches,authored=None):
    """허용 목록의 빈칸만 수정한다. 이미 값/수식이 있으면 즉시 중단한다.

    authored가 있으면 artifact-tool로 입력·내보낸 값이 계획과 같은지 대조한다.
    최종 파일은 원본 ZIP 부품을 복사하고, 허용 셀의 내용에만 <v>를 삽입한다.
    기존 셀 시작 태그(스타일), 다른 셀, 시트 밖 모든 부품 바이트는 유지한다.
    """
    original=Path(original);output=Path(output)
    if original.resolve()==output.resolve():raise ValueError('원본 덮어쓰기 금지')
    output.parent.mkdir(parents=True,exist_ok=True)
    if not patches:shutil.copyfile(original,output);return
    replacements={}
    with ZipFile(original) as z:
        paths=sheet_paths(z)
        authored_sheets={}
        if authored:
            with ZipFile(authored) as a:authored_sheets={s['name']:s['cells'] for s in read_cells(a)}
        for patch in patches:
            part=paths[patch['sheet']];text=replacements.get(part,z.read(part).decode('utf-8'));cells=_raw_cells(text)
            coord=patch['cell'];old=cells.get(coord)
            if old is None or not _blank(old):raise ValueError(f'원본 빈 셀 아님: {patch["sheet"]}!{coord}')
            value=patch['value']
            if not isinstance(value,(int,float)) or isinstance(value,bool):raise ValueError('숫자 보완값만 허용')
            if authored and authored_sheets[patch['sheet']][coord]['value']!=value:raise ValueError('작성 결과와 계획 불일치')
            opening=re.match(r'<c\b[^>]*',old).group().rstrip('/ ')
            # 원본 빈 셀에 type 속성이 없는 숫자 입력만 사용한다.
            if re.search(r'\bt="(?:s|inlineStr|str|b|e)"',opening):raise ValueError('빈칸 타입을 바꾸지 않도록 중단')
            new=opening+'><v>'+str(value)+'</v></c>'
            text=text.replace(old,new,1);replacements[part]=text
        with ZipFile(output,'w') as out:
            for info in z.infolist():out.writestr(info,replacements[info.filename].encode('utf-8') if info.filename in replacements else z.read(info.filename))
    verify_preservation(original,output,patches)

def verify_preservation(original,output,patches):
    """새 보완 셀을 원래 빈 태그로 복원하면 원본 XML과 바이트까지 같아야 한다."""
    with ZipFile(original) as a,ZipFile(output) as b:
        assert a.namelist()==b.namelist(),'ZIP 부품 목록 변경'
        paths=sheet_paths(a);allowed={}
        for p in patches:allowed.setdefault(paths[p['sheet']],[]).append(p['cell'])
        for part in a.namelist():
            old=a.read(part);new=b.read(part)
            if part not in allowed:assert old==new,'수정 금지 부품 변경: '+part;continue
            ot=old.decode();nt=new.decode();oc=_raw_cells(ot);nc=_raw_cells(nt)
            for coord in allowed[part]:nt=nt.replace(nc[coord],oc[coord],1)
            assert nt==ot,'허용 셀 밖 XML 변경: '+part
        before={s['name']:s for s in read_cells(a)};after={s['name']:s for s in read_cells(b)}
        assert list(before)==list(after),'시트명/순서 변경'
        changed=[]
        for name,s in before.items():
            for coord,c in s['cells'].items():
                now=after[name]['cells'][coord]
                if c['value'] is not None:assert c==now,f'기존 값/수식/스타일 변경: {name}!{coord}'
                elif c['value']!=now['value']:changed.append((name,coord))
        assert set(changed)=={(p['sheet'],p['cell']) for p in patches}
        return {'existing_nonblank_cells_changed':0,'existing_formulas_changed':0,'style_or_native_parts_changed':0,'filled_cells':len(changed),'source_sha256':hashlib.sha256(Path(original).read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(Path(output).read_bytes()).hexdigest()}

def export_json(xlsx,output,patches,original_name):
    """엑셀의 시트명·행열·모든 기존 값·수식을 좌표 인덱스 JSON으로 내보낸다."""
    with ZipFile(xlsx) as z:sheets=read_cells(z)
    obj={'schema_version':'original-preserved-1.0','source_filename':original_name,'description':{'cells':'각 시트의 cells는 A1 좌표 인덱스. value는 원본 값 또는 수식 문자열 그대로','preservation':'기존 숫자(0 포함)·문자·수식·시트 순서 유지. changes 목록의 원래 빈 셀만 입력','years':'2024·2025 요청 범위. 원본 범위연도·2026 표기는 변경하지 않고 별도 오류 내역에 기록','formula_cache':'수식 캐시는 원본 그대로 보존. Excel에서 전체 재계산하면 보완값을 반영. 기존 #REF! 수식도 수정하지 않음','units':'01 시트 비용과05 시트 매출은 원. 02 시트는 원본 단위 열을 유지하므로 이미용 보완값은 천원'},'sheets':sheets,'changes':patches}
    save_json(obj,output)
    return obj

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--original',default='원본');p.add_argument('--plan',default='보완계획.json');p.add_argument('--output',default='엑셀');p.add_argument('--json-output',default='JSON');p.add_argument('--authored');args=p.parse_args()
    reports=[]
    for item in json.loads(Path(args.plan).read_text(encoding='utf-8')):
        name=item['filename'];source=Path(args.original)/name;target=Path(args.output)/name
        fill_only_blanks(source,target,item['patches'],Path(args.authored)/name if args.authored and item['patches'] else None)
        reports.append({'filename':name,**verify_preservation(source,target,item['patches'])})
        export_json(target,Path(args.json_output)/(Path(name).stem+'.json'),item['patches'],name)
    save_json(reports,Path(args.output).parent/'원본보존_검증결과.json');print(json.dumps(reports,ensure_ascii=False,indent=2))
