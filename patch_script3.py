import re

with open('patient_report.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update TRANSLATIONS
transl_addition = '''    "Cardiovascular Metrics": "מדדים קרדיווסקולריים",
    "Body Position Statistics": "תנוחות שינה",
    "Average HR": "דופק ממוצע",
    "Min / Max HR": "דופק מינימלי / מקסימלי",
    "HRV (RMSSD)": "שונות דופק (RMSSD)",
'''

if '"Cardiovascular Metrics"' not in content:
    # Insert after 'events / hour'
    content = re.sub(r'("events / hour"[^\n]+)\n', r'\1\n' + transl_addition, content)

# 2. Update y_frac for section 3 and 4
content = content.replace('_section_title(ax3, "Respiratory Disturbance Index (pAHI)", 3, y_frac=1.55, lang=lang)', 
                          '_section_title(ax3, "Respiratory Disturbance Index (pAHI)", 3, y_frac=1.35, lang=lang)')
content = content.replace('_section_title(ax4, "Additional Metrics", 4, y_frac=1.55, lang=lang)',
                          '_section_title(ax4, "Additional Metrics", 4, y_frac=1.35, lang=lang)')

# 3. Update gauge texts
content = content.replace('ax.text(0, -0.40, _t("events / hour", lang)', 'ax.text(0, -0.28, _t("events / hour", lang)')
content = content.replace('ax.text(0, -0.75, _t(sev, lang)', 'ax.text(0, -0.55, _t(sev, lang)')


with open('patient_report_patched4.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Patched successfully!')
