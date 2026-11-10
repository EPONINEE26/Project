# 배운 문법과 연결해서 읽기

workspce.zip의 학생·회원 Django 실습처럼 함수형 views.py, GET/POST, context 딕셔너리, render, redirect, 모델 조회, 세션, HTML/CSS/JavaScript를 사용합니다.
새 언어나 프런트엔드 프레임워크는 추가하지 않았습니다.

1. fcha_tantan/urls.py → brands/urls.py에서 주소를 확인합니다.
2. brands/views.py의 blist(request)를 봅니다.
3. list_context에서 request.GET.get()으로 검색 조건을 읽습니다.
4. Brand.objects.all()로 브랜드를 가져와 for와 if로 목록을 만듭니다.
5. context를 render(request, 'blist.html', context)로 보냅니다.
6. HTML의 for·if·변수 출력으로 화면을 만듭니다.
7. 관심·비교는 request.session에 저장하고 redirect로 되돌아갑니다.

연도와 세션 목록을 만드는 context_for, 연도별 통계를 찾는 brand_row, 정렬 값 선택, 비교 행 준비의 복잡한 한 줄 표현을 기본 for·if로 풀었습니다.
원본의 나머지 통계 처리에는 리스트 컴프리헨션·lambda가 일부 남아 있습니다. 화면과 계산 결과 보존을 위해 필요한 기존 코드를 유지했습니다.

| 문법 / 기능 | 뜻 |
| --- | --- |
| context_for(request) | 메뉴·연도·관심·비교에 공통으로 쓰는 데이터 준비 |
| brand_row(brand, year) | 브랜드 한 개의 선택 연도 수치 준비 |
| slug | tantan 같은 브랜드 고유 문자열; 학생 실습의 no와 같은 조회 기준 |
| get_object_or_404 | DB에 없으면 오류 화면 대신 HTTP 404 반환 |
| @require_GET / @require_POST | 해당 요청 방식만 받도록 제한 |
| prefetch_related | 연결된 연도·지역 자료를 묶어서 읽어 DB 반복 조회를 줄임 |
| related_name | brand.annual_stats처럼 연결된 통계를 조회할 때 쓰는 이름 |
| extends / block | 공통 메뉴를 유지하고 페이지 본문만 교체 |
| include | 카드·필터처럼 반복되는 HTML 조각 사용 |
| load static brand_format | static 태그와 숫자 표시 필터를 불러오기 |
| csrf_token | POST 폼 요청 검증 토큰 |
| requestSubmit() | 선택 항목이 바뀌면 폼을 제출하는 JavaScript |

화면 변경은 HTML/CSS, 조회·계산 변경은 views.py, 데이터 항목 변경은 models.py에서 시작합니다.
JSON API, CSV 입력·내려받기, 금액 필터는 원본 기능을 유지했습니다. 세부 코드를 모두 이해해야 페이지 스타일을 고칠 수 있는 것은 아닙니다.
