from django.db import migrations

# 화면 구성을 위한 예시 요금제입니다(is_example=True → “예시 요금” 표시). 관리자 페이지에서 확정 금액으로 바꾸세요.
PLANS = [
    dict(name='스타터', order=1, monthly_price_krw=0, summary='브랜드 정보를 정확하게 알리는 기본 파트너',
         features=['브랜드 상세 정보·소개 관리 요청', '창업 문의 접수(월 10건)', '예비창업자 사업제안 월 5건'],
         monthly_proposal_limit=5, includes_ad_slot=False, is_highlighted=False),
    dict(name='그로스', order=2, monthly_price_krw=290000, summary='희망 지역·예산이 맞는 예비창업자에게 먼저 제안',
         features=['스타터 기능 전체', '창업 문의 무제한 접수·관리', '예비창업자 사업제안 월 30건', '지역별 매장·유동인구 리포트'],
         monthly_proposal_limit=30, includes_ad_slot=False, is_highlighted=True),
    dict(name='프리미엄', order=3, monthly_price_krw=None, summary='메인·브랜드 탐색 최상단 광고 자리까지 포함',
         features=['그로스 기능 전체', '메인·브랜드 탐색 상단 1·2번 광고 자리', '예비창업자 사업제안 월 100건', '전담 매니저 상담'],
         monthly_proposal_limit=100, includes_ad_slot=True, is_highlighted=False),
]


def create(apps, schema_editor):
    Plan = apps.get_model('partners', 'PartnerPlan')
    if not Plan.objects.exists():
        for plan in PLANS:
            Plan.objects.create(is_example=True, **plan)


class Migration(migrations.Migration):
    dependencies = [('partners', '0001_initial')]
    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
