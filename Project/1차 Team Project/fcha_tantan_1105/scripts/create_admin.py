"""관리자(슈퍼유저) 계정을 만듭니다.

.env에 DJANGO_SUPERUSER_USERNAME / PASSWORD가 없으면 임의의 강한 비밀번호를 만들어 .env에 저장합니다.
이미 같은 아이디가 있으면 아무것도 바꾸지 않습니다(비밀번호를 덮어쓰지 않음).
"""
import os
import secrets
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
env_path = root / '.env'


def read_env():
    values = {}
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip()
    return values


values = read_env()
if not values.get('DJANGO_SUPERUSER_USERNAME') or not values.get('DJANGO_SUPERUSER_PASSWORD'):
    additions = {'DJANGO_SUPERUSER_USERNAME': values.get('DJANGO_SUPERUSER_USERNAME') or 'tantan_admin',
                 'DJANGO_SUPERUSER_EMAIL': values.get('DJANGO_SUPERUSER_EMAIL') or 'admin@fcha-tantan.local',
                 'DJANGO_SUPERUSER_PASSWORD': values.get('DJANGO_SUPERUSER_PASSWORD') or secrets.token_urlsafe(18)}
    if not env_path.exists() and (root / '.env.example').exists():
        env_path.write_text((root / '.env.example').read_text(encoding='utf-8'), encoding='utf-8')
    lines = [l for l in env_path.read_text(encoding='utf-8').splitlines() if l.split('=', 1)[0].strip() not in additions] if env_path.exists() else []
    lines += [f'{k}={v}' for k, v in additions.items()]
    env_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    values.update(additions)
    print('.env에 관리자 계정 정보를 저장했습니다.')

for key in ('DJANGO_SUPERUSER_USERNAME', 'DJANGO_SUPERUSER_EMAIL', 'DJANGO_SUPERUSER_PASSWORD'):
    os.environ[key] = values.get(key, '')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fcha_tantan.settings')
import django
django.setup()
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ['DJANGO_SUPERUSER_USERNAME']
if User.objects.filter(username=username).exists():
    print(f'관리자 계정 "{username}"이 이미 있습니다. 변경하지 않았습니다.')
else:
    User.objects.create_superuser(username=username, email=os.environ['DJANGO_SUPERUSER_EMAIL'],
                                  password=os.environ['DJANGO_SUPERUSER_PASSWORD'])
    print(f'관리자 계정 "{username}"을 만들었습니다. 비밀번호는 .env의 DJANGO_SUPERUSER_PASSWORD를 확인하세요.')
