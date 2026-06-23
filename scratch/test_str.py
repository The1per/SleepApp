import sys
sys.path.append('c:/Users/ynirmfa/Desktop/app')
from patient_report import TRANSLATIONS
from bidi.algorithm import get_display

display_title = TRANSLATIONS.get("Respiratory Disturbance Index (pAHI)")
import re
if "pAHI" in display_title:
    display_title = re.sub(r"\s*\(pAHI\)", "\n(pAHI)", display_title)

lines = display_title.split('\n')
line0 = f"{get_display(lines[0])} .3"

print("line0 repr:", repr(line0))
print("lines[0] repr:", repr(lines[0]))
print("get_display(lines[0]) repr:", repr(get_display(lines[0])))
print("line1 repr:", repr(lines[1]))
