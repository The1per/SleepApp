import sys
sys.path.append('c:/Users/ynirmfa/Desktop/app')
from patient_report import TRANSLATIONS
import re

he_title = TRANSLATIONS.get("Respiratory Disturbance Index (pAHI)")
new_title = re.sub(r"\s*\(pAHI\)", "\n(pAHI)", he_title)

with open("scratch/test_out.txt", "w", encoding="utf-8") as f:
    f.write("original: " + he_title + "\n")
    f.write("new: " + new_title + "\n")
    f.write("Has newline: " + str('\n' in new_title[1:]) + "\n")
