import sys
sys.path.insert(0, r"c:\Program Files\Python310\lib\site-packages")
from mne.io.egi.general import _get_blocks

mff_folder = r"D:\EPI_MFF\mff\V1\YS5_20220814_122851.mff"
try:
    signal_blocks = _get_blocks(mff_folder + r"\signal1.bin")
    n_blocks = signal_blocks["n_blocks"]
    n_samples = signal_blocks["samples_block"].sum()
    print(f"MNE read {n_blocks} blocks, total samples = {n_samples}")
except Exception as e:
    print(f"Error in _get_blocks: {e}")
