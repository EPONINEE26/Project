from pathlib import Path
import ast
import hashlib
import os
import sys
import types

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
FILES=['community/models.py','community/forms.py','community/views.py','community/migrations/0001_initial.py','community/templates/community/author.html','community/templates/community/detail.html']
BEFORE={p:(ROOT/p).read_bytes() for p in FILES}
SOURCE={p:b.decode('utf-8').replace('\r\n','\n') for p,b in BEFORE.items()}
PROPOSED=dict(SOURCE)
form='''class CommentForm(VerifiedBrandMixin,forms.ModelForm):
    brand=forms.ModelChoiceField(queryset=Brand.objects.none(),required=True,label='브랜드')
    class Meta:
        model=Comment
        fields=('brand','content')
        widgets={'content':forms.Textarea(attrs={'rows':3,'maxlength':2000,'placeholder':'경험과 도움이 되는 의견을 나눠주세요.'})}
'''
p='community/forms.py'
a=SOURCE[p].index('class CommentForm(')
b=SOURCE[p].index('# CommentForm과 TipsCommentForm')
PROPOSED[p]=SOURCE[p][:a]+form+'\n'+SOURCE[p][b:]
p='community/views.py';lines=SOURCE[p].splitlines(keepends=True)
nodes=[n for n in ast.parse(SOURCE[p]).body if isinstance(n,ast.FunctionDef)]
creates=[n for n in nodes if n.name=='comment_create']
for n in reversed(creates[1:]):
    a=min([n.lineno]+[d.lineno for d in n.decorator_list])-1
    del lines[a:n.end_lineno]
v=''.join(lines)
first_create=next(n for n in ast.parse(v).body if isinstance(n,ast.FunctionDef) and n.name=='comment_create')
create_text='\n'.join(v.splitlines()[first_create.lineno-1:first_create.end_lineno])
if "return render(request,'community/detail.html',data,status=400)" not in create_text:
    lines=v.splitlines(keepends=True)
    lines.insert(first_create.end_lineno,"    return render(request,'community/detail.html',data,status=400)\n")
    v=''.join(lines)
delete='''@login_required
@require_POST
def delete(request,pk):
    post=get_object_or_404(Post,pk=pk,author=request.user)
    post.delete();messages.success(request,'게시글을 삭제했습니다.')
    return redirect('community:index')
'''
if not any(n.name=='delete' for n in nodes):
    edit=next(n for n in ast.parse(v).body if isinstance(n,ast.FunctionDef) and n.name=='edit')
    lines=v.splitlines(keepends=True)
    lines.insert(edit.end_lineno,'\n\n'+delete+'\n')
    v=''.join(lines)
PROPOSED[p]=v
if len(creates)>1:
    original_lines=SOURCE[p].splitlines(keepends=True)
    first=creates[0]
    first_start=min([first.lineno]+[d.lineno for d in first.decorator_list])-1
    corrected_create=''.join(original_lines[first_start:first.end_lineno]).rstrip()+'\n'
    if "return render(request,'community/detail.html',data,status=400)" not in corrected_create:
        corrected_create+="    return render(request,'community/detail.html',data,status=400)\n"
    replacements=[]
    last=creates[-1]
    replacements.append((min([last.lineno]+[d.lineno for d in last.decorator_list])-1,last.end_lineno,corrected_create))
    replacements.append((first_start,first.end_lineno,delete))
    for a,b,replacement in sorted(replacements,reverse=True):
        original_lines[a:b]=[replacement]
    PROPOSED[p]=''.join(original_lines)
    final_names=[n.name for n in ast.parse(PROPOSED[p]).body if isinstance(n,ast.FunctionDef)]
    assert final_names.count('comment_create')==1 and final_names.count('delete')==1
p='community/migrations/0001_initial.py'
PROPOSED[p]=SOURCE[p].split('\n@login_required')[0].rstrip()+'\n'
for p in ['community/templates/community/author.html','community/templates/community/detail.html']:
    lines=SOURCE[p].splitlines(keepends=True)
    PROPOSED[p]=''.join(l for l in lines if not ('<!--' in l and ('{% endcomment %}' in l or '{% elif can_post %}' in l)))
for p,s in PROPOSED.items():
    if p.endswith('.py'):ast.parse(s)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','fcha_tantan.settings')
import django
django.setup()
for name,path in [('community.forms','community/forms.py'),('community.views','community/views.py')]:
    module=types.ModuleType(name);module.__file__=str(ROOT/path);module.__package__='community'
    sys.modules[name]=module
    exec(compile(PROPOSED[path],str(ROOT/path),'exec'),module.__dict__)
    setattr(sys.modules['community'],name.rsplit('.',1)[1],module)
from django.core.checks import run_checks
issues=run_checks()
errors=[i for i in issues if i.level>=40]
print('SYSTEM CHECK ERRORS:',len(errors))
for issue in issues:print(str(issue))
assert not errors
from django.template import engines, Context, Engine
engine=engines['django'].engine
for p in ['community/templates/community/author.html','community/templates/community/detail.html']:
    engine.from_string(PROPOSED[p]);print('TEMPLATE COMPILED:',p)
from django.test import RequestFactory
from django.http import HttpResponse
from unittest.mock import Mock, patch
view=sys.modules['community.views']
request=RequestFactory().post('/community/1/comments/',{'content':''})
request.user=types.SimpleNamespace(is_authenticated=True,pk=1)
post=types.SimpleNamespace(topic='store_tips',author_id=1,comments=Mock(),pk=1)
form_mock=Mock();form_mock.is_valid.return_value=False
with patch.multiple(view,get_object_or_404=Mock(return_value=post),comment_form_for=Mock(return_value=form_mock),context=Mock(return_value={}),may_comment=Mock(return_value=True),render=Mock(return_value=HttpResponse(status=400))):
    response=view.comment_create(request,1)
    assert response.status_code==400
print('INVALID COMMENT RESPONSE: HTTP 400')
for p,b in BEFORE.items():assert (ROOT/p).read_bytes()==b,'Source changed: '+p
print('ORIGINAL SOURCE FILES: unchanged')

if __name__=='__main__':
    pass
