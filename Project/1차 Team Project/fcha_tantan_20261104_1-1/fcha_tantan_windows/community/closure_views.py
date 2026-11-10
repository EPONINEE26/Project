"""폐업 게시판의 접근 권한·인증·조회·저장·삭제 처리."""

# wraps: 함수를 감쌀 때 원래 함수의 이름과 설명 보존
from functools import wraps
from pathlib import Path
# messages: 다음 화면에 일회성 처리 결과 안내 전달
from django.contrib import messages
# PermissionDenied: 권한 없는 요청에 403 응답 발생
from django.core.exceptions import PermissionDenied
# Paginator: 조회 결과를 페이지 단위로 분리
from django.core.paginator import Paginator
# transaction: 여러 DB 작업을 하나의 처리 묶음으로 관리
from django.db import transaction
# Q: AND·OR 조건을 조합하는 검색 조건 객체
from django.db.models import Q
# FileResponse: 파일 전송 응답, Http404: 없는 대상에 404 응답 발생
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
# patch_vary_headers: 기존 Vary 헤더를 보존하면서 쿠키 조건 추가
from django.utils.cache import patch_vary_headers
# 요청 방식 제한용 데코레이터
from django.views.decorators.http import require_GET, require_http_methods

from brands.views import context_for
from core.models import ModerationEvent
from core.moderation import flag_content
from .closure_forms import ClosureReviewForm, ClosureReviewWriteForm, ClosureVerificationForm
from .closure_models import ClosureReview, ClosureVerification


# 기존 욕설 검사 함수에 전달할 텍스트 필드 이름 지정
TEXT_FIELDS = ("title", "content", "advantages", "disadvantages", "advice")


def closure_context(request):
    """폐점주 화면에 필요한 정보와 분류 목록 전달."""
    data = context_for(request)
    data["page"] = "community"
    data["community_board"] = "closure"

    # 비로그인 화면에도 네 가지 분류 버튼을 표시하기 위한 목록
    data["topics"] = ClosureReview.TOPICS

    # 선택한 분류를 검사하고 화면에 전달
    topic = request.GET.get("topic", "")
    if topic not in dict(ClosureReview.TOPICS):
        topic = ""
    data["topic"] = topic

    # 검색창 입력값 유지
    data["query"] = request.GET.get("query", "").strip()[:100]
    return data


def closure_member_required(view):
    """비로그인 요청의 로그인·회원가입 안내 전환."""
    # 데코레이터: 원래 함수의 앞뒤에 공통 처리 추가
    # view: 감쌀 원래 뷰 함수, wraps: 원래 함수 정보 보존
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            data = closure_context(request)
            # 원래 요청 주소를 로그인·회원가입의 next 인수로 전달
            data["next_url"] = request.get_full_path()
            # 실제 게시글 조회 뷰 실행 없이 안내 HTML 반환
            response = render(request, "community/closure/access.html", data)
        else:
            # 로그인 회원만 원래 뷰 실행
            response = view(request, *args, **kwargs)
        # 회원 전용 응답의 캐시 저장 금지 지정
        response["Cache-Control"] = "private, no-store"
        # 쿠키 상태에 따라 응답이 달라진다는 정보 추가
        patch_vary_headers(response, ("Cookie",))
        return response
    return wrapped


def save_closure_review(review, request):
    """기존 욕설 검사 적용 후 게시글·검수 기록 저장."""
    # flag_content: 기존 정책에 따른 텍스트 정리 및 검수 상태 반영
    # 검수 중인 글의 수정 시 자동 공개 복원 제외
    found = flag_content(review, request, TEXT_FIELDS)
    review.save()
    if found:
        # objects.create: DB 행 생성 및 저장
        # _meta.label_lower: 앱이름.모델이름 형태의 모델 식별자
        ModerationEvent.objects.create(
            target_type=review._meta.label_lower, target_id=review.pk,
            action=review.moderation_state, reason=review.moderation_reason,
            actor=request.user,
        )
        messages.info(request, "검사 대상 표현이 감지되었습니다. 운영정책에 따라 일부 표현이 제거되거나 검수 처리될 수 있습니다.")


# 위쪽의 회원 검사부터 적용, 비로그인은 원래 함수 실행 제외
# GET: 화면 조회, POST: 폼 제출 요청만 허용
@closure_member_required
@require_http_methods(["GET", "POST"])
def closure_verify(request):
    """폐업 인증 신청과 본인의 신청·게시글 내역 표시."""
    # GET은 빈 폼, POST는 일반 입력값과 업로드 파일을 연결한 폼 생성
    # 빈 POST도 제출된 폼으로 처리하기 위해 요청 방식으로 구분
    form = ClosureVerificationForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
    )
    # is_valid: 필수 항목·파일·날짜 등 폼과 모델 검증 실행
    if request.method == "POST" and form.is_valid():
        # commit=False: DB 저장 전 모델 객체만 생성
        # 입력받지 않은 신청자·상태·동의 시각의 서버 지정 단계
        item = form.save(commit=False)
        item.user = request.user
        item.status = "pending"
        item.consent_at = timezone.now()
        item.save()
        messages.success(request, "폐업 인증을 접수했습니다. 관리자 승인 후 글을 작성할 수 있습니다.")
        # 저장 후 GET으로 이동하여 새로고침의 중복 제출 방지
        return redirect("community:closure_verify")
    data = closure_context(request)
    # update: 템플릿에 전달할 딕셔너리에 항목 추가
    data.update(
        form=form,
        verifications=ClosureVerification.objects.filter(user=request.user).select_related("brand"),
        my_reviews=ClosureReview.objects.filter(author=request.user).select_related("brand"),
    )
    return render(request, "community/closure/verify.html", data)


@closure_member_required
@require_GET
def closure_list(request):
    """선택한 분류와 검색어에 맞는 폐점주 게시글 목록."""

    # 사용자가 제출한 검색어를 읽고 양끝 공백 제거, 최대 100자로 제한
    query = request.GET.get("query", "").strip()[:100]

    # 사용자가 선택한 분류를 읽음. 선택하지 않았다면 빈 문자열
    topic = request.GET.get("topic", "")

    # 정해둔 네 가지 분류에 없는 값이면 전체 조회로 처리
    if topic not in dict(ClosureReview.TOPICS):
        topic = ""

    # 승인된 인증에 연결된 공개 게시글만 조회
    # select_related: 작성자·브랜드·인증을 함께 조회하여 추가 DB 조회 감소
    # order_by: 최근 작성한 글부터 정렬
    reviews = ClosureReview.objects.filter(verification__status="approved", moderation_state="visible").select_related("author", "brand", "verification").order_by("-created_at", "-pk")

    # 분류를 선택했다면 해당 분류의 글만 조회
    if topic:
        reviews = reviews.filter(topic=topic)

    # 검색어가 있으면 제목·본문·조언·브랜드명 중 하나에 포함된 글 조회
    # Q는 조건을 만들고, |는 조건 중 하나라도 일치한다는 뜻
    if query:
        reviews = reviews.filter(Q(title__icontains=query) | Q(content__icontains=query) | Q(advice__icontains=query) | Q(brand__name__icontains=query))

    # 분류·검색 결과를 한 페이지당 10개씩 나누고 현재 페이지 선택
    page_obj = Paginator(reviews, 10).get_page(request.GET.get("page"))

    # params: 페이지 이동 시 유지할 조회 조건의 수정 가능한 복사본
    params = request.GET.copy()

    # 기존 페이지 번호 제거. 페이지 버튼이 새 번호를 붙이기 때문
    # None은 page 항목이 없어도 오류가 나지 않게 하는 기본값
    params.pop("page", None)

    # 검사한 분류값을 페이지 이동 조건에 반영
    if topic:
        params["topic"] = topic
    else:
        params.pop("topic", None)

    # 기존 공통 메뉴 정보 등을 가져옴
    data = closure_context(request)

    # page_obj: 현재 페이지의 게시글
    # query: 검색창에 유지할 검색어
    # topics: 네 가지 분류 버튼을 만들 목록
    # topic: 현재 선택된 분류
    # page_query: 페이지 링크에 붙일 조회 조건 문자열
    # page_range: 화면에 표시할 페이지 번호 목록
    data.update(page_obj=page_obj, query=query, topics=ClosureReview.TOPICS, topic=topic, page_query=params.urlencode(), page_range=list(page_obj.paginator.get_elided_page_range(page_obj.number)))

    # 데이터를 목록 템플릿에 전달하여 HTML 응답 반환
    return render(request, "community/closure/list.html", data)


@closure_member_required
@require_GET
def closure_detail(request, pk):
    """공개 글 또는 작성자 본인 글의 상세 접근 허용."""
    # 공개 글 OR 본인 글 조건, 비공개 타인 글 접근 제외
    allowed = Q(verification__status="approved", moderation_state="visible") | Q(author=request.user)
    # get_object_or_404: 조건에 맞는 한 건 조회, 없으면 404 응답
    review = get_object_or_404(
        ClosureReview.objects.select_related("author", "brand", "verification").filter(allowed),
        pk=pk,
    )
    data = closure_context(request)
    data.update(
        review=review,
        is_author=request.user.pk == review.author_id,
        # 실제 제목·본문을 출력할 수 있는 공개 상태 계산
        is_public=review.verification.status == "approved" and review.moderation_state == "visible",
        # 인증 철회 후 수정 중지, 본인 글 삭제는 별도 허용
        can_edit=review.verification.status == "approved",
    )
    return render(request, "community/closure/detail.html", data)


@closure_member_required
@require_http_methods(["GET", "POST"])
def closure_write(request):
    """본인의 승인된 폐업 인증을 이용한 게시글 작성."""
    # exists: 조회 결과의 존재 여부만 검사
    if not ClosureVerification.objects.filter(user=request.user, status="approved").exists():
        messages.info(request, "글 작성은 폐업 인증을 승인받은 회원만 가능합니다. 아래에서 인증을 신청하거나 심사 상태를 확인해주세요.")
        return redirect("community:closure_verify")
    form = ClosureReviewWriteForm(
        request.POST if request.method == "POST" else None, user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        # atomic: 내부 DB 작업을 하나의 트랜잭션으로 처리
        # 예외 발생 시 내부 DB 변경 취소, 파일시스템까지 자동 취소하는 기능은 아님
        with transaction.atomic():
            # select_for_update: 지원 DB에서 행 잠금으로 수정 경쟁 제어
            # SQLite에서는 행 잠금 효과 없음, PostgreSQL 등과 동작 차이 존재
            # 저장 직전에도 인증 소유자와 승인 상태 재검사
            verification = (
                ClosureVerification.objects.select_for_update()
                .filter(pk=form.cleaned_data["verification"].pk, user=request.user, status="approved")
                .first()
            )
            if verification is None:
                # add_error: 특정 입력칸에 오류 연결
                form.add_error("verification", "현재 승인된 본인의 인증만 사용할 수 있습니다.")
            else:
                review = form.save(commit=False)
                # cleaned_data: 검증을 통과해 변환된 입력값
                # 작성자·인증·브랜드는 신뢰할 수 있는 서버 정보로 지정
                review.author = request.user
                review.verification = verification
                review.brand = verification.brand
                save_closure_review(review, request)
                messages.success(request, "폐업 경험을 등록했습니다.")
                return redirect("community:closure_detail", pk=review.pk)
    data = closure_context(request)
    data.update(form=form, review=None)
    return render(request, "community/closure/form.html", data)


@closure_member_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def closure_edit(request, pk):
    """본인 게시글의 내용 수정, 작성자·인증·브랜드 변경 제외."""
    # 함수 전체 DB 처리를 트랜잭션으로 묶음
    # 지원 DB에서 현재 게시글과 인증 행의 수정 경쟁 제어
    review = get_object_or_404(
        ClosureReview.objects.select_for_update(), pk=pk, author=request.user,
    )
    verification = get_object_or_404(
        ClosureVerification.objects.select_for_update(),
        pk=review.verification_id, user=request.user,
    )
    if verification.status != "approved":
        messages.error(request, "폐업 인증이 승인 상태가 아니므로 수정할 수 없습니다.")
        return redirect("community:closure_detail", pk=review.pk)
    # instance: 신규 생성이 아닌 기존 모델 객체 수정 대상으로 지정
    form = ClosureReviewForm(
        request.POST if request.method == "POST" else None, instance=review,
    )
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.author = request.user
        item.verification = verification
        item.brand = verification.brand
        save_closure_review(item, request)
        messages.success(request, "폐업 경험을 수정했습니다.")
        return redirect("community:closure_detail", pk=item.pk)
    data = closure_context(request)
    data.update(form=form, review=review)
    return render(request, "community/closure/form.html", data)


@closure_member_required
@require_http_methods(["GET", "POST"])
def closure_delete(request, pk):
    """본인 게시글의 삭제 확인과 POST 삭제 처리."""
    # URL 조작으로 타인 글을 삭제하지 못하도록 서버에서 작성자 검사
    review = get_object_or_404(ClosureReview, pk=pk, author=request.user)
    # GET은 아래 확인 화면 반환, POST만 실제 삭제
    # 인증 철회 상태에서도 본인 게시글 삭제 허용
    if request.method == "POST":
        review.delete()
        messages.success(request, "게시글을 삭제했습니다.")
        return redirect("community:closure_list")
    data = closure_context(request)
    data.update(review=review)
    return render(request, "community/closure/delete.html", data)


@closure_member_required
@require_GET
def closure_document(request, pk, kind):
    """인증 변경 권한이 있는 관리자에게만 증빙 다운로드 허용."""
    # is_active: 활성 계정, is_staff: 관리자 사이트 접근 대상
    # has_perm: 특정 모델의 변경 권한 검사, 단순 회원·일반 직원 접근 제외
    if not (
        request.user.is_active and request.user.is_staff
        and request.user.has_perm("community.change_closureverification")
    ):
        raise PermissionDenied
    verification = get_object_or_404(ClosureVerification, pk=pk)
    # 허용 목록으로 종류 제한, 임의 파일 경로·필드명 접근 제외
    documents = {"closure": verification.closure_file, "operation": verification.operation_file}
    document = documents.get(kind)
    if not document:
        raise Http404("증빙서류가 없습니다.")
    try:
        # rb: 바이너리 읽기 모드
        handle = document.open("rb")
    except (OSError, ValueError):
        raise Http404("증빙서류를 읽을 수 없습니다.")
    extension = Path(document.name).suffix.lower()
    # as_attachment: 브라우저 표시 대신 다운로드 방식 지정
    # 원본 파일명 대신 인증 번호 기반 다운로드 파일명 지정
    response = FileResponse(
        handle, as_attachment=True, filename=f"closure_{pk}_{kind}{extension}",
    )
    response["Cache-Control"] = "private, no-store"
    # nosniff: 브라우저의 임의 파일 형식 추측 방지
    response["X-Content-Type-Options"] = "nosniff"
    return response
