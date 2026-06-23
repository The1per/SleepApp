import re

with open('patient_report_step5197.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('\\\"', '"')
# Let's just find the first TargetContent using find()
start = text.find('"TargetContent"')
if start != -1:
    content_start = text.find('"', start + 15) + 1
    content_end = text.find('", "ReplacementContent"', content_start)
    if content_end == -1:
        content_end = text.find('", "StartLine"', content_start)
    
    content = text[content_start:content_end]
    content = content.replace('\\\\n', '\\n').replace('\\\\t', '\\t')
    try:
        content = content.encode('utf-8').decode('unicode_escape')
    except:
        pass
    with open('target_0.py', 'w', encoding='utf-8') as out:
        out.write(content)
    print("Extracted successfully!")
