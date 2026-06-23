import os
os.environ['TF_USE_LEGACY_KERAS'] = '1'
import sys
if len(sys.argv) >= 2 and sys.argv[1] == '--caisr-stage-worker':
    try:
        import tensorflow
    except Exception:
        pass
