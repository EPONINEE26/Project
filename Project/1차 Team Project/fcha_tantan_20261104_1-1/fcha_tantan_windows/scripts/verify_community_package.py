"""Run community tests against templates and tests stored in a project ZIP."""
import copy
import os
from pathlib import Path
import sys
import types
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fcha_tantan.settings')
import django
django.setup()
from django.conf import settings
from django.test import override_settings
from django.test.utils import get_runner

archive = Path(sys.argv[1])
with zipfile.ZipFile(archive) as bundle:
    templates = {name.split('/templates/', 1)[1]: bundle.read(name).decode('utf-8')
                 for name in bundle.namelist() if '/templates/' in name and name.endswith('.html')}
    test_source = bundle.read('fcha_tantan_windows/community/tests.py').decode('utf-8')
module = types.ModuleType('community.package_tests')
module.__package__ = 'community'
sys.modules[module.__name__] = module
setattr(sys.modules['community'], 'package_tests', module)
exec(compile(test_source, str(archive) + '/community/tests.py', 'exec'), module.__dict__)
configuration = copy.deepcopy(settings.TEMPLATES)
configuration[0]['APP_DIRS'] = False
configuration[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.locmem.Loader', templates),
    'django.template.loaders.app_directories.Loader',
]
with override_settings(TEMPLATES=configuration):
    failures = get_runner(settings)(verbosity=1).run_tests([module.__name__])
print('PACKAGE_TESTS:', archive.name, 'PASS' if not failures else 'FAIL', flush=True)
sys.exit(bool(failures))
