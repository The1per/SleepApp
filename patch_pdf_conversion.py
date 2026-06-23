import re

def run():
    with open('pipeline.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update create_docx_sleep_report to return a tuple
    replacement_caller = """
    if report_type == "detailed":
        out_en = _create_docx_detailed(
            subject_id=subject_id,
            out_dir=outdir,
            hypno_1hz_int=hypno_1hz_int,
            subject_age=subject_age,
            sex=sex,
            hypno_png_path=hypno_png_path,
            pie_png_path=pie_png_path,
            spo2_edf_path=spo2_edf_path,
            spo2_channel=spo2_channel,
            pleth_channel=pleth_channel,
            plm_metrics=plm_metrics,
            watchpat_pdf_path=watchpat_pdf_path,
            motor_events_png_path=motor_events_png_path,
            lang="en"
        )
        out_he = None
        try:
            out_he = _create_docx_detailed(
                subject_id=subject_id,
                out_dir=outdir,
                hypno_1hz_int=hypno_1hz_int,
                subject_age=subject_age,
                sex=sex,
                hypno_png_path=hypno_png_path,
                pie_png_path=pie_png_path,
                spo2_edf_path=spo2_edf_path,
                spo2_channel=spo2_channel,
                pleth_channel=pleth_channel,
                plm_metrics=plm_metrics,
                watchpat_pdf_path=watchpat_pdf_path,
                motor_events_png_path=motor_events_png_path,
                lang="he"
            )
        except Exception as e:
            print(f"[Warning] Failed to generate HE detailed docx: {e}")
        return out_en, out_he
"""
    # Replace caller
    pattern2 = r"    if report_type == \"detailed\":.*?        return out_en\n"
    match2 = re.search(pattern2, content, re.DOTALL)
    if match2:
        content = content[:match2.start()] + replacement_caller + content[match2.end():]
        print("Successfully replaced create_docx_sleep_report caller to return tuple.")
    else:
        print("Regex match for create_docx_sleep_report failed.")

    # 2. Update PDF conversion logic in mff_yasa_sleepeegpy_combo
    pdf_conversion_block = """
        docx_results = create_docx_sleep_report(
            report_type=docx_report_type,
            subject_id=mff_path_primary.stem,
            outdir=outdir,
            hypno_1hz_int=hypno_1hz_int,
            subject_age=int(subject_age),
            sex=str(sex),
            hypno_png_path=Path(final_hypno_path),
            pie_png_path=legacy_pie_png,
            spo2_edf_path=spo2_edf_path,
            spo2_channel=spo2_channel,
            pleth_channel=pleth_channel,
            plm_metrics=plm_metrics,
            watchpat_pdf_path=append_pdf_path,
            motor_events_png_path=caisr_motor_events_png
        )
        
        # docx_results could be a tuple (en, he) or a single path if simple
        if not isinstance(docx_results, tuple):
            docx_results = (docx_results,)
            
        for d_path in docx_results:
            if not d_path or not Path(d_path).exists():
                continue
            docx_report_path = Path(d_path)
            try:
                from pypdf import PdfWriter
                base_pdf_path = docx_report_path.with_suffix(".pdf")
                if not _convert_docx_to_pdf_safe(docx_report_path, base_pdf_path, timeout_sec=120):
                    raise RuntimeError("docx2pdf conversion failed or timed out")

                if append_pdf_path and Path(append_pdf_path).exists():
                    merger = PdfWriter()
                    merger.append(str(base_pdf_path))
                    merger.append(str(append_pdf_path))
                    # determine language suffix
                    suffix = "_he" if "_he" in docx_report_path.stem else "_en" if "_en" in docx_report_path.stem else ""
                    final_pdf_path = outdir / f"sleep_report_{mff_path_primary.stem}_merged{suffix}.pdf"
                    merger.write(str(final_pdf_path))
                    merger.close()
                    if base_pdf_path.exists(): base_pdf_path.unlink()
            except Exception as e:
                print(f"Error during PDF conversion for {docx_report_path.name}: {e}")
"""
    pattern_pdf = r"        docx_report = create_docx_sleep_report\(.*?        except Exception as e:\n            print\(f\"Error during PDF conversion: \{e\}\"\)\n"
    match_pdf = re.search(pattern_pdf, content, re.DOTALL)
    if match_pdf:
        content = content[:match_pdf.start()] + pdf_conversion_block + content[match_pdf.end():]
        print("Successfully replaced PDF conversion logic.")
    else:
        print("Regex match for PDF conversion failed.")

    # 3. Update keep_extensions in cleanup_output_directory
    content = content.replace("keep_extensions = {'.pdf', '.fif'}", "keep_extensions = {'.pdf', '.fif', '.docx'}")

    with open('pipeline.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    run()
