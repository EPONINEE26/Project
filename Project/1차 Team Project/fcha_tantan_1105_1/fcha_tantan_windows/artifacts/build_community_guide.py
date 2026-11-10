from pathlib import Path
import ast
import hashlib
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

root=Path.cwd()
out=root/'artifacts'
out.mkdir(exist_ok=True)
paths=['community/models.py','community/forms.py','community/views.py','community/migrations/0001_initial.py','community/templates/community/author.html','community/templates/community/detail.html']
original={p:(root/p).read_text(encoding='utf-8') for p in paths}
hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
final=dict(original)
final[paths[0]]=final[paths[0]].replace("    brand=models.ForeignKey('brands.Brand',on_delete=models.PROTECT,null=True,blank=True)\n",'').replace("related_name='community_comments')\n    brand=models.ForeignKey('brands.Brand',on_delete=models.PROTECT)","related_name='community_comments')\n    brand=models.ForeignKey('brands.Brand',on_delete=models.PROTECT,null=True,blank=True)")
form='''class CommentForm(VerifiedBrandMixin,forms.ModelForm):
    brand=forms.ModelChoiceField(queryset=Brand.objects.none(),required=True,label='브랜드')
    class Meta:
        model=Comment
        fields=('brand','content')
        widgets={'content':forms.Textarea(attrs={'rows':3,'maxlength':2000,'placeholder':'경험과 도움이 되는 의견을 나눠주세요.'})}'''
start=final[paths[1]].index('# class CommentForm') if '# class CommentForm' in final[paths[1]] else final[paths[1]].index('class CommentForm')
end=final[paths[1]].index('class TipsCommentForm')
final[paths[1]]=final[paths[1]][:start]+form+'\n\n\n'+final[paths[1]][end:]
v=final[paths[2]].replace('from .forms import PostForm, CommentForm, SelectBrandForm, verified_brands','from .forms import PostForm, CommentForm, TipsCommentForm, SelectBrandForm, verified_brands')
# 중복 함수는 메모리에서만 제거한다. 실제 소스 파일은 쓰지 않는다.
lines=v.splitlines(keepends=True)
seen=set(); spans=[]
for node in ast.parse(v).body:
    if isinstance(node,ast.FunctionDef):
        if node.name in seen:
            spans.append((min([node.lineno]+[d.lineno for d in node.decorator_list])-1,node.end_lineno))
        seen.add(node.name)
for a,b in reversed(spans):del lines[a:b]
v=''.join(lines)
v=v.replace('form=CommentForm(user=request.user),is_author=', 'form=comment_form_for(post,request.user),can_comment=may_comment(request.user,post),is_author=')
v=v.replace("    blocked=owner_required(request)\n    if blocked:return blocked\n    form=CommentForm(request.POST or None,instance=comment,user=request.user)","    if comment.post.topic!='store_tips':\n        blocked=owner_required(request)\n        if blocked:return blocked\n    form=comment_form_for(comment.post,request.user,request.POST if request.method=='POST' else None,instance=comment)")
final[paths[2]]=v
final[paths[3]]=original[paths[3]].split('\n@login_required')[0].rstrip()+'\n'
old='<small class="owner-brand">{{ item.brand.name|clean_brand_name }} 점주{% if item.is_demo %} · 예시{% endif %}</small>'
new='<small class="owner-brand">{% if item.brand_id %}{{ item.brand.name|clean_brand_name }} 점주{% else %}일반회원{% endif %}{% if item.is_demo %} · 예시{% endif %}</small>'
final[paths[4]]=original[paths[4]].replace(old,new)
final[paths[5]]=original[paths[5]].replace('{% elif can_post %}','{% elif can_comment %}')

def block(text,name):
    node=next(n for n in ast.parse(text).body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==name)
    a=min([node.lineno]+[d.lineno for d in getattr(node,'decorator_list',[])])-1
    return '\n'.join(text.splitlines()[a:node.end_lineno])

items=[]
def add(path,kind,where,before,after,why,how):
    items.append((len(items)+1,path,kind,where,before,after,why,how))

add(paths[0],'유지','Post.TOPICS',next(l.strip() for l in original[paths[0]].splitlines() if 'TOPICS=' in l),next(l.strip() for l in final[paths[0]].splitlines() if 'TOPICS=' in l),'store_tips는 저장하는 분류 값이고 매장 준비 꿀팁은 화면에 보이는 이름입니다. 현재 이미 추가되어 있습니다.','추가로 붙여 넣지 마세요. 아래 Comment 클래스만 교체합니다.')
add(paths[0],'수정·중복 삭제','Comment 클래스 전체',block(original[paths[0]],'Comment'),block(final[paths[0]],'Comment'),'brand가 두 번 선언되어 뒤쪽의 필수 설정이 앞쪽의 빈 값 허용 설정을 덮어쓰고 있습니다. null=True는 DB의 빈 값, blank=True는 폼의 생략을 허용합니다.','Comment 클래스 전체를 교체하세요. Post.brand는 필수인 채로 유지합니다.')
add(paths[1],'복원 확인·필수 필드 추가','CommentForm',original[paths[1]][start:end].strip(),form,'처음 확인할 때는 주석 처리되어 있었으나 엑셀 작성 시점에는 주석 해제가 확인되었습니다. 일반 게시판은 인증 브랜드와 댓글 내용을 함께 받습니다. 모델에서 브랜드 생략을 허용하더라도 이 폼에서는 required=True로 브랜드 선택을 필수로 유지합니다.','현재 CommentForm 부분만 아래 완성 코드로 교체하세요. 이미 주석을 해제했다면 복원은 완료된 상태입니다. TipsCommentForm은 지우지 마세요.')
add(paths[1],'유지','TipsCommentForm 클래스',block(original[paths[1]],'TipsCommentForm'),block(final[paths[1]],'TipsCommentForm'),'꿀팁에서는 일반회원도 내용만 입력할 수 있습니다. 이 클래스에는 user 인수를 전달하지 않습니다.','지금 선택한 TipsCommentForm은 그대로 둡니다. CommentForm과 함께 각각 한 개씩 있어야 합니다.')
add(paths[2],'수정','상단 .forms import',next(l for l in original[paths[2]].splitlines() if l.startswith('from .forms')),next(l for l in v.splitlines() if l.startswith('from .forms')),'다른 파일에 정의된 TipsCommentForm을 views.py에서 사용하려면 가져와야 합니다. 이름 끝의 s를 포함해 정확히 일치해야 합니다.','기존 import 한 줄을 수정 후 코드 한 줄로 교체합니다.')
for name,kind,why,how in [
('may_comment','유지','로그인 여부와 글 분류를 확인합니다. 꿀팁은 로그인 회원, 다른 게시판은 인증 점주가 댓글을 작성합니다.','이미 있으므로 중복 추가하지 않습니다.'),
('comment_form_for','유지','꿀팁은 TipsCommentForm, 다른 게시판은 CommentForm을 선택합니다. instance는 수정할 기존 댓글입니다.','이미 있으므로 그대로 둡니다. 위 import가 먼저 필요합니다.'),
('detail','수정','게시글 상세 화면에도 분류에 맞는 폼과 can_comment 권한 값을 전달해야 일반회원에게 꿀팁 입력창이 보입니다.','데코레이터부터 return까지 함수 전체를 교체합니다.'),
('comment_create','수정·중복 삭제','같은 이름의 함수가 두 개면 뒤쪽 함수가 앞쪽 함수를 덮어씁니다. 꿀팁만 점주 인증을 생략하고 작성자 자신의 인증 브랜드가 있을 때 연결합니다.','두 comment_create와 각각의 데코레이터를 제거하고 아래 함수 하나만 넣습니다.'),
('comment_edit','수정','본인 댓글만 수정하며 꿀팁에서는 일반회원도 수정하도록 합니다. POST 입력을 분류에 맞는 폼으로 검증합니다.','함수 전체를 교체합니다. 다른 사람 댓글은 author=request.user 조건으로 차단합니다.'),
('comment_delete','중복 삭제·유지','로그인한 작성자만 POST 요청으로 삭제하도록 유지합니다. 점주 인증이 없어도 본인 댓글은 삭제할 수 있습니다.','중복된 두 함수를 아래 하나로 정리합니다. 마이그레이션에는 넣지 않습니다.')]:
    add(paths[2],kind,name,block(original[paths[2]],name),block(v,name),why,how)
add(paths[3],'삭제','파일 맨 아래 comment_delete 및 데코레이터',original[paths[3]].split('\n@login_required',1)[1].join(['@login_required','']) if '\n@login_required' in original[paths[3]] else '', '(삭제만 합니다. 대체 코드는 없습니다.)','마이그레이션은 DB 구조 변경 기록입니다. 웹 요청을 처리하는 뷰 함수가 들어갈 자리가 아닙니다. 현재 데코레이터 이름도 정의되지 않아 로딩 오류가 납니다.','맨 아래 @login_required부터 comment_delete의 마지막 줄까지만 삭제합니다. Migration 클래스와 operations는 유지합니다.')
add('community/migrations/0002_owner_tips_member_comments.py','생성 예정','Django 명령으로 생성','현재 없음','python manage.py makemigrations community --name owner_tips_member_comments','현재 community 마이그레이션은 0001_initial뿐이므로 다음 번호는 0002로 예상됩니다. 어제 파일의 0003과 존재하지 않는 0002 의존성을 복사하면 안 됩니다.','모델·폼·뷰·기존 마이그레이션 수정 후 명령을 실행합니다. Comment.brand의 null/blank와 Post.topic의 store_tips 변경이 생성되는지 확인합니다. 수동 작성하지 않습니다.')
add(paths[4],'수정','owner-brand의 small 태그',old,new,'브랜드 없는 일반회원 댓글에 점주 표시가 붙지 않도록 분기합니다. 예시 표시는 유지합니다.','small 태그 한 줄 전체를 교체합니다.')
add(paths[5],'수정','댓글 폼 표시 조건','{% elif can_post %}','{% elif can_comment %}','can_post는 게시글 작성용 점주 권한입니다. 댓글에는 detail에서 계산한 can_comment를 사용해야 일반회원의 꿀팁 댓글창이 보입니다.','이 한 줄만 교체합니다. form, csrf_token, 로그인 안내 등 주변 코드는 그대로 둡니다.')
commands='python manage.py check\npython manage.py makemigrations community --name owner_tips_member_comments\npython manage.py migrate'
add('프로젝트 루트 터미널','실행 안내','manage.py가 있는 폴더','아직 실행하지 않음',commands,'check는 설정과 모델 오류 확인, makemigrations는 변경 기록 생성, migrate는 DB에 변경 적용입니다. 소스 수정만으로 기존 DB의 필수 브랜드 조건이 바뀌지 않습니다.','위 수정이 끝나면 한 줄씩 순서대로 실행합니다. 앞 명령이 실패하면 오류부터 해결합니다. 이 문서를 만들면서 명령이나 DB 변경은 실행하지 않았습니다.')

ref=next(p for p in (root.parents[1]/'fcha_tantan_windows_20261104_1-3').glob('*.xlsx') if not p.name.startswith('~$'))
reference=load_workbook(ref,read_only=True)
assert reference.worksheets[0]['A1'].value=='수정 위치'
reference.close()
wb=Workbook(); guide=wb.active;guide.title='처음부터 적용 순서'
guide.append(['순서','파일·구분','해야 할 일','초보자 설명'])
guide.append([0,'먼저 읽기','소스 직접 수정 없음 / 적용 안내서','2026-11-05 이 대화와 현재 파일을 확인한 수정 제안입니다. 다른 대화의 오늘 작업 이력은 포함하지 않았습니다.'])
guide.append([0,'가장 중요한 답변','TipsCommentForm 유지','삭제하지 마세요. forms.py에는 CommentForm과 TipsCommentForm이 모두 필요합니다.'])
for n,p,k,w,b,a,why,how in items:guide.append([n,p+' | '+k,w+' — '+how,why])
guide.append(['참고','어제 엑셀',str(ref),'어제 문서의 모델 → 폼 → 뷰 → DB → 화면 순서와 수정 위치·실제 코드·작성 이유 형식을 참고했습니다.'])
ws=wb.create_sheet('수정 코드 포함 표');ws.append(['수정 위치','실제 파일 줄 번호(작성 시점)','실제 코드(수정 후 또는 유지)','수정 내용','이 코드를 작성한 이유'])
compare=wb.create_sheet('수정 전후 비교');compare.append(['번호','파일','구분','수정 대상','수정 전 코드','수정 후 코드','수정 방법','작성 이유'])
detail=wb.create_sheet('실제 코드와 설명');detail.append(['번호','실제 코드 (한 행에 한 줄)','수정 내용과 작성 이유'])
md=['# 2026-11-05 커뮤니티 댓글 수정 안내','프로젝트 소스는 수정하지 않았습니다. 아래 코드는 사용자가 적용할 최종 제안입니다.','TipsCommentForm은 그대로 유지하고 CommentForm을 함께 사용합니다.','순서: models.py → forms.py → views.py → migrations → 템플릿 → 명령 실행.']
for n,p,k,w,b,a,why,how in items:
    line='신규 생성 예정 / 실행 명령'
    if p in original:
        needle=b.splitlines()[0] if b else w
        pos=original[p].find(needle)
        line=str(original[p][:pos].count('\n')+1)+'줄 부근' if pos>=0 else '대상 이름으로 검색'
    ws.append([p+'\n'+w+' | '+k,line,a,how,why])
    compare.append([n,p,k,w,b,a,how,why])
    detail.append([n,p+' | '+w+' | '+k,how+'\n'+why])
    for code_line in a.splitlines():detail.append([None,code_line,None])
    md.extend(['',f'## {n}. {p} — {w} ({k})',how,why,'```'+('django' if p.endswith('.html') else 'powershell' if k=='실행 안내' or k=='생성 예정' else 'python'),a,'```'])
for p in paths:
    sheet=wb.create_sheet({'community/models.py':'완성 models.py','community/forms.py':'완성 forms.py','community/views.py':'완성 views.py','community/migrations/0001_initial.py':'완성 0001_initial.py','community/templates/community/author.html':'완성 author.html','community/templates/community/detail.html':'완성 detail.html'}[p])
    sheet.append(['최종 줄 번호','전체 완성 코드 (미적용 제안)'])
    for i,l in enumerate(final[p].splitlines(),1):sheet.append([i,l])
    if p.endswith('.py'):ast.parse(final[p])
    md.extend(['',f'## 전체 완성 코드: {p}','아래는 적용 후 모습입니다. 위의 부분 수정 방식과 전체 교체 방식 중 하나만 사용하세요.','```'+('python' if p.endswith('.py') else 'django'),final[p].rstrip(),'```'])
checks=wb.create_sheet('적용 후 확인');checks.append(['확인 항목','예상 결과','실행 여부'])
for case,result in [('비로그인 회원','댓글 작성 시 로그인 필요'),('일반회원 + 꿀팁','브랜드 선택 없이 등록·본인 수정·본인 삭제 가능'),('일반회원 + 다른 분류','댓글 작성 시 점주 인증 안내'),('인증 점주 + 다른 분류','본인의 인증 브랜드 선택 후 댓글 등록 가능'),('타인 댓글 수정·삭제','작성자 조건으로 차단'),('브랜드 없는 댓글 작성자 표시','일반회원 표시'),('검토 중인 게시글','댓글 등록 차단'),('중복 정의','comment_create, comment_delete, Comment.brand 각각 하나'),('마이그레이션','새 파일에 Comment.brand와 Post.topic의 AlterField 확인')]:checks.append([case,result,'사용자 적용 후 확인 필요 / 이번 문서 작업에서 미실행'])
for sheet in wb:
    sheet.freeze_panes='B2';sheet.auto_filter.ref=sheet.dimensions
    sheet.sheet_view.zoomScale=85
    sheet.print_options.horizontalCentered=True
    sheet.sheet_properties.pageSetUpPr.fitToPage=True
    sheet.page_setup.orientation='landscape';sheet.page_setup.paperSize=sheet.PAPERSIZE_A3;sheet.page_setup.fitToWidth=1;sheet.page_setup.fitToHeight=0
    sheet.print_title_rows='1:1'
    for cell in sheet[1]:cell.font=Font(name='맑은 고딕',bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='17365D');cell.alignment=Alignment(wrap_text=True,vertical='center')
    sheet.row_dimensions[1].height=32
    for row in sheet.iter_rows(min_row=2):
        max_lines=1
        for cell in row:
            val=str(cell.value or '')
            cell.font=Font(name='Consolas' if ('완성 ' in sheet.title and cell.column==2) or (sheet.title=='실제 코드와 설명' and cell.column==2) else '맑은 고딕',size=10)
            cell.alignment=Alignment(wrap_text=True,vertical='top')
            if cell.row%2==0:cell.fill=PatternFill('solid',fgColor='EEF3F8')
            max_lines=max(max_lines,sum(max(1,(len(l)+49)//50) for l in val.split('\n')))
        sheet.row_dimensions[row[0].row].height=min(409,max(24,max_lines*15))
    widths=([10,150] if sheet.title.startswith('완성 ') else [9,120,75] if sheet.title=='실제 코드와 설명' else [42,25,110,65,65] if sheet.title=='수정 코드 포함 표' else [8,38,22,30,90,100,65,65] if sheet.title=='수정 전후 비교' else [12,55,85,85])
    for i,width in enumerate(widths[:sheet.max_column],1):sheet.column_dimensions[get_column_letter(i)].width=width
filename=out/'20261105_커뮤니티_수정추가코드_초보자설명.xlsx'
wb.save(filename)
(out/'20261105_커뮤니티_전체수정코드.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
check=load_workbook(filename,read_only=True)
assert len(check.sheetnames)==11
assert check['완성 forms.py'].max_row==len(final[paths[1]].splitlines())+1
check.close()
for p,h in hashes.items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,p+' source changed'
for name in ['comment_create','comment_delete']:assert sum(isinstance(n,ast.FunctionDef) and n.name==name for n in ast.parse(v).body)==1
print('Created:',filename)
print('Validated: 11 sheets, Python syntax, duplicate removal in proposals, original source hashes unchanged.')
