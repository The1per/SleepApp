Created At: 2026-06-05T19:31:40Z
Completed At: 2026-06-05T19:31:40Z
File Path: `file:///c:/Users/ynirmfa/Desktop/app/patient_report_new.py`
Total Lines: 737
Total Bytes: 34624
Showing lines 349 to 370
The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
349: def _generate_single_report(
350:     *,
351:     hypno_1hz_int: np.ndarray,
352:     subject_id: str,
353:     outdir: Path,
354:     subject_age: int | None = None,
355:     sex: str | None = None,
356:     spo2_stats: dict | None = None,
357:     plm_metrics: dict | None = None,
358:     rdi: float | None = None,
359:     ahi: float | None = None,
360:     resp_stats: dict | None = None,
361:     pos_stats: dict | None = None,
362:     notes: list[str] | None = None,
363:     dpi: int = 180,
364:     lang: str = "en",
365: ) -> Path:
366:     rdi_v  = rdi if rdi is not None else ahi
367:     st     = _stats(hypno_1hz_int)
368: 
369:     # ── Page ──────────────────────────────────────────────────────────────────
370:     fig = plt.figure(figsize=(8.5, 11), facecolor=BG)
The above content does NOT show the entire file contents. If you need to view any lines of the file which were not shown to complete your task, call this tool again to view those lines.
