from django.db import migrations

def refresh(apps, schema_editor):
    FAQ = apps.get_model('core','FAQ')
    for faq in FAQ.objects.all():
        faq.answer = faq.answer.replace('카카오 장소검색','전국 장소검색').replace('그래프 항목은 2개','그래프 항목은 5개')
        faq.answer_en = faq.answer_en.replace('up to two chart metrics','up to five chart metrics')
        faq.save(update_fields=['answer','answer_en'])
class Migration(migrations.Migration):
    dependencies = [('core','0002_compare_ten_help')]
    operations = [migrations.RunPython(refresh, migrations.RunPython.noop)]
