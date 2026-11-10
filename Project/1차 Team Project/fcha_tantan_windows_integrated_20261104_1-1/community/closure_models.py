"""폐업 인증과 폐업 경험 게시글의 DB 구조."""

from django.conf import settings
# ValidationError: 입력 검증 실패를 폼 또는 관리자 화면에 전달하는 예외
from django.core.exceptions import ValidationError
# 각 검증기: 최댓값 검사, 최솟값 검사, 정규식 형식 검사
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
# timezone: 프로젝트 시간대 기준 날짜와 시각 처리
from django.utils import timezone

# 기존 검사 함수: 10MB 이하 용량 및 PDF/JPG/PNG 기본 파일 헤더 검사
# 서류 내용·진위·명의의 자동 인증 기능은 아님
from core.documents import validate_evidence
from .closure_files import closure_evidence_path, closure_evidence_storage
# 기존 추상 모델: 검수 상태·작성일·수정일을 신규 테이블에 재사용
from .models import ModeratedContent


class ClosureVerification(models.Model):
    """폐업 인증 신청 저장 모델."""

    # choices: (실제 저장값, 화면 표시값) 목록
    STATUS_CHOICES = [
        ("pending", "검토 중"),
        ("approved", "승인"),
        ("rejected", "반려"),
        ("revoked", "승인 철회"),
    ]

    # ForeignKey: 다른 테이블의 데이터 한 건과 연결하는 외래 키
    # AUTH_USER_MODEL: 프로젝트에서 사용하는 회원 모델 설정
    # CASCADE: 회원 삭제 시 연결된 인증 신청도 삭제
    # related_name: 회원에서 인증 신청을 역방향 조회할 때 사용할 이름
    # verbose_name: 관리자·폼에 표시할 필드 이름
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="closure_verifications", verbose_name="신청자",
    )
    # "앱이름.모델이름": 모델 클래스를 직접 가져오지 않는 문자열 참조
    # PROTECT: 인증이 참조 중인 브랜드의 삭제 차단
    brand = models.ForeignKey(
        "brands.Brand", on_delete=models.PROTECT,
        related_name="closure_verifications", verbose_name="운영했던 브랜드",
    )
    # CharField: 최대 길이가 정해진 문자열 저장
    store_name = models.CharField("운영했던 지점명", max_length=100)
    business_number = models.CharField(
        "사업자등록번호", max_length=10,
        validators=[
            # RegexValidator: 정규식에 맞는 문자열인지 검사
            # ^: 시작, [0-9]: 숫자, {10}: 10번 반복, $: 끝
            # 사업자등록번호의 숫자 10자리 형식 검사이며 실제 발급 여부 검사는 아님
            RegexValidator(
                regex=r"^[0-9]{10}$",
                message="하이픈 없이 숫자 10자리로 입력해주세요.",
            ),
        ],
    )
    # DateField: 시각을 제외한 날짜 저장
    opened_on = models.DateField("개업일")
    closed_on = models.DateField("폐업일")

    # FileField: DB에는 파일 경로 저장, 실제 파일은 저장소에 별도 보관
    # storage: 비공개 저장소 지정, upload_to: 상대 저장 경로 생성 함수 지정
    # validators: 폼·모델 검증 과정에서 실행할 검사 함수 목록
    closure_file = models.FileField(
        "폐업 사실 확인 서류", storage=closure_evidence_storage,
        upload_to=closure_evidence_path, validators=[validate_evidence],
    )
    operation_file = models.FileField(
        "브랜드 운영 이력 확인 서류", storage=closure_evidence_storage,
        upload_to=closure_evidence_path, validators=[validate_evidence],
    )
    # default: 새 객체의 기본값, choices: 허용 선택값 지정
    status = models.CharField(
        "심사 상태", max_length=10, choices=STATUS_CHOICES, default="pending",
    )
    # TextField: 긴 문자열 저장, blank=True: 폼 검증 시 빈 값 허용
    decision_reason = models.TextField("반려·철회 사유", max_length=2000, blank=True)
    consent_at = models.DateTimeField("증빙 심사 동의 일시")
    # auto_now_add: 최초 저장 시 현재 시각 자동 입력
    submitted_at = models.DateTimeField("신청일", auto_now_add=True)
    # null=True: DB에서 값 없음 허용, blank=True: 폼에서 미입력 허용
    reviewed_at = models.DateTimeField("최근 심사일", null=True, blank=True)
    # SET_NULL: 관리자 계정 삭제 시 인증 이력 유지, 연결된 심사자만 비움
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="reviewed_closure_verifications", verbose_name="최근 심사 관리자",
        null=True, blank=True,
    )

    class Meta:
        # Meta: 모델의 표시 이름·기본 정렬·DB 제약조건 등 부가 설정
        verbose_name = "폐업 인증"
        verbose_name_plural = "폐업 인증"
        # -: 내림차순, pk: 각 행의 고유 식별자인 기본키
        ordering = ["-submitted_at", "-pk"]
        constraints = [
            # CheckConstraint: DB에 저장할 값이 지정 조건을 만족하도록 강제하는 제약조건
            # Q: 검사 조건 표현, __gte: 이상(>=), F: 같은 행의 다른 필드 값 참조
            # 폐업일이 개업일 이상이라는 날짜 순서 조건 지정
            # name: DB와 마이그레이션에서 제약조건을 식별할 고유 이름
            models.CheckConstraint(
                condition=models.Q(closed_on__gte=models.F("opened_on")),
                name="closure_dates_in_order",
            ),
        ]

    def __str__(self):
        # __str__: 관리자·선택 상자 등에서 객체를 문자열로 표시할 때 사용할 값
        # get_status_display(): choices의 저장값에 대응하는 표시 문구 반환
        return f"인증 #{self.pk} · {self.brand.name} · {self.get_status_display()}"

    def clean(self):
        # clean: 모델 검증 단계에 추가할 사용자 정의 검사
        # ModelForm 검증 시 호출, 일반 save()에서 자동 호출되는 것은 아님
        super().clean()
        # localdate: 프로젝트 시간대 기준 오늘 날짜
        if self.closed_on and self.closed_on > timezone.localdate():
            # 딕셔너리 키: 오류를 표시할 입력칸 이름
            raise ValidationError({"closed_on": "폐업일은 오늘 이후일 수 없습니다."})
        if self.opened_on and self.closed_on and self.opened_on > self.closed_on:
            raise ValidationError({"closed_on": "폐업일은 개업일보다 빠를 수 없습니다."})


class ClosureReview(ModeratedContent):
    """승인된 인증에 연결되는 폐업 경험 게시글."""

    # 추상 모델 상속: 부모 필드를 신규 테이블에 포함, 기존 Post·Comment 테이블 변경 없음
    # PROTECT: 게시글에 연결된 인증 신청의 삭제 방지
    verification = models.ForeignKey(
        ClosureVerification, on_delete=models.PROTECT,
        related_name="reviews", verbose_name="폐업 인증",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="closure_reviews", verbose_name="작성자",
    )
    brand = models.ForeignKey(
        "brands.Brand", on_delete=models.PROTECT,
        related_name="closure_reviews", verbose_name="브랜드",
    )
    title = models.CharField("제목", max_length=200)
    content = models.TextField("운영과 폐업 경험", max_length=10000)
    advantages = models.TextField("운영하면서 좋았던 점", max_length=3000, blank=True)
    disadvantages = models.TextField("운영하면서 어려웠던 점", max_length=3000, blank=True)
    advice = models.TextField("예비창업자에게 전하고 싶은 조언", max_length=5000)
    # PositiveSmallIntegerField: 작은 범위의 0 이상 정수 저장 필드
    # MinValueValidator·MaxValueValidator: 폼·모델 검증에서 최솟값·최댓값 검사
    # DB 직접 저장에 대한 강제 조건은 아래 CheckConstraint에서 별도 지정
    brand_rating = models.PositiveSmallIntegerField(
        "브랜드 평가", validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1점: 매우 불만족 / 5점: 매우 만족",
    )
    restart_interest = models.PositiveSmallIntegerField(
        "재창업 의향", validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1점: 전혀 없음 / 5점: 매우 높음",
    )

    class Meta:
        verbose_name = "폐업 경험 게시글"
        verbose_name_plural = "폐업 경험 게시글"
        ordering = ["-created_at", "-pk"]
        constraints = [
            # CheckConstraint 자체의 의미: DB 저장값에 조건을 강제하는 제약조건
            # 범위 지정 부분: __gte=1은 1 이상, __lte=5는 5 이하
            # Q 안의 두 조건은 AND로 결합되어 브랜드 평가 1~5만 허용
            models.CheckConstraint(
                condition=models.Q(brand_rating__gte=1, brand_rating__lte=5),
                name="closure_brand_rating_range",
            ),
            # 같은 DB 제약조건 방식으로 재창업 의향을 1~5로 제한
            models.CheckConstraint(
                condition=models.Q(restart_interest__gte=1, restart_interest__lte=5),
                name="closure_restart_rating_range",
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def public_title(self):
        # property: 괄호 없이 속성처럼 접근할 수 있는 계산값 지정
        # review.public_title 접근 시 아래 분기 실행
        # 검수 중인 제목 대신 기존 검수 안내 문구 반환
        if self.moderation_state == "visible":
            return self.title
        return self.visibility_message
