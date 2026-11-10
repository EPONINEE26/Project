from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [('brands', '0007_brandreview_moderation_original_and_more')]
    operations = [migrations.AddField(model_name='adslot', name='cpc_bid_krw', field=models.PositiveIntegerField(default=0, verbose_name='입찰 CPC(원/클릭)', help_text='0이면 경매 노출 제외. 승인된 구좌별 최고 입찰가 우선, 동률은 먼저 등록한 순서. 낙찰 단가는 본인 입찰가.'))]
