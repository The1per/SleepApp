append_code = """
    fig.subplots_adjust(top=gs.top, bottom=gs.bottom, left=gs.left, right=gs.right, hspace=gs.hspace, wspace=gs.wspace)
    
    out_path = outdir / f"{subject_id}_patient_report_{lang}.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor="white", edgecolor="none")
    
    pdf_path = outdir / f"{subject_id}_patient_report_{lang}.pdf"
    try:
        fig.savefig(pdf_path, dpi=dpi, bbox_inches="tight", facecolor="white", edgecolor="none", format="pdf")
    except Exception as e:
        print(f"[PatientReport] Failed to save PDF: {e}")
        
    plt.close(fig)
    return out_path

def generate_patient_report(subject_name=None, **kwargs):
    \"\"\"Generates both English and Hebrew reports, returns path to the English one.\"\"\"
    out_en = _generate_single_report(subject_name=subject_name, lang="en", **kwargs)
    _generate_single_report(subject_name=subject_name, lang="he", **kwargs)
    return out_en

if __name__ == "__main__":
    from pathlib import Path
    import numpy as np
    
    demo_hypno = np.zeros(3600*7)
    demo_hypno[3600*1:3600*2] = 1
    demo_hypno[3600*2:3600*3] = 2
    demo_hypno[3600*3:3600*4] = 3
    demo_hypno[3600*4:3600*5] = 4
    demo_hypno[3600*5:] = 0
    
    out = Path(".")
    generate_patient_report(
        hypno_1hz_int=demo_hypno,
        subject_id="DEMO_001",
        outdir=out,
        subject_name="Test Patient",
        study_date="2023-10-27",
        subject_age=45,
        sex="Male",
        rdi=12.4,
        ahi=8.2,
        spo2_stats={"avg": 94.5, "min": 86.0, "t_under90": 15.3},
        plm_metrics={"PLMI": 5.2},
        resp_stats={"Apnea": 10, "Hypopnea": 20},
        pos_stats={"Supine": 45, "Left": 25, "Right": 20, "Prone": 10},
        cv_stats={"avg_hr": 62.0, "min_hr": 48.0, "max_hr": 110.0, "rmssd": 35.0},
        notes=["Patient slept well.", "No significant arrhythmias."]
    )
    print("Finished. Main EN file:", out / "DEMO_001_patient_report_en.png")
"""

with open('patient_report.py', 'a', encoding='utf-8') as f:
    f.write(append_code)

print('Appended successfully')
