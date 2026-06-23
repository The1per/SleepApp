import os
os.environ['TF_USE_LEGACY_KERAS'] = '1'
import sys

sys.path.append(r'c:\Users\ynirmfa\Desktop\app\CAISR-App-main')
sys.path.append(r'c:\Users\ynirmfa\Desktop\app\CAISR-App-main\stage')

from ProductGraphSleepNet import build_ProductGraphSleepNet

print("Trying to build the CAISR stage model...")
try:
    model = build_ProductGraphSleepNet(
        k=3,
        num_of_chev_filters=128,
        num_of_time_filters=128,
        time_conv_strides=1,
        cheb_polynomials=None,
        time_conv_kernel=3,
        sample_shape=(7, 7, 9),
        num_block=1,
        opt='adam',
        useGL=True,
        GLalpha=0.0,
        regularizer=None,
        GRU_Cell=256,
        attn_heads=40,
        dropout=0.60
    )
    print("Model built successfully!")

    print("Trying to load weights...")
    model.load_weights(r'c:\Users\ynirmfa\Desktop\app\CAISR-App-main\stage\models\weights_fold_3.h5')
    print("Weights loaded successfully!")

except Exception as e:
    import traceback
    traceback.print_exc()
    print("Failed to build model or load weights.")
