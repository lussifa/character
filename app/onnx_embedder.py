import os
from pathlib import Path

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer


class ONNXEmbedder:
    def __init__(self, model_dir: str | None = None):
        model_dir = model_dir or os.getenv("EMBEDDING_MODEL_DIR", "models/embedding")
        self.model_dir = Path(model_dir)

        int8_model = self.model_dir / "model-int8.onnx"
        legacy_int8_model = self.model_dir / "model_int8.onnx"
        fp32_model = self.model_dir / "model.onnx"

        if int8_model.exists():
            self.model_path = int8_model
        elif legacy_int8_model.exists():
            self.model_path = legacy_int8_model
        elif fp32_model.exists():
            self.model_path = fp32_model
        else:
            raise FileNotFoundError(
                f"No ONNX model found in {self.model_dir}. Expected model-int8.onnx or model.onnx"
            )

        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir), local_files_only=True)
        self.session = ort.InferenceSession(str(self.model_path), providers=["CPUExecutionProvider"])
        self.input_names = {i.name for i in self.session.get_inputs()}

    def embed(self, text: str) -> np.ndarray:
        encoded = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=int(os.getenv("EMBEDDING_MAX_LENGTH", "512")),
            return_tensors="np",
        )

        ort_inputs = {}
        for name in self.input_names:
            if name in encoded:
                ort_inputs[name] = encoded[name].astype(np.int64)

        if "input_ids" not in ort_inputs:
            raise RuntimeError(f"ONNX model requires unsupported inputs: {self.input_names}")

        outputs = self.session.run(None, ort_inputs)
        token_embeddings = outputs[0]
        attention_mask = encoded["attention_mask"]

        mask = np.expand_dims(attention_mask, axis=-1).astype(np.float32)
        summed = np.sum(token_embeddings * mask, axis=1)
        counts = np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)
        pooled = summed / counts

        vec = pooled[0]
        norm = np.linalg.norm(vec)
        if norm == 0:
            raise RuntimeError("Embedding norm is zero")
        return (vec / norm).astype(np.float32)
