import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from bidi.algorithm import get_display

fig, ax = plt.subplots(figsize=(6, 2))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)

lang = "he"
title = "מדד הפרעות נשימה\n(pAHI)"
lines = title.split('\n')
number = 3

visual_lines = []
for i, line in enumerate(lines):
    disp = get_display(line)
    if i == 0:
        disp = f"{disp} .{number}"
    visual_lines.append(disp)
visual_text = '\n'.join(visual_lines)

ax.text(0.5, 0.5, visual_text, ha="center", va="center", fontsize=20)
fig.savefig("scratch/test_plot2.png")
