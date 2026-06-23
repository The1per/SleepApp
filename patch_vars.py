def run():
    with open('pipeline.py', 'r', encoding='utf-8') as f:
        text = f.read()

    target = """        # --- pAHI from WatchPAT PDF ---
        _rdi = None
        _spo2_stats = None
        _wpat_hr_stats = None

        if append_pdf_path and Path(append_pdf_path).exists():
            try:
                _wpat = parse_watchpat_pdf(append_pdf_path)
                _rdi = float(_wpat["pAHI"]) if _wpat.get("pAHI") else None"""

    replacement = """        # --- pAHI from WatchPAT PDF ---
        _rdi = None
        _spo2_stats = None
        _wpat_hr_stats = None
        _pos_stats = None
        _resp_stats = None

        if append_pdf_path and Path(append_pdf_path).exists():
            try:
                _wpat = parse_watchpat_pdf(append_pdf_path)
                _rdi = float(_wpat["pAHI"]) if _wpat.get("pAHI") else None
                _pos_stats = _wpat.get("pos_stats")
                _resp_stats = _wpat.get("resp_stats")"""

    if target in text:
        text = text.replace(target, replacement)
        with open('pipeline.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print('Replaced successfully')
    else:
        print('Target not found')

if __name__ == '__main__':
    run()
