import math
import json

def simple_embedding(text: str):
    # 非ONNX版本：轻量词频向量（占位）
    words = text.lower().split()
    vec = {}
    for w in words:
        vec[w] = vec.get(w, 0) + 1
    return vec


def cosine_sim(a, b):
    common = set(a.keys()) & set(b.keys())
    dot = sum(a[w]*b[w] for w in common)
    na = math.sqrt(sum(v*v for v in a.values()))
    nb = math.sqrt(sum(v*v for v in b.values()))
    if na == 0 or nb == 0:
        return 0
    return dot / (na * nb)


def serialize(vec):
    return json.dumps(vec)


def deserialize(s):
    if not s:
        return {}
    return json.loads(s)
