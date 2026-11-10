from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from brands.models import Brand
from community.models import Post


TITLE = '오픈 전날 허둥대지 않는 매장 준비 체크리스트'
CONTENT = '''매장 오픈을 준비할 때 확인할 일을 작업 순서대로 정리한 예시 안내글입니다. 실제 점주의 체험담이 아니며, 업종과 매장 상황에 맞게 조정해 사용하세요.

1. 준비표에 담당자와 완료 날짜를 함께 적으세요
인테리어, 장비 설치, 초도 발주, 직원 교육을 한 표에 모으세요. 항목마다 담당자·마감일·확인 결과를 적으면 빠진 일을 찾기 쉽습니다. 일정이 밀렸을 때 연락할 업체 담당자도 함께 정리하세요.

2. 장비는 켜 보는 데서 끝내지 마세요
냉장고, 제빙기, 조리기기 등은 실제 사용하는 순서대로 시험하세요. 전원 위치와 청소 방법을 확인하고, 이상이 있으면 사진과 증상을 남겨 설치 업체에 전달하세요. 수리 연락처와 보증 자료는 한곳에 보관하세요.

3. 주문부터 수령까지 직접 걸어 보세요
손님 역할과 직원 역할을 나눠 주문 접수, 결제, 제조, 포장, 전달을 연습하세요. 포장재와 도구를 찾느라 멈추는 지점을 기록하고 자주 쓰는 물건부터 손이 닿는 위치로 옮기세요.

4. 초도 재고는 품목별로 나누어 확인하세요
식재료뿐 아니라 컵, 봉투, 영수증 용지, 세제, 쓰레기봉투 같은 소모품도 점검하세요. 현재 수량, 보관 위치, 추가 주문 기준, 거래처 연락처를 적어 두세요. 유통기한이 있는 품목은 먼저 들어온 것을 먼저 사용할 수 있게 배치하세요.

5. 결제와 주문 알림을 미리 시험하세요
POS와 카드 단말기, 영수증 출력, 주문 알림이 정상인지 확인하세요. 시험 결제가 필요하면 서비스 제공 업체의 안내에 따라 진행하고 취소 처리까지 확인하세요. 인터넷 장애 때 연락할 곳도 직원과 공유하세요.

6. 짧은 모의 영업으로 마지막 점검을 하세요
여러 주문이 겹치는 상황을 연습하고 주문 누락, 대기 안내, 재고 부족 대응을 점검하세요. 끝난 뒤 불편했던 점 세 가지를 골라 고치고 다시 확인하세요.

마지막으로 오픈 담당자, 비상 연락처, 당일 해야 할 일의 우선순위를 한 장으로 출력해 두세요. 준비 항목을 많이 적는 것보다 누가 언제 확인했는지 남기는 것이 도움이 됩니다.'''


class Command(BaseCommand):
    help = '매장 준비 꿀팁 예시 게시글 1개를 중복 없이 등록합니다.'

    @transaction.atomic
    def handle(self, *args, **options):
        user, created = get_user_model().objects.get_or_create(
            username='store-tips-example', defaults={'first_name': '매장 준비 안내 예시', 'is_active': False})
        if created:
            user.set_unusable_password()
            user.save(update_fields=['password'])
        brand, _ = Brand.objects.get_or_create(
            slug='store-tips-example', defaults={'name': '매장 준비 안내 예시', 'category': '기타', 'is_demo': True})
        post, created = Post.objects.get_or_create(
            author=user, topic='store_tips', title=TITLE,
            defaults={'brand': brand, 'content': CONTENT, 'is_demo': True, 'moderation_state': 'visible'})
        self.stdout.write(self.style.SUCCESS(f'STORE_TIP_OK: id={post.pk}, created={created}'))
