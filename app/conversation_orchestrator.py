from dataclasses import dataclass
from typing import Any

from .providers import call_model
from .speaker_scheduler import schedule_speakers, scheduler_context
from .memory_decider import decide_memory, decision_to_tier
from .memory_reviser import revise_memory
from .graph_reasoner import GraphReasoner
from .llm_graph_reasoner import infer_graph_with_llm, apply_llm_inferences, llm_reasoning_context
from .world_simulator import simulate_world_step, apply_simulation, simulation_context
from .unified_extractor import extract_structured_updates


@dataclass
class CharacterReply:
    character_id: str
    character_name: str
    text: str
    reason: str


@dataclass
class ConversationResult:
    replies: list[CharacterReply]
    scheduler: str
    cognitive_context: str
    world_simulation: str


async def orchestrate_conversation(
    user_input: str,
    embedder,
    scoped_memory,
    multi_store,
    graph_store,
    world_store,
    model_config=None,
    max_speakers: int = 2,
    auto_simulate_world: bool = True,
) -> ConversationResult:
    query_embedding = embedder.embed(user_input)

    turns = await schedule_speakers(
        user_input=user_input,
        multi_store=multi_store,
        world_store=world_store,
        graph_store=graph_store,
        model_config=model_config,
        max_speakers=max_speakers,
    )
    sched_ctx = scheduler_context(turns, multi_store)

    rule_reasoner = GraphReasoner(graph_store)
    rule_reasoner.apply()
    rule_context = rule_reasoner.reasoning_context()

    replies: list[CharacterReply] = []
    prior_replies: list[dict[str, str]] = []
    unified_reasons: list[str] = []
    extracted_signal_count = 0

    for turn in turns:
        char = multi_store.get_character(turn.character_id)
        if not char:
            continue

        state = char.get("state", {})
        location = state.get("location", "unknown")

        scoped = scoped_memory.search_for_character(
            turn.character_id,
            query_embedding,
            top_k_character=3,
            top_k_shared=1,
            top_k_world=1,
        )
        memory_text = "\n".join(f"[{m['scope']}] {m['text']}" for m in scoped) or "- None"

        char_context = multi_store.character_context(turn.character_id, visible_only=True)
        visible_world_context = world_store.context_for_character(
            character_id=turn.character_id,
            location=location,
            limit_events=8,
        )
        visible_graph_context = graph_store.context_for([turn.character_id, "user"], limit=10)
        prior_text = "\n".join(f"{r['name']}: {r['text']}" for r in prior_replies[-2:]) or "- None"

        prompt = f"""
You are participating in a persistent multi-character world simulation.

IMPORTANT KNOWLEDGE RULES:
- You only know your own memories.
- You only know events visible from your current location.
- You do NOT know private conversations between other NPCs.
- You do NOT know hidden world state unless someone told you.
- If you were not present, you should behave as not knowing.

Visible world context:
{visible_world_context}

Visible graph facts:
{visible_graph_context}

Relevant memories for current speaker:
{memory_text}

Current speaker profile:
{char_context}

Previous replies in this exchange:
{prior_text}

User input:
{user_input}

Reply only as the current speaker. Do not write for other characters.
Stay consistent with your own memories and visible information.
""".strip()

        system = (
            f"You are {char.get('name', turn.character_id)}. "
            "Stay in character. Never use information your character could not know."
        )

        text = await call_model(prompt, system=system, model_config=model_config)

        reply = CharacterReply(
            character_id=turn.character_id,
            character_name=char.get("name", turn.character_id),
            text=text,
            reason=turn.reason,
        )
        replies.append(reply)
        prior_replies.append({"id": turn.character_id, "name": reply.character_name, "text": text})

        decision = await decide_memory(user_input, text, model_config=model_config)
        if decision.action != "ignore":
            embedding = embedder.embed(decision.memory)
            store = scoped_memory.character_store(turn.character_id)
            conflict = store.find_conflict(embedding, threshold=0.90)
            if conflict:
                revision = await revise_memory(conflict["text"], decision.memory, model_config=model_config)
                if revision.action in {"replace", "merge"}:
                    conflict["text"] = revision.revised_memory
                    conflict["embedding"] = embedder.embed(revision.revised_memory).tolist()
                    conflict["importance"] = max(conflict.get("importance", 0.5), revision.importance)
                    store._rewrite()
                elif revision.action == "delete":
                    store.data = [m for m in store.data if m.get("memory_id") != conflict.get("memory_id")]
                    store._rewrite()
            else:
                scoped_memory.add_character_memory(
                    character_id=turn.character_id,
                    text=decision.memory,
                    embedding=embedding,
                    importance=decision.importance,
                    source="orchestrator_ai_decision",
                    tier=decision_to_tier(decision.action),
                )

        extraction = await extract_structured_updates(user_input, text, model_config=model_config)
        if extraction.reason:
            unified_reasons.append(extraction.reason)

        for entity in extraction.entities:
            if not isinstance(entity, dict):
                continue
            entity_id = str(entity.get("entity_id", "")).strip()
            if not entity_id:
                continue
            graph_store.upsert_entity(
                entity_id=entity_id,
                name=str(entity.get("name") or entity_id),
                entity_type=str(entity.get("type") or "unknown"),
                attributes=entity.get("attributes", {}) if isinstance(entity.get("attributes", {}), dict) else {},
            )
            extracted_signal_count += 1

        for relation in extraction.relations:
            if not isinstance(relation, dict):
                continue
            source_id = str(relation.get("source_id", "")).strip()
            target_id = str(relation.get("target_id", "")).strip()
            relation_name = str(relation.get("relation", "")).strip()
            if not source_id or not target_id or not relation_name:
                continue
            try:
                confidence = float(relation.get("confidence", 0.8))
            except Exception:
                confidence = 0.8
            graph_store.add_relation(
                source_id=source_id,
                relation=relation_name,
                target_id=target_id,
                confidence=max(0.0, min(1.0, confidence)),
                evidence=str(relation.get("evidence", ""))[:300],
            )
            extracted_signal_count += 1

        for update in extraction.state_updates:
            if not isinstance(update, dict):
                continue
            key = str(update.get("key", "")).strip()
            if not key:
                continue
            try:
                confidence = float(update.get("confidence", 0.8))
            except Exception:
                confidence = 0.8
            world_store.set_state(
                key=key,
                value=str(update.get("value", "")),
                confidence=max(0.0, min(1.0, confidence)),
                evidence=str(update.get("evidence", ""))[:300],
            )
            extracted_signal_count += 1

        for event in extraction.events:
            if not isinstance(event, dict):
                continue
            title = str(event.get("title", "")).strip()
            description = str(event.get("description", "")).strip()
            if not title or not description:
                continue
            try:
                confidence = float(event.get("confidence", 0.8))
            except Exception:
                confidence = 0.8
            world_store.add_event(
                title=title,
                description=description,
                participants=event.get("participants", []) if isinstance(event.get("participants", []), list) else [],
                location=str(event.get("location", "")),
                effects=event.get("effects", []) if isinstance(event.get("effects", []), list) else [],
                confidence=max(0.0, min(1.0, confidence)),
            )
            extracted_signal_count += 1

        visible_participants = [r["id"] for r in prior_replies]
        world_store.record_dialogue(
            participants=visible_participants,
            content=[{"speaker": reply.character_name, "text": text}],
            location=location,
            privacy="local",
            observable_by=visible_participants,
            title=f"Dialogue at {location}",
            memory_writes={turn.character_id: [decision.memory] if decision.action != "ignore" else []},
        )

        for listener_id in visible_participants:
            if listener_id == turn.character_id:
                continue
            heard_memory = f"{reply.character_name} said at {location}: {text}".strip()
            scoped_memory.add_character_memory(
                character_id=listener_id,
                text=heard_memory,
                embedding=embedder.embed(heard_memory),
                importance=0.62,
                source="conversation_heard",
                tier="short_term",
            )
            world_store.add_knowledge_transfer(
                from_character_id=turn.character_id,
                to_character_id=listener_id,
                fact=heard_memory,
                method="direct_talk",
            )

    llm_context = ""
    if extracted_signal_count > 0:
        llm_facts = await infer_graph_with_llm(graph_store, model_config=model_config, max_entities=40, max_relations=80)
        apply_llm_inferences(graph_store, llm_facts)
        llm_context = llm_reasoning_context(llm_facts, graph_store)

    sim_ctx = ""
    if auto_simulate_world and _should_run_world_simulation(user_input, extracted_signal_count):
        simulation = await simulate_world_step(world_store, graph_store, model_config=model_config)
        apply_simulation(world_store, simulation)
        sim_ctx = simulation_context(simulation)

    cognitive_context = "\n\n".join([
        "Speaker plan:",
        sched_ctx or "- None",
        "",
        "Rule-based inferred facts:",
        rule_context or "- None",
        "",
        "Unified extraction summary:",
        "\n".join(f"- {r}" for r in unified_reasons if r) or "- None",
        "",
        "LLM-inferred facts:",
        llm_context or "- Skipped",
        "",
        "World simulation:",
        sim_ctx or "- Skipped",
    ])

    return ConversationResult(
        replies=replies,
        scheduler=sched_ctx,
        cognitive_context=cognitive_context,
        world_simulation=sim_ctx,
    )


def _should_run_world_simulation(user_input: str, extracted_signal_count: int) -> bool:
    if extracted_signal_count <= 0:
        return False
    low = user_input.lower()
    triggers = [
        "然后", "接下来", "推进", "过了一会", "过一段时间", "下一步", "later", "next", "advance", "simulate",
    ]
    return any(token in low for token in triggers)
