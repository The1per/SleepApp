"""
patient_report.py  —  Patient-friendly one-page sleep summary (clean light theme, EN/HE RTL)
"""
from __future__ import annotations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import NullLocator

try:
    from bidi.algorithm import get_display
except ImportError:
    def get_display(text, base_dir=None):
        return text

def _bidi(text: str) -> str:
    """Apply BiDi visual reordering for LTR renderer (matplotlib/Agg).
    
    matplotlib+Agg renders text strictly left-to-right without BiDi awareness.
    get_display() reorders characters and words so that the visual result
    in an LTR renderer correctly represents RTL (Hebrew) text.
    Apply exactly ONCE per logical string — never twice.
    """
    return get_display(text)

# ── Hebrew font setup ─────────────────────────────────────────────────────────
# matplotlib's default (DejaVu) does not contain Hebrew glyphs.
# Register David.ttf (standard Windows Hebrew font) so Agg can render glyphs.
import matplotlib.font_manager as _fm
from matplotlib.font_manager import FontProperties as _FP
import os as _os

_DAVID_REGULAR = r"C:\Windows\Fonts\david.ttf"
_DAVID_BOLD    = r"C:\Windows\Fonts\davidbd.ttf"

def _register_font(path: str) -> None:
    if _os.path.exists(path):
        _fm.fontManager.addfont(path)

_register_font(_DAVID_REGULAR)
_register_font(_DAVID_BOLD)

# FontProperties objects — pass as `fontproperties=` to ax.text() for Hebrew strings.
HE_FONT      = _FP(fname=_DAVID_REGULAR) if _os.path.exists(_DAVID_REGULAR) else None
HE_FONT_BOLD = _FP(fname=_DAVID_BOLD)    if _os.path.exists(_DAVID_BOLD)    else None

def _he_fp(bold: bool = False):
    """Return appropriate FontProperties for Hebrew text, or None to use default."""
    return HE_FONT_BOLD if bold else HE_FONT


# ── Palette (Soft Purple & Teal Theme) ───────────────────────────────────────
BG        = "#FFFFFF"
PANEL     = "#F8F9FC"
BORDER    = "#E2E5F0"
ACCENT    = "#B48EE5"
TEXT_H    = "#323652"
TEXT_M    = "#656A8A"
TEXT_L    = "#A1A6C2"

C_GOOD    = "#6EC2B5"
C_WARN    = "#B48EE5"
C_BAD     = "#E58EAA"

STAGE_COLORS = {
    "Wake": "#E58EAA",
    "N1":   "#A0AAB5",  # Gray color as requested
    "N2":   "#A3C4F3",
    "N3":   "#7D98C4",
    "REM":  "#B48EE5",
    "Cardiovascular Metrics": "מדדים קרדיווסקולריים",
    "Body Position Statistics": "תנוחות שינה",
    "Average HR": "דופק ממוצע",
    "Min / Max HR": "דופק מינימלי / מקסימלי",
    "HRV (RMSSD)": "שונות דופק (RMSSD)",
}

# ── Localization & RTL Helpers ────────────────────────────────────────────────
TRANSLATIONS = {
    "Overnight Sleep Study Report": "דוח בדיקת שינה לילית",
    "ID:": "ת.ז:",
    "Age:": "גיל:",
    "Male": "זכר",
    "Female": "נקבה",
    "Total Sleep Time:": "זמן שינה כולל:",
    "Sleep Efficiency:": "יעילות שינה:",
    "WASO:": "זמן ערות לאחר תחילת שינה (WASO):",
    "Sleep Architecture": "ארכיטקטורת שינה",
    "Stage Distribution": "התפלגות שלבי שינה",
    "Respiratory Disturbance Index (pAHI)": "מדד הפרעות נשימה (pAHI)",
    "Additional Metrics": "מדדים נוספים",
    "Clinical Statistics": "סטטיסטיקה קלינית",
    "Summary": "סיכום",
    "Sleep Onset": "תחילת שינה",
    "Total Sleep": "זמן שינה כולל",
    "Efficiency": "יעילות",
    "Wake": "Wake",
    "REM": "REM",
    "N1": "N1",
    "N2": "N2",
    "N3": "N3",
    "Normal": "תקין",
    "Mild": "קל",
    "Moderate": "בינוני",
    "Severe": "חמור",
    "Not measured": "לא נמדד",
    "events / hour": "אירועים / שעה",
    "SpO2 Average": "ממוצע SpO2",
    "SpO2 Minimum": "מינימום SpO2",
    "Time < 90%": "זמן < 90%",
    "Limb Movements (PLMI)": "תנועות גפיים (PLMI)",
    "No additional data": "אין נתונים נוספים",
    "Respiratory Indices": "מדדי נשימה",
    "Total Events": "סך הכל",
    "All Night": "כל הלילה",
    "Body Position Statistics": "סטטיסטיקת תנוחות גוף",
    "Supine": "גב",
    "Prone": "בטן",
    "Left": "שמאל",
    "Right": "ימין",
    "Hours": "שעות",
}

def _t(text: str, lang: str) -> str:
    if lang != "he":
        return text
    # Translate and apply BiDi visual reordering ONCE for LTR matplotlib rendering.
    return _bidi(TRANSLATIONS.get(text, text))

def _x(val: float, lang: str) -> float:
    return 1.0 - val if lang == "he" else val

def _ha(align, lang):
    if lang == "he":
        return "right" if align == "left" else ("left" if align == "right" else align)
    return align

# ── Helpers ──────────────────────────────────────────────────────────────────
def _fmt(s: float) -> str:
    return f"{int(s//3600)}h {int((s%3600)//60):02d}m"

def _qcol(v: float) -> str:
    return C_GOOD if v >= 80 else C_WARN if v >= 60 else C_BAD

def _stats(h: np.ndarray) -> dict:
    h = np.asarray(h, dtype=int)
    tib = len(h)
    wake, n1, n2, n3, rem = [(h==i).sum() for i in (0,1,2,3,4)]
    tst = int(n1+n2+n3+rem)
    se  = tst/max(tib,1)*100
    nw  = np.where(h>0)[0]
    sol = int(nw[0]) if len(nw) else tib
    waso = int((h[sol:]==0).sum())
    d = max(tst,1)
    return dict(TIB=tib,TST=tst,SE=se,SOL=sol,WASO=waso,
                N1=n1/d*100,N2=n2/d*100,N3=n3/d*100,REM=rem/d*100,
                Wake=wake/max(tib,1)*100)

def _section_title(ax, title: str, number: int, y_frac=0.96, lang="en"):
    # Draw the bullet dot at the RTL/LTR start margin
    ax.plot(_x(0.0, lang), y_frac, "o", color=ACCENT, markersize=7,
            transform=ax.transAxes, clip_on=False, zorder=6)
    
    if lang == "he":
        # Build logical string: "N. Hebrew title" — one get_display() call handles
        # both char-level and word-level reordering for the LTR matplotlib renderer.
        he_title = TRANSLATIONS.get(title, title)
        display_str = _bidi(f"{number}. {he_title}")
        # Anchor to right side of the panel (RTL reading starts from right)
        ax.text(0.975, y_frac, display_str,
                transform=ax.transAxes, fontsize=13, fontweight="bold",
                color=TEXT_H, va="center", ha="right", zorder=6,
                fontproperties=_he_fp(bold=True))
    else:
        full_title = f"{number}.  {title}"
        ax.text(0.025, y_frac, full_title,
                transform=ax.transAxes, fontsize=13, fontweight="bold",
                color=TEXT_H, va="center", ha="left", zorder=6)
    
    # Underline
    ax.plot([0, 1], [y_frac - 0.06, y_frac - 0.06],
            color=BORDER, lw=0.8, transform=ax.transAxes, clip_on=False)


def _panel(ax):
    ax.set_facecolor(PANEL)
    for sp in ax.spines.values():
        sp.set_color(BORDER); sp.set_linewidth(0.8)

def _pill(ax, x, y, w, h, color, alpha=0.15):
    # FancyBboxPatch takes bottom-left corner
    # If RTL, the x we pass should be the bottom-left of the mirrored box
    # So if original is x, mirrored x is (1.0 - x) - w
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0,rounding_size=0.015",
                                facecolor=color, edgecolor="none", alpha=alpha,
                                transform=ax.transAxes, clip_on=False, zorder=2))


# ── Hypnogram ─────────────────────────────────────────────────────────────────
def _hypno(ax, h: np.ndarray, lang="en"):
    h = np.asarray(h, dtype=int)
    ym = {0:4, 1:3, 2:2, 3:1, 4:5, -1:0}
    cm = {0:STAGE_COLORS["Wake"], 1:STAGE_COLORS["N1"],
          2:STAGE_COLORS["N2"],   3:STAGE_COLORS["N3"],
          4:STAGE_COLORS["REM"],  -1:"#CBD5E1"}
    xs = np.arange(len(h))/3600
    i = 0
    while i < len(h):
        s=h[i]; j=i+1
        while j<len(h) and h[j]==s: j+=1
        ax.fill_between(xs[i:j], 0, np.full(j-i, ym.get(int(s),0)),
                        color=cm.get(int(s),"#CBD5E1"), alpha=0.9, lw=0)
        i = j
        
    # Draw a continuous step line on top to connect the stages ("не рваная")
    y_vals = np.array([ym.get(int(s), 0) for s in h])
    ax.step(xs, y_vals, where="post", color=TEXT_H, linewidth=1.2, alpha=0.8)
    
    mh = xs[-1] if len(xs) else 1
    
    ax.set_ylim(0, 6)
    ax.set_yticks([1,2,3,4,5])
    yticklabels = [_t("N3", lang), _t("N2", lang), _t("N1", lang), _t("Wake", lang), _t("REM", lang)]
    ax.set_yticklabels(yticklabels, fontsize=7)
    
    colors = [STAGE_COLORS["N3"], STAGE_COLORS["N2"], STAGE_COLORS["N1"], STAGE_COLORS["Wake"], STAGE_COLORS["REM"]]
    for tick, color in zip(ax.get_yticklabels(), colors):
        tick.set_color(color)
        tick.set_fontweight("bold")
    ax.tick_params(axis="x", labelsize=7, colors=TEXT_M, length=2)
    ax.set_xlabel(_t("Hours", lang), fontsize=7, color=TEXT_L)
    ax.set_facecolor(PANEL)
    
    if lang == "he":
        ax.set_xlim(mh, -1.2) # Flip X-axis!
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
        ax.spines["left"].set_visible(False)
        ax.spines["right"].set_color(BORDER)
        ax.spines["right"].set_position(("data", 0))
    else:
        ax.set_xlim(-1.2, mh)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(BORDER)
        ax.spines["left"].set_position(("data", 0))
        
    ax.spines["top"].set_visible(False)
    ax.spines["bottom"].set_bounds(0, mh)
    ax.spines["bottom"].set_color(BORDER)
    ax.grid(axis="x", color=BORDER, lw=0.5, linestyle=":")
    ax.tick_params(colors=TEXT_M)


# ── Donut ─────────────────────────────────────────────────────────────────────
def _donut(ax, s: dict, lang="en"):
    lbls   = ["N1","N2","N3","REM","Wake"]
    vals   = [s["N1"],s["N2"],s["N3"],s["REM"],s["Wake"]]
    colors = [STAGE_COLORS[l] for l in lbls]
    _, _, auts = ax.pie(
        vals, colors=colors,
        autopct=lambda p: f"{p:.0f}%" if p > 5 else "",
        wedgeprops=dict(width=0.50, edgecolor="white", linewidth=1.8),
        startangle=90, pctdistance=0.75,
    )
    for at in auts:
        at.set_color("white"); at.set_fontsize(11); at.set_fontweight("bold")
    ax.set_facecolor(PANEL)


# ── Gauge ─────────────────────────────────────────────────────────────────────
def _gauge(ax, val: float, lang="en", vmin=0, vmax=30):
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-1.15, 1.15)
    
    y_scale = 1.0
    ax.set_ylim(-0.95, 1.15)
    ax.axis("off")

    palette = ["#6EC2B5", "#97A8E5", "#B48EE5", "#E58EAA"]
    cmap = LinearSegmentedColormap.from_list("purples", palette)

    n = 180
    outer_r, inner_r = 1.0, 0.65
    
    # If RTL, swap Left and Right visually for the gauge colors?
    # The gauge goes from Normal (Left) to Severe (Right).
    # RTL users read Right to Left. Should Normal be on the Right?
    # Usually gauges remain L->R (like speedometers). We will keep it L->R.
    th = np.linspace(np.pi, 0, n)
    for i in range(n-1):
        t0, t1 = th[i], th[i+1]
        xs = [inner_r * np.cos(t0), outer_r * np.cos(t0), outer_r * np.cos(t1), inner_r * np.cos(t1)]
        ys = [y_scale * inner_r * np.sin(t0), y_scale * outer_r * np.sin(t0), 
              y_scale * outer_r * np.sin(t1), y_scale * inner_r * np.sin(t1)]
        ax.fill(xs, ys, color=cmap(i / n), edgecolor="none", zorder=2, alpha=0.9)

    ax.plot([-1.1, 1.1], [0, 0], color=BORDER, lw=1.5, zorder=1)
    ax.text(-1.0, -0.05, f"{vmin}\n{_t('Normal', lang)}", ha="center", va="top", fontsize=10.5, fontweight="bold", color=palette[0], zorder=3, fontproperties=_he_fp(bold=True) if lang == "he" else None)
    ax.text(1.0, -0.05, f"{vmax}\n{_t('Severe', lang)}", ha="center", va="top", fontsize=10.5, fontweight="bold", color=palette[3], zorder=3, fontproperties=_he_fp(bold=True) if lang == "he" else None)

    for tv in np.linspace(vmin, vmax, 7):
        frac = (tv - vmin) / max(vmax - vmin, 1)
        ang_rad = np.pi * (1 - frac)
        ax.plot([inner_r * np.cos(ang_rad), (inner_r+0.05) * np.cos(ang_rad)],
                [y_scale * inner_r * np.sin(ang_rad), y_scale * (inner_r+0.05) * np.sin(ang_rad)],
                color="white", lw=1.5, zorder=4)

    frac_v = np.clip((val - vmin) / max(vmax - vmin, 1), 0, 1)
    ang_rad = np.pi * (1 - frac_v)
    tip_r = inner_r - 0.06
    nx, ny = tip_r * np.cos(ang_rad), y_scale * tip_r * np.sin(ang_rad)
    
    ax.annotate("", xy=(nx, ny), xytext=(0, 0),
                arrowprops=dict(arrowstyle="-|>", color=TEXT_H, lw=2.5, mutation_scale=16),
                zorder=6)
    ax.plot(0, 0, "o", color=TEXT_H, markersize=8, zorder=7)

    ax.text(0, -0.10, f"{val:.1f}", ha="center", va="top", fontsize=20, fontweight="bold", color=TEXT_H, zorder=8, fontproperties=_he_fp(bold=True) if lang == "he" else None)
    ax.text(0, -0.40, _t("events / hour", lang), ha="center", va="center", fontsize=11, fontweight="bold", color=TEXT_L, zorder=8, fontproperties=_he_fp(bold=True) if lang == "he" else None)
    
    sev = ("Normal" if val < 5 else "Mild" if val < 15 else "Moderate" if val < 30 else "Severe")
    sev_col = {"Normal": palette[0], "Mild": palette[1], "Moderate": palette[2], "Severe": palette[3]}.get(sev, TEXT_M)
    ax.text(0, -0.70, _t(sev, lang), ha="center", va="center", fontsize=13, fontweight="bold", color=sev_col, zorder=8, fontproperties=_he_fp(bold=True) if lang == "he" else None)


# ── Auto bullets ──────────────────────────────────────────────────────────────
def _bullets(s, rdi, spo2, lang="en") -> list[str]:
    # We will translate the whole bullets, or just return basic English if not Hebrew
    b = []
    se = s["SE"]
    if lang == "he":
        if se >= 85:   b.append(f"יעילות שינה טובה ({se:.0f}%) — בטווח התקין.")
        elif se >= 70: b.append(f"יעילות שינה מופחתת במידה מתונה ({se:.0f}%).")
        else:          b.append(f"יעילות שינה נמוכה ({se:.0f}%) — ערנות משמעותית במהלך הלילה.")
        
        n3, rem = s["N3"], s["REM"]
        if n3 >= 15 and rem >= 18:
            b.append("ארכיטקטורת שינה שמורה היטב עם שנת חלום (REM) ושינה עמוקה (N3) מספקת.")
        elif n3 < 10:
            b.append(f"שינה עמוקה (N3) מופחתת ({n3:.0f}%) — ייתכן שהשינה הייתה קלה מהרגיל.")
        elif rem < 15:
            b.append(f"שנת חלום (REM) נמוכה ({rem:.0f}%) — עשוי להשפיע על התאוששות.")
            
        if rdi is not None:
            if rdi < 5:     b.append(f"לא זוהו הפרעות נשימה משמעותיות (pAHI {rdi:.1f}/hr).")
            elif rdi < 15:  b.append(f"נצפו הפרעות נשימה קלות (pAHI {rdi:.1f}/hr) — מומלץ מעקב.")
            else:           b.append(f"הפרעות נשימה משמעותיות (pAHI {rdi:.1f}/hr) — מומלץ ייעוץ רופא.")
            
        if spo2:
            avg = spo2.get("avg", 0); t90 = spo2.get("t_under90", 0)
            if avg >= 95:   b.append(f"ריווי חמצן בדם תקין (ממוצע SpO2 {avg:.1f}%).")
            else:           b.append(f"ממוצע SpO2 {avg:.1f}% עם {t90:.0f} דקות מתחת ל-90% — מומלץ בירור רפואי.")
            
        wm = s["WASO"]/60
        if wm < 20:     b.append("יקיצות מינימליות במהלך הלילה — רצף שינה טוב.")
        elif wm < 45:   b.append(f"ערנות לילית מתונה ({wm:.0f} דקות לאחר תחילת שינה).")
        else:           b.append(f"יקיצות מרובות ({wm:.0f} דקות WASO) — זוהה קיטוע שינה.")
        return [_bidi(line) for line in b[:5]]

    # English default
    if se >= 85:   b.append(f"Sleep efficiency is good ({se:.0f}%) — within the normal range.")
    elif se >= 70: b.append(f"Sleep efficiency is moderately reduced ({se:.0f}%).")
    else:          b.append(f"Sleep efficiency is low ({se:.0f}%) — significant nighttime wakefulness.")
    n3, rem = s["N3"], s["REM"]
    if n3 >= 15 and rem >= 18:
        b.append("Sleep architecture is well-preserved with adequate deep (N3) and REM sleep.")
    elif n3 < 10:
        b.append(f"Deep sleep (N3) is reduced ({n3:.0f}%) — sleep may be lighter than normal.")
    elif rem < 15:
        b.append(f"REM sleep is low ({rem:.0f}%) — may affect memory consolidation and recovery.")
    if rdi is not None:
        if rdi < 5:     b.append(f"No significant respiratory disturbances detected (pAHI {rdi:.1f}/hr).")
        elif rdi < 15:  b.append(f"Mild respiratory disturbances noted (pAHI {rdi:.1f}/hr) — monitoring advised.")
        else:           b.append(f"Significant respiratory disturbances (pAHI {rdi:.1f}/hr) — follow-up recommended.")
    if spo2:
        avg = spo2.get("avg", 0); t90 = spo2.get("t_under90", 0)
        if avg >= 95:   b.append(f"Blood oxygen saturation is normal (mean SpO2 {avg:.1f}%).")
        else:           b.append(f"Mean SpO2 {avg:.1f}% with {t90:.0f} min below 90% — oxygenation review advised.")
    wm = s["WASO"]/60
    if wm < 20:     b.append("Minimal nighttime awakenings — good sleep continuity.")
    elif wm < 45:   b.append(f"Moderate nighttime wakefulness ({wm:.0f} min after sleep onset).")
    else:           b.append(f"Frequent awakenings ({wm:.0f} min WASO) — sleep fragmentation detected.")
    return b[:5]


# ── Internal Single Generator ─────────────────────────────────────────────────

def get_clinical_conclusion(tst_hours, pahi, t90_pct, avg_sat, min_sat, lang):
    if tst_hours > 0 and tst_hours < 4.0:
        if lang == 'he':
            return 'משך השינה היה קצר, דבר העלול להפחית את מהימנות התוצאות.\nהערה: נדרשת בדיקת רופא (Send to review by a physician).'
        else:
            return 'The sleep duration was short, which may reduce the reliability of the results.\nNote: Send to review by a physician.'
    
    if pahi < 5:
        if t90_pct <= 1.0 and min_sat >= 90:
            if lang == 'he':
                return 'בדיקת השינה תקינה.'
            else:
                return 'The sleep study is normal.'
        elif t90_pct > 5.0 or avg_sat < 94 or min_sat < 85:
            if lang == 'he':
                return 'בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה קלה, עם דה-סטורציה לילית שאינה פרופורציונלית.\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה.'
            else:
                return 'The sleep study indicates mild sleep-disordered breathing, with disproportionate nocturnal desaturation.\nRecommendations: continue evaluation/treatment within a sleep clinic.'
        else:
            if lang == 'he':
                return 'בדיקת השינה אינה מצביעה על הפרעת נשימה משמעותית בשינה לפי קריטריון AHI. עם זאת, נצפתה ירידה בריווי החמצן בדם בלילה.\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה.'
            else:
                return 'The sleep study does not indicate significant sleep-disordered breathing according to AHI criteria. However, a drop in blood oxygen saturation was observed at night.\nRecommendations: continue evaluation/treatment within a sleep clinic.'
                
    if pahi < 15:
        if lang == 'he':
            return 'בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה קלה.\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה.'
        else:
            return 'The sleep study indicates mild sleep-disordered breathing.\nRecommendations: continue evaluation/treatment within a sleep clinic.'
            
    if pahi <= 30:
        if lang == 'he':
            return 'בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה בינונית.\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה.'
        else:
            return 'The sleep study indicates moderate sleep-disordered breathing.\nRecommendations: continue evaluation/treatment within a sleep clinic.'
            
    if lang == 'he':
        return 'בדיקת השינה מצביעה על הפרעת נשימה בשינה בדרגה חמורה.\nהמלצות: המשך הערכה/טיפול במסגרת מרפאת שינה.'
    else:
        return 'The sleep study indicates severe sleep-disordered breathing.\nRecommendations: continue evaluation/treatment within a sleep clinic.'

def _generate_single_report(
    *,
    hypno_1hz_int: np.ndarray,
    subject_id: str,
    outdir: Path,
    subject_name: str | None = None,
    study_date: str | None = None,
    subject_age: int | None = None,
    sex: str | None = None,
    spo2_stats: dict | None = None,
    plm_metrics: dict | None = None,
    rdi: float | None = None,
    ahi: float | None = None,
    resp_stats: dict | None = None,
    pos_stats: dict | None = None,
    cv_stats: dict | None = None,
    notes: list[str] | None = None,
    dpi: int = 180,
    lang: str = "en",
    **kwargs
) -> Path:
    rdi_v  = rdi if rdi is not None else ahi
    st     = _stats(hypno_1hz_int)

    # ── Page ──────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(8.5, 11), facecolor=BG)
    
    # --- Add Logo ---
    try:
        import os, sys
        from PIL import Image
        def _resource_path(relative_path):
            try: base_path = sys._MEIPASS
            except Exception: base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)
            
        logo_up_path = _resource_path("logo_up.png")
        if os.path.exists(logo_up_path):
            logo_up_img = Image.open(logo_up_path)
            # Position at top center
            ax_logo_up = fig.add_axes([0.4, 0.92, 0.2, 0.07], anchor='N', zorder=10)
            ax_logo_up.imshow(logo_up_img)
            ax_logo_up.axis('off')
            
        logo_down_path = _resource_path("logo_down.png")
        if os.path.exists(logo_down_path):
            logo_down_img = Image.open(logo_down_path)
            # Position at bottom full width
            ax_logo_down = fig.add_axes([0.05, 0.01, 0.9, 0.08], anchor='S', zorder=10)
            ax_logo_down.imshow(logo_down_img)
            ax_logo_down.axis('off')
    except Exception as e:
        print(f"Logo error: {e}")

    fig.patch.set_facecolor(BG)

    # ── Title ─────────────────────────────────────────────────────────────────
    ax_title = fig.add_axes([0.0, 0.88, 1.0, 0.04])
    ax_title.axis("off")
    if lang == "he":
        # Build full logical Hebrew title string (with date), then _bidi() processes it ONCE.
        # BiDi algorithm correctly handles Hebrew+Latin mix (date stays LTR, Hebrew is RTL).
        he_title = TRANSLATIONS.get("Overnight Sleep Study Report", "")
        logical = f"{he_title} - {study_date}" if study_date else he_title
        t_text = _bidi(logical)
    else:
        he_title = "Overnight Sleep Study Report"
        t_text = f"{he_title} - {study_date}" if study_date else he_title
    ax_title.text(0.5, 0.5, t_text,
                  transform=ax_title.transAxes,
                  fontsize=24, fontweight="bold", color=TEXT_H, va="center", ha="center",
                  fontproperties=_he_fp(bold=True) if lang == "he" else None)
    ax_title.plot([0, 1], [0.05, 0.05], color=ACCENT, lw=2.5,
                  transform=ax_title.transAxes)

    # ── Demographics ──────────────────────────────────────────────────────────
    ax_dem = fig.add_axes([0.0, 0.85, 1.0, 0.028])
    ax_dem.axis("off")
    parts = []
    sid = str(subject_id).split("_")[0]
    if lang == "he":
        # Build each demographic token as logical Hebrew (label: value).
        # _bidi() will handle the full joined line in one pass.
        if sid: parts.append(f"ת.ז: {sid}")
        if subject_age: parts.append(f"גיל: {subject_age}")
        if sex:
            parts.append("זכר" if str(sex).upper() in ("M", "MALE") else "נקבה")
        parts += [
            f"זמן שינה כולל: {_fmt(st['TST'])}",
            f"יעילות: {st['SE']:.0f}%",
            f"WASO: {_fmt(st['WASO'])}",
        ]
        dem_line = " • ".join(parts)
        dem_display = _bidi(dem_line)
    else:
        if sid: parts.append(f"ID: {sid}")
        if subject_age: parts.append(f"Age: {subject_age}")
        if sex:
            parts.append("Male" if str(sex).upper() in ("M", "MALE") else "Female")
        parts += [
            f"Total Sleep: {_fmt(st['TST'])}",
            f"Efficiency: {st['SE']:.0f}%",
            f"WASO: {_fmt(st['WASO'])}",
        ]
        dem_display = " • ".join(parts)

    ax_dem.text(0.5, 0.5, dem_display,
                transform=ax_dem.transAxes, fontsize=10.5,
                color=TEXT_M, va="center", ha="center",
                fontproperties=_he_fp() if lang == "he" else None)



    ax_sep = fig.add_axes([0.0, 0.920, 1.0, 0.003])
    ax_sep.axis("off")
    ax_sep.plot([0,1],[0.5,0.5], color=BORDER, lw=1.0, transform=ax_sep.transAxes)

    # ── Grid ──────────────────────────────────────────────────────────────────
    # Reserve space for top and bottom logos
    gs = GridSpec(5, 2, figure=fig,
                  top=0.845, bottom=0.19,
                  left=0.04, right=0.97,
                  hspace=0.55, wspace=0.28,
                  height_ratios=[0.85, 1.35, 1.35, 1.15, 1.1])

    # Col swap for RTL
    c_left = 1 if lang == "he" else 0
    c_right = 0 if lang == "he" else 1

    # ══ 1 — Sleep Architecture ════════════════════════════════════════════════
    ax1 = fig.add_subplot(gs[0:2, c_left])
    _panel(ax1); ax1.axis("off")
    _section_title(ax1, "Sleep Architecture", 1, y_frac=0.965, lang=lang)

    axi = ax1.inset_axes([0.04, 0.15, 0.92, 0.75])
    _hypno(axi, hypno_1hz_int, lang=lang)

