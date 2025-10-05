from pathlib import Path
path = Path('app/streamlit_app.py')
text = path.read_text()
old = '                            "Description": row.description,\n                            "Preview Ref": row.preview_ref,'
new = '                            "Description": row.description,\n                            "Category": row.category or "",\n                            "Preview Ref": row.preview_ref,'
if old not in text:
    raise SystemExit('detail dataframe block not found')
path.write_text(text.replace(old, new), encoding='utf-8')
