import re, fitz
from pathlib import Path
def parse_watchpat_pdf(pdf_path: "str | Path") -> dict:
    doc = fitz.open(str(pdf_path))
    raw_text = ""
    for page in doc:
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))
        for b in blocks:
            raw_text += b[4] + " "
    doc.close()

    clean_text = re.sub(r'\s+', ' ', raw_text)

    data = {
        "date": "N/A",
        "trt_hours": 0.0,
        "tst_hours": 0.0,
        "efficiency": 0.0,
        "wakes_per_hour": 0.0,
        "pAHI": 0.0,
        "ODI": 0.0,
        "mean_sat": 0.0,
        "min_sat": 0.0,
        "sat_below_90_pct": 0.0,
        "snoring_mean_db": 0.0,
        "hr_stats": None,
        "pos_stats": None,
        "resp_stats": None,
    }

    m = re.search(r"(\d{2}/\d{2}/\d{4})", clean_text)
    if m:
        data["date"] = m.group(1)

    m = re.search(r"Total Recording Time[^\d]+(\d+)\s*hrs[,\s]+(\d+)\s*min", clean_text, re.IGNORECASE)
    if m:
        data["trt_hours"] = int(m.group(1)) + int(m.group(2)) / 60.0

    m = re.search(r"Total Sleep Time[^\d]+(\d+)\s*hrs[,\s]+(\d+)\s*min", clean_text, re.IGNORECASE)
    if m:
        data["tst_hours"] = int(m.group(1)) + int(m.group(2)) / 60.0

    if data["trt_hours"] > 0:
        data["efficiency"] = (data["tst_hours"] / data["trt_hours"]) * 100.0

    m = re.search(r"Number of Wakes\s*:?\s*(\d+)", clean_text, re.IGNORECASE)
    if m and data["tst_hours"] > 0:
        data["wakes_per_hour"] = int(m.group(1)) / data["tst_hours"]

    m = re.search(r"pAHI\s*=\s*(\d+(?:\.\d+)?)", clean_text, re.IGNORECASE)
    if m:
        data["pAHI"] = float(m.group(1))
    else:
        m = re.search(
            r"pAHI\s*3%\s*:?\s*\d+\s+(?:\d+\.\d+\s+)*(\d+\.\d+)",
            clean_text, re.IGNORECASE
        )
        if m:
            data["pAHI"] = float(m.group(1))

    m = re.search(
        r"ODI\s*4%\s*:?\s*(?:\d+\s+)?(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)",
        clean_text, re.IGNORECASE
    )
    if m:
        data["ODI"] = float(m.group(3))

    m = re.search(
        r"Oxygen Saturation Statistics\s+Mean\s*:\s*Minimum\s*:\s*Maximum\s*:\s*"
        r"(\d{2,3})\s+(\d{2,3})\s+(\d{2,3})",
        clean_text, re.IGNORECASE
    )
    if m:
        data["mean_sat"] = float(m.group(1))
        data["min_sat"] = float(m.group(2))

    m = re.search(r"Oxygen Saturation\s*<90.*?Sleep\s*%\s+(\d+(?:\.\d+)?)", clean_text, re.IGNORECASE)
    if m:
        data["sat_below_90_pct"] = float(m.group(1))

    m = re.search(r"Snoring Statistics.*?Mean\s*:?\s*(\d+(?:\.\d+)?)\s*dB", clean_text, re.IGNORECASE)
    if m:
        data["snoring_mean_db"] = float(m.group(1))

    m_pos = re.search(r'Body Position Statistics.*?Sleep %\s*([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)', clean_text)
    if m_pos:
        print("m_pos:", m_pos)
        data["pos_stats"] = {
            "Supine": float(m_pos.group(1)),
            "Prone": float(m_pos.group(2)),
            "Right": float(m_pos.group(3)),
            "Left": float(m_pos.group(4)),
        }

    m_pahi = re.search(r'pAHI 3%\s*:?\s*([\d\.]+|N/A)\s+([\d\.]+|N/A)\s+([\d\.]+|N/A)\s+([\d\.]+|N/A)\s+([\d\.]+|N/A)', clean_text, re.IGNORECASE)
    if m_pahi:
        def _parse_val(v):
            return float(v) if v != 'N/A' else None
        data["resp_stats"] = {
            "pAHI 3%": {
                "all": data.get("pAHI", 0.0),
                "supine": _parse_val(m_pahi.group(1)),
                "nsupine": _parse_val(m_pahi.group(5))
            }
        }
    else:
        # Fallback if positional pAHI is missing
        data["resp_stats"] = {
            "pAHI 3%": {
                "all": data["pAHI"],
                "supine": None,
                "nsupine": None
            }
        }

    return data
print(parse_watchpat_pdf(Path('c:/Users/ynirmfa/Desktop/app/BS005_WP report.pdf')).get('pos_stats'))