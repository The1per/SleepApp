import numpy as np
import mne
from scipy.signal import find_peaks

def compute_cardio_metrics(raw: mne.io.BaseRaw) -> dict | None:
    """
    Extracts Average HR, Min HR, Max HR, and RMSSD (HRV) from an ECG or EMG channel.
    Returns None if no suitable channel is found or if data is too noisy.
    """
    if raw is None:
        return None
        
    # 1. Find a suitable channel (prefer ECG, fallback to EMG/Chin)
    target_ch = None
    ch_names_upper = [ch.upper() for ch in raw.ch_names]
    
    # Priority 1: Dedicated ECG
    for c_idx, ch in enumerate(ch_names_upper):
        if "ECG" in ch or "EKG" in ch:
            target_ch = raw.ch_names[c_idx]
            break
            
    # Priority 2: Chin EMG (often picks up strong QRS)
    if not target_ch:
        for c_idx, ch in enumerate(ch_names_upper):
            if "CHIN" in ch or "EMG" in ch:
                target_ch = raw.ch_names[c_idx]
                break
                
    if not target_ch:
        print("[CardioMetrics] No ECG or EMG channel found for HR extraction.")
        return None
        
    print(f"[CardioMetrics] Using channel '{target_ch}' for Heart Rate extraction.")
    
    try:
        # Load data for this channel
        data, times = raw.copy().pick_channels([target_ch]).get_data(return_times=True)
        sig = data[0]
        sfreq = raw.info['sfreq']
        
        # Simple highpass to remove baseline wander
        # MNE filter requires 2D array: (n_channels, n_samples)
        sig = mne.filter.filter_data(sig, sfreq, l_freq=1.0, h_freq=40.0, verbose="ERROR")
        
        # Absolute value to make peaks prominent regardless of polarity
        sig_abs = np.abs(sig)
        
        # Dynamic threshold based on robust statistics
        median = np.median(sig_abs)
        mad = np.median(np.abs(sig_abs - median))
        threshold = median + 5 * mad
        
        # Minimum distance between peaks (assuming max HR ~200 bpm -> 300 ms -> 0.3 * sfreq)
        min_dist = int(0.3 * sfreq)
        
        peaks, _ = find_peaks(sig_abs, distance=min_dist, height=threshold)
        
        if len(peaks) < 10:
            print("[CardioMetrics] Not enough peaks detected.")
            return None
            
        # Calculate RR intervals in milliseconds
        rr_intervals = np.diff(peaks) / sfreq * 1000.0
        
        # Filter physiological RR intervals (roughly 40 to 180 bpm)
        # 180 bpm = 333 ms, 40 bpm = 1500 ms
        valid_rr = rr_intervals[(rr_intervals > 333) & (rr_intervals < 1500)]
        
        if len(valid_rr) < 10:
            print("[CardioMetrics] Not enough valid RR intervals after filtering noise.")
            return None
            
        # Instantaneous Heart Rate
        hr_array = 60000.0 / valid_rr
        
        # Metrics
        avg_hr = np.mean(hr_array)
        
        # For Min/Max, use percentiles to avoid extreme noise spikes
        min_hr = np.percentile(hr_array, 1)
        max_hr = np.percentile(hr_array, 99)
        
        # HRV: RMSSD (Root Mean Square of Successive Differences)
        successive_diffs = np.diff(valid_rr)
        rmssd = np.sqrt(np.mean(successive_diffs**2))
        
        stats = {
            "avg_hr": float(avg_hr),
            "min_hr": float(min_hr),
            "max_hr": float(max_hr),
            "rmssd": float(rmssd)
        }
        print(f"[CardioMetrics] Success: {stats}")
        return stats
        
    except Exception as e:
        print(f"[CardioMetrics] Extraction failed: {e}")
        return None

def validate_and_merge_cv_stats(wpat_stats: dict | None, edf_stats: dict | None) -> dict | None:
    """
    Cross-validates and merges Heart Rate metrics from WatchPAT and EDF.
    wpat_stats is expected to have: {'avg': float, 'min': float|None, 'max': float}
    edf_stats is expected to have: {'avg_hr': float, 'min_hr': float, 'max_hr': float, 'rmssd': float}
    """
    if not wpat_stats and not edf_stats:
        return None
        
    if not wpat_stats:
        return edf_stats # Only have EDF
        
    # We have WatchPAT. We will use it as the base because PPG is reliable for base HR.
    merged = {
        "avg_hr": wpat_stats["avg"],
        "min_hr": wpat_stats["min"] if wpat_stats.get("min") is not None else "N/A",
        "max_hr": wpat_stats["max"],
        "rmssd": "N/A" # Default if EDF is invalid
    }
    
    if edf_stats:
        # Plausibility check for EDF
        edf_avg = edf_stats["avg_hr"]
        wpat_avg = wpat_stats["avg"]
        
        # If EDF avg is way off from WatchPAT (> 15 bpm diff) or insanely high, it's noise
        if abs(edf_avg - wpat_avg) > 15.0 or edf_avg > 120.0:
            print(f"[CardioMetrics] EDF HR ({edf_avg:.1f}) deviates significantly from WatchPAT ({wpat_avg:.1f}). Discarding EDF HRV.")
        else:
            merged["rmssd"] = edf_stats["rmssd"]
            # Fill N/A minimum HR if EDF is deemed reliable
            if merged["min_hr"] == "N/A" and edf_stats.get("min_hr"):
                merged["min_hr"] = edf_stats["min_hr"]
                print(f"[CardioMetrics] Filled missing WatchPAT Min HR with EDF Min HR: {merged['min_hr']:.1f}")
                
    return merged

if __name__ == "__main__":
    pass
