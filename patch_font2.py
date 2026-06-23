with open('patient_report.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'ax' in line and '.text(' in line and 'fontproperties' not in line:
        if 'bold' in line:
            fp_str = 'fontproperties=_he_fp(bold=True) if lang == "he" else None'
        else:
            fp_str = 'fontproperties=_he_fp() if lang == "he" else None'
            
        # find the matching closing paren of the text call, or just put it at the end of the line if the text call ends there
        # For simplicity, we just look for 	ransform=ax or zorder= or color= or ontsize=
        # Actually, let's just use regex to insert it before the LAST closing parenthesis of the line IF the line ends with a closing parenthesis.
        # But _t(lbl, lang), ends with ), and the text call spans multiple lines!
        # This is why AST or manual edits are better. Let's just do a manual replace_file_content for the whole file!
        pass
