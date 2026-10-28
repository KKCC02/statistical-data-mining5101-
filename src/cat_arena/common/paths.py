"""Repository-relative paths, independent of the process working directory."""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PROJECT_ROOT/'configs/default.json'
CONFIG = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))


def project_path(name):
    path = Path(CONFIG['paths'][name])
    return path if path.is_absolute() else PROJECT_ROOT/path


def module_output(name):
    return project_path('outputs')/name


def write_text(path, content):
    """Stable generated text bytes on Windows and Unix."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content, encoding='utf-8', newline='\n')
