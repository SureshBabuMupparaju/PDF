from pathlib import Path
path = Path('app/html_report.py')
text = path.read_text(encoding='latin-1')
text = text.lstrip('\ufeff\uf0bb\uf0bf\uf0ff')
if text.startswith('ï»¿'):
    text = text[3:]
path.write_text(text, encoding='utf-8')
