"""업종 목록을 DB에 들어온 브랜드에서 만듭니다.

화면용 업종 묶음(커피·한식·치킨 …, constants.CATEGORY_GROUPS) → 그 안의 공정위 세부 업종(브랜드 많은 순).
묶음에 없는 업종은 ‘기타’로 들어갑니다.
"""
from django.db.models import Count
from .constants import CATEGORY_GROUPS, GROUP_OF, OTHER_GROUP


def group_of(category):
    return GROUP_OF.get(category, OTHER_GROUP)


def category_groups(brands):
    counts = dict(brands.order_by().values_list('category').annotate(n=Count('id')))
    groups = {name: {'name': name, 'icon': icon, 'categories': []} for name, icon, _ in CATEGORY_GROUPS}
    for category, n in counts.items():
        groups[group_of(category)]['categories'].append({'name': category, 'count': n})
    result = []
    for name, _, _ in CATEGORY_GROUPS:
        group = groups[name]
        if not group['categories']:
            continue
        group['categories'].sort(key=lambda c: (-c['count'], c['name']))
        group['count'] = sum(c['count'] for c in group['categories'])
        result.append(group)
    return result


def grouped_choices(groups, first=('전체', '전체 업종')):
    # Django ChoiceField용 [(묶음, [(업종, 업종), ...]), ...]
    choices = [first] if first else []
    return choices + [(g['name'], [(c['name'], c['name']) for c in g['categories']]) for g in groups]


def all_category_choices(first=('전체', '전체 업종')):
    from .views import visible_brands
    return grouped_choices(category_groups(visible_brands()), first)
