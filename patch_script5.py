with open('patient_report.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'items = [("N1",st["N1"],STAGE_COLORS["N1"] Karnataka),' in line or 'items = [("N1",st["N1"],STAGE_COLORS["N1"]),' in line:
        skip = True
    
    if skip:
        if 'color=TEXT_M, ha="center", va="center")' in line:
            skip = False
        continue
    
    # Hypnogram size
    if 'axi = ax1.inset_axes([0.04, 0.40, 0.92, 0.50])' in line:
        new_lines.append('    axi = ax1.inset_axes([0.04, 0.15, 0.92, 0.75])\n')
        continue
        
    # Gauge text
    if 'ax.text(0, -0.28, _t("events / hour"' in line:
        new_lines.append(line.replace('-0.28', '-0.40'))
        continue
    if 'ax.text(0, -0.55, _t(sev, lang)' in line:
        new_lines.append(line.replace('-0.55', '-0.70'))
        continue
        
    new_lines.append(line)

with open('patient_report_patched6.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Patched successfully!')
