from django.db import migrations

def update_help(apps, schema_editor):
    FAQ=apps.get_model('core','FAQ')
    FAQ.objects.filter(question='브랜드를 비교하려면 어떻게 하나요?',answer='브랜드 카드의 비교 버튼 또는 지역 살펴보기 표 맨 왼쪽의 비교 체크박스를 선택하세요. 최대 2개를 비교할 수 있으며, 체크를 해제하면 비교함에서 빠집니다. 하단 비교하기에서 매장 수·매출·창업비용 등을 확인하세요.').update(answer='브랜드 카드의 비교 버튼 또는 지역 살펴보기 표 맨 왼쪽의 비교 체크박스를 선택하세요. 최대 10개를 비교할 수 있으며, 체크를 해제하면 비교함에서 빠집니다. 하단 비교하기에서 매장 수·매출·창업비용 등을 확인하세요. 비교표는 항목명이 고정된 가로 스크롤 구조이며, 그래프 항목은 2개까지 선택할 수 있습니다.')
    FAQ.objects.filter(question='브랜드를 비교하려면 어떻게 하나요?',answer_en='Choose Compare on a brand card or tick the leftmost checkbox on the Regions table. Select up to two brands. Untick to remove a brand, then open Compare at the bottom.').update(answer_en='Choose Compare on a brand card or tick the leftmost checkbox on the Regions table. Select up to ten brands. Untick to remove a brand, then open Compare at the bottom. Scroll the comparison table horizontally; metric labels stay fixed. Choose up to two chart metrics.')

class Migration(migrations.Migration):
    dependencies=[('core','0001_initial')]
    operations=[migrations.RunPython(update_help,migrations.RunPython.noop)]
