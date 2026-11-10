"""인증 신청과 게시글 입력값의 폼 생성·검증."""

from django import forms
# 기존 프로젝트의 브랜드 검색 입력 필드 재사용
from brands.lookup import BrandLookupField
from .closure_models import ClosureReview, ClosureVerification


class ClosureVerificationForm(forms.ModelForm):
    """모델 필드를 바탕으로 생성하는 폐업 인증 신청 폼."""

    # ModelForm: 모델 정의를 이용한 입력칸·필수값·검증 규칙 생성 클래스
    # 기본 외래 키 선택 상자를 기존 브랜드 검색 필드로 대체
    brand = BrandLookupField(label="운영했던 브랜드")
    # 모델에 저장되지 않는 폼 전용 체크 항목
    # required=True: 체크하지 않으면 폼 검증 실패
    consent = forms.BooleanField(
        label="폐업 사실과 운영 이력 확인을 위해 제출한 정보를 관리자가 검토하는 것에 동의합니다.",
        required=True,
    )

    class Meta:
        # model: 폼의 저장 대상 모델
        model = ClosureVerification
        # fields: 사용자가 입력 가능한 모델 필드만 지정
        # 신청자·승인 상태·심사자·동의 시각은 조작 방지를 위해 제외
        fields = (
            "brand", "store_name", "business_number", "opened_on", "closed_on",
            "closure_file", "operation_file",
        )
        # widgets: 화면에 출력할 HTML 입력 요소 지정
        # attrs: HTML 속성, format: 입력 요소에 표시할 날짜 형식
        widgets = {
            "opened_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "closed_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "business_number": forms.TextInput(attrs={
                "inputmode": "numeric", "maxlength": 10,
                "placeholder": "하이픈 없이 숫자 10자리",
            }),
        }
        # help_texts: 각 입력칸 아래에 표시할 도움말 지정
        help_texts = {
            "closure_file": "폐업 사실 확인 서류. PDF·JPG·PNG, 파일당 10MB 이하.",
            "operation_file": "신청자와 브랜드·사업체의 관계를 확인할 계약서 등 증빙. PDF·JPG·PNG, 파일당 10MB 이하.",
        }


class ClosureReviewForm(forms.ModelForm):
    """게시글 내용의 작성·수정 폼."""

    class Meta:
        model = ClosureReview
        # 작성자·브랜드·인증은 사용자 입력 대상에서 제외
        fields = (
            "title", "content", "advantages", "disadvantages", "advice",
            "brand_rating", "restart_interest",
        )
        widgets = {
            # Textarea: 여러 줄 입력 요소, rows: 화면에 표시할 줄 수
            "content": forms.Textarea(attrs={"rows": 8}),
            "advantages": forms.Textarea(attrs={"rows": 4}),
            "disadvantages": forms.Textarea(attrs={"rows": 4}),
            "advice": forms.Textarea(attrs={"rows": 6}),
            # min·max: 브라우저 입력 범위 안내
            # 서버 검증과 DB 제약조건을 대신하는 기능은 아님
            "brand_rating": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "restart_interest": forms.NumberInput(attrs={"min": 1, "max": 5}),
        }


class ClosureReviewWriteForm(ClosureReviewForm):
    """신규 글 작성 시 본인의 승인된 인증 선택 항목 추가."""

    # ModelChoiceField: DB 객체 한 건 선택 및 선택값의 조회 대상 포함 여부 검사
    # none(): 기본 선택 대상을 비워 초기 상태의 타인 인증 노출 방지
    verification = forms.ModelChoiceField(
        label="승인된 폐업 인증",
        queryset=ClosureVerification.objects.none(),
        empty_label="승인된 인증을 선택해주세요.",
    )
    # 모델 저장 항목과 별개로 화면의 입력칸 표시 순서 지정
    field_order = (
        "verification", "title", "content", "advantages", "disadvantages",
        "advice", "brand_rating", "restart_interest",
    )

    def __init__(self, *args, user, **kwargs):
        # *args: 위치 인수 묶음, **kwargs: 이름 있는 인수 묶음
        # user: 뷰에서 전달한 로그인 회원 객체
        # 부모 폼 초기화 후 인증 선택 대상 제한
        super().__init__(*args, **kwargs)
        self.fields["verification"].queryset = (
            ClosureVerification.objects.filter(user=user, status="approved")
            # select_related: 외래 키의 브랜드를 함께 조회하여 추가 쿼리 감소
            .select_related("brand")
        )
