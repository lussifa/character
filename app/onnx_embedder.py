import onnxruntime as ort
import numpy as np

class ONNXEmbedder:
    def __init__(self, model_path):
        self.session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        self.input_name = self.session.get_inputs()[0].name

    def embed(self, text: str):
        tokens = np.array([[ord(c) % 256 for c in text[:256]]], dtype=np.float32)
        output = self.session.run(None, {self.input_name: tokens})
        vec = output[0][0]
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
