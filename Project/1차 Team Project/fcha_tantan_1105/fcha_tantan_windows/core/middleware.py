import json
from django.http import QueryDict
from .moderation import TECHNICAL_FIELDS, policy, sanitize


class ContentFilterMiddleware:
    """Filter ordinary user prose on both normal forms and query strings.

    Credentials, IDs, files, URLs and security tokens are not rewritten. Admin
    originals are kept available for review. All mutation endpoints still use CSRF.
    """
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        request.moderation_originals={}
        if not request.path.startswith(('/admin/','/oauth/','/static/')):
            config=policy();request.moderation_policy=config
            def clean_dict(values):
                updated=values.copy()
                for name, entries in values.lists():
                    if name in TECHNICAL_FIELDS or name.startswith('_') or any(x in name.lower() for x in ('password','token','secret')):continue
                    result=[]
                    for value in entries:
                        cleaned,found=sanitize(value,config)
                        if found:request.moderation_originals[name]=value
                        result.append(cleaned)
                    updated.setlist(name,result)
                return updated
            request.GET=clean_dict(request.GET)
            if request.method=='POST' and request.content_type in ('application/x-www-form-urlencoded','multipart/form-data'):
                original_post=request.POST
                request.POST=clean_dict(original_post)
                try:
                    raw=original_post.get('__filtered_originals','{}')
                    submitted=json.loads(raw) if len(raw)<50000 else {}
                    if isinstance(submitted,dict):
                        for name,value in list(submitted.items())[:40]:
                            if name in TECHNICAL_FIELDS or name.startswith('_') or any(x in name.lower() for x in ('password','token','secret')):continue
                            if not isinstance(value,str) or len(value)>10000:continue
                            cleaned,found=sanitize(value,config)
                            if found and request.POST.get(name)==cleaned:request.moderation_originals[name]=value
                except (ValueError,TypeError):pass
        return self.get_response(request)
