def _generate_single_report(
    *,
    hypno_1hz_int: np.ndarray,
    subject_id: str,
    outdir: Path,
    subject_age: int | None = None,
    sex: str | None = None,
    spo2_stats: dict | None = None,
    plm_metrics: dict | None = None,
    rdi: float | None = None,
    ahi: float | None = None,
    resp_stats: dict | None = None,
    pos_stats: dict | None = None,
    notes: list[str] | None = None,
    dpi: int = 180,
    lang: str = "en",
) -> Path:
    rdi_v  = rdi if rdi is not None else ahi
    st     = _stats(hypno_1hz_int)

    # ── Page ──────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(8.5, 11), facecolor=BG)