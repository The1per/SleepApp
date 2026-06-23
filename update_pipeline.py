import re
import ast

def run():
    with open('pipeline.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Create the translations mapping to be inserted before _create_docx_detailed
    translations = '''
DOCX_TRANSLATIONS = {
    'Sleep Study Report - Detailed Analysis': 'דוח מחקר שינה - ניתוח מפורט',
    'Patient Information': 'מידע על המטופל',
    'Subject ID:': 'תעודת זהות:',
    'Age:': 'גיל:',
    'years': 'שנים',
    'Sex:': 'מין:',
    'Male': 'זכר',
    'Female': 'נקבה',
    'Recording Duration:': 'משך ההקלטה:',
    'Parameter': 'פרמטר',
    'Result': 'תוצאה',
    'Value': 'ערך',
    'Normal Range': 'טווח תקין',
    'Sleep Architecture': 'ארכיטקטורת שינה',
    'Total Sleep Time (min)': 'זמן שינה כולל (דקות)',
    'Sleep Latency (min)': 'חביון שינה (דקות)',
    'Sleep Efficiency': 'יעילות שינה',
    'WASO (min)': 'זמן ערות לאחר תחילת שינה (דקות)',
    'Sleep Stages Distribution': 'פיזור שלבי השינה',
    'Sleep Stage': 'שלב שינה',
    'Percentage': 'אחוזים',
    'Wake': 'ערות',
    'N1 (Light Sleep)': 'N1 (שינה קלה)',
    'N2 (Light Sleep)': 'N2 (שינה קלה)',
    'N3 (Deep/SWS)': 'N3 (שינה עמוקה)',
    'REM Sleep': 'שנת חלום (REM)',
    'Hypnogram': 'היפנוגרמה',
    'Visual representation of sleep stages throughout the recording:': 'ייצוג חזותי של שלבי השינה לאורך ההקלטה:',
    'Respiratory & Oxygenation Analysis': 'ניתוח נשימה וחמצון',
    'Oxygen Saturation (SpO2)': 'ריווי חמצן בדם (SpO2)',
    'Average SpO2': 'ממוצע SpO2',
    'Minimum SpO2': 'מינימום SpO2',
    'Time Below 90% (min)': 'זמן מתחת ל-90% (דקות)',
    'Limb Movements Analysis (AASM Criteria)': 'ניתוח תנועות גפיים (קריטריוני AASM)',
    'Total Limb Movements': 'סה"כ תנועות גפיים',
    'Limb Movement Index (LMSI)': 'אינדקס תנועות גפיים (LMSI)',
    'Periodic Limb Movements (PLM)': 'תנועות גפיים מחזוריות (PLM)',
    'PLM Index (PLMI)': 'אינדקס PLM (PLMI)',
    'WatchPAT Graphs': 'גרפים של WatchPAT',
    'WatchPAT Clinical Summary': 'סיכום קליני של WatchPAT',
    'pAHI (events/hr)': 'pAHI (אירועים/שעה)',
    'ODI 4% (events/hr)': 'ODI 4% (אירועים/שעה)',
    'Mean SpO2': 'ממוצע SpO2',
    'Time below SpO2 90%': 'זמן מתחת ל-SpO2 90%',
    'Snoring mean intensity': 'עוצמת נחירות ממוצעת',
    'Clinical Notes': 'הערות קליניות',
    'Sleep Stage Definitions:': 'הגדרות שלבי השינה:',
    '• N1: Transition from wakefulness to sleep (light sleep)': '• N1: מעבר מעירות לשינה (שינה קלה)',
    '• N2: Consolidated light sleep with sleep spindles and K-complexes': '• N2: שינה קלה מבוססת עם כישורי שינה ומכלולי K',
    '• N3 (SWS): Deep slow-wave sleep, restorative sleep stage': '• N3 (SWS): שנת גלים איטיים עמוקה, שלב שינה משקם',
    '• REM: Rapid Eye Movement sleep, associated with dreaming': '• REM: שנת תנועות עיניים מהירות, קשורה לחלימה',
    'Note: ': 'הערה: ',
    'Results marked with ▲/▼ deviate more than 2 Standard Deviations from age- and sex-matched normative data.': 'תוצאות המסומנות עם ▲/▼ חורגות ביותר משתי סטיות תקן מנתונים נורמטיביים תואמי גיל ומין.',
    'Page ': 'עמוד ',
}
'''

    # Modify the signature of _create_docx_detailed
    content = content.replace(
        '    motor_events_png_path: Path | None = None,\n) -> Path:',
        '    motor_events_png_path: Path | None = None,\n    lang: str = "en",\n) -> Path:'
    )

    # Insert translations before _create_docx_detailed
    content = content.replace('def _create_docx_detailed(', translations + '\n\ndef _create_docx_detailed(')

    replacement_body = """
    subject_id = str(subject_id).split('_')[0]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    def _t(text):
        if lang == "he":
            return DOCX_TRANSLATIONS.get(text, text)
        return text

    normal_ranges = get_result_ranges(subject_age, sex)
    hypno_stats = hypno_report_stats(hypno_1hz_int)

    avg_spo2 = None
    minimal_spo2 = None
    time_under_90 = None
    if spo2_edf_path:
        try:
            avg_spo2, minimal_spo2, time_under_90, _ = analyse_spo2(
                spo2_edf_path, spo2_channel=spo2_channel, pleth_channel=pleth_channel
            )
        except Exception:
            avg_spo2, minimal_spo2, time_under_90 = None, None, None

    watchpat_data = None
    watchpat_summary_text = None
    if watchpat_pdf_path and Path(watchpat_pdf_path).exists():
        try:
            watchpat_data = parse_watchpat_pdf(watchpat_pdf_path)
            watchpat_summary_text = generate_watchpat_summary(watchpat_data)
        except Exception:
            pass

    time_examination = _seconds_to_hms_str(hypno_stats["TIB"])
    tst_min  = hypno_stats["SPT"]  / 60.0
    lat_min  = hypno_stats["LAT"]  / 60.0
    waso_min = hypno_stats["WASO"] / 60.0
    time_sleep_str = f"{tst_min:.1f}"
    lat_str        = f"{lat_min:.1f}"
    waso_str       = f"{waso_min:.1f}"
    b90_str = f"{time_under_90 / 60.0:.1f}" if time_under_90 is not None else "N/A"

    document = Document()
    style = document.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)
    
    # RTL Helper
    def set_rtl(run=None, para=None, table=None):
        if lang != "he": return
        if run:
            run.font.rtl = True
        if para:
            para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if table:
            tblPr = table._element.xpath('w:tblPr')
            if tblPr:
                bidi = OxmlElement('w:bidiVisual')
                tblPr[0].append(bidi)

    def add_p(text='', bold=False, level=None):
        if level is not None:
            p = document.add_heading(_t(text), level=level)
        else:
            p = document.add_paragraph(_t(text))
        set_rtl(para=p)
        if p.runs:
            for r in p.runs:
                if bold: r.bold = True
                set_rtl(run=r)
        return p

    def add_r(para, text, bold=False):
        r = para.add_run(_t(text))
        if bold: r.bold = True
        set_rtl(run=r)
        return r

    # --- HEADER ---
    section = document.sections[0]
    header_para = section.header.paragraphs[0]
    header_para.text = "|Sagol School of Neuroscience|Sleep Study Report|"
    header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in header_para.runs:
        run.font.name = 'Calibri'
        run.font.color.rgb = RGBColor(128, 128, 128)
        run.font.size = Pt(9)

    # --- FOOTER ---
    footer_para = section.footer.paragraphs[0]
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer_para.add_run(_t("Page "))
    footer_run.font.name = 'Calibri'
    footer_run.font.color.rgb = RGBColor(128, 128, 128)
    footer_run.font.size = Pt(9)
    fldChar1 = OxmlElement('w:fldChar');  fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText'); instrText.set(qn('xml:space'), 'preserve'); instrText.text = "PAGE"
    fldChar2 = OxmlElement('w:fldChar');  fldChar2.set(qn('w:fldCharType'), 'end')
    footer_run._r.append(fldChar1); footer_run._r.append(instrText); footer_run._r.append(fldChar2)

    # --- TITLE ---
    title = add_p('Sleep Study Report - Detailed Analysis', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.runs[0].font.name = 'Calibri'
    title.runs[0].font.color.rgb = RGBColor(29, 53, 87)

    # --- PATIENT INFO ---
    add_p('Patient Information', level=1)
    info_table = document.add_table(rows=3, cols=2)
    set_rtl(table=info_table)
    
    sex_str = 'Male' if str(sex).upper().startswith('M') else 'Female'
    
    info_table.rows[0].cells[0].text = _t('Subject ID:')
    info_table.rows[0].cells[1].text = subject_id
    info_table.rows[1].cells[0].text = _t('Age:')
    info_table.rows[1].cells[1].text = f"{subject_age} {_t('years')}"
    info_table.rows[2].cells[0].text = _t('Sex:')
    info_table.rows[2].cells[1].text = _t(sex_str)
    
    for row in info_table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                set_rtl(para=p)
                for r in p.runs: set_rtl(run=r)
        row.cells[0].paragraphs[0].runs[0].font.bold = True

    add_p()
    dp = add_p()
    add_r(dp, 'Recording Duration: ', bold=True)
    add_r(dp, time_examination)

    def style_table_header(table):
        for cell in table.rows[0].cells:
            shd = OxmlElement('w:shd')
            shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), '1D3557')
            cell._tc.get_or_add_tcPr().append(shd)
            for para in cell.paragraphs:
                set_rtl(para=para)
                for run in para.runs:
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(255, 255, 255)
                    set_rtl(run=run)

    def add_row_no_ref(row_idx: int, param: str, result: str, normal: str, table):
        cells = table.rows[row_idx].cells
        cells[0].text = _t(param)
        indicator = ""
        if _check_if_abnormal(result, normal):
            vm = re.search(r"[-+]?\d*\.\d+|\d+", str(result))
            nm = re.search(r"([-+]?\d*\.\d+|\d+)\s*±", str(normal))
            if vm and nm:
                indicator = " ▲" if float(vm.group()) > float(nm.group(1)) else " ▼"
        
        cells[1].text = ""
        p = cells[1].paragraphs[0]
        run = p.add_run(f"{result}{indicator}")
        if indicator:
            run.font.color.rgb = RGBColor(230, 57, 70)
            run.font.bold = True
            
        for cell in cells:
            for para in cell.paragraphs:
                set_rtl(para=para)
                for r in para.runs: set_rtl(run=r)

    # 1: SLEEP ARCHITECTURE
    add_p('Sleep Architecture', level=1)
    t = document.add_table(rows=5, cols=2)
    set_rtl(table=t)
    t.style = 'Light Grid Accent 1'
    t.rows[0].cells[0].text = _t('Parameter'); t.rows[0].cells[1].text = _t('Result')
    style_table_header(t)
    add_row_no_ref(1, 'Total Sleep Time (min)', time_sleep_str, normal_ranges['TST'], t)
    add_row_no_ref(2, 'Sleep Latency (min)',    lat_str,        normal_ranges['LAT'], t)
    add_row_no_ref(3, 'Sleep Efficiency',       f"{hypno_stats['SE']:.1f}%", normal_ranges['SE'],  t)
    add_row_no_ref(4, 'WASO (min)',             waso_str,       normal_ranges['WASO'], t)

    add_p()
    add_p('Sleep Stages Distribution', level=1)
    st = document.add_table(rows=6, cols=2)
    set_rtl(table=st)
    st.style = 'Light Grid Accent 1'
    st.rows[0].cells[0].text = _t('Sleep Stage'); st.rows[0].cells[1].text = _t('Percentage')
    style_table_header(st)
    add_row_no_ref(1, 'Wake',             f"{hypno_stats['Wake']:.1f}%", 'N/A',                st)
    add_row_no_ref(2, 'N1 (Light Sleep)', f"{hypno_stats['N1']:.1f}%",   normal_ranges['N1'],  st)
    add_row_no_ref(3, 'N2 (Light Sleep)', f"{hypno_stats['N2']:.1f}%",   normal_ranges['N2'],  st)
    add_row_no_ref(4, 'N3 (Deep/SWS)',   f"{hypno_stats['N3']:.1f}%",   normal_ranges['N3'],  st)
    add_row_no_ref(5, 'REM Sleep',        f"{hypno_stats['REM']:.1f}%",  normal_ranges['REM'], st)

    add_p()
    add_p('Hypnogram', level=1)
    add_p('Visual representation of sleep stages throughout the recording:')
    if Path(hypno_png_path).exists():
        document.add_picture(str(hypno_png_path), width=Inches(6.5))
        document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    add_p()
    if Path(pie_png_path).exists():
        document.add_picture(str(pie_png_path), width=Inches(5.0))
        document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 2: RESPIRATORY
    add_p()
    add_p('Respiratory & Oxygenation Analysis', level=1)
    if avg_spo2 is not None:
        add_p('Oxygen Saturation (SpO2)', level=2)
        spo2t = document.add_table(rows=4, cols=2)
        set_rtl(table=spo2t)
        spo2t.style = 'Light Grid Accent 1'
        spo2t.rows[0].cells[0].text = _t('Parameter'); spo2t.rows[0].cells[1].text = _t('Result')
        style_table_header(spo2t)
        add_row_no_ref(1, 'Average SpO2',        f"{avg_spo2:.2f}%",        normal_ranges['AvS'],  spo2t)
        add_row_no_ref(2, 'Minimum SpO2',         f"{minimal_spo2[1]:.2f}%", normal_ranges['MinS'], spo2t)
        add_row_no_ref(3, 'Time Below 90% (min)', b90_str,                   normal_ranges['B90'],  spo2t)
        add_p()

    if plm_metrics is not None and plm_metrics["Total_LMS"] > 0:
        add_p('Limb Movements Analysis (AASM Criteria)', level=2)
        plmt = document.add_table(rows=5, cols=2)
        set_rtl(table=plmt)
        plmt.style = 'Light Grid Accent 1'
        plmt.rows[0].cells[0].text = _t('Parameter'); plmt.rows[0].cells[1].text = _t('Result')
        style_table_header(plmt)
        add_row_no_ref(1, 'Total Limb Movements',          str(plm_metrics["Total_LMS"]),      'N/A',    plmt)
        add_row_no_ref(2, 'Limb Movement Index (LMSI)',    f"{plm_metrics['LMSI']:.1f} / hr",  'N/A',    plmt)
        add_row_no_ref(3, 'Periodic Limb Movements (PLM)', str(plm_metrics["Total_PLM"]),      'N/A',    plmt)
        add_row_no_ref(4, 'PLM Index (PLMI)',              f"{plm_metrics['PLMI']:.1f} / hr",  '< 15.0', plmt)
        add_p()

    if watchpat_pdf_path and Path(watchpat_pdf_path).exists():
        add_p('WatchPAT Graphs', level=2)
        try:
            for img_path in extract_watchpat_visuals(Path(watchpat_pdf_path), out_dir):
                if img_path.exists():
                    document.add_picture(str(img_path), width=Inches(6.2))
                    document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                    add_p()
        except Exception:
            pass

    if motor_events_png_path and motor_events_png_path.exists():
        try:
            document.add_picture(str(motor_events_png_path), width=Inches(6.2))
            document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_p()
        except Exception:
            pass

    if watchpat_pdf_path and Path(watchpat_pdf_path).exists():
        add_p()
        add_p('WatchPAT Clinical Summary', level=1)
        if watchpat_data is not None:
            wpt = document.add_table(rows=7, cols=2)
            set_rtl(table=wpt)
            wpt.style = 'Light Grid Accent 1'
            wpt.rows[0].cells[0].text = _t('Parameter'); wpt.rows[0].cells[1].text = _t('Value')
            style_table_header(wpt)
            for i, (param, val) in enumerate([
                ('pAHI (events/hr)',       f"{watchpat_data['pAHI']:.1f}"),
                ('ODI 4% (events/hr)',      f"{watchpat_data['ODI']:.1f}"),
                ('Mean SpO2',               f"{watchpat_data['mean_sat']:.0f}%"),
                ('Minimum SpO2',            f"{watchpat_data['min_sat']:.0f}%"),
                ('Time below SpO2 90%',     f"{watchpat_data['sat_below_90_pct']:.1f}%"),
                ('Snoring mean intensity',  f"{watchpat_data['snoring_mean_db']:.0f} dB"),
            ], start=1):
                wpt.rows[i].cells[0].text = _t(param)
                wpt.rows[i].cells[1].text = val
                for cell in wpt.rows[i].cells:
                    for para in cell.paragraphs:
                        set_rtl(para=para)
                        for r in para.runs: set_rtl(run=r)
            add_p()

        if watchpat_summary_text:
            for i, line in enumerate(watchpat_summary_text.split('\\n')):
                line = line.strip()
                if not line:
                    continue
                # Assuming this text is generated in English, we might not have direct translations for it.
                # Just add it as is, but apply RTL if needed.
                p = add_p(line)
                if i < 2 and p.runs:
                    p.runs[0].bold = True
                    p.runs[0].font.size = Pt(11)

    add_p()
    add_p('Clinical Notes', level=1)
    dp = add_p()
    add_r(dp, 'Sleep Stage Definitions:', bold=True)
    add_p('• N1: Transition from wakefulness to sleep (light sleep)')
    add_p('• N2: Consolidated light sleep with sleep spindles and K-complexes')
    add_p('• N3 (SWS): Deep slow-wave sleep, restorative sleep stage')
    add_p('• REM: Rapid Eye Movement sleep, associated with dreaming')
    add_p()
    dp = add_p()
    add_r(dp, 'Note: ', bold=True)
    add_r(dp, 'Results marked with ▲/▼ deviate more than 2 Standard Deviations from age- and sex-matched normative data.')

    suffix = f"_{lang}" if lang != "en" else ""
    out_path = out_dir / f"sleep_report_{subject_id}_detailed{suffix}.docx"
    document.save(str(out_path))
    return out_path
"""

    import textwrap
    # We replace from "    subject_id = str(subject_id).split('_')[0]"
    # all the way to the end of _create_docx_detailed.
    
    # Let's find the exact block to replace using regex
    pattern = r"(    subject_id = str\(subject_id\)\.split\('_'\)\[0\].*?    return out_path\n)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.start()] + replacement_body + content[match.end():]
        print("Successfully replaced _create_docx_detailed body.")
    else:
        print("Regex match failed.")

    # Now update create_docx_sleep_report to generate two reports
    replacement_caller = """
    if report_type == "detailed":
        out_en = _create_docx_detailed(
            subject_id=subject_id,
            out_dir=outdir,
            hypno_1hz_int=hypno_1hz_int,
            subject_age=subject_age,
            sex=sex,
            hypno_png_path=hypno_png_path,
            pie_png_path=pie_png_path,
            spo2_edf_path=spo2_edf_path,
            spo2_channel=spo2_channel,
            pleth_channel=pleth_channel,
            plm_metrics=plm_metrics,
            watchpat_pdf_path=watchpat_pdf_path,
            motor_events_png_path=motor_events_png_path,
            lang="en"
        )
        try:
            _create_docx_detailed(
                subject_id=subject_id,
                out_dir=outdir,
                hypno_1hz_int=hypno_1hz_int,
                subject_age=subject_age,
                sex=sex,
                hypno_png_path=hypno_png_path,
                pie_png_path=pie_png_path,
                spo2_edf_path=spo2_edf_path,
                spo2_channel=spo2_channel,
                pleth_channel=pleth_channel,
                plm_metrics=plm_metrics,
                watchpat_pdf_path=watchpat_pdf_path,
                motor_events_png_path=motor_events_png_path,
                lang="he"
            )
        except Exception as e:
            print(f"[Warning] Failed to generate HE detailed docx: {e}")
        return out_en
"""
    # Replace caller
    pattern2 = r"    if report_type == \"detailed\":.*?        \)"
    match2 = re.search(pattern2, content, re.DOTALL)
    if match2:
        content = content[:match2.start()] + replacement_caller + content[match2.end():]
        print("Successfully replaced create_docx_sleep_report caller.")
    else:
        print("Regex match 2 failed.")

    with open('pipeline.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    run()
