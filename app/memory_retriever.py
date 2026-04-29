from .embeddings import simple_embedding, cosine_sim, deserialize


def retrieve_memories(user_input, memories, top_k=3):
    query_vec = simple_embedding(user_input)

    scored = []
    for m in memories:
        vec = deserialize(m.embedding_json)
        score = cosine_sim(query_vec, vec)
        scored.append((score, m))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [m for s, m in scored[:top_k] if s > 0]
