# -*- coding: utf-8 -*-
"""
프차탄탄 공공데이터 수집기 — 다운로드 안내 + API 수집 + Selenium 표 추출
확인일: 2026-10-19 / 권장: Python 3.11 이상, Windows, Chrome

[처음 실행]
1. 이 파일을 C:\\workspace\\fcha_data 폴더에 저장한다.
2. 그 폴더를 VS Code로 열고 터미널에서 아래 명령을 각각 실행한다.
   python -m pip install -U requests selenium pandas lxml python-dotenv
   python fcha_tantan_collector.py
3. 메뉴 1에서 수집 순서를 읽고, 2(API) 또는 3(Selenium)을 선택한다.
   안내만 보려면: python fcha_tantan_collector.py --guide

[정확한 범위]
API: 본인이 활용신청하고 시험 호출한 Request URL로 전체 페이지를 수집한다.
Selenium: 사람이 원하는 공개 화면/연도를 선택한 뒤 HTML 표를 자동 추출한다.
사이트마다 다른 검색·로그인·다운로드 버튼을 무작정 누르는 자동화는 아니다.
PDF/이미지/캔버스는 표 추출 대상이 아니다. 원본 다운로드를 이용한다.
실제 API 인증키와 공개 화면 접근이 필요한 부분은 사용자 PC에서 확인해야 한다.
이 파일 자체에 프랜차이즈 실데이터나 인증키가 들어 있지는 않다.

[저장]
파일 옆 data/실행일시_작업명/ 아래 CSV, JSON, 원본, 출처/완료상태를 저장한다.
여러 번 실행해도 이전 수집 결과를 덮어쓰지 않는다. CSV는 엑셀용 UTF-8 BOM.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from io import StringIO
from pathlib import Path
from urllib.parse import quote, quote_plus, unquote, unquote_plus, urlsplit, urlunsplit
import os
import random
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
SERVICE_KEY = os.getenv("DATA_GO_KR_KEY", "").strip()


ROOT = Path(__file__).resolve().parent / "data"

DATASETS = [
    ("1. 브랜드 기본정보·업종·브랜드관리번호",
        "공정거래위원회_가맹정보_브랜드 목록 정보 제공 서비스",
        "https://www.data.go.kr/data/15125467/openapi.do"),

    ("2. 브랜드별 가맹점 수·평균매출 등",
        "공정거래위원회_가맹정보_브랜드별 가맹점 현황 제공 서비스",
        "https://www.data.go.kr/data/15110241/openapi.do"),

    ("3. 브랜드별 창업비용",
        "공정거래위원회_가맹정보_브랜드별 창업 금액 현황 제공 서비스",
        "https://www.data.go.kr/data/15110265/openapi.do"),

    ("4. 지역·업종 평균매출(브랜드별 매출 아님)",
        "공정거래위원회_가맹정보_지역별 업종별 평균 매출액 현황 제공 서비스",
        "https://www.data.go.kr/data/15110302/openapi.do"),

    ("5. 전국 실제 매장 위치·업종 보조자료",
        "소상공인시장진흥공단_상가(상권)정보_API",
        "https://www.data.go.kr/data/15012005/openapi.do"),

    ("6. 브랜드별 지역별 가맹점·직영점 현황 (브랜드관리번호 필요)",
        "공정거래위원회_가맹정보_브랜드별 지역별 가맹점 현황 제공 서비스",
        "https://www.data.go.kr/data/15125490/openapi.do"),
    ("7. 주요 업종별 가맹점 수·개폐점률",
        "공정거래위원회_가맹정보 주요 업종별 가맹점수, 개폐점률 현황 제공 서비스",
        "https://www.data.go.kr/data/15157660/openapi.do"),
]
GUIDE = """
프차탄탄 수집 순서
============================================================
① 브랜드 기본정보 → ② 가맹점·매출 → ③ 창업비용 → ④ 서울 지역자료
우선 업종: 카페(공시 분류의 '커피' 포함), 치킨, 편의점, 미용실.
연도: 2024, 2025를 각각 조회한다. 제공되지 않는 연도는 미공개로 남긴다.
공시 기준연도·회계연도·수집연도를 서로 같은 값으로 취급하지 않는다.

A. 공공데이터포털에서 파일 받기
------------------------------------------------------------
1. https://www.data.go.kr 접속 → 필요한 경우 회원가입·로그인.
2. 아래 데이터셋 이름으로 검색. '파일데이터'와 '오픈API'를 구분한다.
3. 파일데이터: 상세페이지에서 설명·기준연도·컬럼 정의·단위 확인.
4. 다운로드(또는 제공기관 바로가기) → CSV/XLSX/ZIP 원본을 그대로 보관.
   예: 소상공인시장진흥공단 상가(상권)정보 → 해당 시점 서울 자료 선택.
   현재 매장 명단 하나로 과거 2024·2025 개업/폐업을 복원할 수는 없다.
5. 원본 파일명, 상세페이지 URL, 기준일, 다운로드일, 금액단위를 기록한다.

B. 오픈API로 자료 받기 — 이 프로그램 메뉴 2
------------------------------------------------------------
1. 아래 API 상세페이지 → '활용신청' → 목적: 프랜차이즈 비교 학습용.
2. 승인 여부를 확인하고, 마이페이지의 해당 활용신청 내역에서 인증정보 확인.
   화면 메뉴명은 포털 개편에 따라 달라질 수 있다.
3. 상세페이지의 '활용명세/상세기능'에서 조회 기능을 펼친다.
4. Try it out/실행 기능에서 명세에 나온 필수 입력값을 채운다.
   연도 항목 이름은 yr 또는 jngBizCrtrYr 등 API마다 다를 수 있다.
   pageNo=1, numOfRows=100을 권장. 응답형식 선택이 있으면 JSON 선택.
   업종코드 등 필수 조건은 해당 명세의 실제 코드값을 사용한다.
5. Execute/실행 후 정상 응답을 확인하고 'Request URL' 전체를 복사한다.
   상세페이지 주소(openapi.do)가 아니라 실제 조회 요청 URL이다.
6. 메뉴 2 → 작업명 입력 → 복사한 URL 붙여넣기.
   .env의 DATA_GO_KR_KEY를 자동 사용한다. 없을 때만 인증키를 입력한다.
   URL에 포함된 기존 키는 사용하지 않는다. Encoding/Decoding 모두 지원한다.
   키는 화면에 표시하거나 파일에 저장하지 않는다. 채팅으로 보내지 않는다.
7. 프로그램이 pageNo만 증가시키며 수집한다. 연도·업종 등 조건은 유지한다.
8. 다음 연도·다른 업종은 포털에서 시험 호출한 뒤 메뉴 2로 다시 수집한다.
   예: 브랜드현황_2024, 브랜드현황_2025, 서울상가_2025_기준일확인.
9. manifest.json의 complete와 row_count, expected_total을 확인한다.
   실패한 작업은 부분수집이다. 같은 작업명을 입력하고 기존 폴더를 선택하면 이어받는다.

C. Selenium으로 공개 웹 표 수집 — 메뉴 3
------------------------------------------------------------
1. Chrome 설치 후 메뉴 3 선택. 드라이버는 Selenium Manager가 관리한다.
   최초 실행 때 드라이버 다운로드 인터넷 연결이 필요할 수 있다.
2. 시작 URL 입력. 기본값은 가맹사업정보제공시스템이다.
   https://franchise.ftc.go.kr 에서 정보공개서 열람 → 브랜드 검색.
   공개 화면에서 원하는 브랜드·기준연도·지역을 직접 선택한다.
3. 터미널로 돌아와 Enter → 열린 탭 번호 선택.
4. 화면에 표시되는 HTML 표를 CSV/JSON으로 자동 추출한다.
   iframe 내부 표도 수집하며 병합셀은 pandas로 펼친다.
   브라우저 화면의 표가 원본 데이터인지, 항목 설명 표인지 직접 확인한다.
5. 페이지가 여러 개면 다음 화면을 직접 연 뒤 Enter로 추가 수집한다.
   다른 브랜드 상세 화면으로 이동해도 같은 방식으로 반복할 수 있다.
6. 공개 표가 없거나 PDF뿐이라면 다운로드 원본을 이용한다.
   보안문자·접근제한이 나타나면 수집을 중단하고 공식 다운로드/API를 쓴다.
   사이트별 검색·페이지 이동 버튼 자동 클릭은 포함하지 않았다.

D. 프차탄탄 DB로 가공할 때 꼭 지킬 것
------------------------------------------------------------
1. 브랜드관리번호가 있으면 브랜드 ID로 사용. 없으면 회사명+브랜드명으로
   임시 매칭하고 사람이 확인. 이름만 비슷하다고 같은 브랜드로 합치지 않는다.
2. 브랜드/브랜드연도통계/브랜드지역통계/지역업종통계를 따로 보관한다.
   브랜드지역통계가 없는 API에서 서울 값을 임의로 만들지 않는다.
3. 전국 브랜드 평균매출을 '서울 브랜드 매출'로 표시하지 않는다.
   지역별 업종 평균매출도 특정 브랜드의 서울 매출이 아니다.
4. 원본의 신규등록·계약종료·계약해지·명의변경은 각각 보관한다.
   종료+해지는 '계약종료·해지 합계'로 표시. 실제 폐업 수라고 단정하지 않는다.
5. 연간 평균매출인지 명세에서 확인 → 금액단위를 원 단위로 통일한 다음
   연매출÷12를 '월평균 환산매출'로 표시한다. 실제 월별 매출과 다르다.
6. 자료가 없는 값은 null/빈칸. 원본 0은 그대로 남기고 0의 의미를 확인한다.
   이 자료만으로 매장별 홀/배달 매출이나 점주 순이익을 산출하지 않는다.
7. 서울 실데이터, 서울 외 더미데이터는 is_dummy와 source로 구분한다.
   이번 수집기는 실데이터 원본만 저장한다. 더미를 실측 데이터에 섞지 않는다.
8. 매장 상호에 브랜드명이 포함됐다는 이유만으로 가맹점으로 확정하지 않는다.
9. 메인: 업종별 브랜드 요약 / bview: 브랜드 상세·출처·기준연도 /
   bcompare: 같은 연도·지역범위·금액단위끼리 비교한다.

권장 가공 컬럼 (공통항목이며 모든 API가 전부 제공하는 것은 아님)
브랜드ID / 회사명 / 브랜드명 / 업종대분류 / 업종중분류 /
공시기준연도 / 회계연도 / 지역코드 / 지역명 / 통계범위 /
가맹점수 / 직영점수 / 신규등록수 / 계약종료수 / 계약해지수 / 명의변경수 /
평균연매출_원 / 월평균환산매출_원 / 가맹비_원 / 교육비_원 /
보증금_원 / 기타비용_원 / 출처URL / 수집일 / is_dummy

검증 범위
------------------------------------------------------------
공식 데이터셋 설명과 Selenium 문서 확인 및 로컬 파서·수집 흐름 테스트.
실제 인증키 호출과 사용자 PC의 공개 웹 화면 수집은 여기서 검증하지 못했다.
API URL·필수항목은 추측해서 고정하지 않고, 정상 시험 호출 URL을 사용한다.
Selenium 코드는 특정 사이트의 현재 검색버튼 선택자에 의존하지 않는다.
"""


def show_guide():
    print(GUIDE)
    for purpose, title, url in DATASETS:
        print(f"\n{purpose}\n  {title}\n  {url}")
    print("\n공식 사용법: https://www.data.go.kr/ugs/selectPublicDataUseGuideView.do")
    print("Selenium: https://www.selenium.dev/documentation/selenium_manager/")


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def job_dir(label):
    label = re.sub(r"[^\w가-힣.-]+", "_", label).strip("._")[:60] or "수집"
    folder = ROOT / f"{datetime.now():%Y%m%d_%H%M%S_%f}_{label}"
    folder.mkdir(parents=True)
    return folder


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def save_records(folder, rows, stem="records"):
    save_json(folder / f"{stem}.json", rows)
    if not rows:
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (folder / f"{stem}.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                             for k, v in row.items()})


def split_request_url(url):
    """인증키를 한 번만 디코딩한다. 디코딩 키 안의 +는 공백으로 바꾸지 않는다."""
    parts = urlsplit(url.strip())
    if (parts.scheme != "https" or parts.hostname not in {"apis.data.go.kr", "api.data.go.kr"}
            or parts.username or parts.password or parts.port not in {None, 443}):
        raise ValueError("https://apis.data.go.kr/... 또는 https://api.data.go.kr/... 실제 Request URL을 입력하세요.")
    params = {}
    for pair in parts.query.split("&"):
        if not pair:
            continue
        key, _, value = pair.partition("=")
        key = unquote_plus(key)
        params[key] = unquote(value) if key.lower() == "servicekey" else unquote_plus(value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")), params


def normalize_service_key(value):
    """별도로 입력한 Encoding/Decoding 키 모두 지원. + 문자는 보존한다."""
    value = value.strip()
    return unquote(value) if re.search(r"%[0-9a-fA-F]{2}", value) else value


def redact_secrets(text, params):
    """서버가 반사한 키도 원본/URL 인코딩 형태 모두 가린다."""
    for name, value in params.items():
        if name.lower() in {"servicekey", "apikey", "key", "token", "access_token"} and value:
            variants = {str(value), quote(str(value), safe=""), quote_plus(str(value))}
            variants |= {quote(v, safe="") for v in list(variants)}
            for variant in sorted(variants, key=len, reverse=True):
                text = re.sub(re.escape(variant), "[인증키 가림]", text, flags=re.IGNORECASE)
    return text


def http_error_message(result, params):
    text = redact_secrets(result.content.decode("utf-8-sig", errors="replace"), params)
    codes = {
        "SERVICE_ACCESS_DENIED_ERROR": "이 API의 이용 권한이 확인되지 않았습니다. 포털에서 해당 API가 승인 상태인지 확인하세요.",
        "PERMISSION_DENIED": "요청 권한이 거부됐습니다. 해당 API의 활용신청 승인 상태를 확인하세요.",
        "SERVICE_KEY_IS_NOT_REGISTERED_ERROR": "서버가 인증키를 인식하지 못했습니다. 복사한 키와 해당 API의 승인 상태를 확인해야 합니다.",
        "SERVICE_KEY_IS_NULL": "서버에 인증키가 전달되지 않았습니다.",
        "NO_OPENAPI_SERVICE_ERROR": "호출 주소를 확인해야 합니다. End Point만이 아니라 상세 조회 기능이 포함된 Request URL이 필요합니다.",
        "DEADLINE_HAS_EXPIRED_ERROR": "API 이용 기간이 만료됐습니다. 포털에서 이용 기간을 확인하세요.",
        "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR": "오늘의 API 호출 허용량을 초과했습니다.",
        "BLACKLIST_IP_ACCESS_ERROR": "서버에서 접속 IP를 차단했습니다. 제공기관의 확인이 필요합니다.",
    }
    code = next((c for c in codes if c in text), None)
    summary = codes[code] if code else "서버가 요청을 거부했습니다. HTTP 번호만으로는 원인을 확정할 수 없습니다."
    # HTML/XML도 터미널에서 읽을 수 있게 정리하고 출력량을 제한한다.
    detail = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    detail = re.sub(r"<[^>]*>", " ", detail)
    detail = re.sub(r"\s+", " ", detail).strip()[:1200] or "(서버가 상세 설명을 보내지 않았습니다.)"
    return (f"HTTP {result.status_code}\n{summary}\n서버 응답: {detail}\n"
            "이 진단 내용을 복사해서 보내주세요. 인증키는 자동으로 가립니다.")


def safe_url(url):
    """브라우저 출처는 쿼리·fragment를 제외해 인증정보/세션값 저장을 피한다."""
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def xml_object(element):
    children = list(element)
    if not children:
        return element.text or ""
    result = {}
    for child in children:
        name = child.tag.rsplit("}", 1)[-1]
        value = xml_object(child)
        if name in result:
            if not isinstance(result[name], list):
                result[name] = [result[name]]
            result[name].append(value)
        else:
            result[name] = value
    return result


def parse_response(text):
    """공공데이터포털 표준 JSON/XML 응답만 지원. 오류·알 수 없는 구조는 중단."""
    stripped = text.lstrip("\ufeff \n\r\t")
    if stripped.startswith("<"):
        root = ET.fromstring(stripped)
        obj = xml_object(root)
    else:
        obj = json.loads(stripped)
    if not isinstance(obj, dict):
        raise ValueError("응답 최상위가 객체가 아닙니다. 이 API의 응답 구조를 별도 확인하세요.")
    response = obj.get("response", obj)
    if not isinstance(response, dict):
        raise ValueError("response 구조를 확인하세요.")
    header = response.get("header", response.get("cmmMsgHeader", {}))
    if isinstance(header, dict):
        code = header.get("resultCode", header.get("returnReasonCode"))
        if code is not None and str(code) not in {"0", "00"}:
            raise ValueError(f"API 오류 코드 {str(code)[:10]}: 활용승인·인증키·필수항목·호출량 확인.")
    code = response.get("resultCode")
    if code is not None and str(code) not in {"0", "00"}:
        raise ValueError(f"API 오류 코드 {str(code)[:10]}: 활용승인·요청값 확인.")
    body = response.get("body", response)
    if not isinstance(body, dict):
        raise ValueError("body 구조를 확인하세요.")
    total = body.get("totalCount")
    total = int(total) if total not in {None, ""} else None
    if total is not None and total < 0:
        raise ValueError("totalCount가 음수입니다.")
    if "items" not in body:
        if total == 0:
            return [], total
        raise ValueError("items가 없습니다. 표준 응답이 아니거나 인증 오류입니다.")
    items = body["items"]
    if isinstance(items, dict):
        if not items:
            items = []
        elif "item" in items:
            items = items["item"]
        else:
            raise ValueError("items.item 구조를 확인하세요.")
    if items is None or (isinstance(items, str) and not items.strip()):
        items = []
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list) or any(not isinstance(r, dict) for r in items):
        raise ValueError("행 목록 구조가 예상과 다릅니다. 원본 응답 명세 확인이 필요합니다.")
    return items, total


def _safe_label(label):
    return re.sub(r"[^\w가-힣.-]+", "_", label).strip("._")[:60] or "수집"


def _raw_page(folder, page):
    for ext in ("json", "xml"):
        path = folder / "raw" / f"page_{page:06d}.{ext}"
        if path.exists():
            return path
    return None


def _write_atomic(path, value):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _retry_get(session, base, request_params, attempts=6):
    import requests
    for attempt in range(attempts):
        try:
            result = session.get(base, params=request_params, timeout=(15, 90), allow_redirects=False)
            if result.status_code == 200:
                return result
            if result.status_code not in {429, 500, 502, 503, 504}:
                raise ValueError(http_error_message(result, request_params))
        except (requests.Timeout, requests.ConnectionError):
            if attempt == attempts - 1:
                raise RuntimeError("연결 오류가 반복되었습니다. 다음 실행에서 이어받을 수 있습니다.") from None
        if attempt == attempts - 1:
            raise RuntimeError(f"서버 오류/호출 제한이 반복되었습니다 (HTTP {result.status_code}). 나중에 재개하세요.")
        wait = min(120, 2 ** attempt * 3) + random.uniform(0, 1)
        print(f"  일시적 오류: {attempt+1}/{attempts}회, {wait:.1f}초 후 재시도")
        time.sleep(wait)


def _export_raw(folder, manifest):
    """원본 페이지를 읽어 CSV/JSON을 스트리밍 생성. 큰 데이터도 메모리에 쌓지 않음."""
    import tempfile
    pages = manifest["pages_saved"]
    # 필드 목록은 한 번만 훑어 수집 (원본 순서 보존).
    fields = []
    seen_fields = set()
    for page in range(1, pages + 1):
        path = _raw_page(folder, page)
        if path is None:
            raise ValueError(f"{page}페이지 원본이 없어 결과 파일을 만들 수 없습니다.")
        batch, _ = parse_response(path.read_text(encoding="utf-8"))
        for row in batch:
            for k in row:
                if k not in seen_fields:
                    fields.append(k)
                    seen_fields.add(k)
    csv_tmp = folder / "records.csv.tmp"
    json_tmp = folder / "records.json.tmp"
    unique_ids = set()
    written = 0
    with csv_tmp.open("w", newline="", encoding="utf-8-sig") as cf, json_tmp.open("w", encoding="utf-8") as jf:
        writer = csv.DictWriter(cf, fieldnames=fields)
        writer.writeheader()
        jf.write("[\n")
        for page in range(1, pages + 1):
            batch, _ = parse_response(_raw_page(folder, page).read_text(encoding="utf-8"))
            for row in batch:
                # 상가업소 고유번호가 있는 경우에만 중복 제거
                store_id = row.get("bizesId")
                if store_id:
                    if store_id in unique_ids:
                        continue
                    unique_ids.add(store_id)
                writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})
                if written:
                    jf.write(",\n")
                jf.write(json.dumps(row, ensure_ascii=False))
                written += 1
        jf.write("\n]\n")
    csv_tmp.replace(folder / "records.csv")
    json_tmp.replace(folder / "records.json")
    manifest["exported_rows"] = written
    manifest["duplicates_removed"] = manifest["row_count"] - written
    print(f"  결과 파일 생성: {written:,}건 (중복 제외 {manifest['duplicates_removed']:,}건)")


def fetch_pages(base, params, folder, session, max_pages=100000, delay=0.7, resume=False):
    """매 페이지 원본 저장, 자동 재시도, 실패 후 재개, 대용량 스트리밍 결과 생성."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "raw").mkdir(exist_ok=True)
    manifest_path = folder / "manifest.json"
    public_params = {k: v for k, v in params.items()
                     if k.lower() not in {"servicekey", "apikey", "token", "access_token"}}
    if resume:
        if not manifest_path.exists():
            raise ValueError("재개할 manifest.json이 없습니다.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("source_url") != base or manifest.get("query") != public_params:
            raise ValueError("이전 작업과 URL 또는 조회조건이 다릅니다. 같은 URL을 입력하세요.")
        if manifest.get("complete"):
            print("이미 완료된 작업입니다. 결과 파일만 확인하세요.")
            return manifest
    else:
        manifest = {"mode": "api", "source_url": base, "query": public_params,
                    "started_at": now(), "complete": False, "row_count": 0,
                    "expected_total": None, "pages_saved": 0, "is_dummy": False}
    # manifest 저장 중 종료된 경우에도 원본 파일 기준으로 복구
    count, expected, fingerprints = 0, None, set()
    page = 1
    while _raw_page(folder, page) is not None:
        batch, total = parse_response(_raw_page(folder, page).read_text(encoding="utf-8"))
        count += len(batch)
        if total is not None:
            if expected is not None and total != expected:
                raise ValueError("저장된 페이지 간 totalCount가 다릅니다.")
            expected = total
        fingerprints.add(hashlib.sha256(json.dumps(batch, sort_keys=True, ensure_ascii=False).encode()).hexdigest())
        page += 1
    manifest.update(row_count=count, expected_total=expected, pages_saved=page-1, complete=False)
    _write_atomic(manifest_path, manifest)
    if page > 1:
        print(f"  기존 원본 {page-1}페이지 / {count:,}건 확인. {page}페이지부터 진행합니다.")
    try:
        for page_no in range(page, max_pages + 1):
            request_params = dict(params, pageNo=str(page_no))
            result = _retry_get(session, base, request_params)
            text = result.content.decode("utf-8-sig")
            batch, total = parse_response(text)
            if total is not None:
                if expected is not None and total != expected:
                    raise ValueError("수집 도중 totalCount가 바뀌었습니다. 기준 시점 변경 여부를 확인하세요.")
                expected = total
            if batch:
                fingerprint = hashlib.sha256(json.dumps(batch, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                if fingerprint in fingerprints:
                    raise ValueError("동일한 페이지가 반복됩니다. 페이지 이동 지원 여부를 확인하세요.")
                fingerprints.add(fingerprint)
            # 인증키가 서버 응답에 반사될 경우 원본에도 남기지 않음
            text = redact_secrets(text, {k:v for k,v in params.items() if k.lower() == "servicekey"})
            suffix = "xml" if text.lstrip().startswith("<") else "json"
            dest = folder / "raw" / f"page_{page_no:06d}.{suffix}"
            tmp = dest.with_name(dest.name + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(dest)
            count += len(batch)
            manifest.update(row_count=count, expected_total=expected, pages_saved=page_no)
            _write_atomic(manifest_path, manifest)
            print(f"  {page_no}페이지: {len(batch)}건 / 누적 {count:,}건", flush=True)
            if expected is not None and count > expected:
                raise ValueError("수집 건수가 totalCount를 초과했습니다.")
            if expected is not None and count == expected:
                manifest["complete"] = True
                break
            if not batch:
                if expected is not None and count != expected:
                    raise ValueError("전체 건수보다 일찍 빈 페이지가 나왔습니다.")
                manifest["complete"] = True
                manifest["completion_rule"] = "빈 페이지 도달"
                break
            time.sleep(delay)
        else:
            raise ValueError("최대 페이지 수에 도달했습니다. 조회 범위를 나누거나 제한을 늘리세요.")
    except KeyboardInterrupt:
        manifest["error"] = "사용자가 중단함. 다음 실행에서 이어받기 가능"
        print("\n수집 일시중단. 다음 실행에서 같은 작업 폴더를 선택해 재개하세요.")
    except Exception as exc:
        manifest["error_type"] = type(exc).__name__
        manifest["error"] = str(exc) if type(exc) is ValueError else "일시적인 네트워크/서버 문제. 다음 실행에서 재개하세요."
        print("수집 일시중단:", manifest["error"])
    finally:
        manifest["finished_at"] = now()
        _write_atomic(manifest_path, manifest)
        # 대용량일 때 매번 전체 JSON을 만드는 대신 완료 후 생성
        if manifest["complete"]:
            try:
                _export_raw(folder, manifest)
            except Exception as exc:
                manifest["export_error"] = type(exc).__name__
                print("결과 파일 생성 오류. raw 원본은 안전하게 보관됨:", type(exc).__name__)
            _write_atomic(manifest_path, manifest)
        else:
            print("  수집한 모든 페이지는 raw/에 저장됨. 재개 후 완료되면 CSV/JSON 생성")
    return manifest


def collect_api():
    import requests
    print("\n정상 시험 호출한 Request URL을 사용합니다. 작업명과 URL은 매번 직접 입력할 수 있습니다.")
    label = input("작업명 (예: 전국상가_음식): ").strip() or "API"
    url = getpass.getpass("Request URL 전체 붙여넣기 (화면에 표시되지 않음): ")
    base, params = split_request_url(url)
    params = {k: v for k, v in params.items() if k.lower() != "servicekey"}
    key = normalize_service_key(SERVICE_KEY)
    if not key:
        key = normalize_service_key(getpass.getpass(".env에 키가 없습니다. 일반 인증키 입력: "))
    if not key or key.lower() == "data-portal-test-key":
        raise ValueError("유효한 일반 인증키가 필요합니다. .env의 DATA_GO_KR_KEY를 확인하세요.")
    params["ServiceKey" if "storeList" in base else "serviceKey"] = key
    if "pageNo" not in params:
        raise ValueError("Request URL에 pageNo가 없습니다.")
    print("조회조건:", {k:v for k,v in params.items() if k.lower() != "servicekey"})
    candidates = sorted((d for d in ROOT.glob(f"*_{_safe_label(label)}") if (d / "manifest.json").exists()), reverse=True)
    folder = None
    if candidates:
        print("\n같은 작업명의 이전 저장 폴더:")
        for i, d in enumerate(candidates[:5], 1):
            print(f"  {i}. {d.name}")
        selected = input("이어받을 폴더 번호 (새 작업은 Enter): ").strip()
        if selected:
            if not selected.isdigit() or not 1 <= int(selected) <= min(5, len(candidates)):
                raise ValueError("올바른 폴더 번호를 선택하세요.")
            folder = candidates[int(selected)-1]
    resume = folder is not None
    if not resume:
        folder = job_dir(label)
    with requests.Session() as session:
        manifest = fetch_pages(base, params, folder, session, resume=resume)
    print("전체 수집 완료" if manifest["complete"] else "부분 수집 — 재실행하여 이어받기 가능")
    print("저장 위치:", folder)


def visible_tables(driver, depth=0, frame_path="main"):
    """CSS 클래스명을 추측하지 않고 현재 문서와 보이는 iframe의 HTML 표를 읽는다."""
    from selenium.webdriver.common.by import By
    tables, skipped = [], []
    for index, element in enumerate(driver.find_elements(By.TAG_NAME, "table"), 1):
        if element.is_displayed():
            tables.append({"frame": frame_path, "table_index": index,
                           "html": element.get_attribute("outerHTML")})
    frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
    if depth >= 3:
        if frames:
            skipped.append(f"{frame_path}: 깊이 제한으로 하위 프레임 생략")
        return tables, skipped
    for index, frame in enumerate(frames, 1):
        entered = False
        try:
            if not frame.is_displayed():
                continue
            driver.switch_to.frame(frame)
            entered = True
            children, errors = visible_tables(driver, depth + 1, f"{frame_path}/frame{index}")
            tables.extend(children)
            skipped.extend(errors)
        except Exception as exc:
            skipped.append(f"{frame_path}/frame{index}: {type(exc).__name__}")
        finally:
            if entered:
                driver.switch_to.parent_frame()
    return tables, skipped


def export_table(html, folder, stem):
    import pandas as pd
    # 문자열과 원본 HTML을 보존. ID의 선행 0 등 원본 의미는 HTML과 대조한다.
    frames = pd.read_html(StringIO(html), flavor="lxml", keep_default_na=False, displayed_only=False)
    # 최초 파싱으로 실제 열 수를 확인한 뒤 문자열 변환기로 재파싱해 선행 0 보존.
    df = pd.read_html(StringIO(html), flavor="lxml", keep_default_na=False,
                      displayed_only=False, converters={i: str for i in range(len(frames[0].columns))})[0]
    original_columns = [str(c) for c in df.columns]
    # 중복·다단 머리글도 고유한 번호를 붙여 JSON 키 충돌을 피한다.
    df.columns = [f"{i:02d}_{name}" for i, name in enumerate(original_columns, 1)]
    (folder / f"{stem}.html").write_text(html, encoding="utf-8")
    df.to_csv(folder / f"{stem}.csv", index=False, encoding="utf-8-sig")
    (folder / f"{stem}.json").write_text(df.to_json(orient="records", force_ascii=False, indent=2), encoding="utf-8")
    return {"rows": len(df), "columns": original_columns, "file_stem": stem}


def collect_selenium():
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    print("\n원하는 브랜드/연도/표를 직접 연 뒤 추출합니다. 메뉴 1의 C 참고.")
    url = input("시작 URL [https://franchise.ftc.go.kr]: ").strip() or "https://franchise.ftc.go.kr"
    if urlsplit(url).scheme not in {"https", "http"}:
        raise ValueError("http 또는 https URL을 입력하세요.")
    folder = job_dir("Selenium")
    manifest = {"mode": "selenium", "started_at": now(), "is_dummy": False,
                "scope": "사용자가 선택한 화면의 HTML 표; 전체 DB 수집을 의미하지 않음", "captures": []}
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    try:
        driver.get(url)
        count = 0
        while True:
            action = input("\n브라우저에서 원하는 표를 연 뒤 Enter / 종료는 q: ").strip().lower()
            if action == "q":
                break
            handles = driver.window_handles
            for i, handle in enumerate(handles, 1):
                driver.switch_to.window(handle)
                print(f"  {i}. {driver.title[:90]}")
            selected = input("수집할 탭 번호 [1]: ").strip() or "1"
            if not selected.isdecimal() or not 1 <= int(selected) <= len(handles):
                print("표시된 번호를 선택하세요.")
                continue
            driver.switch_to.window(handles[int(selected) - 1])
            WebDriverWait(driver, 20).until(lambda d: d.find_element(By.TAG_NAME, "body"))
            driver.switch_to.default_content()
            tables, skipped = visible_tables(driver)
            if not tables:
                print("보이는 HTML 표가 없습니다. PDF/이미지이거나 아직 조회되지 않은 화면일 수 있습니다.")
                continue
            label = input("화면 메모 (브랜드명/연도/지역/단위 — 화면에서 직접 확인): ").strip()
            count += 1
            capture = {"captured_at": now(), "source_url": safe_url(driver.current_url),
                       "title": driver.title, "user_note_unverified": label,
                       "skipped_frames": skipped, "tables": [], "complete": False}
            for i, table in enumerate(tables, 1):
                stem = f"capture_{count:03d}_table_{i:03d}"
                try:
                    info = export_table(table["html"], folder, stem)
                    info.update(frame=table["frame"], table_index=table["table_index"])
                    capture["tables"].append(info)
                    print(f"  {stem}: {info['rows']}행 저장")
                except Exception as exc:
                    capture["tables"].append({"file_stem": stem, "error_type": type(exc).__name__})
                    print(f"  {stem}: 추출 실패 ({type(exc).__name__})")
            capture["complete"] = not skipped and all("error_type" not in t for t in capture["tables"])
            manifest["captures"].append(capture)
            save_json(folder / "manifest.json", manifest)
            print("현재 화면 표 추출 완료" if capture["complete"] else "일부 표/프레임 누락: manifest 확인")
            print("다음 페이지·다른 브랜드는 브라우저에서 이동 후 반복하세요.")
    finally:
        manifest["finished_at"] = now()
        save_json(folder / "manifest.json", manifest)
        driver.quit()
        print("저장 위치:", folder)


def main():
    parser = argparse.ArgumentParser(description="프차탄탄: 수집 안내/API/Selenium 단일 파일")
    parser.add_argument("--guide", action="store_true", help="설치 없이 안내만 출력")
    args = parser.parse_args()
    if args.guide:
        show_guide()
        return
    while True:
        print("\n프차탄탄 공공데이터 수집기 — 수정본 v4 (.env·재시도·이어받기)\n1. 자료 받는 법·수집 순서\n2. API 전체 페이지 수집\n3. Selenium 공개 표 추출\n0. 종료")
        choice = input("번호: ").strip()
        try:
            if choice == "0":
                return
            if choice == "1":
                show_guide()
            elif choice == "2":
                collect_api()
            elif choice == "3":
                collect_selenium()
            else:
                print("0~3 중 선택하세요.")
        except ImportError:
            print("먼저 실행: python -m pip install -U requests selenium pandas lxml python-dotenv")
        except (KeyboardInterrupt, EOFError):
            print("\n작업을 중단했습니다. 저장된 부분자료와 manifest를 확인하세요.")
            return
        except Exception as exc:
            # 브라우저/HTTP 예외에 인증정보가 있을 수 있어 원문 전체를 출력하지 않는다.
            print("실행 실패:", str(exc) if type(exc) is ValueError else type(exc).__name__)
            print("설치·인터넷·Chrome·조회조건을 확인하세요. 안내는 메뉴 1입니다.")


if __name__ == "__main__":
    main()


https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInUpjong?serviceKey=REDACTED&pageNo=1&numOfRows=1000&divId=indsLclsCd&key=I2&type=json