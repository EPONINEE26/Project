# 데이터와 화면 연결 안내

모델 정의 위의 `# 데이터:` 주석과 admin 등록 위의 `# 관리자` 주석에 관리 대상과 출력 화면을 표시했습니다. 화면 함수의 `# 화면 출력:` 주석은 전달하는 템플릿을 가리킵니다.

자치구 유동인구 출력 경로:

1. `DistrictPopulationStat`: 자치구별 분기 통계 저장.
2. `market.analysis.district_population_card(area)`: 선택 상권의 행정구역코드 앞 5자리로 최신 자치구 통계 조회.
3. `analysis_context()`: `district_card`를 화면 컨텍스트에 추가.
4. `brands/templates/bregion.html`: 자치구 템플릿 포함.
5. `brands/templates/includes/district_population.html`: 자치구 유동인구·분포·출처 표시.

관리자 화면은 `market/admin.py`의 `DistrictPopulationStatAdmin`에서 목록·검색·분기 필터를 설정합니다.

## 전체 모델과 사용 화면

| 모델 | 정의 파일 | 데이터와 사용 화면 |
| --- | --- | --- |
| `SavedBrand` | [accounts/models.py](../accounts/models.py) | 회원별 관심 브랜드 → 관심 목록·저장 버튼 상태 |
| `MemberProfile` | [accounts/models.py](../accounts/models.py) | 회원 연락처·창업 희망조건·동의 → 내 정보·사업제안 대상 조회 |
| `EmailVerification` | [accounts/models.py](../accounts/models.py) | 이메일 인증번호 해시·만료/시도 기록 → 가입·탈퇴 인증 처리(번호 원문 출력 없음) |
| `Brand` | [brands/models.py](../brands/models.py) | 브랜드 기본정보 → 홈·브랜드 목록/상세·비교·추천·지역상권 후보 카드 |
| `AnnualStat` | [brands/models.py](../brands/models.py) | 연도별 공시 매출·매장 수·창업비용 → 브랜드 목록/상세·비교·계산기 |
| `RegionalStat` | [brands/models.py](../brands/models.py) | 브랜드 지역별 통계 → 선택 지역의 브랜드 매출·매장 수 |
| `AreaSales` | [brands/models.py](../brands/models.py) | 공시 면적당 매출 → 브랜드 상세·비교의 평당 매출 |
| `AdSlot` | [brands/models.py](../brands/models.py) | 광고 구좌·입찰가·노출기간 → 홈·브랜드 탐색 광고 카드 |
| `OwnerVerification` | [brands/models.py](../brands/models.py) | 점주 인증 신청·증빙·승인 상태 → 인증 내역·점주 기능 접근 확인 |
| `BrandReview` | [brands/models.py](../brands/models.py) | 인증 점주 후기 → 브랜드 상세 후기·후기 작성 화면 |
| `ModeratedContent` | [community/models.py](../community/models.py) | 게시물 공개/블라인드 상태 공통 필드 → 게시글·댓글 추상 기반(별도 테이블 없음) |
| `Post` | [community/models.py](../community/models.py) | 점주 게시글 → 커뮤니티 목록·상세·작성자 글 목록 |
| `Comment` | [community/models.py](../community/models.py) | 게시글 댓글 → 커뮤니티 상세 댓글 목록 |
| `Report` | [community/models.py](../community/models.py) | 게시글·댓글 신고 → 관리자 신고 검토 목록 |
| `ModerationPolicy` | [core/models.py](../core/models.py) | 비속어·공개 제한 정책 → 게시물 필터·삭제 안내 문구 |
| `ModerationEvent` | [core/models.py](../core/models.py) | 게시물 검토 작업 이력 → 관리자 검토 로그(일반 화면 비공개) |
| `FAQ` | [core/models.py](../core/models.py) | 공개 FAQ·분류·대상 → 고객센터·챗봇 답변 자료 |
| `Notice` | [core/models.py](../core/models.py) | 공개 공지 → 고객센터 공지 목록 |
| `SupportTicket` | [core/models.py](../core/models.py) | 회원 문의·관리자 답변 → 내 문의 목록/상세 |
| `StartupCondition` | [market/analysis_models.py](../market/analysis_models.py) | 회원별 저장 창업조건 → 지역상권분석·맞춤 브랜드 추천 입력값 |
| `DataSource` | [market/analysis_models.py](../market/analysis_models.py) | 공공자료 출처·수집일·비고 → 상권/자치구 통계 출처 안내 |
| `CommercialArea` | [market/analysis_models.py](../market/analysis_models.py) | 상권 코드·행정구역코드·경계 → 지도 상권 판정·상권명·자치구 연결 |
| `IndustryCode` | [market/analysis_models.py](../market/analysis_models.py) | 공공 업종 코드·브랜드 업종 대응 → 매장 업종 집계·상권 업종 통계 |
| `AreaObservation` | [market/analysis_models.py](../market/analysis_models.py) | 상권·출처·기간·단위 공통 필드 → 인구/매출/개폐업 모델의 추상 기반(별도 테이블 없음) |
| `PopulationStat` | [market/analysis_models.py](../market/analysis_models.py) | 상권별 유동·상주·직장인구 → 지역상권분석 인구 카드·상세 |
| `DistrictPopulationStat` | [market/analysis_models.py](../market/analysis_models.py) | 자치구별 길단위 유동인구 CSV → 지역상권분석 자치구 참고 영역(includes/district_population.html) |
| `IndustrySales` | [market/analysis_models.py](../market/analysis_models.py) | 상권·업종별 매출 → 분석 컨텍스트 industry_sales(상세 템플릿에서 사용) |
| `StoreTrend` | [market/analysis_models.py](../market/analysis_models.py) | 상권·업종별 운영/개업/폐업 수 → 분석 컨텍스트 store_trends(상세 템플릿에서 사용) |
| `PublicStore` | [market/analysis_models.py](../market/analysis_models.py) | 공공 매장 스냅샷·좌표·업종 → 공공 매장 지도·선택 상권 매장 집계 |
| `Attractor` | [market/analysis_models.py](../market/analysis_models.py) | 상권 주변 집객시설 → 관리자 관리용(사용자 화면 출력 예정) |
| `BrandOperation` | [market/analysis_models.py](../market/analysis_models.py) | 브랜드 운영조건·확인 출처 → 맞춤 추천·지역상권 브랜드 후보의 조건/주의사항 |
| `StoreLocation` | [market/models.py](../market/models.py) | 회원 등록 매장·후보지 위치 → 내 매장 목록/상세·공개 점주 지도 |
| `FloatingPopulation` | [market/models.py](../market/models.py) | 회원 매장별 유동인구 측정 기록 → 내 매장 상세(공공 상권·자치구 통계와 별개) |
| `TransferListing` | [market/models.py](../market/models.py) | 양도양수 매물·금액·공개 상태 → 매물 목록/상세·내 매물 |
| `TransferInquiry` | [market/models.py](../market/models.py) | 매물 문의·연락처 공개 동의 → 매물 상세의 문의 내역 |
| `PartnerPlan` | [partners/models.py](../partners/models.py) | 본사 서비스 요금제 → 입점/광고 요금제 화면 |
| `PartnerInquiry` | [partners/models.py](../partners/models.py) | 본사 입점·광고 문의 접수 → 관리자 문의 목록 |
| `PartnerAccount` | [partners/models.py](../partners/models.py) | 본사 계정·소속 브랜드·승인 상태 → 본사 신청·사업제안 접근 확인 |
| `BusinessProposal` | [partners/models.py](../partners/models.py) | 본사→회원 사업제안·수락 상태 → 제안 발송 목록·회원 수신함 |
