import re

with open('patient_report.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add get_clinical_conclusion function before _generate_single_report
conclusion_func = '''
def get_clinical_conclusion(tst_hours, pahi, t90_pct, avg_sat, min_sat, lang):
    if tst_hours > 0 and tst_hours < 4.0:
        if lang == 'he':
            return 'משך השינה היה קצר, דבר העלול להפחית את מהימנות התוצאות.\\nהערה: נדרשת בדיקת רופא (Send to review by a physician).'
        else:
            return 'The sleep duration was short, which may reduce the reliability of the results.\\nNote: Send to review by a physician.'
    
    if pahi < 5:
        if t90_pct <= 1.0 and min_sat >= 90:
            if lang == 'he':
                return 'בדיקת השינה תקינה.'
            else:
                return 'The sleep study is normal.'
        elif t90_pct > 5.0 or avg_sat < 94 or min_sat < 85:
            if lang == 'he':
                return 'בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה קלה, עם דה-סטורציה לילית שאינה פרופורציונלית.\\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה.'
            else:
                return 'The sleep study indicates mild sleep-disordered breathing, with disproportionate nocturnal desaturation.\\nRecommendations: continue evaluation/treatment within a sleep clinic.'
        else:
            if lang == 'he':
                return 'בדיקת השינה אינה מצביעה על הפרעת נשימה משמעותית בשינה לפי קריטריון AHI. עם זאת, נצפתה ירידה בריווי החמצן בדם בלילה.\\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה.'
            else:
                return 'The sleep study does not indicate significant sleep-disordered breathing according to AHI criteria. However, a drop in blood oxygen saturation was observed at night.\\nRecommendations: continue evaluation/treatment within a sleep clinic.'
                
    if pahi < 15:
        if lang == 'he':
            return 'בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה קלה.\\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה.'
        else:
            return 'The sleep study indicates mild sleep-disordered breathing.\\nRecommendations: continue evaluation/treatment within a sleep clinic.'
            
    if pahi <= 30:
        if lang == 'he':
            return 'בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה בינונית.\\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה.'
        else:
            return 'The sleep study indicates moderate sleep-disordered breathing.\\nRecommendations: continue evaluation/treatment within a sleep clinic.'
            
    if lang == 'he':
        return 'בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה חמורה.\\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה.'
    else:
        return 'The sleep study indicates severe sleep-disordered breathing.\\nRecommendations: continue evaluation/treatment within a sleep clinic.'

'''

if 'def get_clinical_conclusion' not in content:
    content = content.replace('def _generate_single_report(', conclusion_func + 'def _generate_single_report(')

# 2. Patch TRANSLATIONS
if '"Cardiovascular Metrics"' not in content:
    content = content.replace('"No additional data": "אין נתונים נוספים",', '"No additional data": "אין נתונים נוספים",\n    "Cardiovascular Metrics": "מדדים קרדיווסקולריים",\n    "Body Position Statistics": "סטטיסטיקת תנוחת גוף",\n    "Average HR": "דופק ממוצע",\n    "Min / Max HR": "דופק מינימלי / מקסימלי",\n    "HRV (RMSSD)": "שונות דופק (RMSSD)",')

# 3. Patch GridSpec top
old_gs = '''    gs = GridSpec(5, 2, figure=fig,
                  top=0.80, bottom=0.15,
                  left=0.04, right=0.97,
                  hspace=0.55, wspace=0.28,'''
new_gs = '''    gs = GridSpec(5, 2, figure=fig,
                  top=0.865, bottom=0.23,
                  left=0.04, right=0.97,
                  hspace=0.55, wspace=0.28,'''
content = content.replace(old_gs, new_gs)

# 4. Patch _gauge text coords
old_gauge_text_1 = 'ax.text(0, -0.75, _t("events / hour", lang)'
new_gauge_text_1 = 'ax.text(0, -0.40, _t("events / hour", lang)'
content = content.replace(old_gauge_text_1, new_gauge_text_1)

old_gauge_text_2 = 'ax.text(0, -1.10, _t(sev, lang)'
new_gauge_text_2 = 'ax.text(0, -0.75, _t(sev, lang)'
content = content.replace(old_gauge_text_2, new_gauge_text_2)

# 5. Patch Footer section
footer_start_idx = content.find('    # ── Footer')

if footer_start_idx != -1:
    new_footer = '''    # ── Footer ────────────────────────────────────────────────────────────────
    ax_f = fig.add_axes([0.04, 0.08, 0.92, 0.14])
    ax_f.axis("off")
    ax_f.plot([0,1],[0.85,0.85], color=BORDER, lw=0.8, transform=ax_f.transAxes)

    tst_hrs = st.get('TST', 0) / 60.0
    rdi_val = rdi_v if rdi_v is not None else 0
    t90_val = (spo2_stats.get('t_under90', 0) / max(st.get('TST', 1), 1)) * 100.0 if spo2_stats else 0
    avg_sat_val = spo2_stats.get('avg', 100) if spo2_stats else 100
    min_sat_val = spo2_stats.get('min', 100) if spo2_stats else 100
    
    conclusion = get_clinical_conclusion(tst_hrs, rdi_val, t90_val, avg_sat_val, min_sat_val, lang)
    
    import textwrap
    wrapped_lines = []
    for line in conclusion.split('\\n'):
        wrapped_lines.extend(textwrap.wrap(line, width=120 if lang == "en" else 100))
        
    if lang == "he":
        conclusion = '\\n'.join([get_display(ln) for ln in wrapped_lines])
    else:
        conclusion = '\\n'.join(wrapped_lines)

    ax_f.text(0.5, 0.63, conclusion, ha="center", va="center", fontsize=13,
              color=TEXT_H, transform=ax_f.transAxes, fontweight="bold",
              linespacing=1.6, fontproperties=_he_fp(bold=True) if lang == "he" else None)

    disc_str = "This report is for informational purposes only. Please consult your physician for medical interpretation."
    if lang == "he":
        disc_str = "דוח זה נועד למידע בלבד. אנא היוועץ ברופא לפענוח רפואי."
        disc_str = get_display(disc_str)

    ax_f.text(0.5, 0.15, disc_str, ha="center", va="center", fontsize=7.5,
              color=TEXT_M, transform=ax_f.transAxes, linespacing=1.4,
              fontproperties=_he_fp() if lang == "he" else None)
'''
    content = content[:footer_start_idx] + new_footer

with open('patient_report_patched.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched completely!")
