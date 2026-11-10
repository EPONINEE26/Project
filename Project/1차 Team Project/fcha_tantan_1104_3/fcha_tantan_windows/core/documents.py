"""Local evidence precheck: file signatures/required files. Never certifies authenticity."""
from pathlib import Path
from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_evidence(file):
    if not file:return file
    if file.size > 10*1024*1024:raise ValidationError('파일은 10MB 이하로 올려주세요.')
    suffix=Path(file.name).suffix.lower()
    position=file.tell();head=file.read(12);file.seek(position)
    valid=(suffix=='.pdf' and head.startswith(b'%PDF-')) or (suffix=='.png' and head.startswith(b'\x89PNG\r\n\x1a\n')) or (suffix in ('.jpg','.jpeg') and head.startswith(b'\xff\xd8\xff'))
    if not valid:raise ValidationError('실제 PDF·JPG·PNG 파일만 올릴 수 있습니다. 확장자만 바꾼 파일은 허용되지 않습니다.')
    return file


def precheck(instance, field_names):
    checks=[]
    for name in field_names:
        file=getattr(instance,name,None)
        if not file:
            checks.append({'field':name,'ok':False,'message':'자료 미제출'});continue
        try:
            with file.open('rb') as handle:validate_evidence(handle)
            checks.append({'field':name,'ok':True,'message':'파일 형식·용량 확인'})
        except (ValidationError,OSError,ValueError):
            checks.append({'field':name,'ok':False,'message':'파일 열기 또는 형식 확인 필요'})
    instance.document_check={'method':'local_rules','checked_at':timezone.now().isoformat(),'checks':checks,
                             'summary':'기본 파일 점검 완료. 서류 내용·진위·명의·브랜드 일치 여부는 관리자 검토가 필요합니다.',
                             'ai_performed':False}
    instance.save(update_fields=['document_check'])
    return instance.document_check
