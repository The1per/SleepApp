import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from bidi.algorithm import get_display

fig, ax = plt.subplots(figsize=(4, 1))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)

disp_val1 = get_display("3.2 דקות")
disp_val2 = get_display("דקות 3.2")

ax.text(0.5, 0.7, disp_val1, ha="center", fontsize=15)
ax.text(0.5, 0.3, disp_val2, ha="center", fontsize=15)

plt.savefig("c:/Users/ynirmfa/Desktop/app/scratch/test_metric.png")
