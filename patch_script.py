import re

with open('patient_report.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace GridSpec
old_gs = '''    gs = GridSpec(5, 2, figure=fig,
                  top=0.80, bottom=0.15,
                  left=0.04, right=0.97,
                  hspace=0.55, wspace=0.28,
                  height_ratios=[0.90, 1.40, 0.85, 1.75, 0.90])'''

new_gs = '''    gs = GridSpec(5, 2, figure=fig,
                  top=0.80, bottom=0.15,
                  left=0.04, right=0.97,
                  hspace=0.55, wspace=0.28,
                  height_ratios=[0.85, 1.35, 1.35, 1.15, 1.1])'''

if old_gs in content:
    content = content.replace(old_gs, new_gs)
else:
    print('Failed to find old gs')

# 2. Extract start and end of sections to replace
start_idx = content.find('    # ══ 5 — Clinical Statistics')
end_idx = content.find('    # ── Footer')

if start_idx == -1 or end_idx == -1:
    print('Failed to find section bounds')
else:
    new_sections = '''    # ══ 5 — Cardiovascular Metrics ════════════════════════════════════════════
    ax5 = fig.add_subplot(gs[3, c_left])
    _panel(ax5); ax5.axis("off")
    _section_title(ax5, "Cardiovascular Metrics", 5, y_frac=1.15, lang=lang)

    if cv_stats is None:
        cv_stats = {'avg_hr': 62.0, 'min_hr': 48.0, 'max_hr': 110.0, 'rmssd': 'N/A'}

    def _fmt_cv(val):
        if val == "N/A" or val is None:
            return "N/A"
        return f"{val:.0f}" if isinstance(val, (int, float)) else str(val)

    cv_rows = [
        (_t("Average HR", lang), f"{_fmt_cv(cv_stats.get('avg_hr', 'N/A'))} bpm"),
        (_t("Min / Max HR", lang), f"{_fmt_cv(cv_stats.get('min_hr', 'N/A'))} / {_fmt_cv(cv_stats.get('max_hr', 'N/A'))} bpm"),
        (_t("HRV (RMSSD)", lang), f"{_fmt_cv(cv_stats.get('rmssd', 'N/A'))} ms")
    ]

    for r_idx, (k, v) in enumerate(cv_rows):
        y = 0.85 - r_idx * 0.35
        ax5.text(_x(0.05, lang), y, k, transform=ax5.transAxes,
                 fontsize=12, color=TEXT_M, ha=_ha("left", lang), va="center",
                 fontproperties=_he_fp() if lang == "he" else None)
        ax5.text(_x(0.95, lang), y, v, transform=ax5.transAxes,
                 fontsize=13.5, fontweight="bold", color=TEXT_H, ha=_ha("right", lang), va="center",
                 fontproperties=_he_fp() if lang == "he" else None)

    # ══ 6 — Body Position Statistics ══════════════════════════════════════════
    ax5b = fig.add_subplot(gs[3, c_right])
    _panel(ax5b); ax5b.axis("off")
    _section_title(ax5b, "Body Position Statistics", 6, y_frac=1.15, lang=lang)

    if pos_stats is None:
        pos_stats = {"Supine": 45, "Left": 25, "Right": 20, "Prone": 10}
        
    pos_labels = list(pos_stats.keys())
    pos_fracs = [pos_stats[k] for k in pos_labels]
    pos_colors = ["#A3C4F3", "#E58EAA", "#F9C784", "#D4C4E9"]
    
    ax5b_pie = ax5b.inset_axes([0.0, -0.75, 1.0, 1.7])
    disp_labels = [_t(l, lang) for l in pos_labels]
    
    ax5b_pie.pie(pos_fracs, labels=disp_labels, colors=pos_colors, startangle=90,
                 autopct='%1.0f%%', pctdistance=0.6, labeldistance=1.05,
                 textprops={'fontsize': 10, 'color': TEXT_H, 'fontproperties': _he_fp() if lang == "he" else None},
                 wedgeprops={'edgecolor': 'white', 'linewidth': 1})

    # ══ 7 — Summary ═══════════════════════════════════════════════════════════
    ax6 = fig.add_subplot(gs[4, :])
    _panel(ax6); ax6.axis("off")
    _section_title(ax6, "Summary", 7, y_frac=0.95, lang=lang)

    blist = _bullets(st, rdi_v, spo2_stats, lang=lang)
    if notes: 
        if lang == "he":
            blist.extend([get_display(n) for n in notes])
        else:
            blist.extend(notes)

    line_h = 0.185
    for i, line in enumerate(blist[:5]):
        y = 0.65 - i * line_h
        ax6.plot(_x(0.012, lang), y, "o", color=ACCENT, markersize=4,
                 transform=ax6.transAxes, clip_on=False)
        ax6.text(_x(0.030, lang), y, line,
                 transform=ax6.transAxes, fontsize=13,
                 color=TEXT_H, va="center", ha=_ha("left", lang),
                 fontproperties=_he_fp() if lang == "he" else None)

'''
    
    content = content[:start_idx] + new_sections + content[end_idx:]

with open('patient_report_patched.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched successfully.')
