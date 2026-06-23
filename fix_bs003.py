import os
import re
import numpy as np
from pathlib import Path

filepath = r'F:\My Drive\PD2_Clean\BS003_sleep_20260520_001323.mff'
eeg_file = 'signal1.bin' 
fname = os.path.join(filepath, eeg_file)

# 1. Get Exact Samples and sfreq from signal1.bin directly!
with open(fname, 'rb') as fid:
    # First block
    meta = np.fromfile(fid, dtype=np.dtype('i4'), count=1).item()
    header_size = np.fromfile(fid, dtype=np.dtype('i4'), count=1).item()
    block_size = np.fromfile(fid, dtype=np.dtype('i4'), count=1).item()
    nc = np.fromfile(fid, dtype=np.dtype('i4'), count=1).item()
    
    # Read sigoffset (nc elements)
    sigoffset = np.fromfile(fid, dtype=np.dtype('i4'), count=nc)
    # Read sigfreq (nc elements)
    sigfreq = np.fromfile(fid, dtype=np.dtype('i4'), count=nc)
    
    sfreq = sigfreq[0] >> 8
    print(f'sfreq from block header: {sfreq}')
    
    samples_per_block = int(block_size / 4 / nc)
    block_full_size = header_size + block_size
    
    fid.seek(0, 2)
    file_size = fid.tell()
    
    num_full_blocks = file_size // block_full_size
    remainder = file_size % block_full_size
    
    total_samples = num_full_blocks * samples_per_block
    
    if remainder > 0:
        # Seek to the last block
        last_block_offset = num_full_blocks * block_full_size
        fid.seek(last_block_offset)
        l_meta = np.fromfile(fid, dtype=np.dtype('i4'), count=1).item()
        if l_meta == 1:
            l_header_size = np.fromfile(fid, dtype=np.dtype('i4'), count=1).item()
            l_block_size = np.fromfile(fid, dtype=np.dtype('i4'), count=1).item()
            l_nc = np.fromfile(fid, dtype=np.dtype('i4'), count=1).item()
            if l_nc == nc:
                total_samples += int(l_block_size / 4 / l_nc)

print(f'Total exact samples: {total_samples}')

# 2. Get div from info.xml
import xml.etree.ElementTree as ET
info_filepath = os.path.join(filepath, 'info.xml')
info_xml = ET.parse(info_filepath).getroot()
record_time = info_xml.find('.//{http://www.egi.com/info_mff}recordTime').text

g = re.match(
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.(\d{6}(?:\d{3})?)[+-]\d{2}:\d{2}',
    record_time,
)
frac = g.groups()[0]
div = 1000 if len(frac) == 6 else 1000000

duration_us = int((total_samples / sfreq) * div)
print(f'Duration_us: {duration_us}')

last_block_idx = num_full_blocks + (1 if remainder > 0 else 0)

xml_str = f"""<?xml version="1.0" encoding="utf-8"?>
<epochs xmlns="http://www.egi.com/epochs_mff">
    <epoch>
        <beginTime>0</beginTime>
        <endTime>{duration_us}</endTime>
        <firstBlock>1</firstBlock>
        <lastBlock>{last_block_idx}</lastBlock>
    </epoch>
</epochs>
"""

epochs_path = os.path.join(filepath, 'epochs.xml')
with open(epochs_path, 'w', encoding='utf-8') as f:
    f.write(xml_str)
print(f'Successfully created {epochs_path}')
