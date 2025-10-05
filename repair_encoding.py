from pathlib import Path
for file in ['app/html_report.py', 'app/streamlit_app.py']:
    path = Path(file)
    raw = path.read_text(encoding='latin-1')
    fixed = raw.encode('latin-1').decode('utf-8', errors='ignore')
    if fixed.startswith('\ufeff'):
        fixed = fixed[1:]
    path.write_text(fixed, encoding='utf-8')
