import re

path = r'c:\Project\Smart-Kisan-FInal-main\TerraSpectra-Hyperspectral-Crop-Disease-Forecasting\frontend\src\App.jsx'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

replacements = [
    ("'#f8fafc'", "'var(--text-main)'"),
    ('"#f8fafc"', '"var(--text-main)"'),
    ("'#e2e8f0'", "'var(--text-secondary)'"),
    ('"#e2e8f0"', '"var(--text-secondary)"'),
    ("'#cbd5e1'", "'var(--text-secondary)'"),
    ('"#cbd5e1"', '"var(--text-secondary)"'),
    ("'#94a3b8'", "'var(--text-muted)'"),
    ('"#94a3b8"', '"var(--text-muted)"'),
    ("'#64748b'", "'var(--text-faint)'"),
    ('"#64748b"', '"var(--text-faint)"'),
    ("'#090d16'", "'var(--bg-card-alt)'"),
    ('"#090d16"', '"var(--bg-card-alt)"'),
    ("'#0b1120'", "'var(--bg-sidebar)'"),
    ('"#0b1120"', '"var(--bg-sidebar)"'),
    ("'#0f172a'", "'var(--bg-card)'"),
    ('"#0f172a"', '"var(--bg-card)"'),
    ("'#1e293b'", "'var(--border-color)'"),
    ('"#1e293b"', '"var(--border-color)"'),
    ("'#334155'", "'var(--border-hover)'"),
    ('"#334155"', '"var(--border-hover)"'),
    ('1px solid #1e293b', '1px solid var(--border-color)'),
    ('1px solid #334155', '1px solid var(--border-hover)'),
    ('2px solid #1e293b', '2px solid var(--border-color)'),
    ("borderTop: '1px solid #1e293b'", "borderTop: '1px solid var(--border-color)'"),
    ("borderBottom: '1px solid #1e293b'", "borderBottom: '1px solid var(--border-color)'"),
]

count = 0
for old, new in replacements:
    occurrences = c.count(old)
    if occurrences > 0:
        c = c.replace(old, new)
        count += occurrences

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

print(f'Successfully replaced {count} hardcoded color occurrences in App.jsx!')

