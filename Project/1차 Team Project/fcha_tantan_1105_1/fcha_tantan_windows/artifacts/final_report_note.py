from pathlib import Path
from openpyxl import load_workbook
from openpyxl.styles import Font,PatternFill,Alignment
import zipfile
root=Path(__file__).resolve().parents[1]
p=root/'artifacts/community_all_work_20261105.xlsx'
w=load_workbook(p)
s=w.create_sheet('발표 전 댓글창 수정',1)
s.append(['파일','현재 줄 번호','교체할 코드','설명 한 줄'])
s.append(['community/templates/community/detail.html','82줄','            {# 댓글 입력창은 아래 can_comment 조건으로 표시합니다. #}','82줄을 Django 주석으로 바꾸면 옛 can_post 조건이 실행되지 않으며, 84줄의 can_comment와 아래 댓글 입력창이 정상적으로 처리됩니다.'])
s.append(['작업 방법','Ctrl+G → 82 → Enter','82줄 전체만 위 코드로 교체','84줄의 {% elif can_comment %}는 바꾸지 않는 한 줄 수정 방법입니다.'])
s.freeze_panes='C2';s.auto_filter.ref=s.dimensions
for c in s[1]:c.font=Font(name='맑은 고딕',bold=True,color='FFFFFF');c.fill=PatternFill('solid',fgColor='17365D')
for row in s:
    for c in row:c.alignment=Alignment(wrap_text=True,vertical='top')
for key,width in [('A',55),('B',30),('C',110),('D',110)]:s.column_dimensions[key].width=width
s.row_dimensions[2].height=65;s.row_dimensions[3].height=50
for row in w['전체 코드와 한줄 설명'].iter_rows(min_row=2):
    if row[3].value=='Comment.brand':row[2].value='52줄 — Comment 클래스 안의 brand'
    if row[3].value=='댓글 입력창 조건':row[2].value='82~84줄 전체 / 한 줄 수정 방법은 발표 전 댓글창 수정 시트 참조'
w.save(p)
with zipfile.ZipFile(root/'artifacts/community_all_work_20261105.zip','w',zipfile.ZIP_DEFLATED) as z:
    z.write(p,p.name)
    for f in (root/'artifacts/comment_report_20261105').rglob('*'):
        if f.is_file():z.write(f,str(f.relative_to(root/'artifacts/comment_report_20261105')))
test=load_workbook(p,read_only=True)
assert test['발표 전 댓글창 수정'].cell(2,2).value=='82줄'
test.close()
print('Validated XLSX:',p.stat().st_size,'bytes;',len(w.sheetnames),'sheets')
