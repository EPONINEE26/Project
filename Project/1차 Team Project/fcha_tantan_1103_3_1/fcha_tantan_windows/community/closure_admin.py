"""폐업 인증 관리자 심사와 게시글 관리 화면 등록."""

from django import forms
from django.contrib import admin

# URL 이름을 실제 경로로 변환
from django.urls import reverse
from django.utils import timezone

# 삽입되는 값을 이스케이프하면서 HTML 조각 생성
from django.utils.html import format_html

# 기존 관리자 검수 기능을 새 모델에 재사용
from .admin import ModeratedAdmin
from .closure_models import ClosureReview, ClosureVerification


class ClosureVerificationAdminForm(forms.ModelForm):
    """인증 승인 전 관리자 확인 항목."""

    # 모델에 저장되지 않는 관리자 폼 전용 확인 항목
    identity_checked = forms.BooleanField(
        label="신청자가 해당 사업체를 운영한 사람임을 확인했습니다.",
        required=False,
    )

    closure_checked = forms.BooleanField(
        label="제출 서류의 사업체와 폐업 사실을 확인했습니다.",
        required=False,
    )

    brand_checked = forms.BooleanField(
        label="운영했던 브랜드와 사업체의 관계를 확인했습니다.",
        required=False,
    )

    class Meta:
        model = ClosureVerification

        # 심사 상태와 사유만 관리자 변경 대상으로 지정
        fields = ("status", "decision_reason")

    def clean(self):
        # 부모 폼의 기본 검증 결과 수신
        data = super().clean()
        status = data.get("status")

        # 승인 상태 저장 시 세 확인 항목의 체크 여부 검사
        if status == "approved":
            checks = (
                "identity_checked",
                "closure_checked",
                "brand_checked",
            )
            for name in checks:
                if not data.get(name):
                    self.add_error(
                        name,
                        "승인 전 확인이 필요합니다.",
                    )

        # 반려·철회 시 신청자에게 전달할 사유 필수 지정
        if status in ("rejected", "revoked"):
            reason = data.get("decision_reason", "").strip()

            if not reason:
                self.add_error(
                    "decision_reason",
                    "반려 또는 승인 철회 사유를 입력해주세요.",
                )

        return data


# register: 지정 모델의 관리자 화면 등록
@admin.register(ClosureVerification)
class ClosureVerificationAdmin(admin.ModelAdmin):
    form = ClosureVerificationAdminForm

    # 관리자 목록 화면의 표시 열 지정
    list_display = (
        "id",
        "user",
        "brand",
        "store_name",
        "closed_on",
        "status",
        "submitted_at",
        "reviewed_at",
    )

    # 관리자 목록 화면의 필터 지정
    list_filter = ("status", "submitted_at")

    # 관리자 검색 대상 지정
    # __: 연결된 모델의 필드 접근
    search_fields = (
        "user__username",
        "brand__name",
        "store_name",
        "business_number",
    )

    # 신청 원본과 심사 기록의 직접 편집 제외
    readonly_fields = (
        "user",
        "brand",
        "store_name",
        "business_number",
        "opened_on",
        "closed_on",
        "evidence_links",
        "consent_at",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
    )

    # 관리자 상세 화면의 표시 항목과 순서 지정
    # FileField 원본 대신 권한 검사 다운로드 링크 표시
    fields = (
        "user",
        "brand",
        "store_name",
        "business_number",
        "opened_on",
        "closed_on",
        "evidence_links",
        "consent_at",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
        "identity_checked",
        "closure_checked",
        "brand_checked",
        "status",
        "decision_reason",
    )

    @admin.display(description="제출 증빙 다운로드")
    def evidence_links(self, obj):
        if not obj or not obj.pk:
            return "-"

        # URL 이름과 인증 번호를 이용한 다운로드 주소 생성
        closure_url = reverse(
            "community:closure_document",
            kwargs={
                "pk": obj.pk,
                "kind": "closure",
            },
        )

        operation_url = reverse(
            "community:closure_document",
            kwargs={
                "pk": obj.pk,
                "kind": "operation",
            },
        )

        return format_html(
            '<a href="{}">폐업 사실 확인 서류</a><br>'
            '<a href="{}">브랜드 운영 이력 서류</a>',
            closure_url,
            operation_url,
        )

    def save_model(self, request, obj, form, change):
        # 실제 저장을 수행한 관리자와 시각 기록
        obj.reviewed_by = request.user
        obj.reviewed_at = timezone.now()

        if obj.status == "approved":
            # 승인 후 이전 반려 사유의 화면 잔존 방지
            obj.decision_reason = ""

        # Django 기본 관리자 저장 처리 호출
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        # 관리자 화면에서 인증 신청을 임의 생성하는 기능 제외
        return False

    def has_delete_permission(self, request, obj=None):
        # 인증 이력 삭제 제외
        # 반려·승인 철회를 통한 상태 관리
        return False


@admin.register(ClosureReview)
class ClosureReviewAdmin(ModeratedAdmin):
    """기존 검수 기능을 새 폐업 게시글에 적용."""

    list_display = (
        "id",
        "title",
        "author",
        "brand",
        "verification",
        "moderation_state",
        "created_at",
    )

    search_fields = (
        "title",
        "content",
        "advice",
        "author__username",
        "brand__name",
    )

    # 부모 관리자의 읽기 전용 항목에 연결 정보 추가
    # 작성자·브랜드·인증의 관리자 변경 제외
    readonly_fields = ModeratedAdmin.readonly_fields + (
        "author",
        "brand",
        "verification",
    )

    def has_add_permission(self, request):
        # 관리자 화면에서 인증 절차를 우회한 신규 게시글 생성 제외
        return False