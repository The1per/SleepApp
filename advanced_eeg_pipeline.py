import mne
import numpy as np
import pandas as pd
import yasa
import warnings

def run_advanced_eeg_analysis(raw, hypno_1hz, sfreq):
    """
    Выполняет расширенный анализ ЭЭГ для детекции сонных веретен и медленных волн.
    Каналы жестко заданы для EGI-256.
    
    Сонные веретена (Центральные): E59 (C3), E183 (C4), VREF (Cz)
    Медленные волны (Лобные): E36 (F3), E224 (F4), E37 (Fz)
    """
    metrics = {}
    
    # 1. Сонные веретена (Spindles)
    spindle_channels = ['E183', 'E59', 'VREF']
    avail_spindle = [ch for ch in spindle_channels if ch in raw.ch_names]
    print(f"[ADV DEBUG] avail_spindle: {avail_spindle}")
    
    if avail_spindle:
        # Pre-fill with 0.0 so they are never empty in the CSV
        for ch in avail_spindle:
            metrics[f'Spindle_Density_{ch}'] = 0.0
            metrics[f'Spindle_Amp_{ch}'] = 0.0
            metrics[f'Spindle_Freq_{ch}'] = 0.0
            metrics[f'Spindle_Dur_{ch}'] = 0.0
            print(f"[ADV DEBUG] Pre-filled Spindle metrics for {ch} with 0.0")
            
        try:
            # yasa работает с микровольтами
            data_sp = raw.get_data(picks=avail_spindle) * 1e6  # to microvolts
            
            # Upsample hypnogram to match data size
            hypno_up = yasa.hypno_upsample_to_data(hypno=hypno_1hz, sf_hypno=1, data=data_sp, sf_data=sfreq)
            
            # yasa.spindles_detect принимает numpy array
            sp = yasa.spindles_detect(data_sp, sfreq, ch_names=avail_spindle, hypno=hypno_up)
            print(f"[ADV DEBUG] yasa.spindles_detect returned: {'None' if sp is None else 'SpindlesResults'}")
            if sp is not None:
                sp_summary = sp.summary(grp_chan=True)
                print(f"[ADV DEBUG] sp_summary columns: {sp_summary.columns.tolist()}")
                print(f"[ADV DEBUG] sp_summary index: {sp_summary.index.tolist()}")
                for ch in avail_spindle:
                    if ch in sp_summary.index:
                        metrics[f'Spindle_Density_{ch}'] = sp_summary.loc[ch, 'Density'] if 'Density' in sp_summary.columns else sp_summary.loc[ch, 'Count']
                        metrics[f'Spindle_Amp_{ch}'] = sp_summary.loc[ch, 'Amplitude'] if 'Amplitude' in sp_summary.columns else 0.0
                        metrics[f'Spindle_Freq_{ch}'] = sp_summary.loc[ch, 'Frequency'] if 'Frequency' in sp_summary.columns else 0.0
                        metrics[f'Spindle_Dur_{ch}'] = sp_summary.loc[ch, 'Duration'] if 'Duration' in sp_summary.columns else 0.0
                        print(f"[ADV DEBUG] Populated actual Spindle metrics for {ch}")
                    else:
                        print(f"[ADV DEBUG] Channel {ch} not in sp_summary.index")
        except Exception as e:
            print(f"[ADV DEBUG] Exception in Spindle detection: {e}")
            warnings.warn(f"Spindle detection failed: {e}")

    # 2. Медленные волны (Slow Waves)
    sw_channels = ['E224', 'E36', 'E37']
    avail_sw = [ch for ch in sw_channels if ch in raw.ch_names]
    print(f"[ADV DEBUG] avail_sw: {avail_sw}")
    
    if avail_sw:
        # Pre-fill with 0.0 so they are never empty in the CSV
        for ch in avail_sw:
            metrics[f'SW_Density_{ch}'] = 0.0
            metrics[f'SW_Amp_{ch}'] = 0.0
            metrics[f'SW_Freq_{ch}'] = 0.0
            metrics[f'SW_Slope_{ch}'] = 0.0
            print(f"[ADV DEBUG] Pre-filled SW metrics for {ch} with 0.0")
            
        try:
            data_sw = raw.get_data(picks=avail_sw) * 1e6
            
            # Upsample hypnogram to match data size
            hypno_up = yasa.hypno_upsample_to_data(hypno=hypno_1hz, sf_hypno=1, data=data_sw, sf_data=sfreq)
            
            # yasa.sw_detect
            sw = yasa.sw_detect(data_sw, sfreq, ch_names=avail_sw, hypno=hypno_up)
            print(f"[ADV DEBUG] yasa.sw_detect returned: {'None' if sw is None else 'SWResults'}")
            if sw is not None:
                sw_summary = sw.summary(grp_chan=True)
                print(f"[ADV DEBUG] sw_summary columns: {sw_summary.columns.tolist()}")
                print(f"[ADV DEBUG] sw_summary index: {sw_summary.index.tolist()}")
                for ch in avail_sw:
                    if ch in sw_summary.index:
                        metrics[f'SW_Density_{ch}'] = sw_summary.loc[ch, 'Density'] if 'Density' in sw_summary.columns else sw_summary.loc[ch, 'Count']
                        metrics[f'SW_Amp_{ch}'] = sw_summary.loc[ch, 'PTP'] if 'PTP' in sw_summary.columns else 0.0
                        metrics[f'SW_Freq_{ch}'] = sw_summary.loc[ch, 'Frequency'] if 'Frequency' in sw_summary.columns else 0.0
                        metrics[f'SW_Slope_{ch}'] = sw_summary.loc[ch, 'Slope'] if 'Slope' in sw_summary.columns else 0.0
                        print(f"[ADV DEBUG] Populated actual SW metrics for {ch}")
                    else:
                        print(f"[ADV DEBUG] Channel {ch} not in sw_summary.index")
        except Exception as e:
            print(f"[ADV DEBUG] Exception in Slow wave detection: {e}")
            warnings.warn(f"Slow wave detection failed: {e}")
            
    print(f"[ADV DEBUG] Returning metrics: {metrics}")
    return metrics
