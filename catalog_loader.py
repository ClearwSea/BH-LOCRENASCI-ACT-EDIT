"""Load the minimal v0.2.0 editor catalog from source or a PyInstaller bundle."""
import json
from pathlib import Path
import sys


def catalog_path():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'editor_catalog.json'


def load_catalog():
    """Return a fresh independent catalog, without reading game files or saves."""
    document = json.loads(catalog_path().read_text(encoding='utf-8'))
    if document.get('format_version') != 1 or not isinstance(document.get('catalog'), dict):
        raise ValueError('存档编辑器目录格式不正确')
    return document['catalog']
