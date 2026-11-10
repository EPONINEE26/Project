"""폐업 인증 증빙의 비공개 저장 설정."""

# Path: 운영체제에 맞는 경로 연결 및 파일 확장자 추출 클래스
from pathlib import Path
# uuid4: 충돌 가능성이 매우 낮은 임의 식별자 생성 함수
from uuid import uuid4

# settings: 기존 프로젝트 설정값 참조 객체
from django.conf import settings
# FileSystemStorage: 파일을 서버 디스크에 저장하는 Django 기본 저장소
from django.core.files.storage import FileSystemStorage
# deconstructible: 객체 생성 정보를 마이그레이션에 기록할 수 있도록 지원
from django.utils.deconstruct import deconstructible


# @: 클래스나 함수에 추가 동작을 적용하는 데코레이터 문법
# 마이그레이션에서 사용자 정의 저장소 객체를 다시 생성할 수 있도록 지정
@deconstructible
class ClosureEvidenceStorage(FileSystemStorage):
    """FileSystemStorage를 상속하는 폐업 증빙 전용 저장소."""

    def __init__(self):
        # __init__: 객체 생성 시 실행되는 초기화 메서드
        # super(): 부모 클래스의 기능 참조
        # Path / 문자열: 운영체제에 맞게 하위 경로 연결
        # MEDIA_ROOT 아래 closure_evidence 폴더를 저장 위치로 지정
        super().__init__(
            location=Path(settings.MEDIA_ROOT) / "closure_evidence",
        )

    def url(self, name):
        # 부모 저장소의 url 메서드를 재정의하여 공개 URL 생성 차단
        # NotImplementedError: 해당 기능을 제공하지 않는다는 예외
        # 관리자 권한 검사 뷰를 통한 다운로드만 제공
        raise NotImplementedError("폐업 증빙은 공개 URL을 제공하지 않습니다.")


# 클래스 호출로 저장소 객체 생성, FileField의 storage 인수로 재사용
closure_evidence_storage = ClosureEvidenceStorage()


def closure_evidence_path(instance, filename):
    """회원 번호와 임의 파일명으로 증빙 경로 생성."""
    # instance: 파일을 저장할 인증 모델 객체
    # filename: 제출된 원본 파일명
    # suffix: 마지막 확장자, lower(): 소문자 변환
    extension = Path(filename).suffix.lower()
    # user_id: 연결된 회원의 기본키, uuid4().hex: 임의 식별자의 문자열 표현
    # f 문자열: 중괄호의 값을 문자열에 삽입
    # 원본 파일명에 들어갈 수 있는 개인정보의 경로 노출 방지
    return f"{instance.user_id}/{uuid4().hex}{extension}"
