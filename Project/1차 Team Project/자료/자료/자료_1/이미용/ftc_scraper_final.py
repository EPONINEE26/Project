#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공정거래위원회 가맹사업정보제공시스템(정보공개서) 스크래퍼 + 엑셀 생성기
────────────────────────────────────────────────────────────────────
대상 : 에이바헤어 / 블루클럽 / 제오헤어 / 로이드밤 / 토리헤어

수집 지표 (사이트 실제 표와의 대응)
  · 창업비용  ←  "가맹점사업자의 부담금" 표 (가입비(가맹비)+교육비+보증금+기타비용 = 합계, 단위 천원)
  · 개점수    ←  "가맹점 변동 현황" 표의 '신규개점'
  · 폐점수    ←  "가맹점 변동 현황" 표의 '계약종료' + '계약해지'
  · 매장수(서울/경기) ← "가맹점 및 직영점 현황" 표의 서울/경기 가맹점수
  · 연매출    ←  "가맹점사업자의 평균 매출액" 표 (전국/서울/경기, 단위 천원)

출력 : 브랜드별 xlsx 5개
  · 1번 시트 = index(연도) x columns(지표) 형태의 데이터
  · 2번 시트 = 메타정보(상호, 영업표지, 출처 URL, 단위, 비고)

실행
  pip install requests beautifulsoup4 lxml pandas openpyxl
  python ftc_scraper_final.py                # 실시간 수집
  python ftc_scraper_final.py --offline ./html   # 저장된 HTML로 재생성(검증용)

주의
  · encFirMstSn 토큰은 시간이 지나면 404('페이지 오류')가 되므로,
    실패 시 브랜드명으로 목록을 재조회해 새 토큰을 받아 재시도한다.
  · 부담금·평균매출액은 정보공개서에 '최신 사업연도' 1개년만 공시된다.
    없는 연도는 임의 생성하지 않고 NaN(공백)으로 둔다.
"""

import argparse
import os
import re
import time
from datetime import datetime
from urllib.parse import quote

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE = "https://franchise.ftc.go.kr"
LIST_URL = BASE + "/mnu/00013/program/userRqst/list.do"
VIEW_URL = BASE + "/mnu/00013/program/userRqst/view.do"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 사용자가 제공한 원본 정보공개서 URL
TARGETS = [
    {"key": "에이바헤어", "url": VIEW_URL + "?encFirMstSn=m6cLyZkQpxNcoxzeCLZBkQ%3D%3D"},
    {"key": "블루클럽",   "url": VIEW_URL + "?encFirMstSn=0jA7scs7wuABP16%2B48r8mQ%3D%3D"},
    {"key": "제오헤어",   "url": VIEW_URL + "?encFirMstSn=pNdkNfn4xox%2BzOLRnH53Ag%3D%3D"},
    {"key": "로이드밤",   "url": VIEW_URL + "?encFirMstSn=R%2FJiamYt%2FvLM0Up1THERzA%3D%3D"},
    {"key": "토리헤어",   "url": VIEW_URL + "?encFirMstSn=TDZ86QnReTlSUmcX%2FHhOMA%3D%3D"},
]

TARGET_YEARS = [2024, 2025]
OUT_DIR = "output"

COLUMNS = [
    "창업비용_합계(천원)", "가입비(가맹비)(천원)", "교육비(천원)", "보증금(천원)", "기타비용(천원)",
    "개점수(신규개점)", "계약종료", "계약해지", "폐점수(계약종료+계약해지)",
    "매장수_서울", "매장수_경기", "매장수_전국",
    "연매출_전국평균(천원)", "연매출_서울(천원)", "연매출_경기(천원)",
]


# ────────────────────────────────────────────── 공통 유틸
def to_int(txt):
    s = str(txt).replace(",", "").strip()
    return int(s) if re.fullmatch(r"-?\d+", s) else None


def cell_text(tr):
    return [" ".join(c.get_text(" ", strip=True).split()) for c in tr.find_all(["th", "td"])]


def new_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get(LIST_URL, timeout=30, verify=False)     # 세션 쿠키 확보
    return s


# ────────────────────────────────────────────── 1) 토큰 재발급(목록 재조회)
def resolve_token(session, keyword):
    """브랜드명으로 목록을 조회해 (상호, 영업표지, encFirMstSn) 확보"""
    for col in ("brd", "tNm"):                     # brd=상호, tNm=영업표지
        url = (f"{LIST_URL}?column={col}&selUpjong=&selIndus="
               f"&pageUnit=100&pageIndex=1&searchKeyword={quote(keyword)}")
        html = session.get(url, timeout=30, verify=False).text
        for tr in re.findall(r"<tr>(.*?)</tr>", html, re.S):
            tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
            if len(tds) < 3:
                continue
            clean = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x)).strip() for x in tds]
            tok = re.search(r"fn_moveUrl\('[^']*',\s*'([^']+)'\)", tr)
            if tok and (keyword in clean[0] or keyword in clean[1]):
                return clean[0], clean[1], tok.group(1)
    return None, None, None


# ────────────────────────────────────────────── 2) 상세 HTML 수집
def fetch_html(session, target):
    r = session.get(target["url"], timeout=60, verify=False)
    r.encoding = "utf-8"
    if r.status_code == 200 and "페이지 오류" not in r.text:
        return r.text, target["url"], "원본 URL"

    biz, brand, token = resolve_token(session, target["key"])
    if not token:
        raise RuntimeError(f"[{target['key']}] 상세페이지 조회 실패(토큰 재발급 불가)")
    url = VIEW_URL + "?encFirMstSn=" + quote(token, safe="")
    r = session.get(url, timeout=60, verify=False)
    r.encoding = "utf-8"
    if r.status_code != 200 or "페이지 오류" in r.text:
        raise RuntimeError(f"[{target['key']}] 토큰 재발급 후에도 조회 실패")
    return r.text, url, f"브랜드명 재조회(상호={biz}, 영업표지={brand})"


# ────────────────────────────────────────────── 3) 표 파싱
def parse_detail(html):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()

    d = {"store": {}, "change": {}, "fee": {}, "sales": {}}
    for tb in soup.find_all("table"):
        cap = tb.find("caption")
        capt = " ".join(cap.get_text(" ", strip=True).split()) if cap else ""
        trs = tb.find_all("tr")
        if not trs:
            continue

        # (가) 지역별 가맹점수/직영점수 : 지역(행) x 연도(열, 3칸=전체·가맹점수·직영점수)
        if "가맹점 및 직영점 현황" in capt:
            hdr = cell_text(trs[0])
            years = [int(re.sub(r"[^0-9]", "", h)[:4]) for h in hdr[1:] if re.search(r"20\d\d", h)]
            for tr in trs[2:]:
                c = cell_text(tr)
                if len(c) < 4:
                    continue
                region, vals = c[0], c[1:]
                for i, y in enumerate(years):
                    trip = vals[i * 3:(i + 1) * 3]      # [전체, 가맹점수, 직영점수]
                    if len(trip) >= 2 and trip[1] != "":
                        d["store"].setdefault(region, {})[y] = to_int(trip[1])   # 가맹점수

        # (나) 가맹점 변동 현황 : 연도(행) x 신규개점·계약종료·계약해지·명의변경(열)
        elif "변동 현황" in capt:
            for tr in trs[1:]:
                c = cell_text(tr)
                if c and re.fullmatch(r"20\d\d", c[0]):
                    d["change"][int(c[0])] = {
                        "신규개점": to_int(c[1]) if len(c) > 1 else None,
                        "계약종료": to_int(c[2]) if len(c) > 2 else None,
                        "계약해지": to_int(c[3]) if len(c) > 3 else None,
                        "명의변경": to_int(c[4]) if len(c) > 4 else None,
                    }

        # (다) 가맹점사업자의 부담금(창업비용) : 단위 천원
        elif capt.startswith("가맹점사업자의 부담금") or "가입비(가맹비)" in tb.get_text():
            head, row = cell_text(trs[0]), (cell_text(trs[1]) if len(trs) > 1 else [])
            if "가입비" in " ".join(head) and len(row) >= 5:
                d["fee"] = {"가입비": to_int(row[0]), "교육비": to_int(row[1]),
                            "보증금": to_int(row[2]), "기타비용": to_int(row[3]),
                            "합계": to_int(row[4])}

        # (라) 평균매출액 : 지역(행) x 연도(열, 3칸=가맹점수·평균매출액·면적당)
        elif "평균 매출액" in capt:
            hdr = cell_text(trs[0])
            years = [int(re.sub(r"[^0-9]", "", h)[:4]) for h in hdr[1:] if re.search(r"20\d\d", h)]
            for tr in trs[2:]:
                c = cell_text(tr)
                if len(c) < 3:
                    continue
                region, vals = c[0], c[1:]
                for i, y in enumerate(years):
                    trip = vals[i * 3:(i + 1) * 3]
                    if len(trip) >= 2 and trip[1] != "":
                        d["sales"].setdefault(region, {})[y] = to_int(trip[1])
    return d


# ────────────────────────────────────────────── 4) DataFrame (index=연도, columns=지표)
def build_frame(d):
    fee_latest = d["fee"] if d["fee"] else {}
    sales_latest = {k: v.get(max(TARGET_YEARS)) for k, v in d["sales"].items()}
    rows = []
    for y in TARGET_YEARS:
        ch = d["change"].get(y, {})
        closed = (ch.get("계약종료") or 0) + (ch.get("계약해지") or 0) if ch else None
        is_latest = (y == max(TARGET_YEARS))
        rows.append({
            "연도": y,
            # 부담금 : 최신 사업연도 1개년만 공시 → 그 연도에만 기입
            "창업비용_합계(천원)": fee_latest.get("합계") if is_latest else None,
            "가입비(가맹비)(천원)": fee_latest.get("가입비") if is_latest else None,
            "교육비(천원)": fee_latest.get("교육비") if is_latest else None,
            "보증금(천원)": fee_latest.get("보증금") if is_latest else None,
            "기타비용(천원)": fee_latest.get("기타비용") if is_latest else None,
            "개점수(신규개점)": ch.get("신규개점"),
            "계약종료": ch.get("계약종료"),
            "계약해지": ch.get("계약해지"),
            "폐점수(계약종료+계약해지)": closed,
            "매장수_서울": d["store"].get("서울", {}).get(y),
            "매장수_경기": d["store"].get("경기", {}).get(y),
            "매장수_전국": d["store"].get("전체", {}).get(y),
            "연매출_전국평균(천원)": sales_latest.get("전체") if is_latest else None,
            "연매출_서울(천원)": sales_latest.get("서울") if is_latest else None,
            "연매출_경기(천원)": sales_latest.get("경기") if is_latest else None,
        })
    return pd.DataFrame(rows).set_index("연도")[COLUMNS]


# ────────────────────────────────────────────── 5) 엑셀 저장
def save_excel(df, name, biz, url, note, path):
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    meta = [("시트명", name), ("상호(법인명)", biz), ("영업표지", name),
            ("출처", "공정거래위원회 가맹사업거래 정보공개서"),
            ("수집 URL", url),
            ("수집일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("수집경로", note),
            ("단위", "부담금·평균매출액 = 천원 (원 환산 시 ×1,000)"),
            ("비고", "창업비용·연매출은 정보공개서 최신 사업연도(2025)만 공시되어 2024년 값은 공백. "
                     "개점·폐점·매장수는 2024·2025 각각 공시값.")]

    with pd.ExcelWriter(path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name=name)                                  # index/columns 데이터
        pd.DataFrame(meta, columns=["항목", "내용"]).to_excel(w, sheet_name="메타정보", index=False)

        ws, thin = w.book[name], Side(style="thin", color="BFBFBF")
        for c in range(1, df.shape[1] + 2):
            cell = ws.cell(row=1, column=c)
            cell.fill = PatternFill("solid", fgColor="1F3864")
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = Border(thin, thin, thin, thin)
        for r in range(2, df.shape[0] + 2):
            for c in range(1, df.shape[1] + 2):
                cell = ws.cell(row=r, column=c)
                cell.border = Border(thin, thin, thin, thin)
                if c == 1:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal="center")
                else:
                    cell.number_format = "#,##0"
        ws.freeze_panes = "B2"
        ws.column_dimensions["A"].width = 8
        for i in range(2, df.shape[1] + 2):
            ws.column_dimensions[get_column_letter(i)].width = 17
        ws.row_dimensions[1].height = 34
        w.book["메타정보"].column_dimensions["A"].width = 14
        w.book["메타정보"].column_dimensions["B"].width = 95


# ────────────────────────────────────────────── main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", metavar="HTML_DIR",
                    help="저장된 HTML(page_브랜드.html)로만 재생성")
    ap.add_argument("--out", default=OUT_DIR)
    args = ap.parse_args()

    import urllib3
    urllib3.disable_warnings()
    os.makedirs(args.out, exist_ok=True)

    session = None if args.offline else new_session()
    results = []

    for t in TARGETS:
        name = t["key"]
        try:
            if args.offline:
                path = os.path.join(args.offline, f"page_{name}.html")
                html = open(path, encoding="utf-8").read()
                used_url, note = t["url"], f"저장 HTML 재파싱({path})"
            else:
                html, used_url, note = fetch_html(session, t)

            data = parse_detail(html)
            df = build_frame(data)

            m = re.search(r"법인명[^<]*</th>\s*<td[^>]*>(.*?)</td>", html, re.S)
            biz = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""

            safe = re.sub(r'[\\/:*?"<>|]', "_", name)     # 파일명 = 정확한 상호/영업표지
            out = os.path.join(args.out, f"{safe}.xlsx")
            save_excel(df, name, biz, used_url, note, out)
            results.append((name, biz, out, df))
            print(f"[OK] {name} ({biz}) -> {out}")
        except Exception as e:
            print(f"[FAIL] {name} : {e}")
        if session:
            time.sleep(1.5)

    print("\n" + "=" * 108)
    for name, biz, out, df in results:
        print(f"\n■ {name} / {biz}   {out}")
        print(df.to_string())
    return results


if __name__ == "__main__":
    main()
