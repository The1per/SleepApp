from pathlib import Path
import numpy as np
from pipeline import _create_docx_detailed

outdir = Path("test_docx_output")
outdir.mkdir(exist_ok=True)
hypno = np.zeros(28800, dtype=int)
# give some random data so hypno stats don't crash
hypno[3600:14400] = 2
hypno[14400:18000] = 3
hypno[18000:21600] = 4

print("Generating EN docx...")
_create_docx_detailed(
    subject_id="DEMO_001",
    out_dir=outdir,
    hypno_1hz_int=hypno,
    subject_age=52,
    sex="M",
    hypno_png_path=Path("nonexistent.png"),
    pie_png_path=Path("nonexistent.png"),
    lang="en"
)

print("Generating HE docx...")
_create_docx_detailed(
    subject_id="DEMO_001",
    out_dir=outdir,
    hypno_1hz_int=hypno,
    subject_age=52,
    sex="M",
    hypno_png_path=Path("nonexistent.png"),
    pie_png_path=Path("nonexistent.png"),
    lang="he"
)
print("Done!")
