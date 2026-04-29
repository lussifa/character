import os
from pathlib import Path

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer


class ONNXEmbedder:
    """Transformer ONNX embedding runtime.

    Expected model layout:

    models/embedding/
      model.onnx
      tokenizer.json / tokenizer_config.json / vocab files

    This class intentionally has no fallback. If the model or tokenizer is
    missing, startup should fail so memory quality is never silently degraded.
    """

    def __init__(self, model_dir: str | None = None, model_file: str | None = None):
        model_dir = model_dir or os.getenv("EMBEDDING_MODEL_DIR", "models/embedding")
        model_file = model_file or os.getenv("EMBEDDING_ONNX_FILE", "model.onnx")

        self.model_dir = Path(model_dir)
        self.model_path = self.model_dir / model_file

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"ONNX embedding model not found: {self.model_path}. "
                "Put a transformer embedding ONNX model in models/embedding/model.onnx."
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
        pooled = self._mean_pool(token_embeddings, attention_mask)[0]
        return self._normalize(pooled)

    @staticmethod
    def _mean_pool(token_embeddings: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
        mask = np.expand_dims(attention_mask, axis=-1).astype(np.float32)
        summed = np.sum(token_embeddings * mask, axis=1)
        counts = np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)
        return summed / counts

    @staticmethod
    def _normalize(vec: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vec)
        if norm == 0:
            raise RuntimeError("Embedding norm is zero; check the ONNX model output.")
        return (vec / norm).astype(np.float32)
