from pathlib import Path

try:
    import yaml
except ImportError:
    print('PyYAML unavailable; structural checks only')
    text = Path('.github/workflows/dev4_pipeline.yml').read_text(encoding='utf-8')
    assert 'jobs:' in text and 'forge:' in text and 'workflow_dispatch:' in text
else:
    data = yaml.safe_load(Path('.github/workflows/dev4_pipeline.yml').read_text(encoding='utf-8'))
    assert 'jobs' in data and 'forge' in data['jobs']
    assert 'workflow_dispatch' in data.get(True, data.get('on', {})) or 'workflow_dispatch' in data.get('on', {})
print('workflow validation ok')
