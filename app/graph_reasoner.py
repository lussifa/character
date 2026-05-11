from dataclasses import dataclass


@dataclass
class InferredFact:
    source_id: str
    relation: str
    target_id: str
    confidence: float
    evidence: str


class GraphReasoner:
    RESCUE_RELATIONS = {"saved", "rescued", "protected", "救过", "救了", "拯救", "保护"}
    PARENT_RELATIONS = {"parent_of", "father_of", "mother_of", "父亲", "母亲"}
    HOSTILE_RELATIONS = {"enemy_of", "rival_of", "hostile_to", "敌对", "敌人", "仇敌", "宿敌"}
    AFFILIATION_RELATIONS = {"member_of", "belongs_to", "serves", "属于", "服务于", "效忠"}

    def __init__(self, graph_store):
        self.graph_store = graph_store

    def infer(self) -> list[InferredFact]:
        inferred = []
        relations = self.graph_store.graph.get("relations", [])

        for rel in relations:
            relation = rel.get("relation", "")
            src = rel.get("source_id")
            tgt = rel.get("target_id")
            confidence = float(rel.get("confidence", 0.7))

            if not src or not tgt:
                continue

            if relation in self.RESCUE_RELATIONS:
                inferred.append(InferredFact(
                    source_id=tgt,
                    relation="likely_trusts",
                    target_id=src,
                    confidence=min(1.0, confidence * 0.85),
                    evidence=f"Derived from {src} {relation} {tgt}",
                ))
                inferred.append(InferredFact(
                    source_id=tgt,
                    relation="may_feel_indebted_to",
                    target_id=src,
                    confidence=min(1.0, confidence * 0.75),
                    evidence=f"Derived from rescue relation: {src} {relation} {tgt}",
                ))

            if relation in self.PARENT_RELATIONS:
                inferred.append(InferredFact(
                    source_id=tgt,
                    relation="child_of",
                    target_id=src,
                    confidence=confidence,
                    evidence=f"Inverse of {src} {relation} {tgt}",
                ))

            if relation in self.HOSTILE_RELATIONS:
                inferred.append(InferredFact(
                    source_id=tgt,
                    relation=relation,
                    target_id=src,
                    confidence=confidence * 0.95,
                    evidence=f"Symmetric relation inferred from {src} {relation} {tgt}",
                ))

            if relation in self.AFFILIATION_RELATIONS:
                inferred.append(InferredFact(
                    source_id=src,
                    relation="affiliated_with",
                    target_id=tgt,
                    confidence=confidence * 0.9,
                    evidence=f"Affiliation inferred from {src} {relation} {tgt}",
                ))

        return self._dedupe(inferred)

    def apply(self):
        inferred = self.infer()
        for fact in inferred:
            self.graph_store.add_relation(
                source_id=fact.source_id,
                relation=fact.relation,
                target_id=fact.target_id,
                confidence=fact.confidence,
                evidence=fact.evidence,
            )
        return inferred

    def reasoning_context(self, limit=30):
        facts = self.infer()[:limit]
        entity_name = lambda eid: self.graph_store.graph.get("entities", {}).get(eid, {}).get("name", eid)
        lines = []
        for fact in facts:
            lines.append(
                f"- {entity_name(fact.source_id)} {fact.relation} {entity_name(fact.target_id)} "
                f"(confidence={fact.confidence:.2f})"
            )
        return "\n".join(lines)

    @staticmethod
    def _dedupe(facts: list[InferredFact]) -> list[InferredFact]:
        seen = set()
        result = []
        for fact in facts:
            key = (fact.source_id, fact.relation, fact.target_id)
            if key in seen:
                continue
            seen.add(key)
            result.append(fact)
        return result
