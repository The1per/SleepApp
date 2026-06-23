import re

with open('patient_report.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update TRANSLATIONS dict
transl_addition = '''    "Cardiovascular Metrics": "מדדים קרדיווסקולריים",
    "Body Position Statistics": "תנוחות שינה",
    "Average HR": "דופק ממוצע",
    "Min / Max HR": "דופק מינימלי / מקסימלי",
    "HRV (RMSSD)": "שונות דופק (RMSSD)",
}'''
content = content.replace('}', transl_addition, 1) # Only replace the FIRST closing brace (which is the end of TRANSLATIONS)

# 2. Update STAGE_COLORS for N1
content = content.replace('"N1":   "#B39DDB",  # Darker, more visible purple', '"N1":   "#A0AAB5",  # Gray color as requested')
content = content.replace('"N1":   "#B39DDB",', '"N1":   "#A0AAB5",')

# 3. Update Hypnogram Y-Axis colors
hypno_old = '''    yticklabels = [_t("N3", lang), _t("N2", lang), _t("N1", lang), _t("Wake", lang), _t("REM", lang)]
    ax.set_yticklabels(yticklabels, fontsize=7, color=TEXT_M)'''

hypno_new = '''    yticklabels = [_t("N3", lang), _t("N2", lang), _t("N1", lang), _t("Wake", lang), _t("REM", lang)]
    ax.set_yticklabels(yticklabels, fontsize=7)
    
    colors = [STAGE_COLORS["N3"], STAGE_COLORS["N2"], STAGE_COLORS["N1"], STAGE_COLORS["Wake"], STAGE_COLORS["REM"]]
    for tick, color in zip(ax.get_yticklabels(), colors):
        tick.set_color(color)
        tick.set_fontweight("bold")'''

content = content.replace(hypno_old, hypno_new)

with open('patient_report_patched5.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Patched successfully!')
