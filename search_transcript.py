import json
with open(r'C:\Users\ynirmfa\.gemini\antigravity-ide\brain\747230af-8392-4070-873e-abcda23f5c70\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        step = data.get('step_index')
        if step <= 25:
            for call in data.get('tool_calls', []):
                name = call.get('name')
                args = call.get('args', {})
                print(f'Step {step} tool: {name}')
                if name in ('write_to_file', 'replace_file_content'):
                    print('   Target:', args.get('TargetFile'))
                elif name == 'run_command':
                    cmd = args.get('CommandLine', '')
                    if len(cmd) > 100:
                        cmd = cmd[:100] + '...'
                    print('   Cmd:', cmd)
