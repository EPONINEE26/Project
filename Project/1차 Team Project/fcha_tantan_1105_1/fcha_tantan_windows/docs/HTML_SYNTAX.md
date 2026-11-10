# HTML 파일별 사용 문법

문서의 경로는 manage.py가 있는 바깥 fcha_tantan 기준입니다.
모든 화면은 Django가 {{ 변수 }}, {% for %}, {% if %} 등을 처리해 HTML로 응답합니다.
HTML 파일을 직접 열면 이 문법이 처리되지 않습니다.

| 공통 문법 | 의미 |
| --- | --- |
| extends / block | base.html의 메뉴·푸터를 공유하고 본문을 끼워 넣음 |
| include | 반복되는 카드·버튼 HTML을 불러옴 |
| load static | static 폴더 파일 경로를 만드는 태그 준비 |
| static | CSS·JS·이미지의 /static/ 주소 출력 |
| load brand_format | 숫자·금액 표시 필터 준비 |
| {{ 변수 }} | views.py에서 받은 context 값 출력 |
| for / empty | 목록 반복, 목록이 비었을 때 표시 |
| if / else | 조건에 따라 화면 표시 |
| url | urls.py의 이름으로 이동 주소 생성 |
| csrf_token | POST 요청 검증 |
| with | 템플릿에서 잠시 쓸 값에 이름 붙이기 |
| number / money | 원본의 숫자·금액 표시 필터 |
| urlencode | 지역명 등을 URL에 사용할 수 있게 변환 |
| default_if_none | None 값을 지정한 값으로 표시 |
| slice | 문자열 일부 표시 |
| length | 목록 개수 |

## 파일별 실제 태그와 필터

### brands/templates/base.html

- Django 태그: block, csrf_token, else, endblock, endfor, endif, for, if, load, static, url
- 값 표시 필터: length

### brands/templates/bcompare.html

- Django 태그: block, else, endblock, endfor, endif, endwith, extends, for, if, include, load, static, url, with
- 값 표시 필터: add, length, number

### brands/templates/blist.html

- Django 태그: block, endblock, extends, include
- 값 표시 필터: 없음

### brands/templates/bregion.html

- Django 태그: block, else, empty, endblock, endfor, endif, extends, for, if, include, load, url
- 값 표시 필터: number, slice, urlencode

### brands/templates/bsaved.html

- Django 태그: block, endblock, extends, include
- 값 표시 필터: 없음

### brands/templates/bview.html

- Django 태그: block, else, empty, endblock, endfor, endif, endwith, extends, for, if, include, load, static, url, with
- 값 표시 필터: add, default_if_none, money, number, slice

### brands/templates/guide.html

- Django 태그: block, else, endblock, endif, extends, if, include
- 값 표시 필터: 없음

### brands/templates/includes/badge.html

- Django 태그: else, endif, if
- 값 표시 필터: 없음

### brands/templates/includes/bars.html

- Django 태그: endfor, endif, for, if, load
- 값 표시 필터: number

### brands/templates/includes/brand_card.html

- Django 태그: else, endif, endwith, if, include, load, static, url, with
- 값 표시 필터: add, default_if_none, number

### brands/templates/includes/compare_button.html

- Django 태그: csrf_token, else, endif, if, url
- 값 표시 필터: 없음

### brands/templates/includes/list_section.html

- Django 태그: else, empty, endfor, endif, for, if, include, load, url
- 값 표시 필터: length

### brands/templates/includes/save_button.html

- Django 태그: csrf_token, else, endif, if, url
- 값 표시 필터: 없음

### brands/templates/includes/year_select.html

- Django 태그: empty, endfor, endif, for, if
- 값 표시 필터: 없음

### home/templates/index.html

- Django 태그: block, empty, endblock, endfor, endif, extends, for, if, include, url
- 값 표시 필터: 없음

## 화면별 HTML과 동작

| 파일 | 주요 HTML·동작 | 연결된 CSS·JS |
| --- | --- | --- |
| index.html | section, 링크, 네이비 배경·CSS 막대 장식, 목록 include | hero·art-block 클래스 |
| base.html | head, link, script, header, nav, main, footer, 비교함 POST 폼 | style.css·django.css·common.js 불러오기 |
| blist.html, bsaved.html | 공통 목록 include, GET 검색·필터 | cards·filter-panel |
| bview.html | section, 통계 표시, CSS 막대차트, details/summary 펼치기, #목차 링크 | metrics·chart·bar-list·detail-tabs |
| bcompare.html | table 비교표, CSV 다운로드 링크, 비교 해제 폼 | compare-table |
| bregion.html | 지역 링크·표·지역 합계, 비교 버튼 | region-layout·region-tiles |
| guide.html | 지표 설명 패널 | guide-grid·panel |
| includes/list_section.html | GET form, input 검색, radio 업종, select 연도·지역·정렬 | common.js의 change 이벤트로 제출 |
| includes/brand_card.html | img, 링크, 카드 데이터, 관심·비교 include | brand-card·card-cover |
| includes/compare_button.html | POST form, hidden next, csrf, 비교 토글 button | compare-toggle |
| includes/save_button.html | POST form, csrf, 하트 button | save-btn |
| includes/year_select.html | select와 option 반복 | year-form에서 자동 제출 |
| includes/bars.html | width 값으로 지역별 막대 길이 표현 | bar-track·bar-fill |
| includes/badge.html | 예시·출처 조건 표시 | demo-label |

## static 파일 문법

- style.css: 클래스 선택자, flex/grid, 색상 변수, padding/margin, position, hover/focus, transition, @media 반응형, Google Fonts @import. 원본 그대로입니다.
- django.css: form과 버튼 배치, 상세 영역 등 폼 보완 스타일. 원본 그대로입니다.
- common.js: document.addEventListener('change', function(event){...}), const, closest(), matches(), if, requestSubmit(). 필터 또는 연도 선택 시 GET 폼을 제출합니다.
- JavaScript로 카드 본문을 조립하지 않습니다. 화면은 Django for·if로 출력합니다.
- images: 원본 사진과 SVG 파일이며 HTML img와 static 태그로 연결합니다.

버튼별 이동 주소는 PAGE_NAVIGATION.md에서 확인합니다. 화면 조회 과정은 SCHOOL_PATTERN.md와 LEARNING_GUIDE.md를 함께 읽으면 됩니다.
