import xml.etree.ElementTree as ET
import re
import shutil
from pathlib import Path
from mne.io.egi.general import _get_blocks

def _recover_egi_epochs_xml(mff_path):
    """Recover or recreate a corrupted epochs.xml for EGI .mff files.

    This function parses the binary `signal1.bin` using MNE's internal `_get_blocks` 
    to calculate the exact number of blocks and samples. It then retrieves the time 
    divisor from `info.xml` and calculates the precise ``endTime`` in microseconds 
    to reconstruct a valid ``epochs.xml``.
    
    This is useful for recordings that were interrupted (e.g. power loss),
    or affected by PSG synchronization bugs, resulting in a mismatch between 
    binary size and XML metadata.

    Parameters
    ----------
    mff_path : str | Path
        The path to the .mff directory.
    """
    mff_path = Path(mff_path)
    signal_bin = mff_path / "signal1.bin"
    epochs_xml = mff_path / "epochs.xml"
    info_xml_path = mff_path / "info.xml"
    
    if not signal_bin.exists() or not info_xml_path.exists():
        raise FileNotFoundError(f"Missing essential MFF files in {mff_path}")

    # 1. Use MNE's built-in parser to get exact block and sample counts
    # This guarantees our new epochs.xml will perfectly match MNE's expectations
    signal_blocks = _get_blocks(str(signal_bin))
    total_samples = int(signal_blocks["samples_block"].sum())
    last_block_idx = int(signal_blocks["n_blocks"])
    sfreq = int(signal_blocks["sfreq"])

    # 2. Extract record time format from info.xml to determine fractional multiplier
    tree = ET.parse(info_xml_path)
    root = tree.getroot()
    record_time_elem = root.find(".//{http://www.egi.com/info_mff}recordTime")
    if record_time_elem is None:
        raise ValueError("Could not find <recordTime> in info.xml")
        
    record_time = record_time_elem.text
    match = re.match(r".*\.(\d{6}(?:\d{3})?)[+-]", record_time)
    if not match:
        raise ValueError(f"Unexpected recordTime format: {record_time}")
        
    frac = match.group(1)
    # Determine if microseconds (len 6) or nanoseconds (len 9)
    div = 1000 if len(frac) == 6 else 1000000

    # 3. Calculate exact duration in microseconds
    # endTime is expected in microseconds.
    duration_us = int((total_samples / sfreq) * (div * 1000))

    # 4. Backup existing corrupted epochs.xml (if it exists)
    if epochs_xml.exists():
        backup_epochs_xml = mff_path.parent / f"{mff_path.name}__epochs_corrupted.xml"
        if not backup_epochs_xml.exists():
            shutil.copy2(epochs_xml, backup_epochs_xml)

    # 5. Write the corrected epochs.xml
    xml_str = (
        f'<?xml version="1.0" encoding="utf-8"?>\n'
        f'<epochs xmlns="http://www.egi.com/epochs_mff">\n'
        f'    <epoch>\n'
        f'        <beginTime>0</beginTime>\n'
        f'        <endTime>{duration_us}</endTime>\n'
        f'        <firstBlock>1</firstBlock>\n'
        f'        <lastBlock>{last_block_idx}</lastBlock>\n'
        f'    </epoch>\n'
        f'</epochs>\n'
    )
    epochs_xml.write_text(xml_str, encoding="utf-8")
    print(f"Successfully created/recovered epochs.xml for {mff_path.name} with {total_samples} samples and {last_block_idx} blocks.")

def safe_read_raw_egi(mff_path, preload=False, verbose=None, **kwargs):
    import mne
    try:
        return mne.io.read_raw_egi(str(mff_path), preload=preload, verbose=verbose, **kwargs)
    except Exception as e:
        error_str = str(e).lower()
        if 'blocks' in error_str or 'epoch' in error_str or 'match' in error_str or isinstance(e, FileNotFoundError):
            print(f"Error reading {mff_path}: {e}. Attempting recovery of epochs.xml...")
            try:
                _recover_egi_epochs_xml(mff_path)
                return mne.io.read_raw_egi(str(mff_path), preload=preload, verbose=verbose, **kwargs)
            except Exception as e_recovery:
                print(f"Recovery failed for {mff_path}: {e_recovery}")
                raise e # raise original error if recovery fails or doesn't fix it
        else:
            raise

if __name__ == "__main__":
    # Example usage:
    mff_folder = r"D:\EPI_MFF\mff\V1\MH5_20231112_101819.mff"
    _recover_egi_epochs_xml(mff_folder)
