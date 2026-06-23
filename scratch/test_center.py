import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6, 2))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)

# EN test
t1 = ax.text(0.175, 0.8, "3. Respiratory Disturbance", fontsize=13, fontweight="bold", ha="left", va="center", transform=ax.transAxes)
fig.canvas.draw()
bbox = t1.get_window_extent()
bbox_axes = bbox.transformed(ax.transAxes.inverted())
x_center = (bbox_axes.x0 + bbox_axes.x1) / 2

ax.text(x_center, 0.6, "Index (pAHI)", fontsize=13, fontweight="bold", ha="center", va="center", transform=ax.transAxes)

# HE test
t2 = ax.text(0.825, 0.4, "מדד הפרעות נשימה .3", fontsize=13, fontweight="bold", ha="right", va="center", transform=ax.transAxes)
fig.canvas.draw()
bbox2 = t2.get_window_extent()
bbox_axes2 = bbox2.transformed(ax.transAxes.inverted())
x_center2 = (bbox_axes2.x0 + bbox_axes2.x1) / 2

ax.text(x_center2, 0.2, "(pAHI)", fontsize=13, fontweight="bold", ha="center", va="center", transform=ax.transAxes)

plt.savefig("c:/Users/ynirmfa/Desktop/app/scratch/test_center.png")
