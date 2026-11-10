"""폐업 인증과 폐업 경험 게시판 전용 DB 모델."""

from django.conf import settings
from django.core.exceptions import ValidationError

# 입력값의 최솟값·최댓값·문자열 형식 검사
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)

from django.db import models
from django.utils import timezone

# 기존 프로젝트의 파일 용량·확장자·기본 파일 헤더 검사 함수 재사용
from core.documents import validate_evidence

from .closure_files import (
    closure_evidence_path,
    closure_evidence_storage,
)

# 기존 추상 모델의 검수 필드·작성일·수정일 재사용
# 기존 Post·Comment 테이블 변경 없이 신규 테이블에 필드 포함
from .models import ModeratedContent


class ClosureVerification(models.Model):
    """폐업 인증 신청 정보."""

    # 실제 DB 저장값과 화면 표시 문구의 쌍 지정
    STATUS_CHOICES = [
        ("pending", "검토 중"),
        ("approved", "승인"),
        ("rejected", "반려"),
        ("revoked", "승인 철회"),
    ]

    # ForeignKey: 다른 테이블의 데이터 한 건과 연결
    # AUTH_USER_MODEL: 현재 프로젝트에서 사용하는 회원 모델 참조
    # CASCADE: 회원 삭제 시 해당 회원의 인증 신청도 삭제
    # related_name: 회원 객체에서 인증 신청 목록 조회 시 사용할 이름
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="closure_verifications",
        verbose_name="신청자",
    )

    # 문자열 모델 참조로 brands 앱의 Brand 모델과 연결
    # PROTECT: 인증에서 참조 중인 브랜드의 삭제 방지
    brand = models.ForeignKey(
        "brands.Brand",
        on_delete=models.PROTECT,
        related_name="closure_verifications",
        verbose_name="운영했던 브랜드",
    )

    store_name = models.CharField(
        "운영했던 지점명",
        max_length=100,
    )

    # 사업자등록번호의 숫자 10자리 형식 검사
    # 실제 사업자 정보의 진위 판별은 관리자 심사 대상
    business_number = models.CharField(
        "사업자등록번호",
        max_length=10,
        validators=[
            RegexValidator(
                regex=r"^[0-9]{10}$",
                message="하이픈 없이 숫자 10자리로 입력해주세요.",
            ),
        ],
    )

    opened_on = models.DateField("개업일")
    closed_on = models.DateField("폐업일")

    # FileField: DB에는 파일 경로 저장, 실제 파일은 저장소에 보관
    # storage: 비공개 전용 저장소 지정
    # upload_to: 회원 번호와 임의 파일명으로 저장 경로 생성
    # validators: 파일 형식·용량 검사
    closure_file = models.FileField(
        "폐업 사실 확인 서류",
        storage=closure_evidence_storage,
        upload_to=closure_evidence_path,
        validators=[validate_evidence],
    )

    operation_file = models.FileField(
        "브랜드 운영 이력 확인 서류",
        storage=closure_evidence_storage,
        upload_to=closure_evidence_path,
        validators=[validate_evidence],
    )

    # 신규 신청의 기본 상태를 검토 중으로 지정
    status = models.CharField(
        "심사 상태",
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
    )

    # blank=True: 폼에서 빈 값 허용
    decision_reason = models.TextField(
        "반려·철회 사유",
        max_length=2000,
        blank=True,
    )

    consent_at = models.DateTimeField("증빙 심사 동의 일시")

    # auto_now_add: 최초 저장 시 현재 시각 자동 입력
    submitted_at = models.DateTimeField(
        "신청일",
        auto_now_add=True,
    )

    # null=True: DB에 값 없음 허용
    # 심사 전에는 심사일과 심사자 미지정
    reviewed_at = models.DateTimeField(
        "최근 심사일",
        null=True,
        blank=True,
    )

    # SET_NULL: 심사 관리자 계정 삭제 시 인증 기록 유지, 심사자만 비움
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_closure_verifications",
        verbose_name="최근 심사 관리자",
        null=True,
        blank=True,
    )

    class Meta:
        # Meta: 테이블 생성·조회·관리자 표시 관련 옵션 지정
        verbose_name = "폐업 인증"
        verbose_name_plural = "폐업 인증"

        # - 접두사: 내림차순 정렬
        # 같은 신청 시각에는 큰 PK부터 정렬
        ordering = ["-submitted_at", "-pk"]

        # CheckConstraint: DB 저장 단계의 조건 검사
        # Q: 조건 표현, F: 같은 행의 다른 필드 값 참조
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    closed_on__gte=models.F("opened_on"),
                ),
                name="closure_dates_in_order",
            ),
        ]

    def __str__(self):
        # 관리자·선택 상자 등에서 사용할 객체 표시 문자열 반환
        return (
            f"인증 #{self.pk} · {self.brand.name} · "
            f"{self.get_status_display()}"
        )

    def clean(self):
        """폼·관리자 검증 과정의 날짜 검사."""

        # 부모 모델의 검증 처리 유지
        super().clean()

        # timezone.localdate(): 프로젝트 시간대 기준 오늘 날짜
        if self.closed_on and self.closed_on > timezone.localdate():
            raise ValidationError({
                "closed_on": "폐업일은 오늘 이후일 수 없습니다.",
            })

        if (
            self.opened_on
            and self.closed_on
            and self.opened_on > self.closed_on
        ):
            raise ValidationError({
                "closed_on": "폐업일은 개업일보다 빠를 수 없습니다.",
            })


class ClosureReview(ModeratedContent):
    """승인된 폐업 인증을 근거로 작성하는 경험 게시글."""

    # ModeratedContent: 기존 추상 모델
    # 추상 모델 상속으로 검수 상태·작성일·수정일 필드 재사용
    # 기존 게시글 데이터와 별도 테이블 사용

    # PROTECT: 게시글이 연결된 인증 신청의 삭제 방지
    verification = models.ForeignKey(
        ClosureVerification,
        on_delete=models.PROTECT,
        related_name="reviews",
        verbose_name="폐업 인증",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="closure_reviews",
        verbose_name="작성자",
    )

    brand = models.ForeignKey(
        "brands.Brand",
        on_delete=models.PROTECT,
        related_name="closure_reviews",
        verbose_name="브랜드",
    )

    title = models.CharField(
        "제목",
        max_length=200,
    )

    content = models.TextField(
        "운영과 폐업 경험",
        max_length=10000,
    )

    advantages = models.TextField(
        "운영하면서 좋았던 점",
        max_length=3000,
        blank=True,
    )

    disadvantages = models.TextField(
        "운영하면서 어려웠던 점",
        max_length=3000,
        blank=True,
    )

    advice = models.TextField(
        "예비창업자에게 전하고 싶은 조언",
        max_length=5000,
    )

    # PositiveSmallIntegerField: 작은 범위의 0 이상 정수 저장
    # validators로 폼·모델 검증 시 실제 허용 범위를 1~5로 제한
    brand_rating = models.PositiveSmallIntegerField(
        "브랜드 평가",
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1점: 매우 불만족 / 5점: 매우 만족",
    )

    restart_interest = models.PositiveSmallIntegerField(
        "재창업 의향",
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1점: 전혀 없음 / 5점: 매우 높음",
    )

    class Meta:
        verbose_name = "폐업 경험 게시글"
        verbose_name_plural = "폐업 경험 게시글"
        ordering = ["-created_at", "-pk"]

        # 폼 검증 외에 DB에서도 점수 범위 제한
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    brand_rating__gte=1,
                    brand_rating__lte=5,
                ),
                name="closure_brand_rating_range",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    restart_interest__gte=1,
                    restart_interest__lte=5,
                ),
                name="closure_restart_rating_range",
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def public_title(self):
        # property: 함수 호출 괄호 없이 속성처럼 접근하는 계산값
        # 검수 중인 글의 실제 제목 노출 방지
        if self.moderation_state == "visible":
            return self.title
        return self.visibility_message