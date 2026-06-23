import sys
sys.path.append('c:/Users/ynirmfa/Desktop/app')
from bidi.algorithm import get_display

with open("c:/Users/ynirmfa/Desktop/app/scratch/test_out.txt", "w", encoding="utf-8") as f:
    f.write("Original 1: 3.2 דקות\n")
    f.write("Display 1: " + get_display("3.2 דקות") + "\n")
    f.write("Original 2: דקות 3.2\n")
    f.write("Display 2: " + get_display("דקות 3.2") + "\n")
    
    # What about % ?
    f.write("Original 3: 87.0 %\n")
    f.write("Display 3: " + get_display("87.0 %") + "\n")
    f.write("Original 4: % 87.0\n")
    f.write("Display 4: " + get_display("% 87.0") + "\n")
