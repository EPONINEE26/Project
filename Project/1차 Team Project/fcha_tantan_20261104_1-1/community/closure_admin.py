"""폐업 인증 관리자 심사 및 신규 게시글 관리 등록."""

from django import forms
from django.contrib import admin
# reverse: URL 이름과 인수를 실제 경로로 변환
from django.urls import reverse
from django.utils import timezone
# format_html: 삽입 값을 이스케이프하면서 HTML 조각 생성
from django.utils.html import format_html
# 기존 관리자 클래스 상속으로 검수 기능 재사용, 원본 클래스 수정 없음
from .admin import ModeratedAdmin
from .closure_models import ClosureReview, ClosureVerification


class ClosureVerificationAdminForm(forms.ModelForm):
    """관리자 승인 전 확인 항목과 반려·철회 사유 검증."""

    # 폼 전용 필드: 모델 컬럼은 아니며 승인 전 확인용
    # required=False: 반려·검토 중 저장에는 체크 불필요, 승인 시 clean에서 필수 검사
    identity_checked = forms.BooleanField(
        label="신청자가 해당 사업체를 운영한 사람임을 확인했습니다.", required=False,
    )
    closure_checked = forms.BooleanField(
        label="제출 서류의 사업체와 폐업 사실을 확인했습니다.", required=False,
    )
    brand_checked = forms.BooleanField(
        label="운영했던 브랜드와 사업체의 관계를 확인했습니다.", required=False,
    )

    class Meta:
        model = ClosureVerification
        # 심사 결과만 변경 허용, 원본 신청 정보 편집 제외
        fields = ("status", "decision_reason")

    def clean(self):
        # 부모 검증 결과 수신 후 여러 입력칸에 걸친 추가 조건 검사
        data = super().clean()
        status = data.get("status")
        if status == "approved":
            for name in ("identity_checked", "closure_checked", "brand_checked"):
                if not data.get(name):
                    self.add_error(name, "승인 전 확인이 필요합니다.")
        if status in ("rejected", "revoked"):
            if not data.get("decision_reason", "").strip():
                self.add_error("decision_reason", "반려 또는 승인 철회 사유를 입력해주세요.")
        return data


# admin.register: 해당 모델의 관리자 화면 등록
@admin.register(ClosureVerification)
class ClosureVerificationAdmin(admin.ModelAdmin):
    form = ClosureVerificationAdminForm
    # list_display: 관리자 목록의 표시 열
    list_display = ("id", "user", "brand", "store_name", "closed_on", "status", "submitted_at", "reviewed_at")
    # list_filter: 목록 우측의 필터
    list_filter = ("status", "submitted_at")
    # search_fields: 관리자 검색 대상, __: 연결 모델의 필드 접근
    search_fields = ("user__username", "brand__name", "store_name", "business_number")
    # readonly_fields: 화면에 표시하지만 직접 편집하지 못할 항목
    readonly_fields = (
        "user", "brand", "store_name", "business_number", "opened_on", "closed_on",
        "evidence_links", "consent_at", "submitted_at", "reviewed_at", "reviewed_by",
    )
    # fields: 상세 화면 표시 순서, 원본 FileField 대신 권한 검사 링크 표시
    fields = (
        "user", "brand", "store_name", "business_number", "opened_on", "closed_on",
        "evidence_links", "consent_at", "submitted_at", "reviewed_at", "reviewed_by",
        "identity_checked", "closure_checked", "brand_checked", "status", "decision_reason",
    )

    @admin.display(description="제출 증빙 다운로드")
    def evidence_links(self, obj):
        # obj: 현재 관리자 상세 화면의 인증 객체
        if not obj or not obj.pk:
            return "-"
        # kwargs: 경로 변수 이름과 값을 전달하는 딕셔너리
        closure_url = reverse("community:closure_document", kwargs={"pk": obj.pk, "kind": "closure"})
        operation_url = reverse("community:closure_document", kwargs={"pk": obj.pk, "kind": "operation"})
        # FileField.url 호출 제외, 관리자 권한을 확인하는 뷰 주소만 제공
        return format_html(
            '<a href="{}">폐업 사실 확인 서류</a><br><a href="{}">브랜드 운영 이력 서류</a>',
            closure_url, operation_url,
        )

    def save_model(self, request, obj, form, change):
        # 관리자 저장 직전 실제 심사자와 심사 시각 기록
        obj.reviewed_by = request.user
        obj.reviewed_at = timezone.now()
        if obj.status == "approved":
            # 승인 후 이전 반려 사유의 화면 잔존 방지
            obj.decision_reason = ""
        # 부모의 실제 저장 처리 호출, change: 기존 데이터 변경 여부
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        # 관리자 화면의 인증 임의 생성 기능 제외
        return False

    def has_delete_permission(self, request, obj=None):
        # 인증 이력 삭제 제외, 반려·승인 철회 방식으로 상태 관리
        return False


@admin.register(ClosureReview)
class ClosureReviewAdmin(ModeratedAdmin):
    """기존 검수 관리자 기능을 새 폐업 게시글에 적용."""
    list_display = ("id", "topic", "title", "author", "brand", "verification", "moderation_state", "created_at")
    list_filter = ModeratedAdmin.list_filter + ("topic",)
    search_fields = ("title", "content", "advice", "author__username", "brand__name")
    # 튜플 + 연산: 부모 읽기 전용 항목을 유지하면서 새 항목 추가
    readonly_fields = ModeratedAdmin.readonly_fields + ("author", "brand", "verification")

    def has_add_permission(self, request):
        # 관리자에서 인증을 우회하는 신규 게시글 생성 제외
        return False
