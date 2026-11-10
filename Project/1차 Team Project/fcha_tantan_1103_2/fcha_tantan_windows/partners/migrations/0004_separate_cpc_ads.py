from django.db import migrations, models

def separate_ads(apps, schema_editor):
    Plan = apps.get_model('partners', 'PartnerPlan')
    for plan in Plan.objects.all():
        plan.includes_ad_slot = False
        plan.summary = plan.summary.replace('메인·브랜드 탐색 최상단 광고 자리까지 포함', '브랜드 성장을 위한 프리미엄 파트너 서비스')
        plan.features = [x for x in plan.features if not ('광고' in x and ('자리' in x or '구좌' in x))]
        plan.save(update_fields=['includes_ad_slot', 'summary', 'features'])

class Migration(migrations.Migration):
    dependencies = [('partners', '0003_partneraccount_authorization_file_and_more')]
    operations = [
        migrations.AddField(model_name='partnerinquiry', name='ad_position', field=models.PositiveSmallIntegerField(verbose_name='광고 구좌', choices=[(1,'AD 1번 구좌'),(2,'AD 2번 구좌')], null=True, blank=True)),
        migrations.AddField(model_name='partnerinquiry', name='cpc_bid_krw', field=models.PositiveIntegerField(verbose_name='희망 CPC(원/클릭)', null=True, blank=True)),
        migrations.RunPython(separate_ads, migrations.RunPython.noop),
    ]
