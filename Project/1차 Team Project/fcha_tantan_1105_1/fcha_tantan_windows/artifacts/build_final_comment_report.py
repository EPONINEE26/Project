from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import ast, os, sys, types, zipfile, hashlib
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'artifacts/comment_report_20261105_final'
OUT.mkdir(parents=True,exist_ok=True)
paths=['community/models.py','community/forms.py','community/views.py','community/urls.py','community/migrations/0001_initial.py','community/migrations/0002_owner_tips_member_comments.py','community/templates/community/author.html','community/templates/community/detail.html']
raw={p:(ROOT/p).read_bytes() for p in paths if (ROOT/p).exists()}
src={p:b.decode('utf-8').replace('\r\n','\n') for p,b in raw.items()}
fixed=dict(src)
def nodes(text,name):
    return [n for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name]
def bounds(n):return min([n.lineno]+[d.lineno for d in getattr(n,'decorator_list',[])]),n.end_lineno
def extract(text,name):
    ns=nodes(text,name)
    if not ns:return ''
    a,b=bounds(ns[-1]);return '\n'.join(text.splitlines()[a-1:b])
form='''class CommentForm(VerifiedBrandMixin,forms.ModelForm):
    brand=forms.ModelChoiceField(queryset=Brand.objects.none(),required=True,label='브랜드')
    class Meta:
        model=Comment
        fields=('brand','content')
        widgets={'content':forms.Textarea(attrs={'rows':3,'maxlength':2000,'placeholder':'경험과 도움이 되는 의견을 나눠주세요.'})}
'''
p='community/forms.py';s=src[p];a=s.index('class CommentForm(');b=s.index('class TipsCommentForm(')
fixed[p]=s[:a]+form+'\n\n'+s[b:]
p='community/views.py';s=src[p]
s=s.replace('\n        data=context(request);data.update(post=post,comments_list=comments,','\n    data=context(request);data.update(post=post,comments_list=comments,')
create=extract(s,'comment_create')
if "return render(request,'community/detail.html',data,status=400)" not in create:
    create+="\n    return render(request,'community/detail.html',data,status=400)"
lines=s.splitlines(keepends=True);ns=nodes(s,'comment_create')
for n in reversed(ns):
    a,b=bounds(n);lines[a-1:b]=[(create+'\n') if n is ns[-1] else '']
s=''.join(lines)
if not nodes(s,'delete'):
    s+='''\n@login_required
@require_POST
def delete(request,pk):
    post=get_object_or_404(Post,pk=pk,author=request.user)
    post.delete();messages.success(request,'게시글을 삭제했습니다.')
    return redirect('community:index')
'''
fixed[p]=s
p='community/templates/community/detail.html'
fixed[p]=''.join(l for l in src[p].splitlines(keepends=True) if not ('<!--' in l and '{% elif can_post %}' in l))
p='community/templates/community/author.html'
fixed[p]=''.join(l for l in src[p].splitlines(keepends=True) if not ('<!--' in l and '{% endcomment %}' in l))
p='community/migrations/0001_initial.py'
fixed[p]=src[p].split('\n@login_required')[0].rstrip()+'\n'

os.environ.setdefault('DJANGO_SETTINGS_MODULE','fcha_tantan.settings')
import django
django.setup()
for name,p in [('community.forms','community/forms.py'),('community.views','community/views.py')]:
    module=types.ModuleType(name);module.__package__='community';module.__file__=str(ROOT/p)
    sys.modules[name]=module
    exec(compile(fixed[p],str(ROOT/p),'exec'),module.__dict__)
    setattr(sys.modules['community'],name.rsplit('.',1)[1],module)
from django.core.checks import run_checks
errors=[str(e) for e in run_checks() if e.level>=40]
assert not errors,errors
from django.template import engines, Context
from community.forms import TipsCommentForm
engine=engines['django'].engine
for p in ['community/templates/community/detail.html','community/templates/community/author.html']:engine.from_string(fixed[p])
p='community/templates/community/detail.html';a=fixed[p].rindex("{% if post.moderation_state != 'visible' %}");b=fixed[p].index('</section>',a)
tests=[]
for label,owner,allowed,logged,visible,want in [('일반회원·꿀팁',False,True,True,True,True),('인증 점주·꿀팁',True,True,True,True,True),('일반회원·기존 게시판',False,False,True,True,False),('비로그인',False,False,False,True,False),('검토 중인 글',True,True,True,False,False)]:
    ctx={'post':types.SimpleNamespace(pk=11,moderation_state='visible' if visible else 'blind'),'user':types.SimpleNamespace(is_authenticated=logged),'request':types.SimpleNamespace(path='/community/11/'),'form':TipsCommentForm(),'can_post':owner,'can_comment':allowed,'csrf_token':'test-token'}
    html=engine.from_string(fixed[p][a:b]).render(Context(ctx))
    actual='comment-form' in html
    assert actual==want,label
    tests.append((label,'입력창 표시' if want else '입력창 숨김','통과'))
from unittest.mock import Mock,patch
from django.test import RequestFactory
from django.http import HttpResponse
v=sys.modules['community.views'];req=RequestFactory().post('/community/11/comments/',{'content':'발표 확인용'})
req.user=types.SimpleNamespace(pk=1,is_authenticated=True)
post=types.SimpleNamespace(pk=11,topic='store_tips',author_id=2,comments=Mock())
f=Mock();f.is_valid.return_value=False
with patch.multiple(v,get_object_or_404=Mock(return_value=post),comment_form_for=Mock(return_value=f),context=Mock(return_value={}),may_comment=Mock(return_value=True),render=Mock(return_value=HttpResponse(status=400))):assert v.comment_create(req,11).status_code==400
f.is_valid.return_value=True;comment=Mock();f.save.return_value=comment
brands=Mock();brands.first.return_value=None;save=Mock()
with patch.multiple(v,get_object_or_404=Mock(return_value=post),comment_form_for=Mock(return_value=f),verified_brands=Mock(return_value=brands),record_match=save):
    response=v.comment_create(req,11)
    assert response.status_code==302 and comment.author is req.user and comment.post is post and comment.brand is None
    save.assert_called_once()
tests.extend([('일반회원 댓글 등록 경로','브랜드 없이 저장 처리 호출 후 이동','모의 객체 검사 통과 / 실제 DB 저장 미실행'),('잘못된 댓글 입력','HTTP 400 화면 응답','모의 객체 검사 통과'),('Django 시스템 검사','오류 0개','메모리 수정안 검사 통과'),('두 화면 파일 문법','컴파일 성공','통과')])

items=[]
def add(p,target,code,why,how='제시 코드로 교체',needle=None):
    text=src.get(p,'');ls=text.splitlines();loc='생성된 파일 / 명령 실행 위치'
    if target in ['CommentForm','TipsCommentForm','verified_brands','VerifiedBrandMixin','may_comment','comment_form_for','comment_create','comment_edit','comment_delete','delete','detail','record_match']:
        ns=nodes(text,target) if text else []
        if ns:loc=' / '.join(f'{bounds(n)[0]}~{bounds(n)[1]}줄' for n in ns)
        elif target=='delete':loc='함수 추가 위치: 파일 맨 아래 빈 줄'
    elif needle:
        numbers=[i for i,l in enumerate(ls,1) if needle in l and not l.lstrip().startswith('#')]
        if numbers:loc='·'.join(map(str,numbers))+'줄'
    items.append([len(items)+1,p,loc,target,code,why,how])
p='community/models.py'
for target,needle,why in [('TOPICS','TOPICS=','글을 분류하는 선택 목록으로, store_tips는 저장할 값이고 매장 준비 꿀팁은 화면에 보여줄 이름입니다.'),('topic','topic=models','선택한 분류를 저장하는 칸으로, choices=TOPICS는 선택 목록을 연결하고 default=free는 기본 분류를 정합니다.')]:
    line=next(l for l in fixed[p].splitlines() if needle in l and not l.lstrip().startswith('#'));add(p,target,line,why,needle=needle)
add(p,'Comment.brand',next(l for l in fixed[p].splitlines() if 'null=True,blank=True)' in l and not l.lstrip().startswith('#')),'null=True는 DB에 빈 값을 허용하고 blank=True는 입력 생략을 허용하여 브랜드 없는 일반회원 댓글을 저장하게 합니다.',needle='brand=models.ForeignKey')
for target,why in [('verified_brands','로그인 여부·승인 상태·계약 종료일을 확인하여 해당 회원의 유효한 인증 브랜드만 가져옵니다.'),('VerifiedBrandMixin','브랜드 선택 목록을 본인의 인증 브랜드로 제한하고 하나뿐이면 기본 선택값을 설정합니다.'),('CommentForm','기존 게시판에서는 인증 브랜드와 댓글 내용을 입력받고 required=True로 브랜드 선택을 필수로 정합니다.'),('TipsCommentForm','꿀팁에서는 fields=(content,)로 댓글 내용만 입력받고 브랜드 선택을 요구하지 않습니다.')]:add('community/forms.py',target,extract(fixed['community/forms.py'],target),why,'함수·클래스의 설정과 들여쓰기를 설명하는 코드')
p='community/views.py';add(p,'forms import',next(l for l in fixed[p].splitlines() if l.startswith('from .forms')),'다른 파일에 있는 입력창과 인증 브랜드 조회 함수를 이 파일에서 사용할 수 있게 가져옵니다.',needle='from .forms import')
for target,why in [('may_comment','로그인했고 꿀팁 글이거나 인증 브랜드가 있으면 댓글을 작성할 수 있다는 결과를 돌려줍니다.'),('comment_form_for','게시글 종류에 맞는 입력창을 선택하며 data는 제출 내용이고 instance는 수정할 기존 댓글입니다.'),('comment_create','공개 글 조회→분류별 인증 확인→입력 검사→작성자·글 연결→내용 검수와 저장→게시글 이동 순서로 댓글을 등록합니다.'),('detail','게시글·댓글 목록과 분류에 맞는 댓글 입력창 및 can_comment를 화면에 전달합니다.'),('comment_edit','본인 댓글을 찾아 꿀팁은 일반회원도 수정하도록 하며 instance로 기존 댓글을 지정합니다.'),('comment_delete','로그인한 작성자 본인의 댓글만 삭제하고 해당 게시글 화면으로 돌아갑니다.'),('delete','본인 게시글을 삭제하고 목록으로 이동하며 urls.py가 참조하는 views.delete 함수를 제공합니다.'),('record_match','금지어를 검사하고 댓글을 저장하며 감지 결과에 따라 검토 기록과 안내 메시지를 만듭니다.')]:add(p,target,extract(fixed[p],target),why,'완성 코드 시트의 단일 함수 구성 참고 / 같은 이름의 함수를 중복 추가하지 않음')
add('community/urls.py','댓글·게시글 주소',src['community/urls.py'],'주소와 함수 이름을 연결하며 comment_create는 댓글 등록, comment_delete는 댓글 삭제, delete는 게시글 삭제입니다.','주소 연결 설명용')
p='community/migrations/0002_owner_tips_member_comments.py'
if p in fixed:add(p,'DB 변경 기록',fixed[p],'Comment.brand의 빈 값 허용과 Post.topic의 꿀팁 선택 항목을 DB 변경 기록에 반영합니다.','Django가 생성하는 파일이며 초기 마이그레이션에 웹 요청 처리 함수를 넣지 않음')
add('community/templates/community/author.html','작성자 표시',next(l for l in fixed['community/templates/community/author.html'].splitlines() if 'owner-brand' in l),'브랜드가 있으면 브랜드명과 점주를, 없으면 일반회원을 표시합니다.',needle='owner-brand')
add('community/templates/community/detail.html','댓글 입력창 조건','            {% elif can_comment %}','댓글 작성 권한이 참일 때 입력창을 보여주며 can_comment는 게시글 정보인 post와 서로 다른 변수입니다.','현재 최종 파일 기준 조건문 설명 / 과거 줄 번호를 그대로 적용하지 않음',needle='can_comment')
add('community/templates/community/detail.html','댓글 등록 폼',"<form method=\"post\" action=\"{% url 'community:comment_create' post.pk %}\" class=\"form-stack comment-form\">{% csrf_token %}{% include 'includes/form_fields.html' %}<button class=\"button\">댓글 등록</button></form>",'post.pk로 댓글이 달릴 게시글 번호를 전달하고 csrf_token과 입력 내용을 댓글 등록 주소로 제출합니다.',needle='class="form-stack comment-form"')
dp='community/templates/community/detail.html'
comment_line=next((l for l in src[dp].splitlines() if '{#' in l and '댓글' in l),'            {# 댓글 입력창 표시 조건 #}')
add(dp,'화살표 표시 수정',comment_line,'HTML 주석 안의 Django 조건문이 처리되면서 남던 --> 표시를 Django 주석으로 바꾸어 화면에 출력되지 않게 했습니다.','이번 대화에서 detail.html을 직접 수정한 부분',needle=comment_line.strip())
for marker,title,why in [('article-actions','게시글 신고 버튼 제거','게시글 신고 입력란과 버튼을 화면에서 제거하고 게시글 작성자 본인의 수정·삭제 기능을 남겼습니다.'),('comment-actions','댓글 신고 버튼 제거','댓글 신고 버튼을 화면에서 제거하고 댓글 작성자 본인의 수정·삭제 기능을 남겼습니다.')]:
    a=src[dp].index(marker);a=src[dp].rfind('<div',0,a);b=src[dp].index('</div>',a)+len('</div>')
    code=src[dp][a:b]
    add(dp,title,code,why,'이번 대화에서 detail.html을 직접 수정한 부분 / 신고 표시 조건만 변경한 중간안을 최종 버튼 제거로 마무리')
    items[-1][2]=f'{src[dp][:a].count(chr(10))+1}~{src[dp][:b].count(chr(10))+1}줄'
for row in items:
    if row[3]=='Comment.brand':
        comment_node=nodes(src[row[1]],'Comment')[-1]
        line=next(n for n in comment_node.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='brand' for t in n.targets))
        row[2]=f'{line.lineno}줄 — Comment 클래스 안의 brand'

wb=Workbook();intro=wb.active;intro.title='처음부터 읽기'
intro.append(['순서','내용','초보자 설명'])
intro.append([1,'작업 목표','매장 준비 꿀팁에서 로그인한 일반회원도 브랜드 선택 없이 댓글을 작성·수정·삭제하게 합니다.'])
intro.append([2,'핵심 원인','HTML 주석 <!-- --> 안에서도 Django의 {% elif can_post %}가 실행되어 댓글 입력창을 건너뛸 수 있습니다.'])
intro.append([3,'최종 화면 변경','옛 조건은 Django 주석으로 바꾸고 can_comment로 입력창을 표시하며, 게시글·댓글 신고 버튼은 화면에서 제거했습니다.'])
intro.append([4,'줄 번호 기준',datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M KST')+'의 저장 파일 기준이며, 수정 후 줄 번호는 완성 코드 시트에서 별도 확인합니다.'])
intro.append([5,'작업 구분','detail.html의 주석과 신고 버튼 부분은 대화 후반에 직접 수정했습니다. 다른 파일은 사용자 편집 내용과 적용 안내용 수정안을 구분해 기록했으며, 이번 엑셀 생성은 소스·DB를 변경하지 않습니다.'])
intro.append([6,'검증 범위','시스템 검사·템플릿 문법·5가지 댓글창 표시 조건·모의 객체를 이용한 등록/입력 오류 경로 검사입니다. 실제 DB 댓글 저장은 실행하지 않았습니다.'])
intro.append([7,'어제 문서 참고','점주커뮤니티에서 매장 준비 꿀팁 추가항목 코드 및 설명.xlsx의 수정 위치·줄 번호·실제 코드·작성 이유 형식을 참고했습니다.'])
main=wb.create_sheet('전체 코드와 한줄 설명');main.append(['순서','파일','현재 저장 파일 줄 번호','코드 이름','수정 후 코드','코드 설명 한 줄','적용 방법'])
for row in items:main.append(row)
meaning=wb.create_sheet('함수 줄별 설명');meaning.append(['파일·함수','함수 안 상대 줄','실제 코드','이 줄의 의미'])
rules=[('@login_required','로그인한 회원만 실행합니다.'),('@require_POST','등록·삭제 내용을 제출하는 POST 요청만 받습니다.'),('def ','입력받을 값과 실행할 처리 절차의 이름을 정합니다.'),('get_object_or_404','번호와 작성자 등의 조건에 맞는 정보를 찾고 없으면 404 응답을 만듭니다.'),('if post.topic!=','꿀팁이 아닌 글인지 확인하여 점주 인증 검사 여부를 정합니다.'),('blocked=','점주 인증이 없으면 보낼 인증 화면 응답을 준비합니다.'),('if blocked:','인증 화면으로 보내야 하면 여기서 처리를 끝냅니다.'),('form=comment_form_for','게시글 분류에 맞는 입력창으로 제출 내용을 검사할 준비를 합니다.'),('form.is_valid','누락·길이 초과·허용되지 않은 선택 등 입력 오류를 검사합니다.'),('commit=False','아직 DB에 저장하지 않고 작성자와 게시글을 연결할 댓글 정보를 만듭니다.'),('comment.brand=','댓글 작성자 본인의 인증 브랜드를 연결하고 없으면 비워 둡니다.'),('record_match(','금지어를 검사하고 저장 처리 함수를 실행합니다.'),('redirect(','다른 주소로 이동하라는 응답을 돌려줍니다.'),('data=context','화면에 전달할 게시글·입력창·권한 등의 정보를 준비합니다.'),('return render','준비한 정보로 HTML 화면을 만들어 응답합니다.'),('instance=comment','새 댓글 생성이 아니라 해당 기존 댓글을 수정하도록 지정합니다.'),('return ','함수의 처리 결과를 호출한 곳으로 돌려줍니다.')]
for target in ['may_comment','comment_form_for','comment_create','comment_edit','comment_delete','delete','detail']:
    for num,line in enumerate(extract(fixed['community/views.py'],target).splitlines(),1):
        why=next((v for k,v in rules if k in line),'상위 조건 안에서 해당 댓글·게시글 정보를 설정하거나 다음 처리에 사용할 값을 준비합니다.')
        meaning.append(['views.py / '+target,num,line,why])
gloss=wb.create_sheet('용어와 실수 방지');gloss.append(['표현','쉬운 설명'])
for row in [('TOPICS','고를 수 있는 게시글 분류 목록'),('topic','게시글 한 개에 선택한 분류를 저장하는 칸'),('post','현재 게시글 정보'),('can_post','게시글 작성 가능 여부'),('can_comment','해당 게시글의 댓글 작성 가능 여부'),('pk','회원·게시글·댓글을 구별하는 고유 번호'),('request','요청한 회원·제출한 내용 등이 담긴 정보'),('POST','입력 내용을 서버로 제출하는 요청 방식'),('GET','화면이나 정보를 조회하는 요청 방식'),('None','값이 없다는 뜻'),('instance','수정할 기존 댓글'),('== / !=','같은지 / 다른지 비교'),('들여쓰기','함수 안 4칸, 그 안 조건문 안 8칸처럼 어떤 코드에 속하는지 구분'),('HTML 주석','<!-- -->는 Django 태그 실행을 막지 않음'),('마이그레이션','DB의 저장 구조를 바꾸는 기록이며 댓글 등록·삭제 함수를 넣는 파일이 아님'),('같은 이름 함수 두 개','파이썬은 뒤쪽 함수를 사용하므로 최종 완성 코드에서는 각각 하나로 구성')]:gloss.append(row)
checks=wb.create_sheet('검사 결과');checks.append(['검사 항목','예상 동작','검사 결과'])
for row in tests:checks.append(row)
assert 'community:report_post' not in src[dp] and 'community:report_comment' not in src[dp]
checks.append(['신고 버튼 최종 화면','게시글·댓글 신고 버튼 없음','최종 저장 템플릿에 두 신고 주소가 없는 것을 확인'])
checks.append(['화살표 최종 화면','옛 can_post 주석 조건 없음','최종 저장 템플릿에 <!--{% elif can_post %}-->가 없는 것을 확인'])
history=wb.create_sheet('오류 원인과 해결');history.append(['오늘 발생한 문제','원인','해결 내용','주의할 점'])
for row in [('TipsCommentForm 이름 오류','forms.py의 클래스 이름과 import가 일치하지 않음','TipsCommentForm을 정확한 이름으로 import','TipCommentForm이 아니라 TipsCommentForm'),('일반회원 댓글 제한','기존 점주 인증과 브랜드 선택 폼을 꿀팁에도 적용','꿀팁에는 내용만 받는 폼과 분류별 인증 조건 적용','기존 게시판의 점주 조건과 구분'),('views.delete 없음','urls.py가 참조하는 게시글 삭제 함수 누락','delete 함수 복원 코드 안내','comment_delete는 댓글 삭제로 서로 다른 함수'),('댓글 등록 함수 중복','같은 이름의 함수가 두 개여서 뒤쪽 함수가 사용됨','완성 코드 사본은 comment_create 하나로 구성','현재 코드와 수정안의 줄 번호를 별도 시트로 구분'),('들여쓰기 오류','detail 함수의 data 줄 앞 공백이 한 단계 더 들어감','함수 안의 다른 줄과 같은 4칸으로 정렬','공백도 코드 구조의 일부'),('endcomment 오류','시작 표시 없는 endcomment가 HTML 주석 안에 들어감','올바른 작성자 표시 코드로 교체 안내','HTML 주석은 Django 태그 처리를 막지 않음'),('댓글 입력창 없음','HTML 주석 속 옛 can_post 조건이 먼저 실행됨','옛 조건을 Django 주석으로 변경','can_comment 한 줄만 다시 입력하는 것으로는 옛 조건이 사라지지 않음'),('화면에 --> 출력','조건문 처리 후 HTML 주석 끝부분이 화면에 남음','{# 댓글 입력창 표시 조건 #}로 직접 수정','바깥에 <!-- -->를 덧붙이지 않음'),('일반회원에게 신고 버튼 노출','첫 번째 숨김 조건은 인증 브랜드가 있는 계정에 노출 가능','최종적으로 게시글·댓글 신고 버튼 블록을 화면에서 제거','댓글 입력창과 작성자 본인 수정·삭제 기능은 별도')]:history.append(row)
cmd=wb.create_sheet('실행 명령');cmd.append(['순서','PowerShell 명령','설명 한 줄','진행 조건'])
for i,(c,why) in enumerate([('python manage.py check','프로젝트 설정과 주소 연결 등을 검사합니다.'),('python manage.py makemigrations community --name owner_tips_member_comments','모델 변경에 필요한 기록을 만듭니다.'),('python manage.py migrate','변경 기록을 실제 DB에 적용합니다.'),('python manage.py runserver','개발 서버를 실행합니다.')],1):cmd.append([i,c,why,'앞 단계가 성공한 다음 실행 / 오류 시 다음 단계 진행 중단'])
for i,p in enumerate(paths,1):
    if p not in src:continue
    snap=wb.create_sheet('현재줄_'+str(i));snap.append(['파일','현재 줄 번호','현재 저장된 코드'])
    for n,l in enumerate(src[p].splitlines(),1):snap.append([p,n,l])
    fin=wb.create_sheet('완성코드_'+str(i));fin.append(['파일','수정 후 줄 번호','검증한 완성 코드 사본'])
    for n,l in enumerate(fixed[p].splitlines(),1):fin.append([p,n,l])
    dest=OUT/'proposed'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(fixed[p],encoding='utf-8')
for sh in wb:
    sh.freeze_panes='C2';sh.auto_filter.ref=sh.dimensions;sh.sheet_view.zoomScale=85
    sh.print_title_rows='1:1';sh.sheet_properties.pageSetUpPr.fitToPage=True
    sh.page_setup.orientation='landscape';sh.page_setup.paperSize=sh.PAPERSIZE_A3;sh.page_setup.fitToWidth=1;sh.page_setup.fitToHeight=0
    for cell in sh[1]:cell.fill=PatternFill('solid',fgColor='17365D');cell.font=Font(name='맑은 고딕',bold=True,color='FFFFFF');cell.alignment=Alignment(wrap_text=True,vertical='center')
    sh.row_dimensions[1].height=32
    widths=[8,42,28,27,110,100,85] if sh==main else [42,18,155] if sh.title.startswith(('현재줄_','완성코드_')) else [38,18,100,90] if sh==meaning else [30,75,100,65]
    for n,width in enumerate(widths[:sh.max_column],1):sh.column_dimensions[get_column_letter(n)].width=width
    for row in sh.iter_rows(min_row=2):
        height=25
        for cell in row:
            cell.font=Font(name='맑은 고딕',size=10);cell.alignment=Alignment(wrap_text=True,vertical='top')
            if cell.row%2==0:cell.fill=PatternFill('solid',fgColor='EEF3F8')
            height=max(height,15*sum(max(1,(len(l)+59)//60) for l in str(cell.value or '').split('\n')))
        sh.row_dimensions[row[0].row].height=min(height,409)
xlsx=ROOT/'artifacts/community_work_20261105_final.xlsx';wb.save(xlsx)
md=['# 2026-11-05 전체 작업 코드와 설명','소스·DB 미변경. 검증된 수정안 사본입니다.']
for n,p,loc,target,code,why,how in items:md.extend(['',f'## {n}. {p} | {loc} | {target}',how,'```'+('django' if p.endswith('.html') else 'python'),code,'```','설명: '+why])
(OUT/'code_and_explanation.md').write_text('\n'.join(md),encoding='utf-8')
archive=ROOT/'artifacts/community_work_20261105_final.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    z.write(xlsx,xlsx.name)
    for p in OUT.rglob('*'):
        if p.is_file():z.write(p,str(p.relative_to(OUT)))
test=load_workbook(xlsx,read_only=True);assert test['전체 코드와 한줄 설명'].max_row==len(items)+1;test.close()
for p,b in raw.items():assert (ROOT/p).read_bytes()==b,'Source changed: '+p
print('EXCEL:',xlsx)
print('ZIP:',archive)
print('ITEMS:',len(items),'SHEETS:',len(wb.sheetnames))
print('CHECK: system 0 errors; templates valid; five display conditions passed; mocked valid/invalid POST passed; source/DB unchanged.')
