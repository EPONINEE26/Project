from pathlib import Path
import ast
from datetime import datetime
from zoneinfo import ZoneInfo
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment

root=Path.cwd()
p=root/'artifacts/20261105_커뮤니티_수정추가코드_초보자설명.xlsx'
w=load_workbook(p)
records=[]
def locate(path,target):
    f=root/path
    if not f.exists():return '현재 파일 없음 — 명령 실행 시 생성 예정'
    s=f.read_text(encoding='utf-8');lines=s.splitlines()
    if path.endswith('.py'):
        tree=ast.parse(s)
        nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==target]
        if nodes:
            return ' / '.join(f'{min([n.lineno]+[d.lineno for d in getattr(n,"decorator_list",[])])}~{n.end_lineno}줄' for n in nodes)
    needles={'Post.TOPICS':'TOPICS=','상단 .forms import':'from .forms import','owner-brand의 small 태그':'<small class="owner-brand">','댓글 폼 표시 조건':'{% elif can_','파일 맨 아래 comment_delete 및 데코레이터':'@login_required','Comment 클래스 전체':'class Comment(','CommentForm':'class CommentForm(','TipsCommentForm 클래스':'class TipsCommentForm('}
    needle=needles.get(target,target)
    if target=='Comment 클래스 전체':return locate(path,'Comment')
    if target=='TipsCommentForm 클래스':return locate(path,'TipsCommentForm')
    if target=='파일 맨 아래 comment_delete 및 데코레이터':return locate(path,'comment_delete')
    found=[str(i) for i,l in enumerate(lines,1) if needle in l]
    return '·'.join(found)+'줄' if found else '파일 내 대상 이름 검색'

for row in w['수정 전후 비교'].iter_rows(min_row=2):
    n,path,kind,target=[c.value for c in row[:4]]
    location=locate(path,target) if path!='프로젝트 루트 터미널' else '해당 없음 — manage.py가 있는 폴더의 터미널'
    records.append((n,path,location,kind,target,row[6].value))
    rownum=row[0].row
    w['수정 코드 포함 표'].cell(rownum,2,location)
    w['처음부터 적용 순서'].cell(rownum+2,5,location)
w['처음부터 적용 순서'].cell(1,5,'현재 파일의 정확한 줄 번호')
comp=w['수정 전후 비교'];comp.cell(1,9,'현재 파일의 정확한 줄 번호')
for i,r in enumerate(records,2):comp.cell(i,9,r[2])
sheet=w.create_sheet('줄 번호 먼저 보기',0)
sheet.append(['순서','파일','현재 줄 번호(수정 전)','구분','찾을 대상','수정 방법'])
for r in records:sheet.append(r)
sheet.append(['기준 시각',datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M KST'),'현재 디스크에 저장된 파일 기준','','','수정하면 이후 줄 번호가 달라질 수 있으므로 대상 이름도 함께 확인하세요.'])
sheet.append(['중복 함수 안내','community/views.py','두 범위를 모두 표시했습니다.','','comment_create / comment_delete','표시된 두 함수와 데코레이터를 정리하고 완성 코드는 하나만 남기세요.'])
model=(root/'community/models.py').read_text(encoding='utf-8').splitlines()
commented=[str(i) for i,l in enumerate(model,1) if l.lstrip().startswith('# class Comment(')]
if commented:sheet.append(['현재 파일 참고','community/models.py',','.join(commented)+'줄','주석 상태','예전 Comment 클래스','현재 활성 Comment 클래스의 줄 번호를 수정 대상으로 표시했습니다. #로 주석 처리한 예전 코드는 실행되지 않습니다.'])
for s in [sheet,w['처음부터 적용 순서'],comp,w['수정 코드 포함 표']]:
    s.freeze_panes='C2';s.auto_filter.ref=s.dimensions
    for c in s[1]:c.font=Font(name='맑은 고딕',bold=True,color='FFFFFF');c.fill=PatternFill('solid',fgColor='17365D');c.alignment=Alignment(wrap_text=True,vertical='center')
    for row in s.iter_rows(min_row=2):
        for c in row:c.alignment=Alignment(wrap_text=True,vertical='top')
sheet.column_dimensions['A'].width=12;sheet.column_dimensions['B'].width=55;sheet.column_dimensions['C'].width=35;sheet.column_dimensions['D'].width=22;sheet.column_dimensions['E'].width=40;sheet.column_dimensions['F'].width=90
w['처음부터 적용 순서'].column_dimensions['E'].width=35
comp.column_dimensions['I'].width=35
for i in range(2,sheet.max_row+1):sheet.row_dimensions[i].height=60
q=p.with_name('20261105_커뮤니티_수정추가코드_초보자설명_줄번호포함.xlsx')
w.save(q)
v=load_workbook(q,read_only=True)
assert v.sheetnames[0]=='줄 번호 먼저 보기'
assert all(v['수정 전후 비교'].cell(i,9).value for i in range(2,len(records)+2))
v.close()
for r in records:print(r[1],r[4],r[2])
print('Saved:',q)
