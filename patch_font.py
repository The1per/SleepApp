import re

with open('patient_report.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if 'ax' in line and '.text(' in line and 'fontproperties' not in line:
        if 'bold' in line:
            fp_str = 'fontproperties=_he_fp(bold=True) if lang == "he" else None'
        else:
            fp_str = 'fontproperties=_he_fp() if lang == "he" else None'
        
        # We need to insert it before the closing ')' of the text call.
        # This is tricky because the call might span multiple lines.
        # But looking at patient_report.py, most are single lines or end with ) on a known line.
        # Let's just find the ) at the end of the line.
        if line.rstrip().endswith(')') or line.rstrip().endswith('),'):
            new_line = line.rstrip()
            if new_line.endswith(','):
                new_line = new_line[:-1]
                if new_line.endswith(')'):
                    new_line = new_line[:-1] + f", {fp_str}),\n"
            else:
                new_line = new_line[:-1] + f", {fp_str})\n"
            line = new_line
        else:
            # If the line ends with ,, it continues on the next line. We can add it here.
            if line.rstrip().endswith(','):
                line = line.rstrip() + f" {fp_str},\n"
                
    new_lines.append(line)

with open('patient_report_patched.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Patched!")
