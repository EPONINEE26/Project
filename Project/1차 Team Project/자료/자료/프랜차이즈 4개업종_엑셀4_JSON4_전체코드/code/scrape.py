"""브랜드별 공개 웹 표 수집. HTML 표·출처·응답 오류를 JSON으로 남긴다.

실행: python scrape.py --sources ../sources.json --output ../scraped
동적 화면/403/로그인 벽을 성공으로 위장하지 않는다. 실패는 errors.json.
수집 표의 공시일만 보고 실적연도를 지정하지 않는다. normalize_table에서
표의 2024/2025 열을 직접 확인한 값만 연도별 관측값으로 변환한다.
"""
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import argparse
import json
import re
import time

class TableParser(HTMLParser):
    """표의 tr/th/td를 행/열로 추출한다. rowspan/colspan 표는 검토 대상으로 표시."""
    def __init__(self):
        super().__init__()
        self.tables=[]; self.table=None; self.row=None; self.cell=None
        self.depth=0; self.spans=False
    def handle_starttag(self, tag, attrs):
        if tag=='table':
            self.depth+=1
            if self.depth==1:self.table=[];self.spans=False
        elif self.depth==1 and tag=='tr':self.row=[]
        elif self.depth==1 and tag in ('td','th'):
            self.cell=[]
            attributes=dict(attrs)
            self.spans |= any(attributes.get(k,'1')!='1' for k in ('rowspan','colspan'))
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if self.depth==1 and tag in ('td','th') and self.cell is not None:
            if self.row is not None:self.row.append(' '.join(' '.join(self.cell).split()))
            self.cell=None
        elif self.depth==1 and tag=='tr' and self.row is not None:
            if self.row:self.table.append(self.row)
            self.row=None
        elif tag=='table' and self.depth:
            if self.depth==1:self.tables.append({'rows':self.table,'requires_span_review':self.spans})
            self.depth-=1

def normalize_table(table, brand, industry, source_url):
    """명시적 연도 열이 있는 단순 표만 변환. 공시연도→실적연도 자동 치환 금지.

    문자열에 2024/2025가 정확히 적힌 열만 취한다. 연도 의미는 자동으로
    알 수 없어 year_basis='table_label_unreviewed'로 보존하며 분석 본문에
    자동 합치지 않는다. 검토자가 실적연도 표인지 확인해야 한다.
    """
    if table['requires_span_review'] or not table['rows']:return []
    header=table['rows'][0]
    columns={i:int(re.sub(r'년$','',v.strip())) for i,v in enumerate(header)
             if re.fullmatch(r'202[45]년?',v.strip())}
    out=[]
    for row in table['rows'][1:]:
        for i,year in columns.items():
            if i>=len(row):continue
            value=row[i].replace(',','')
            if re.fullmatch(r'\d+',value):
                out.append({'brand':brand,'industry':industry,'table_year':year,
                            'row_label':row[0],'value':int(value),'source_url':source_url,
                            'year_basis':'table_label_unreviewed','analysis_use':False})
    return out

def scrape(source):
    """HTTP 상태·내용 해시·조회시각을 남겨 수집의 재현성을 높인다."""
    url=source['url']
    req=Request(url,headers={'User-Agent':'FranchiseResearch/1.0 (educational table extraction)'})
    with urlopen(req,timeout=25) as response:
        data=response.read()
        encoding=response.headers.get_content_charset() or 'utf-8'
        html=data.decode(encoding,errors='replace')
        status=response.status
    parser=TableParser();parser.feed(html)
    if not parser.tables:raise ValueError('HTML 표 없음: 동적 렌더링 또는 접근 제한 여부 검토')
    extracted=[]
    for table in parser.tables:
        extracted.extend(normalize_table(table,source.get('brand'),source.get('industry'),url))
    return {'source':source,'http_status':status,
            'retrieved_at':datetime.now(timezone.utc).isoformat(),
            'response_sha256':hashlib.sha256(data).hexdigest(),
            'tables':parser.tables,'year_labelled_values':extracted}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sources',required=True)
    parser.add_argument('--output',default='scraped')
    args=parser.parse_args()
    sources=json.loads(Path(args.sources).read_text(encoding='utf-8'))
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    success=[];errors=[]
    for number,source in enumerate(sources):
        if not source.get('url'):continue
        try:
            result=scrape(source)
            path=output/f'tables_{number:02d}.json'
            path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            success.append({'url':source['url'],'path':path.name,'tables':len(result['tables'])})
        except (HTTPError,URLError,TimeoutError,ValueError,OSError) as exc:
            errors.append({'url':source['url'],'error':str(exc),'analysis_use':False})
        time.sleep(0.5)
    (output/'collection_log.json').write_text(json.dumps({'success':success,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'수집 성공 {len(success)} / 실패 {len(errors)}. 수집 표의 실적연도 검토 후 분석에 반영하세요.')

if __name__=='__main__':main()
