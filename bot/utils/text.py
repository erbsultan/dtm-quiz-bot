def split_long_message(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n\n", 0, limit)
        if split_at == -1:
            split_at = remaining.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit

        chunk = remaining[:split_at].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at:].strip()

    if remaining:
        chunks.append(remaining)
    return chunks


def safe_join_sections(sections: list[str], limit: int = 3900) -> list[str]:
    messages: list[str] = []
    current = ""

    for section in [section.strip() for section in sections if section and section.strip()]:
        candidate = f"{current}\n\n{section}".strip() if current else section
        if len(candidate) <= limit:
            current = candidate
            continue

        if current:
            messages.append(current)
        split_sections = split_long_message(section, limit=limit)
        messages.extend(split_sections[:-1])
        current = split_sections[-1] if split_sections else ""

    if current:
        messages.append(current)
    return messages
