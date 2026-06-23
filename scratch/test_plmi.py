import sys
sys.path.append('c:/Users/ynirmfa/Desktop/app')
from bidi.algorithm import get_display

with open("c:/Users/ynirmfa/Desktop/app/scratch/test_out.txt", "w", encoding="utf-8") as f:
    f.write(get_display("4.1 / שעה"))
