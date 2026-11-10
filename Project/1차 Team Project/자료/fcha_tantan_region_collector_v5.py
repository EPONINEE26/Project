# -*- coding: utf-8 -*-
"""프차탄탄 6번 API: 전국/전 업종, 연도별 고유 brandMnno 순차 수집.
입력: 브랜드관리번호_연도별_업종별_정리.zip (동일 폴더)
키: .env 의 DATA_GO_KR_KEY
최초에는 --test 로 실제 API 응답을 검증한 후 --run 사용.
"""
import argparse, csv, io, json, os, sqlite3, time, zipfile, random
from collections import defaultdict
from pathlib import Path
import requests
from dotenv import load_dotenv
from urllib.parse import unquote

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')
URL = 'https://apis.data.go.kr/1130000/FftcBrandFrcsDmsStusService/getbrandFrcsDmsstus2'
# API 상세 페이지에서 확인한 실제 Request URL의 경로가 다르면 --url 옵션으로 입력하세요.
ZIP = BASE / '브랜드관리번호_연도별_업종별_정리.zip'
OUT = BASE / 'data' / '브랜드지역현황_v5'

def load_ids():
    result = defaultdict(dict)
    with zipfile.ZipFile(ZIP) as z:
        for name in z.namelist():
            if not name.lower().endswith('.csv') or not name[:4].isdigit():
                continue
            for row in csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig'))):
                year = str(row.get('기준연도') or name[:4]).strip()
                bid = str(row.get('brandMnno') or '').strip()
                if not bid or year not in ('2024','2025','2026'):
                    continue
                item = result[year].setdefault(bid, {'brandMnno':bid,'year':year,'brandNm':row.get('브랜드명',''),'categories':[]})
                cat = [row.get('업종대분류',''),row.get('업종중분류','')]
                if cat not in item['categories']:
                    item['categories'].append(cat)
    return result

def parse(body):
    try:
        obj = json.loads(body)
    except ValueError as exc:
        raise RuntimeError('JSON이 아닌 응답입니다. 실제 요청 URL 및 인증/응답형식을 확인하세요.') from exc
    response = obj.get('response', obj)
    if not isinstance(response, dict):
        raise RuntimeError('응답 response 형식이 다릅니다.')
    header = response.get('header',{})
    if isinstance(header,dict):
        code = header.get('resultCode')
        if code is not None and str(code) not in ('0','00'):
            raise RuntimeError('API 응답 오류 코드: '+str(code))
    body = response.get('body',response)
    if not isinstance(body,dict):
        raise RuntimeError('응답 body 형식이 다릅니다.')
    total = body.get('totalCount')
    total = int(total) if total not in (None,'') else None
    items = body.get('items',[])
    if isinstance(items,dict): items = items.get('item',[])
    if items is None: items=[]
    if isinstance(items,dict): items=[items]
    if not isinstance(items,list) or any(not isinstance(x,dict) for x in items):
        raise RuntimeError('items 구조가 예상과 다릅니다.')
    return items,total

def get_page(session,url,key,year,bid,page,delay):
    params={'serviceKey':key,'pageNo':page,'numOfRows':100,'resultType':'json','jngBizCrtraYr':year,'brandMnno':bid}
    for attempt in range(5):
        try:
            r=session.get(url,params=params,timeout=(15,70))
            if r.status_code==200:
                rows,total=parse(r.text)
                return rows,total
            if r.status_code in (401,403):
                import re
                codes = re.findall(
                    r'SERVICE_[A-Z_]+|PERMISSION_DENIED|NO_OPENAPI_SERVICE_ERROR',
                    r.text)
                print("HTTP 상태:", r.status_code)
                print("응답 형식:", r.headers.get("Content-Type"))
                print("서버 오류 코드:", codes or "표준 오류 코드 없음")

                raise RuntimeError(f'인증/권한 오류 HTTP {r.status_code}')
            if r.status_code not in (429,500,502,503,504):
                raise RuntimeError(f'HTTP {r.status_code}: URL·파라미터 확인')
        except (requests.Timeout,requests.ConnectionError):
            pass
        if attempt==4: raise RuntimeError('연결 오류 또는 서버 호출 제한. 다음 실행에 이어받기')
        time.sleep(min(60,3*2**attempt)+random.random())
    raise RuntimeError('요청 실패')

def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--test',action='store_true',help='2024년 한 브랜드의 첫 페이지로 응답 구조 검증')
    g.add_argument('--run',action='store_true',help='전 연도 전체 브랜드 수집')
    p.add_argument('--url',required=True,help='공공데이터포털에서 검증한 실제 상세 기능 URL (인증키·쿼리 제외)')
    p.add_argument('--delay',type=float,default=0.8)
    p.add_argument('--max-calls',type=int,default=0,help='이번 실행에서 최대 API 호출 횟수 (0=제한 없음)')
    a=p.parse_args()
    if a.delay<0.3: p.error('delay는 0.3초 이상 권장')
    if not ZIP.exists(): p.error(f'입력 ZIP 없음: {ZIP}')
    key = unquote(os.getenv('DATA_GO_KR_KEY','').strip())
    if not key: p.error('.env에 DATA_GO_KR_KEY를 설정하세요. 채팅에 키를 올리지 마세요.')
    all_ids=load_ids()
    for year in ('2024','2025','2026'):
        print(f'{year}: 중복 제거 후 {len(all_ids[year]):,}개 브랜드',flush=True)
    with requests.Session() as session:
        if a.test:
            year='2024'; bid=next(iter(all_ids[year]))
            try:
                rows,total=get_page(session,a.url,key,year,bid,1,a.delay)
            except Exception as exc:
                print('시험 호출 실패:',str(exc)); return
            print('시험 호출 성공:',year,bid,'첫 페이지',len(rows),'건','totalCount',total)
            print('응답 필드:',list(rows[0]) if rows else '(빈 결과: 다른 브랜드도 검증 필요)')
            return
        OUT.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(OUT/'progress.sqlite3')
        db.execute('CREATE TABLE IF NOT EXISTS completed (year TEXT, brand TEXT, count INTEGER, PRIMARY KEY(year,brand))')
        db.execute('CREATE TABLE IF NOT EXISTS results (year TEXT, brand TEXT, page INTEGER, position INTEGER, payload TEXT, PRIMARY KEY(year,brand,page,position))')
        db.commit()
        calls=0
        try:
            for year in ('2024','2025','2026'):
                done=0
                for bid in all_ids[year]:
                    if db.execute('SELECT 1 FROM completed WHERE year=? AND brand=?',(year,bid)).fetchone():
                        continue
                    # 페이지별 커밋. 브랜드 단위 완료 전까지 다음 실행에서 재조회 가능
                    page=1; count=0; expected=None
                    while True:
                        if a.max_calls and calls>=a.max_calls:
                            print('이번 실행 호출 상한 도달. --run 으로 이어받으세요.'); return
                        rows,total=get_page(session,a.url,key,year,bid,page,a.delay)
                        calls+=1
                        if expected is not None and total is not None and expected!=total:
                            raise RuntimeError('수집 도중 totalCount 변경')
                        if total is not None: expected=total
                        with db:
                            for pos,row in enumerate(rows):
                                db.execute('INSERT OR REPLACE INTO results VALUES (?,?,?,?,?)',(year,bid,page,pos,json.dumps(row,ensure_ascii=False)))
                        count+=len(rows)
                        if (expected is not None and count>=expected) or not rows:
                            break
                        page+=1
                        if page>1000: raise RuntimeError('페이지 한도 초과')
                        time.sleep(a.delay)
                    with db:
                        db.execute('INSERT OR REPLACE INTO completed VALUES (?,?,?)',(year,bid,count))
                    done+=1
                    if done%50==0: print(f'{year} 이번 실행 완료 {done:,}개 / 호출 {calls:,}회',flush=True)
                    time.sleep(a.delay)
                print(year,'전체 브랜드 완료',flush=True)
        except KeyboardInterrupt:
            print('\n중단됨. 진행 상황은 SQLite에 보존. 재실행 시 완료된 브랜드 건너뜀.')
        except Exception as exc:
            print('수집 중지:',str(exc),'\n진행 상황 보존. API 조건을 확인한 뒤 재실행하세요.')
        finally:
            db.close()
            print('저장 위치:',OUT)

if __name__=='__main__': main()


