"""폐업 게시판의 회원 안내·인증·조회·작성·수정·삭제 처리."""

# wraps: 다른 함수로 감쌀 때 원래 함수의 이름·설명 보존
from functools import wraps

# Path: 다운로드 파일의 확장자 추출
from pathlib import Path

# messages: 처리 결과를 다음 화면에 전달하는 일회성 안내
from django.contrib import messages

# PermissionDenied: 권한 없는 요청에 403 응답 발생
from django.core.exceptions import PermissionDenied

# Paginator: 조회 결과를 페이지 단위로 분리
from django.core.paginator import Paginator

# transaction: 여러 DB 작업의 묶음 처리
from django.db import transaction

# Q: AND·OR 조건을 조합하는 검색 조건 객체
from django.db.models import Q

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

# 기존 Vary 응답 헤더를 보존하면서 Cookie 조건 추가
from django.utils.cache import patch_vary_headers

# 허용할 HTTP 요청 방식 제한
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
)

# 기존 공통 레이아웃 데이터 생성 함수 재사용
from brands.views import context_for

# 기존 검수 기록 모델과 욕설 검사 함수 재사용
from core.models import ModerationEvent
from core.moderation import flag_content

from .closure_forms import (
    ClosureReviewForm,
    ClosureReviewWriteForm,
    ClosureVerificationForm,
)
from .closure_models import ClosureReview, ClosureVerification


# 욕설 검사 대상의 게시글 텍스트 필드 지정
TEXT_FIELDS = (
    "title",
    "content",
    "advantages",
    "disadvantages",
    "advice",
)


def closure_context(request):
    """새 폐업 게시판의 공통 화면 데이터 생성."""

    # 기존 공통 레이아웃 데이터 재사용
    data = context_for(request)

    # 기존 레이아웃에서 사용할 페이지 구분값 지정
    data["page"] = "community"
    return data


def closure_member_required(view):
    """비로그인 요청에 로그인·회원가입 안내 적용."""

    # 데코레이터: 원래 함수 실행 전후에 공통 처리 추가
    # @wraps(view): 원래 뷰 함수의 이름·설명 보존
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            data = closure_context(request)

            # 로그인·회원가입 링크에 원래 요청 주소 전달
            data["next_url"] = request.get_full_path()

            # 실제 게시글 조회 함수 실행 없이 안내 화면 반환
            response = render(
                request,
                "community/closure/access.html",
                data,
            )
        else:
            # 로그인 회원의 요청만 원래 뷰 함수로 전달
            response = view(request, *args, **kwargs)

        # 회원 전용 응답의 캐시 저장 방지
        response["Cache-Control"] = "private, no-store"

        # 쿠키 상태에 따라 응답 내용이 달라진다는 정보 지정
        patch_vary_headers(response, ("Cookie",))
        return response

    return wrapped


def save_closure_review(review, request):
    """게시글 검사·저장·검수 기록 생성."""

    # 기존 검사 정책을 기준으로 텍스트 검사와 검수 상태 처리
    found = flag_content(review, request, TEXT_FIELDS)

    # 검사 결과가 반영된 게시글 저장
    review.save()

    if found:
        # _meta.label_lower: 앱이름.모델이름 형식의 식별자
        ModerationEvent.objects.create(
            target_type=review._meta.label_lower,
            target_id=review.pk,
            action=review.moderation_state,
            reason=review.moderation_reason,
            actor=request.user,
        )

        messages.info(
            request,
            "검사 대상 표현이 감지되었습니다. "
            "운영정책에 따라 일부 표현이 제거되거나 검수 처리될 수 있습니다.",
        )


# 바깥쪽 회원 검사부터 실행
# 비로그인 사용자는 인증 폼 대신 로그인·회원가입 안내 표시
@closure_member_required
@require_http_methods(["GET", "POST"])
def closure_verify(request):
    """폐업 인증 신청과 본인의 심사 내역 표시."""

    # GET: 입력값 없는 신청 폼 생성
    # POST: 전달된 일반 입력값과 업로드 파일을 연결한 폼 생성
    # 빈 POST도 제출된 폼으로 처리하기 위해 요청 방식으로 구분
    form = ClosureVerificationForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
    )

    # is_valid(): 필수값·파일·모델 검증 수행
    if request.method == "POST" and form.is_valid():
        # commit=False: DB 저장 전 모델 객체만 생성
        # 입력받지 않은 신청자·상태·동의 시각을 추가할 단계
        item = form.save(commit=False)

        item.user = request.user
        item.status = "pending"
        item.consent_at = timezone.now()
        item.save()

        messages.success(
            request,
            "폐업 인증을 접수했습니다. "
            "관리자 승인 후 글을 작성할 수 있습니다.",
        )

        # 저장 후 GET 주소로 이동하여 새로고침에 의한 중복 제출 방지
        return redirect("community:closure_verify")

    data = closure_context(request)
    data.update(
        form=form,

        # 본인의 인증 신청만 조회
        verifications=(
            ClosureVerification.objects.filter(user=request.user)
            .select_related("brand")
        ),

        # 비공개 처리된 글도 본인 내역에서 접근할 수 있도록 조회
        my_reviews=(
            ClosureReview.objects.filter(author=request.user)
            .select_related("brand")
        ),
    )

    return render(
        request,
        "community/closure/verify.html",
        data,
    )


@closure_member_required
@require_GET
def closure_list(request):
    """로그인 회원에게 공개 게시글 목록 표시."""

    # GET 검색어의 양쪽 공백 제거 및 최대 길이 제한
    query = request.GET.get("query", "").strip()[:100]

    # 두 조건을 모두 충족하는 글만 공개
    # 1. 연결된 폐업 인증이 승인 상태
    # 2. 게시글 검수 상태가 공개
    reviews = (
        ClosureReview.objects.filter(
            verification__status="approved",
            moderation_state="visible",
        )
        .select_related("author", "brand", "verification")
        .order_by("-created_at", "-pk")
    )

    if query:
        # |: OR 조건
        # icontains: 대소문자를 구분하지 않는 포함 검색
        reviews = reviews.filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
            | Q(advice__icontains=query)
            | Q(brand__name__icontains=query)
        )

    # 한 페이지당 10건 지정
    # get_page(): 잘못된 페이지 값도 가능한 페이지로 보정
    page_obj = Paginator(reviews, 10).get_page(
        request.GET.get("page")
    )

    data = closure_context(request)
    data.update(
        page_obj=page_obj,
        query=query,
    )

    return render(
        request,
        "community/closure/list.html",
        data,
    )


@closure_member_required
@require_GET
def closure_detail(request, pk):
    """공개 게시글 또는 본인 게시글의 상세 접근 허용."""

    # 공개 글은 모든 로그인 회원에게 접근 허용
    # 비공개 글은 작성자 본인에게만 관리 화면 접근 허용
    allowed = (
        Q(
            verification__status="approved",
            moderation_state="visible",
        )
        | Q(author=request.user)
    )

    # get_object_or_404(): 대상이 없거나 접근 조건에 맞지 않으면 404 반환
    review = get_object_or_404(
        ClosureReview.objects.select_related(
            "author",
            "brand",
            "verification",
        ).filter(allowed),
        pk=pk,
    )

    data = closure_context(request)
    data.update(
        review=review,
        is_author=request.user.pk == review.author_id,

        # HTML에서 실제 본문 공개 여부를 판단할 값 지정
        is_public=(
            review.verification.status == "approved"
            and review.moderation_state == "visible"
        ),

        # 인증 미승인 상태에서 게시글 수정 중지
        can_edit=review.verification.status == "approved",
    )

    return render(
        request,
        "community/closure/detail.html",
        data,
    )


@closure_member_required
@require_http_methods(["GET", "POST"])
def closure_write(request):
    """본인의 승인된 폐업 인증으로 게시글 작성."""

    # exists(): 조건에 맞는 데이터의 존재 여부만 검사
    has_approved_verification = (
        ClosureVerification.objects.filter(
            user=request.user,
            status="approved",
        ).exists()
    )

    if not has_approved_verification:
        messages.info(
            request,
            "글 작성은 폐업 인증을 승인받은 회원만 가능합니다. "
            "아래에서 인증을 신청하거나 심사 상태를 확인해주세요.",
        )
        return redirect("community:closure_verify")

    # user 인수로 로그인 회원을 전달하여 인증 선택 대상 제한
    form = ClosureReviewWriteForm(
        request.POST if request.method == "POST" else None,
        user=request.user,
    )

    if request.method == "POST" and form.is_valid():
        # atomic: 블록 내부 DB 작업을 하나의 트랜잭션으로 처리
        # 예외 발생 시 해당 DB 변경 취소
        # 파일시스템 작업까지 자동 취소되는 기능은 아님
        with transaction.atomic():

            # 저장 직전 인증 소유자·승인 상태 재검사
            # select_for_update: 지원 DB에서 조회 행의 수정 경쟁 제어
            # SQLite에서는 행 잠금 효과가 없어 서버 DB와 동작 차이 존재
            verification = (
                ClosureVerification.objects.select_for_update()
                .filter(
                    pk=form.cleaned_data["verification"].pk,
                    user=request.user,
                    status="approved",
                )
                .first()
            )

            if verification is None:
                # 상태 변경으로 저장이 불가능한 경우 입력칸 오류 지정
                form.add_error(
                    "verification",
                    "현재 승인된 본인의 인증만 사용할 수 있습니다.",
                )
            else:
                review = form.save(commit=False)

                # 작성자는 로그인 계정으로 지정
                review.author = request.user

                # 인증과 브랜드는 승인된 인증 정보로 지정
                review.verification = verification
                review.brand = verification.brand

                save_closure_review(review, request)

                messages.success(
                    request,
                    "폐업 경험을 등록했습니다.",
                )
                return redirect(
                    "community:closure_detail",
                    pk=review.pk,
                )

    data = closure_context(request)
    data.update(
        form=form,
        review=None,
    )

    return render(
        request,
        "community/closure/form.html",
        data,
    )


@closure_member_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def closure_edit(request, pk):
    """본인 게시글의 내용만 수정."""

    # 함수 전체의 DB 처리를 트랜잭션으로 묶음
    # 지원 DB에서는 기존 게시글의 동시 수정 경쟁 제어
    review = get_object_or_404(
        ClosureReview.objects.select_for_update(),
        pk=pk,
        author=request.user,
    )

    verification = get_object_or_404(
        ClosureVerification.objects.select_for_update(),
        pk=review.verification_id,
        user=request.user,
    )

    if verification.status != "approved":
        messages.error(
            request,
            "폐업 인증이 승인 상태가 아니므로 수정할 수 없습니다.",
        )
        return redirect(
            "community:closure_detail",
            pk=review.pk,
        )

    # instance 지정으로 신규 생성 대신 기존 게시글 수정
    form = ClosureReviewForm(
        request.POST if request.method == "POST" else None,
        instance=review,
    )

    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)

        # 조작된 요청으로 작성자·인증·브랜드가 바뀌지 않도록 재지정
        item.author = request.user
        item.verification = verification
        item.brand = verification.brand

        # 검수 중인 글 수정 시 기존 검수 상태 유지
        save_closure_review(item, request)

        messages.success(
            request,
            "폐업 경험을 수정했습니다.",
        )
        return redirect(
            "community:closure_detail",
            pk=item.pk,
        )

    data = closure_context(request)
    data.update(
        form=form,
        review=review,
    )

    return render(
        request,
        "community/closure/form.html",
        data,
    )


@closure_member_required
@require_http_methods(["GET", "POST"])
def closure_delete(request, pk):
    """본인 게시글 삭제 확인과 실제 삭제 처리."""

    # 작성자 조건을 서버에서 검사하여 타인 게시글 삭제 차단
    review = get_object_or_404(
        ClosureReview,
        pk=pk,
        author=request.user,
    )

    # 인증 철회 여부와 관계없이 본인 게시글 삭제 허용
    # GET 요청은 삭제하지 않고 아래 확인 화면 반환
    if request.method == "POST":
        review.delete()

        messages.success(
            request,
            "게시글을 삭제했습니다.",
        )
        return redirect("community:closure_list")

    data = closure_context(request)
    data.update(review=review)

    return render(
        request,
        "community/closure/delete.html",
        data,
    )


@closure_member_required
@require_GET
def closure_document(request, pk, kind):
    """인증 심사 권한을 가진 관리자에게 증빙 다운로드 허용."""

    # is_staff만 검사하지 않고 인증 변경 권한도 함께 검사
    # superuser는 Django의 기본 권한 처리에 따라 접근 가능
    can_review = (
        request.user.is_active
        and request.user.is_staff
        and request.user.has_perm(
            "community.change_closureverification"
        )
    )

    if not can_review:
        raise PermissionDenied

    verification = get_object_or_404(
        ClosureVerification,
        pk=pk,
    )

    # 허용된 증빙 종류만 대응
    # URL로 임의 파일 경로나 모델 필드 지정 차단
    documents = {
        "closure": verification.closure_file,
        "operation": verification.operation_file,
    }
    document = documents.get(kind)

    if not document:
        raise Http404("증빙서류가 없습니다.")

    try:
        # rb: 바이너리 읽기 모드
        handle = document.open("rb")
    except (OSError, ValueError):
        raise Http404("증빙서류를 읽을 수 없습니다.")

    extension = Path(document.name).suffix.lower()

    # FileResponse: 파일을 응답 본문으로 전송
    # as_attachment=True: 브라우저 표시 대신 다운로드 방식 지정
    # 원본 파일명 대신 인증 번호 기반 다운로드 파일명 지정
    response = FileResponse(
        handle,
        as_attachment=True,
        filename=f"closure_{pk}_{kind}{extension}",
    )

    response["Cache-Control"] = "private, no-store"

    # 브라우저의 임의 콘텐츠 형식 추측 방지
    response["X-Content-Type-Options"] = "nosniff"
    return response