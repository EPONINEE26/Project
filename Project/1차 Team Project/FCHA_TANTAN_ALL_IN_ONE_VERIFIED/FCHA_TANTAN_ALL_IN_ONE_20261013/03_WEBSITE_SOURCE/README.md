# 프차 탄탄 | FCHA TANTAN

네이비 #18243A · 레몬 #F4EF76 · 화이트 / IBM Plex Sans KR

완성된 반응형 프런트엔드 + 실행 가능한 Django/Pandas 연동 시작 프로젝트입니다.
현재 브랜드 8개와 2024·2025 통계는 모두 가상입니다. 실제 통계 수집은 포함하지 않았습니다.

## 1. 가장 빠르게 화면 확인 (Windows PowerShell)

압축을 C:\workspace\fcha_tantan 에 풀었다고 가정합니다. 프로젝트 폴더에 dist, backend, docs가 보여야 합니다.

```powershell
cd C:\workspace\fcha_tantan
python -m http.server 8080 --directory dist
```
브라우저에서 http://localhost:8080 을 여세요. 종료: Ctrl+C.
index.html을 더블클릭하면 브라우저 보안 정책 때문에 JSON 로딩이 실패할 수 있습니다.
Node.js, npm, React 설치는 필요 없습니다.

## 2. Django + SQLite로 전체 실행

```powershell
cd C:\workspace\fcha_tantan
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py seed_demo
.\.venv\Scripts\python.exe backend\manage.py runserver
```
http://127.0.0.1:8000 을 여세요. Django에서 실행하면 자동으로 API 모드가 됩니다.
PowerShell 실행 정책을 변경하거나 가상환경 activate를 실행하지 않아도 됩니다.
Python 3.12 이상 권장. 패키지는 프로젝트 가상환경에만 설치됩니다.

관리자 생성 (필요할 때):
```powershell
.\.venv\Scripts\python.exe backend\manage.py createsuperuser
```
관리자 화면: http://127.0.0.1:8000/admin/

## 3. 구현한 화면과 기능

- 브랜드 탐색: 실시간 검색, 업종·지역·연도 필터, 정렬, 결과 없음 상태
- 브랜드 상세: 전국 4대 지표, 3년 개업/폐업 그래프, 17개 지역 분포, 비용 구성
- 최대 3개 브랜드 비교: 같은 연도 기준, 지역별 표, CSV 다운로드
- 관심 브랜드: 브라우저 localStorage 저장
- 지역 살펴보기: 17개 시·도별 브랜드 매장 수와 전국 대비 비중
- 데이터 안내: 지표 정의, 출처, 예시/실제 구분
- 모바일 반응형, 키보드 포커스, 본문 바로가기, 오류/로딩/빈 상태

관심 브랜드는 해당 브라우저에 저장되며 로그인·기기 간 동기화는 포함하지 않습니다.
브랜드 사진은 참고용입니다. 해당 가상 브랜드의 실제 매장이 아닙니다.

## 4. 폴더 역할

| 경로 | 역할 |
| --- | --- |
| dist/index.html | 공통 HTML 뼈대 |
| dist/css/style.css | 브랜드 색상, 반응형, 전체 UI |
| dist/js/app.js | 화면과 사용자 동작 |
| dist/js/api.js | JSON/API 데이터 요청 전담 |
| dist/js/data-utils.js | 검색·필터·월매출 계산 함수 |
| dist/js/config.js | 정적 실행 모드 설정 |
| dist/data/brands.json | 예시 API 응답 |
| backend/brands/models.py | 브랜드·연간통계·지역통계 모델 |
| backend/brands/views.py | JSON 조회 API |
| backend/brands/management/commands/import_stats.py | Pandas CSV 검증 및 DB 저장 |
| docs/API_CONTRACT.md | 프런트/백엔드 데이터 계약 |
| docs/BACKEND_NEXT.md | 실데이터 연결 순서 |
| docs/sample_stats.csv | CSV 형식 예제 (가상) |

## 5. 검증

```powershell
.\.venv\Scripts\python.exe backend\manage.py test brands
```
Node.js가 있으면 순수 데이터 함수 테스트:
```powershell
node --test tests/data.test.js
```
이 프로젝트는 로컬 Django 개발 설정입니다. 실제 배포 전 DEBUG=0, 환경변수 SECRET_KEY, ALLOWED_HOSTS, 운영용 정적 파일 서버, HTTPS, DB 백업을 설정하세요. Sites 미리보기는 정적 프런트엔드만 제공합니다. Python 서버는 별도 서버에 배포해야 합니다.

## 디자인·자료

사용자 제공 FCHA_TANTAN_Branding_Refined.pdf의 이름·색상·서체·슬로건과 콘셉트 이미지, 첨부 브랜드 카드 구조를 반영했습니다. 콘셉트 이미지는 제공 PDF에서 추출했습니다.
상세 구조 참고: https://myfranchise.kr/20213692/오와케이크 (동적 상세 전체는 확인 제한)
사진: Unsplash 참고 이미지. 원본 URL은 docs/ASSETS.md에 기재했습니다.
Django 공식 문서: https://docs.djangoproject.com/en/5.2/
