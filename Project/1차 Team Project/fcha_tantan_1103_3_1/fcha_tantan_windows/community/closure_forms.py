"""폐업 인증 신청·게시글 입력 폼과 입력값 검증."""

from django import forms

# 기존 브랜드 검색 입력 필드 재사용
from brands.lookup import BrandLookupField

from .closure_models import ClosureReview, ClosureVerification


class ClosureVerificationForm(forms.ModelForm):
    """모델 필드 기반의 폐업 인증 신청 폼."""

    # ModelForm: 모델 정의를 기준으로 입력칸·필수값·검증 규칙 생성
    # 기본 브랜드 선택 상자 대신 기존 검색 입력 필드 지정
    brand = BrandLookupField(label="운영했던 브랜드")

    # 모델에 저장하는 필드가 아닌 폼 전용 동의 항목
    # 체크하지 않으면 form.is_valid() 실패
    consent = forms.BooleanField(
        label=(
            "폐업 사실과 운영 이력 확인을 위해 제출한 정보를 "
            "관리자가 검토하는 것에 동의합니다."
        ),
        required=True,
    )

    class Meta:
        model = ClosureVerification

        # 사용자 입력을 허용할 모델 필드만 지정
        # 신청자·심사 상태·심사자·동의 시각은 입력 대상에서 제외
        fields = (
            "brand",
            "store_name",
            "business_number",
            "opened_on",
            "closed_on",
            "closure_file",
            "operation_file",
        )

        # widgets: 각 필드의 HTML 입력 요소 지정
        widgets = {
            "opened_on": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "closed_on": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "business_number": forms.TextInput(
                attrs={
                    "inputmode": "numeric",
                    "maxlength": 10,
                    "placeholder": "하이픈 없이 숫자 10자리",
                },
            ),
        }

        # help_texts: 입력칸 아래에 표시할 도움말 지정
        help_texts = {
            "closure_file": (
                "폐업 사실을 확인할 수 있는 서류를 제출해주세요. "
                "PDF·JPG·PNG, 파일당 10MB 이하."
            ),
            "operation_file": (
                "신청자와 해당 브랜드·사업체의 관계를 확인할 수 있는 "
                "계약서 등 증빙을 제출해주세요. "
                "PDF·JPG·PNG, 파일당 10MB 이하."
            ),
        }


class ClosureReviewForm(forms.ModelForm):
    """게시글 내용 입력 폼."""

    class Meta:
        model = ClosureReview

        # 작성자·브랜드·연결된 인증은 사용자 변경 대상에서 제외
        fields = (
            "title",
            "content",
            "advantages",
            "disadvantages",
            "advice",
            "brand_rating",
            "restart_interest",
        )

        widgets = {
            "content": forms.Textarea(attrs={"rows": 8}),
            "advantages": forms.Textarea(attrs={"rows": 4}),
            "disadvantages": forms.Textarea(attrs={"rows": 4}),
            "advice": forms.Textarea(attrs={"rows": 6}),

            # min·max는 브라우저 입력 안내
            # 실제 범위 검증은 모델 validators에서도 수행
            "brand_rating": forms.NumberInput(
                attrs={"min": 1, "max": 5},
            ),
            "restart_interest": forms.NumberInput(
                attrs={"min": 1, "max": 5},
            ),
        }


class ClosureReviewWriteForm(ClosureReviewForm):
    """새 게시글 작성 시 승인된 인증 선택 항목 추가."""

    # ModelChoiceField: 모델 객체 한 건 선택 및 선택값 검증
    # 기본 조회 대상을 비워 다른 회원의 인증 노출 방지
    verification = forms.ModelChoiceField(
        label="승인된 폐업 인증",
        queryset=ClosureVerification.objects.none(),
        empty_label="승인된 인증을 선택해주세요.",
    )

    # 화면에 표시할 입력 항목 순서 지정
    field_order = (
        "verification",
        "title",
        "content",
        "advantages",
        "disadvantages",
        "advice",
        "brand_rating",
        "restart_interest",
    )

    def __init__(self, *args, user, **kwargs):
        # *args: 전달된 위치 인수 묶음
        # **kwargs: 전달된 이름 있는 인수 묶음
        # 부모 폼 초기화 후 로그인 회원 기준의 선택 대상 지정
        super().__init__(*args, **kwargs)

        self.fields["verification"].queryset = (
            ClosureVerification.objects.filter(
                user=user,
                status="approved",
            )
            # 연결된 브랜드를 함께 조회하여 추가 DB 조회 감소
            .select_related("brand")
        )