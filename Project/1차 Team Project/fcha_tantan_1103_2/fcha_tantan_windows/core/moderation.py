"""Small, transparent local word filter. No LLM or paid service is used."""
import re
import unicodedata
from django.db import OperationalError, ProgrammingError
from .models import ModerationPolicy, default_terms

ZERO_WIDTH = re.compile('[\u200b-\u200f\u202a-\u202e\u2060\ufeff]')
TECHNICAL_FIELDS = {'csrfmiddlewaretoken','password','password1','password2','old_password','new_password1','new_password2',
                   'email','username','login','next','code','key','token','uid','action','status','brand','verification',
                   'latitude','longitude','phone','contact_phone','business_number','postcode','language','lang','url','path'}


def policy():
    try:
        item = ModerationPolicy.objects.filter(pk=1).first()
    except (OperationalError, ProgrammingError):
        item = None
    return item or ModerationPolicy()


def patterns(terms):
    for term in terms:
        if not isinstance(term, str) or not term.strip() or len(term)>40: continue
        term = unicodedata.normalize('NFKC', term.strip())
        body = r'[\s._*·\-]*'.join(re.escape(ch) for ch in term)
        if term.isascii(): body = r'(?<![A-Za-z])' + body + r'(?![A-Za-z])'
        yield re.compile(body, re.I)


def sanitize(value, config=None):
    config = config or policy()
    if not config.enabled or not isinstance(value,str): return value, False
    normalized = ZERO_WIDTH.sub('', unicodedata.normalize('NFKC', value))
    cleaned = normalized
    matched = False
    for pattern in patterns(config.blocked_terms):
        cleaned, count = pattern.subn('',cleaned)
        matched = matched or bool(count)
    return (cleaned.strip() if matched else value), matched


def flag_content(obj, request, fields):
    config = getattr(request,'moderation_policy',None) or policy()
    originals = {}
    for name in fields:
        raw = getattr(request,'moderation_originals',{}).get(name, getattr(obj,name,''))
        clean, found = sanitize(raw, config)
        setattr(obj,name,clean)
        if found: originals[name] = raw
    if originals:
        obj.moderation_original = originals
        if obj.moderation_state not in ('blind','removed'):
            obj.moderation_state = 'blind' if config.blind_on_match else 'visible'
        obj.moderation_reason = '비속어 자동 감지 · 관리자 검토 필요'
    # Editing a blind/removed item never makes it public without staff review.
    return bool(originals)


def public_message(obj):
    return policy().removed_message if obj.moderation_state=='removed' else '운영정책에 따라 검토 중인 게시물입니다.'
