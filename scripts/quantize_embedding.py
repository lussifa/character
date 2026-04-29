from pathlib import Path
from onnxruntime.quantization import quantize_dynamic, QuantType

MODEL_DIR = Path('models/embedding')
FP32_MODEL = MODEL_DIR / 'model.onnx'
INT8_MODEL = MODEL_DIR / 'model-int8.onnx'

if not FP32_MODEL.exists():
    raise FileNotFoundError(f'Missing source ONNX model: {FP32_MODEL}')

quantize_dynamic(
    model_input=str(FP32_MODEL),
    model_output=str(INT8_MODEL),
    weight_type=QuantType.QInt8,
)

print(f'Wrote INT8 model: {INT8_MODEL}')
