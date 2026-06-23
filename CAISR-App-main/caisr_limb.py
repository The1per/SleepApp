import os, sys, glob, time, argparse
import numpy as np
import pandas as pd
from scipy import signal
from scipy.signal import resample_poly
from typing import List, Tuple

# ИСПРАВЛЕНИЕ ДЛЯ PYINSTALLER: Динамический путь к папке 'limb'
current_dir = os.path.dirname(os.path.abspath(__file__))
limb_utils_dir = os.path.join(current_dir, 'limb')
if limb_utils_dir not in sys.path:
    sys.path.insert(0, limb_utils_dir)

from utils_limb import *
from utils_docker import *


def timer(tag: str) -> None:
    """
    Displays a simple progress bar for the given tag, printing dots incrementally for aesthetics.
    """
    print(tag)
    for i in range(1, len(tag) + 1):
        print('.' * i + '     ', end='\r')
        time.sleep(1.5 / len(tag))  
    print()

def extract_run_parameters(param_csv: str) -> List[bool]:
    assert os.path.exists(param_csv), 'run parameter file is not found.'
    params = pd.read_csv(param_csv)
    overwrite = params['overwrite'].values[0]
    return overwrite

def set_output_paths(input_paths: List[str], csv_folder: str, overwrite: bool) -> Tuple[List[str], List[str]]:
    total = len(input_paths)
    IDs = [p.split('/')[-1].split('.')[0] for p in input_paths]
    # ПРИМЕЧАНИЕ: Скрипт ожидает, что csv_folder заканчивается на '/'
    csv_paths = [f'{csv_folder}limb/{ID}_limb.csv' for ID in IDs]
    assert len(input_paths) == len(csv_paths), 'SETUP ERROR: The number of input and CSV files is not equal.'
    input_paths, csv_paths = filter_already_processed_files(input_paths, csv_paths, overwrite)
    return input_paths, csv_paths

def filter_already_processed_files(input_paths: List[str], csv_paths: List[str], overwrite: bool) -> Tuple[List[str], List[str]]:
    total = len(input_paths)
    todo_indices = [p for p, path in enumerate(csv_paths) if not os.path.exists(path)]
    if not overwrite:
        input_paths, csv_paths = filter_todo_files(input_paths, csv_paths, todo_indices)
    tag = '(overwrite) ' if overwrite else ''
    print(f'>> {total - len(todo_indices)}/{total} files already processed\n>> {len(input_paths)} to go.. {tag}\n')
    return input_paths, csv_paths

def filter_todo_files(input_paths: List[str], csv_paths: List[str], keep_indices: List[int]) -> Tuple[List[str], List[str]]:
    input_paths = np.array(input_paths)[keep_indices].tolist()
    csv_paths = np.array(csv_paths)[keep_indices].tolist()
    return input_paths, csv_paths

def create_empty_ouput(path, EMGs, each_id, save_path):
    print(' - Creating empty limb movement file.')
    fs_input = 200 
    output_Hz = 1
    zeros_1hz = reshape_array(np.zeros(len(EMGs)), window_size=fs_input)[:,0].astype(int)
    ones_1hz = reshape_array(np.ones(len(EMGs)), window_size=fs_input)[:,0].astype(float)
    t1 = ((np.arange(len(zeros_1hz)))*fs_input).astype(int)
    t2 = ((np.arange(len(zeros_1hz))+1)*fs_input).astype(int)
    df = pd.DataFrame({'start_idx':t1,'end_idx':t2,'limb':zeros_1hz, 'plm': zeros_1hz, 'prob_no':ones_1hz,'prob_limb':zeros_1hz.astype(float)})
    df.to_csv(save_path, index=False)

def process_limb(in_paths, save_paths, overwrite):    
    for num, (path, save_path) in enumerate(zip(in_paths, save_paths)):
        each_id = path.split('/')[-1]
        the_id = each_id[:-3]
        tag = the_id if len(the_id)<21 else the_id[:20]+'..'
        print(f'(# {num + 1}/{len(in_paths)}) Processing "{tag}"')
        
        try:
            EMGs, Fs = select_signals_cohort(path)
            if np.all(EMGs==0):
                print(f'Both "lat" and "rat" are empty.')
                create_empty_ouput(path, EMGs, each_id, save_path)
                continue
            new_Fs = 100; 
            if new_Fs != Fs:   
                emg_signal = resample_poly(EMGs, new_Fs, Fs)
        except Exception as e:
            print(f'ERROR: "{the_id}".')
            create_empty_ouput(path, EMGs, each_id, save_path)
            continue
        
        signal_emg = np.array(emg_signal.T)
        signal_emg *= 1e6  
        sample_rate = 100
        fs = sample_rate

        emg_channels = signal_emg.shape[0] 

        dur_samples_below_count = int(np.ceil(0.05 * sample_rate))
        lower_threshold_uV = 2
        upper_threshold_uV = 10
        min_duration_sec = 1
        max_duration_sec = 10.0
        filter_hp_freq_Hz = 15
        sliding_window_len_sec = 0.5
        filter_order = 100
        merge_lm_within_sec = min_duration_sec

        filtered_data = []
        LM_line = []

        LM = []
        for ch in range(emg_channels):
            filtered_data.append(signal_emg[ch, :])
            order = filter_order
            w = filter_hp_freq_Hz
            n = order
            delay = int(n / 2)
            b = signal.firwin(n+1, w / (sample_rate / 2), pass_zero=False)
            LM_line = signal.lfilter(b, 1, filtered_data[ch], axis=0)
            LM_line = np.concatenate((np.abs(LM_line[delay:]), np.zeros(delay)))
            LM_above_thresh_high = np.where(LM_line >= upper_threshold_uV)[0]
            window_len = int(sliding_window_len_sec * sample_rate)
            max_dur = int(max_duration_sec * sample_rate)
            data_length = len(LM_line)

            LM_above_thresh_high = LM_above_thresh_high[LM_above_thresh_high < data_length - max_dur - 1]
            LM_below_thresh_low = LM_above_thresh_high.copy()
            ma_b = np.ones(window_len) / window_len
            ma_a = 1
            avg_LM_line = signal.lfilter(ma_b, ma_a, LM_line)

            if len(LM_above_thresh_high) == 0:
                detectStruct = {
                    'new_events_LAT': [],
                    'new_data_LAT': LM_line,
                    'AUC_LAT': [],
                }
                LM_candidates_valid = np.zeros((0, 2), dtype=int)
            else:
                start = LM_above_thresh_high[0] + 1
                cand = np.where(avg_LM_line[start:start + max_dur] < lower_threshold_uV)[0]
                if len(cand) > 0:
                    LM_below_thresh_low[0] = start + cand[0] + 1
                last_crossed_index = LM_below_thresh_low[0]

                for k in range(1, len(LM_above_thresh_high)): 
                    start = LM_above_thresh_high[k] + 1
                    if start > last_crossed_index:
                        cand = np.where(avg_LM_line[start:start + max_dur] < lower_threshold_uV)[0]
                        if len(cand) > 0:
                            LM_below_thresh_low[k] = start + cand[0] + 1
                            last_crossed_index = LM_below_thresh_low[k]

                LM_candidates = np.column_stack((LM_above_thresh_high, LM_below_thresh_low))
                LM_candidates = np.array(LM_candidates.tolist())
                LM_dur_range = np.ceil(np.array([min_duration_sec, max_duration_sec]) * sample_rate)
                lm_dur = LM_candidates[:, 1] - LM_candidates[:, 0]
                valid_indices = np.where((lm_dur >= LM_dur_range[0]) & (lm_dur <= LM_dur_range[1]))[0]
                LM_candidates = LM_candidates[valid_indices]

                min_samples = int(round(merge_lm_within_sec * sample_rate))

                if min_samples > 0:
                    LM_candidates = merge_nearby_events(LM_candidates, min_samples)

                LM_candidates = LM_candidates[0]
                LM_2 = LM_candidates
                duration = LM_2[:, 1] - LM_2[:, 0]
                duration = duration + 1

                AUC = np.zeros(duration.shape)
                for k in range(len(AUC)):
                    AUC[k] = np.sum(LM_line[LM_2[k, 0]:LM_2[k, 1]]) / duration[k]
                if ch == 0:
                    lm_LAT = LM_candidates

                LM_candidates_valid = lm_LAT
                LM_candidates_valid = np.sort(LM_candidates_valid, axis=0)
            min_samples = int(round(merge_lm_within_sec * sample_rate))
            LM_candidates_valid = merge_nearby_events(LM_candidates_valid, min_samples)
            LM_candidates_valid = LM_candidates_valid[0]  
                    
            PLM_min_interval_sec = 5
            PLM_max_interval_sec = 90
            PLM_min_LM_req = 4
            merge_LM_within_sec = 0.5

            PLM_offset2onset_min_dur_sec = 10
            PLM_offset2onset_max_dur_sec = 90

            LM_evts = LM_candidates_valid
            if len(LM_evts) > 1:
                PLM_candidates = np.zeros(len(LM_evts), dtype=bool)
                PLM_series = np.zeros(len(PLM_candidates), dtype=int)
                meet_interval2_duration_criteria = np.zeros(len(LM_evts), dtype=bool)

                interval1 = np.diff(LM_evts[:, 0])
                interval2 = LM_evts[1:, 0] - LM_evts[:-1, 1]

                PLM_onset2onset_range = [PLM_min_interval_sec, PLM_max_interval_sec]
                PLM_onset2onset_range = [x * sample_rate for x in PLM_onset2onset_range]
                LM_interval_candidates = (interval1 >= PLM_onset2onset_range[0]) & (interval1 <= PLM_onset2onset_range[1])

                PLM_offset2onset_range = [PLM_offset2onset_min_dur_sec, PLM_offset2onset_max_dur_sec] 
                PLM_offset2onset_range = [x * sample_rate for x in PLM_offset2onset_range]

                PLM_min_LM_intervals = PLM_min_LM_req - 1

                in_PLM_series_flag = False
                num_series = 0

                for k in range(len(interval1) - PLM_min_LM_intervals + 1):
                    if np.all(LM_interval_candidates[k : k+PLM_min_LM_intervals] == True):
                        if not in_PLM_series_flag:
                            num_series += 1
                            in_PLM_series_flag = True

                        PLM_candidates[k : k + PLM_min_LM_intervals + 1] = True
                        PLM_series[k : k + PLM_min_LM_intervals + 1] = num_series

                        if np.all((interval2[k : k + PLM_min_LM_intervals] >= PLM_offset2onset_range[0]) &
                            (interval2[k : k + PLM_min_LM_intervals] <= PLM_offset2onset_range[1])):
                                meet_interval2_duration_criteria[k : k + PLM_min_LM_intervals] = True
                    else:
                        in_PLM_series_flag = False
                
                PLM_candidates[-1] = False
                PLM_events = LM_evts[PLM_candidates]
                PLM_series = PLM_series[PLM_candidates]
                meets_interval2_duration_criteria = meet_interval2_duration_criteria[PLM_candidates]

                interval1_sec = interval1[PLM_candidates[:-1]]
                interval2_sec = interval2[PLM_candidates[:-1]]
                plm_duration = PLM_events[:, 1] - PLM_events[:, 0]
                plm_duration = plm_duration + 1
                new_events = PLM_events
            else:
                paramStruct = {}
                new_events = []

            detectStruct = {
            'LM_candidates': LM_candidates_valid,
            'PLM_events': new_events
            }

            LM_ferri = np.zeros(EMGs.shape[0])
            for lm_num in range(0,len(LM_candidates_valid)):
                start = LM_candidates_valid[lm_num, 0]
                end = LM_candidates_valid[lm_num, 1]
                LM_ferri[start-1:end-1] = 1

            PLM_ferri = np.zeros(EMGs.shape[0])
            for lm_num in range(0,len(new_events)):
                start = new_events[lm_num, 0]
                end = new_events[lm_num, 1]
                PLM_ferri[start-1:end-1] = 1

            fs_input = 200 
            output_Hz = 1
            task = 'limb'
            LM_ferri_1Hz = reshape_array(LM_ferri, window_size=fs_input)
            PLM_ferri_1Hz = reshape_array(PLM_ferri, window_size=fs_input)
            
            majority_values_LM = (np.sum(LM_ferri_1Hz, axis=1) > fs_input//2).astype(int)
            majority_values_PLM = (np.sum(PLM_ferri_1Hz, axis=1) > fs_input//2).astype(int)

            num_classes = 2
            one_hot_labels = np.eye(num_classes)[majority_values_LM.flatten()]
            
            t1 = ((np.arange(len(majority_values_LM)))*fs_input).astype(int)
            t2 = ((np.arange(len(majority_values_LM))+1)*fs_input).astype(int)
            
            df = pd.DataFrame({'start_idx':t1,'end_idx':t2,'limb':majority_values_LM, 'plm': majority_values_PLM, 'prob_no':one_hot_labels[:,0],'prob_limb':one_hot_labels[:,1]})
            df.to_csv(save_path, index=False)


# НОВАЯ ФУНКЦИЯ ДЛЯ ПРЯМОГО ЗАПУСКА
def run_limb_detection(input_path: str, save_path: str):
    """
    Главная функция для запуска модуля ног напрямую, минуя subprocess.
    """
    # Добавляем слэши на конце, так как код внутри ожидает такой формат
    if not input_path.endswith('/') and not input_path.endswith('\\'):
        input_path += '/'
    if not save_path.endswith('/') and not save_path.endswith('\\'):
        save_path += '/'

    timer('* Starting "caisr_limb" (created by Samaneh Nasiri, PhD)')

    # Ищем файлы корректно через os.path.join
    search_pattern = os.path.join(input_path, '*.h5')
    input_files = glob.glob(search_pattern)
    
    param_file = os.path.join(input_path, 'run_parameters', 'limb.csv')
    overwrite = extract_run_parameters(param_file)

    in_paths, save_paths = set_output_paths(input_files, save_path, overwrite)
    process_limb(in_paths, save_paths, overwrite)    

    timer('* Finishing "caisr_limb"')

# Сохраняем старый консольный запуск для совместимости
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run CAISR limb movement detection.")
    parser.add_argument("--input_path", type=str, default='./data/', help="Path to the input data folder")
    parser.add_argument("--save_path", type=str, default='./caisr_output/intermediate/', help="Path to save the output features")
    args = parser.parse_args()

    run_limb_detection(args.input_path, args.save_path)