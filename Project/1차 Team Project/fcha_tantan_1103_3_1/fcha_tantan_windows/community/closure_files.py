"""폐업 인증 증빙 파일의 비공개 저장 설정."""

# Path: 운영체제에 맞는 파일 경로 처리
from pathlib import Path

# uuid4: 원본 파일명 대신 사용할 임의 식별자 생성
from uuid import uuid4

# settings: 기존 프로젝트의 MEDIA_ROOT 설정 참조
from django.conf import settings

# FileSystemStorage: 파일을 서버 디스크에 저장하는 Django 기본 클래스
from django.core.files.storage import FileSystemStorage

# deconstructible: 사용자 정의 객체를 마이그레이션에 기록하기 위한 설정
from django.utils.deconstruct import deconstructible


@deconstructible
class ClosureEvidenceStorage(FileSystemStorage):
    """폐업 인증 증빙 전용 저장소."""

    def __init__(self):
        # super(): 부모 클래스의 초기화 함수 호출
        # MEDIA_ROOT 아래 closure_evidence 폴더를 저장 위치로 지정
        super().__init__(
            location=Path(settings.MEDIA_ROOT) / "closure_evidence",
        )

    def url(self, name):
        # 증빙 파일의 공개 URL 생성 차단
        # 권한 검사 전용 뷰를 통한 다운로드만 허용
        raise NotImplementedError(
            "폐업 인증 증빙은 공개 URL을 제공하지 않습니다."
        )


# 모델의 FileField에서 사용할 저장소 객체 생성
closure_evidence_storage = ClosureEvidenceStorage()


def closure_evidence_path(instance, filename):
    """회원별 증빙 저장 경로 생성."""

    # suffix: 파일 확장자 추출
    # lower(): 대문자 확장자를 소문자로 통일
    extension = Path(filename).suffix.lower()

    # instance: 파일을 저장할 ClosureVerification 객체
    # user_id: 인증 신청자의 회원 번호
    # uuid4().hex: 파일명 충돌 방지용 임의 문자열
    # 원본 파일명에 포함될 수 있는 개인정보의 저장 경로 노출 방지
    return f"{instance.user_id}/{uuid4().hex}{extension}"