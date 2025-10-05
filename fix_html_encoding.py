from pathlib import Path
path = Path('app/html_report.py')
text = path.read_text(encoding='utf-8', errors='ignore')
path.write_text(text, encoding='utf-8')
