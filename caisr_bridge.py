import os
import sys
import shutil
import subprocess
from pathlib import Path
import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mne

# Вспомогательная функция для получения путей в PyInstaller
def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсу, работает для разработки и для PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ==============================================================================
# 1. DIAGNOSTIC UTILS
# ==============================================================================

def print_directory_tree(dir_path: Path, prefix=""):
    """Рекурсивно печатает дерево файлов для дебага."""
    if not dir_path.exists():
        return
    for item in dir_path.iterdir():
        if item.is_dir():
            print(f"{prefix}📁 {item.name}")
            print_directory_tree(item, prefix + "  ")
        else:
            print(f"{prefix}📄 {item.name} ({item.stat().st_size} bytes)")

def diagnose_h5_file(h5_path: Path):
    """Открывает H5 и проверяет, есть ли данные в каналах ног."""
    print(f"\n[CAISR DIAGNOSTICS] --- H5 SANITY CHECK FOR {h5_path.name} ---")
    try:
        with h5py.File(str(h5_path), 'r') as f:
            if 'signals' not in f:
                print(" ❌ Группа 'signals' не найдена в H5 файле!")
                return
            
            sigs = f['signals']
            print(f" 📂 Найдены каналы: {list(sigs.keys())}")
            
            for ch in ['lat', 'rat', 'ecg']:
                if ch in sigs:
                    data = sigs[ch][:]
                    min_val = np.min(data)
                    max_val = np.max(data)
                    is_zero = bool(np.all(data == 0))
                    print(f" 📊 Канал '{ch}': shape={data.shape}, min={min_val:.6e}, max={max_val:.6e}, all_zeros={is_zero}")
                else:
                    print(f" ❌ Канал '{ch}' ОТСУТСТВУЕТ в H5 файле!")
    except Exception as e:
        print(f" ❌ Ошибка при чтении H5: {e}")
    print("[CAISR DIAGNOSTICS] -----------------------------------------\n")


# ==============================================================================
# 2. DATA PREPARATION FOR CAISR
# ==============================================================================

def export_to_caisr_h5(raw: mne.io.BaseRaw, channels_map_list: list, h5_path: Path):
    print(f"[CAISR DEBUG] Starting data export to {h5_path.name}...")
    
    raw_resampled = raw.copy().resample(200.0, n_jobs=1)
    n_samples = raw_resampled.n_times
    print(f"[CAISR DEBUG] Resampling completed. Samples: {n_samples} (200 Hz)")
    
    req_channels = [
        'f3-m2', 'f4-m1', 'c3-m2', 'c4-m1', 'o1-m2', 'o2-m1', 
        'e1-m2', 'e2-m1', 'chin1-chin2', 'abd', 'chest', 'spo2', 'ecg', 
        'lat', 'rat', 'legl', 'legr', 'leg_l', 'leg_r',
        'chin', 'cz-oz'
    ]
    
    signal_df = pd.DataFrame(np.zeros((n_samples, len(req_channels)), dtype=np.float32), columns=req_channels)
    
    mapped_count = 0
    for mne_ch, caisr_ch in channels_map_list:
        if mne_ch in raw_resampled.ch_names and caisr_ch in req_channels:
            data = raw_resampled.get_data(picks=mne_ch, units="V").squeeze()
            
            if signal_df[caisr_ch].abs().sum() > 0:
                signal_df[caisr_ch] = signal_df[caisr_ch] + data
            else:
                signal_df[caisr_ch] = data
            mapped_count += 1
            print(f"[CAISR DEBUG] Channel {mne_ch} successfully mapped to slot {caisr_ch}")

    if mapped_count == 0:
        print("[CAISR ERROR] WARNING! No channels were mapped to H5. Check your channel mapping!")

    t = np.arange(n_samples)
    if signal_df['ecg'].abs().sum() == 0:
        print("[CAISR DEBUG] Real ECG missing. Injecting dummy ECG (60 BPM)...")
        fake_ecg = 0.0001 * np.sin(2 * np.pi * 1.0 * (t / 200.0)) 
        fake_ecg[::200] = 0.001 
        signal_df['ecg'] = fake_ecg.astype(np.float32)

    h5_path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(str(h5_path), 'w') as f:
        f.attrs['sampling_rate'] = 200
        f.attrs['unit_voltage'] = 'V'
        group_signals = f.create_group('signals')
        for name in signal_df.columns:
            group_signals.create_dataset(
                name, data=signal_df[name].values.reshape(-1, 1), 
                shape=(n_samples, 1), maxshape=(n_samples, 1), 
                dtype='float32', compression="gzip"
            )
    print("[CAISR DEBUG] H5 export successfully completed.")

# ==============================================================================
# 3. DOCKER PIPELINE ORCHESTRATION
# ==============================================================================

def run_full_caisr_pipeline(
    raw: mne.io.BaseRaw, 
    subject_id: str,
    outdir: Path,
    stages_csv_path: str = None
) -> dict:
    
    # Получаем динамический путь к папке CAISR
    base_dir = Path(resource_path("CAISR-App-main"))
    data_dir = base_dir / 'data'
    output_dir = base_dir / 'caisr_output'
    
    for d in [data_dir, output_dir]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True, exist_ok=True)
        
    (data_dir / 'raw').mkdir(parents=True, exist_ok=True)
        
    h5_file = data_dir / f"{subject_id}.h5"
    
    robust_map = []
    for mne_ch in raw.ch_names:
        ch_up = mne_ch.upper()
        
        if 'LEFT_LEG' in ch_up or 'LAT' in ch_up: 
            robust_map.extend([(mne_ch, 'lat'), (mne_ch, 'legl'), (mne_ch, 'leg_l')])
        elif 'RIGHT_LEG' in ch_up or 'RAT' in ch_up: 
            robust_map.extend([(mne_ch, 'rat'), (mne_ch, 'legr'), (mne_ch, 'leg_r')])
            
        # ==============================================================
        # ИСПРАВЛЕНИЕ: Добавлен парсинг твоего единого канала 'EMG Leg'
        elif 'EMG LEG' in ch_up or ch_up == 'LEG': 
            robust_map.extend([(mne_ch, 'lat'), (mne_ch, 'legl'), (mne_ch, 'leg_l')])
        # ==============================================================
            
        elif 'ECG' in ch_up or 'EKG' in ch_up: 
            robust_map.append((mne_ch, 'ecg'))
        elif 'SPO2' in ch_up or 'SAO2' in ch_up:
            robust_map.append((mne_ch, 'spo2'))
        elif 'CHEST' in ch_up or 'THOR' in ch_up:
            robust_map.append((mne_ch, 'chest'))
        elif 'ABD' in ch_up:
            robust_map.append((mne_ch, 'abd'))
            
        elif ch_up in ['E183', 'E104'] or ch_up == 'C4' or 'C4-M1' in ch_up: 
            robust_map.extend([(mne_ch, 'c4-m1'), (mne_ch, 'c3-m2'), (mne_ch, 'cz-oz')])
        elif ch_up in ['E59', 'E36'] or ch_up == 'C3' or 'C3-M2' in ch_up: 
            robust_map.append((mne_ch, 'c3-m2'))
            
        elif ch_up in ['E224', 'E124'] or ch_up == 'F4' or 'F4-M1' in ch_up: 
            robust_map.extend([(mne_ch, 'f4-m1'), (mne_ch, 'f3-m2')])
        elif ch_up in ['E36', 'E24'] or ch_up == 'F3' or 'F3-M2' in ch_up: 
            robust_map.append((mne_ch, 'f3-m2'))
            
        elif ch_up in ['E150', 'E83'] or ch_up == 'O2' or 'O2-M1' in ch_up: 
            robust_map.extend([(mne_ch, 'o2-m1'), (mne_ch, 'o1-m2')])
        elif ch_up in ['E116', 'E70'] or ch_up == 'O1' or 'O1-M2' in ch_up: 
            robust_map.append((mne_ch, 'o1-m2'))
            
        elif ch_up in ['E252', 'E25', 'E226'] or ch_up == 'E1' or 'E1-M2' in ch_up: 
            robust_map.append((mne_ch, 'e1-m2'))
        elif ch_up in ['E2', 'E8', 'E47'] or ch_up == 'E2' or 'E2-M1' in ch_up: 
            robust_map.append((mne_ch, 'e2-m1'))
            
        elif ch_up in ['E240', 'E126', 'E243', 'E127'] or 'EMG-R' in ch_up or 'EMG-L' in ch_up: 
            robust_map.extend([(mne_ch, 'chin1-chin2'), (mne_ch, 'chin')])

    export_to_caisr_h5(raw, robust_map, h5_file)
    diagnose_h5_file(h5_file)
    
    dest_stage_dir = output_dir / subject_id
    dest_stage_dir.mkdir(parents=True, exist_ok=True)
    
    if stages_csv_path and Path(stages_csv_path).exists():
        shutil.copy2(stages_csv_path, dest_stage_dir / f"{subject_id}_stages.csv")
        shutil.copy2(stages_csv_path, output_dir / f"{subject_id}_stages.csv")

    # =========================================================================
    # ЗАПУСК STAGING: сначала Docker, при неудаче — нативный Python (CAISR_stage)
    # =========================================================================
    print(f"\n[CAISR DEBUG] LAUNCHING STAGING PIPELINE (Docker preferred, native fallback)...")
    
    stage_out_dir = output_dir / 'intermediate' / 'stage'
    stage_out_dir.mkdir(parents=True, exist_ok=True)

    docker_staging_ok = False
    try:
        if str(base_dir) not in sys.path:
            sys.path.insert(0, str(base_dir))
        from run_caisr_docker import run_docker_pipeline
        run_docker_pipeline(str(base_dir))
        # Проверяем что файл действительно появился (Docker мог завершиться без ошибки но без результата)
        stage_files = list(stage_out_dir.glob("*_stage.csv"))
        if stage_files:
            docker_staging_ok = True
            print("[CAISR DEBUG] Docker staging completed and output verified.")
        else:
            print("[CAISR DEBUG] Docker ran but produced no stage CSV — falling back to native.")
    except Exception as e:
        print(f"[CAISR DEBUG] Docker staging failed: {e} — switching to native Python staging.")

    if not docker_staging_ok:
        print("[CAISR DEBUG] LAUNCHING NATIVE PYTHON STAGING (Subprocess Worker)...")
        try:
            import glob as _glob
            import os
            import json
            import subprocess
            if str(base_dir) not in sys.path:
                sys.path.insert(0, str(base_dir))

            # Подготовка run_parameters/stage.csv (требуется caisr_stage)
            param_dir = data_dir / 'run_parameters'
            param_dir.mkdir(parents=True, exist_ok=True)
            pd.DataFrame({'overwrite': [True]}).to_csv(param_dir / 'stage.csv', index=False)

            input_files = _glob.glob(str(data_dir / '*.h5'))
            if not input_files:
                print("[CAISR ERROR] No H5 files found in data_dir for staging!")
            else:
                model_path = str(base_dir / 'stage' / 'models/')
                if not model_path.endswith('/'):
                    model_path += '/'
                
                save_paths = [
                    str(stage_out_dir / (Path(p).stem + '_stage.csv'))
                    for p in input_files
                ]
                
                kwargs = {
                    'base_dir': str(base_dir),
                    'input_files': input_files,
                    'save_paths': save_paths,
                    'model_path': model_path
                }
                
                # Запускаем через подпроцесс чтобы обойти TLS Limit Error 1114 (TensorFlow + PyQt5)
                cmd = [sys.executable, '--caisr-stage-worker', json.dumps(kwargs)]
                
                # Если скомпилировано с --noconsole, CREATE_NO_WINDOW предотвращает появление черных окон
                creationflags = 0x08000000 if sys.platform == 'win32' else 0
                
                print("[CAISR DEBUG] Starting subprocess worker...")
                result = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags)
                
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
                    
                if result.returncode == 0:
                    print("[CAISR DEBUG] Native staging completed successfully via subprocess worker.")
                else:
                    print(f"[CAISR ERROR] Subprocess worker failed with code {result.returncode}")
        except Exception as e:
            print(f"[CAISR ERROR] Native staging also failed: {e}")
            import traceback
            traceback.print_exc()

    # =========================================================================
    # НАТИВНЫЙ ЗАПУСК ДЛЯ НОГ (ИСПОЛЬЗУЕМ ПРЯМОЙ ИМПОРТ)
    # =========================================================================
    print("\n[CAISR DEBUG] LAUNCHING NATIVE PYTHON FOR LIMB MODULE...")
    
    param_dir = data_dir / 'run_parameters'
    param_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({'overwrite': [True]}).to_csv(param_dir / 'limb.csv', index=False)
    
    limb_out_dir = output_dir / 'intermediate' / 'limb'
    limb_out_dir.mkdir(parents=True, exist_ok=True)
    (limb_out_dir / 'data').mkdir(parents=True, exist_ok=True)
    
    try:
        # 1. Добавляем путь к CAISR в sys.path, чтобы Python смог импортировать caisr_limb
        if str(base_dir) not in sys.path:
            sys.path.insert(0, str(base_dir))
            
        # 2. Импортируем нашу новую функцию
        from caisr_limb import run_limb_detection
        
        # 3. Конвертируем пути в строки с обязательным слешем на конце
        input_path_str = str(data_dir).replace('\\', '/') + '/'
        save_path_str = str(output_dir / 'intermediate').replace('\\', '/') + '/'
        
        # 4. Вызываем функцию напрямую внутри текущего процесса
        run_limb_detection(input_path=input_path_str, save_path=save_path_str)
        print("[CAISR DEBUG] Limb detection completed successfully.")
        
    except Exception as e:
        print(f"[CAISR ERROR] Native limb script failed: {e}")
        import traceback
        traceback.print_exc()

    # =========================================================================

    results = {"limb_events_csv": None, "stages_csv": None, "pdf_report": None}
    outdir.mkdir(parents=True, exist_ok=True)

    all_output_files = list(output_dir.rglob(f"*{subject_id}*.*"))
    print(f"[CAISR DEBUG] Files found in CAISR output folder: {[f.name for f in all_output_files]}")

    # Collect stage CSV candidates separately to avoid duplicates
    stage_csv_candidates = []
    for f in all_output_files:
        dest_path = outdir / f.name
        if f.suffix == '.csv':
            if 'limb' in f.name.lower():
                shutil.copy2(f, dest_path)
                results["limb_events_csv"] = str(dest_path)
                print(f"[CAISR DEBUG] Successfully copied limb file to {dest_path}")
            elif 'stage' in f.name.lower():
                stage_csv_candidates.append(f)
        elif f.suffix == '.pdf':
            shutil.copy2(f, dest_path)
            results["pdf_report"] = str(dest_path)

    # Pick best stage CSV: prefer native _stage.csv over YASA-copy _stages.csv
    if stage_csv_candidates:
        # Sort: files with '_stage.csv' (not '_stages.csv') come first
        stage_csv_candidates.sort(key=lambda p: (0 if p.name.endswith('_stage.csv') else 1, p.name))
        best_stage = stage_csv_candidates[0]
        dest_path = outdir / best_stage.name
        shutil.copy2(best_stage, dest_path)
        results["stages_csv"] = str(dest_path)
        print(f"[CAISR DEBUG] Successfully copied stage file to {dest_path} "
              f"(selected from {len(stage_csv_candidates)} candidate(s))")

    h5_file.unlink(missing_ok=True)
    return results


def parse_caisr_nrem_events(limb_csv_path: str, hypno_1hz_int: np.ndarray) -> pd.DataFrame:
    print(f"[PLOT DEBUG] Parsing NREM limb events from {limb_csv_path}")
    if not limb_csv_path or not Path(limb_csv_path).exists():
        print("[PLOT DEBUG] Limb CSV file not found or path is empty!")
        return pd.DataFrame()
        
    df = pd.read_csv(limb_csv_path)
    nrem_events = []
    
    if 'limb' in df.columns:
        df = df[df['limb'] == 1]
        
    print(f"[PLOT DEBUG] Found {len(df)} total limb events in CSV.")
    
    for _, row in df.iterrows():
        start_sec = (row.get('start_idx', row.get('start', 0)) / 200.0) * 2.0
        end_sec = (row.get('end_idx', row.get('end', 0)) / 200.0) * 2.0
        
        hyp_idx = int(start_sec)
        if hyp_idx < len(hypno_1hz_int) and hypno_1hz_int[hyp_idx] in [1, 2, 3]:
            nrem_events.append({
                "start_sec": start_sec, "end_sec": end_sec,
                "duration": end_sec - start_sec, "type": "NREM_CAISR_Event"
            })
            
    print(f"[PLOT DEBUG] Filtered down to {len(nrem_events)} events during NREM sleep.")
    return pd.DataFrame(nrem_events)

def plot_combined_hypnogram(
    path: Path | str, hypno_1hz_int: np.ndarray, start_dt: pd.Timestamp,
    rbdtector_events: pd.DataFrame = None, caisr_nrem_events: pd.DataFrame = None,
    rbd_signal_name: str = "EMG-R", title: str | None = None, verbose: bool = True,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    hypno_1hz_int = np.asarray(hypno_1hz_int, dtype=int).ravel()
    
    t_hours = np.arange(hypno_1hz_int.size) / 3600.0
    remapped = pd.Series(hypno_1hz_int).map({-2:-2, -1:-1, 0:0, 1:2, 2:3, 3:4, 4:1}).fillna(-2).to_numpy()
    y_vals = -1.0 * remapped

    fig = plt.figure(figsize=(14, 5.5), dpi=150, facecolor='w')
    
    # Adjust subplot position to leave space for top/bottom margins
    # original was implicit (left=0.125, bottom=0.1, right=0.9, top=0.9)
    # let's explicitly adjust the subplot parameter
    fig.subplots_adjust(top=0.85, bottom=0.15)
    
    # --- Add Logo ---
    try:
        import os, sys
        from PIL import Image
        def _resource_path(relative_path):
            try: base_path = sys._MEIPASS
            except Exception: base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)
            
        logo_up_path = _resource_path("logo_up.png")
        if os.path.exists(logo_up_path):
            logo_up_img = Image.open(logo_up_path)
            # Position at top center
            ax_logo_up = fig.add_axes([0.4, 0.89, 0.2, 0.09], anchor='N', zorder=10)
            ax_logo_up.imshow(logo_up_img)
            ax_logo_up.axis('off')
            
        logo_down_path = _resource_path("logo_down.png")
        if os.path.exists(logo_down_path):
            logo_down_img = Image.open(logo_down_path)
            # Position at bottom full width
            ax_logo_down = fig.add_axes([0.05, 0.01, 0.9, 0.12], anchor='S', zorder=10)
            ax_logo_down.imshow(logo_down_img)
            ax_logo_down.axis('off')
    except Exception as e:
        print(f"Logo error: {e}")

    t_text = title if title else "CAISR Sleep Analysis Report"
    if start_dt is not None:
        try:
            t_text += f" - {start_dt.strftime('%d.%m.%Y')}"
        except Exception:
            pass
    fig.suptitle(t_text, fontsize=20, fontweight="bold", y=0.85)

    ax = fig.add_subplot(111)
    ax.step(t_hours, y_vals, where="post", color="k", linewidth=1.5, alpha=0.5)

    masks = {
        "REM": np.ma.masked_not_equal(remapped, 1), "W": np.ma.masked_not_equal(remapped, 0),
        "N1": np.ma.masked_not_equal(remapped, 2), "N2": np.ma.masked_not_equal(remapped, 3),
        "N3": np.ma.masked_not_equal(remapped, 4),
    }
    colors = {"REM": "r", "W": "b", "N1": "c", "N2": "g", "N3": "m"}
    for stage, arr in masks.items():
        ax.step(t_hours, -1.0 * arr, where="post", color=colors[stage], linewidth=2.0)

    if rbdtector_events is not None and not rbdtector_events.empty:
        try:
            clean_sig = rbd_signal_name.replace("-", "").upper()
            rec_start = start_dt if start_dt else pd.to_datetime(rbdtector_events.iloc[0, 0])
            
            def to_day_seconds(dt):
                if isinstance(dt, str): dt = pd.to_datetime(dt)
                return dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6

            rec_start_sec = to_day_seconds(rec_start)
            plotted_rbd = 0
            for _, row in rbdtector_events.iterrows():
                if len(row) < 3: continue
                label = str(row[2]).replace("-","").upper()
                if clean_sig in label:
                    ev_start_sec = to_day_seconds(row[0])
                    ev_end_sec = to_day_seconds(row[1])

                    diff_start = ev_start_sec - rec_start_sec
                    diff_end = ev_end_sec - rec_start_sec
                    if diff_start < -43200: diff_start += 86400
                    if diff_end < -43200: diff_end += 86400
                    
                    start_h, end_h = diff_start / 3600.0, diff_end / 3600.0
                    if end_h > 0 and start_h < t_hours[-1]:
                        ax.hlines(y=-4.4, xmin=max(0, start_h), xmax=min(t_hours[-1], end_h),
                                  color="red", linewidth=8.0, alpha=1.0, 
                                  label='RBD Event (RBDtector)' if plotted_rbd == 0 else "")
                        plotted_rbd += 1
        except Exception as e:
            if verbose: print(f"[PLOT ERROR] Error plotting RBD events: {e}")

    if caisr_nrem_events is not None and not caisr_nrem_events.empty:
        try:
            plotted_nrem = 0
            for _, row in caisr_nrem_events.iterrows():
                start_h = row['start_sec'] / 3600.0
                end_h = row['end_sec'] / 3600.0
                if end_h > 0 and start_h < t_hours[-1]:
                    ax.hlines(y=-4.7, xmin=max(0, start_h), xmax=min(t_hours[-1], end_h),
                              color="blue", linewidth=8.0, alpha=0.8, 
                              label='NREM Event (CAISR)' if plotted_nrem == 0 else "")
                    plotted_nrem += 1
        except Exception as e:
            if verbose: print(f"[PLOT ERROR] Error plotting CAISR events: {e}")

    ax.set_yticks([0, -1, -2, -3, -4])
    ax.set_yticklabels(["W", "R", "N1", "N2", "N3"])
    ax.set_ylim(-5.0, 0.5) 
    ax.set_xlim(0, max(t_hours[-1] if t_hours.size else 0, 0.01))
    ax.set_xlabel("Time [hrs]")
    if title: ax.set_title(title)
    
    handles, labels = ax.get_legend_handles_labels()
    if handles: ax.legend(handles, labels, loc='lower right', fontsize='small')

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)

def plot_motor_events_standalone(
    out_path, h: np.ndarray, caisr_nrem_events, rbdtector_events, start_dt
):
    import matplotlib.pyplot as plt
    import pandas as pd
    
    fig, ax = plt.subplots(figsize=(10, 1.2))
    
    t_hours = h.size / 3600.0
    ax.set_xlim(0, t_hours)
    ax.set_ylim(0, 1)
    
    ax.yaxis.set_visible(False)
    ax.set_xticks(np.arange(0, t_hours + 1, 1))
    ax.set_xticklabels([])
    ax.tick_params(axis="x", length=3, color="#666666")
    for spine in ax.spines.values():
        spine.set_edgecolor("#666666")
        spine.set_linewidth(1.0)
    
    ax.set_title("Motor Events", loc='left', fontsize=12, fontweight="bold", style="italic", color="#333333", pad=6)
    
    plm_plotted = False
    if caisr_nrem_events is not None and not caisr_nrem_events.empty:
        for _, row in caisr_nrem_events.iterrows():
            st_h = row["start_sec"] / 3600.0
            en_h = row["end_sec"] / 3600.0
            ax.axvspan(st_h, en_h, color="#4A80C0", alpha=1.0, ymin=0, ymax=1)
            plm_plotted = True
            
    rbd_plotted = False
    if rbdtector_events is not None and not rbdtector_events.empty and start_dt is not None:
        try:
            def to_day_seconds(dt):
                if isinstance(dt, str): dt = pd.to_datetime(dt)
                return dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6

            rec_start_sec = to_day_seconds(start_dt)
            for _, row in rbdtector_events.iterrows():
                if len(row) < 3: continue
                ev_start_sec = to_day_seconds(row[0])
                ev_end_sec = to_day_seconds(row[1])

                diff_start = ev_start_sec - rec_start_sec
                diff_end = ev_end_sec - rec_start_sec
                if diff_start < -43200: diff_start += 86400
                if diff_end < -43200: diff_end += 86400
                
                st_h = diff_start / 3600.0
                en_h = diff_end / 3600.0
                
                if en_h > 0 and st_h < t_hours:
                    ax.axvspan(max(0, st_h), min(t_hours, en_h), color="#E04A4A", alpha=1.0, ymin=0, ymax=1)
                    rbd_plotted = True
        except Exception as e:
            pass
            
    if plm_plotted or rbd_plotted:
        leg_str = []
        if plm_plotted: leg_str.append("PLM (Blue)")
        if rbd_plotted: leg_str.append("RBD (Red)")
        
        ax.text(0.99, 1.1, " | ".join(leg_str), transform=ax.transAxes,
                fontsize=10, color="#666666", ha="right", va="bottom")
    else:
        ax.text(0.5, 0.5, "No motor events detected", transform=ax.transAxes,
                fontsize=12, color="#666666", ha="center", va="center")
    
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path