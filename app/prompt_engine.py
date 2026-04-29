def build_prompt(character, memories, user_input, template):
    memory_text = "\n".join([m.content for m in memories])
    return template.template.format(
        character_name=character.name,
        character_desc=character.description,
        memory=memory_text,
        user_input=user_input
    )
