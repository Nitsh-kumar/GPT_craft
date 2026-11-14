import re
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.db.crud_memory import MemoryCRUD
from app.db.models import UserPreferences, UserMemory
from app.schemas.memory import MemoryCategory

STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "by", "of",
    "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did",
    "can", "could", "should", "would", "may", "might", "must", "it", "this", "that",
    "these", "those", "i", "you", "he", "she", "we", "they", "me", "him", "her", "us",
    "them", "what", "which", "who", "whom", "how", "when", "where", "why", "just", "so",
}

TECH_KEYWORDS = {
    "python", "javascript", "typescript", "react", "vite", "vue", "angular", "node",
    "fastapi", "django", "flask", "docker", "kubernetes", "postgres", "sqlite",
    "sql", "tailwind", "css", "html", "api", "database", "git", "github", "aws",
    "frontend", "backend", "fullstack", "architecture", "microservice", "testing",
}


class MemoryService:
    @staticmethod
    def get_preferences(db: Session, user_id: int) -> UserPreferences:
        return MemoryCRUD.get_or_create_preferences(db, user_id)

    @staticmethod
    def update_preferences(
        db: Session,
        user_id: int,
        profile: Optional[str] = None,
        style: Optional[str] = None,
        memory_enabled: Optional[bool] = None,
    ) -> UserPreferences:
        return MemoryCRUD.update_preferences(
            db=db,
            user_id=user_id,
            profile=profile,
            style=style,
            memory_enabled=memory_enabled,
        )

    @staticmethod
    def list_memories(db: Session, user_id: int) -> List[UserMemory]:
        return MemoryCRUD.get_user_memories(db, user_id, active_only=True)

    @staticmethod
    def add_memory(
        db: Session,
        user_id: int,
        content: str,
        category: MemoryCategory = "general",
        conversation_id: Optional[int] = None,
    ) -> UserMemory:
        return MemoryCRUD.create_memory(
            db=db,
            user_id=user_id,
            content=content,
            category=category,
            conversation_id=conversation_id,
        )

    @staticmethod
    def delete_memory(db: Session, user_id: int, memory_id: int) -> bool:
        return MemoryCRUD.delete_memory(db=db, user_id=user_id, memory_id=memory_id)

    @staticmethod
    def clear_all(db: Session, user_id: int) -> int:
        return MemoryCRUD.clear_all_memories(db=db, user_id=user_id)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        tokens = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower())
        return {t for t in tokens if t not in STOP_WORDS}

    @staticmethod
    def get_relevant_memories(
        db: Session,
        user_id: int,
        query_text: str,
        limit: int = 5,
    ) -> List[str]:
        """
        Query-aware relevance ranking for memories:
        Combines token overlap, category domain weighting, and recency decay.
        """
        prefs = MemoryCRUD.get_or_create_preferences(db, user_id)
        if not prefs.memory_enabled:
            return []

        all_memories = MemoryCRUD.get_user_memories(db, user_id, active_only=True)
        if not all_memories:
            return []

        query_tokens = MemoryService._tokenize(query_text)
        has_tech_query = bool(query_tokens & TECH_KEYWORDS)

        scored_memories = []
        for idx, mem in enumerate(all_memories):
            mem_tokens = MemoryService._tokenize(mem.content)
            overlap = len(query_tokens & mem_tokens)

            score = float(overlap * 3.0)
            if has_tech_query and mem.category in ("tech_stack", "project"):
                score += 2.0
            if mem.category == "preference":
                score += 1.0

            recency_bonus = max(0.0, 1.5 - (idx * 0.1))
            score += recency_bonus

            scored_memories.append((score, mem.content))

        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [content for _, content in scored_memories[:limit]]

    @staticmethod
    def extract_memories_from_text(text: str) -> List[Dict[str, str]]:
        """
        Heuristic pattern extractor detecting explicit 'remember that' commands
        and strong declarative preference statements in user chat messages.
        Stops at sentence boundaries to avoid capturing follow-up questions.
        """
        extracted: List[Dict[str, str]] = []
        normalized = text.strip()

        explicit_patterns: List[tuple[str, MemoryCategory]] = [
            (r"(?:please\s+)?remember\s+(?:that\s+)?([^.!?\n]+)", "preference"),
            (r"keep\s+in\s+mind\s+(?:that\s+)?([^.!?\n]+)", "preference"),
            (r"note\s+that\s+([^.!?\n]+)", "preference"),
            (r"don't\s+forget\s+(?:that\s+)?([^.!?\n]+)", "preference"),
        ]

        for pattern, default_cat in explicit_patterns:
            matches = re.finditer(pattern, normalized, re.IGNORECASE)
            for match in matches:
                fact = match.group(1).strip().rstrip(".!?,")
                if len(fact) >= 5:
                    cat: MemoryCategory = (
                        "tech_stack"
                        if any(k in fact.lower() for k in TECH_KEYWORDS)
                        else default_cat
                    )
                    if not any(
                        fact.lower() in e["content"].lower() or e["content"].lower() in fact.lower()
                        for e in extracted
                    ):
                        extracted.append({"content": fact, "category": cat})

        declarative_patterns: List[tuple[str, MemoryCategory]] = [
            (r"\b(i\s+prefer\s+[^.!?\n]+)", "preference"),
            (r"\b(my\s+(?:tech\s+)?stack\s+is\s+[^.!?\n]+)", "tech_stack"),
            (r"\b(i\s+(?:am|work\s+as)\s+(?:a|an)\s+[^.!?\n]+)", "tech_stack"),
            (r"\b(my\s+project\s+(?:name\s+)?is\s+[^.!?\n]+)", "project"),
            (r"\b(i\s+(?:am\s+building|build)\s+[^.!?\n]+)", "project"),
        ]

        for pattern, cat in declarative_patterns:
            matches = re.finditer(pattern, normalized, re.IGNORECASE)
            for match in matches:
                fact = match.group(1).strip().rstrip(".!?,")
                if len(fact) >= 8 and not any(
                    fact.lower() in e["content"].lower() or e["content"].lower() in fact.lower()
                    for e in extracted
                ):
                    extracted.append({"content": fact, "category": cat})

        return extracted

    @staticmethod
    def format_user_instructions(preferences: Optional[UserPreferences]) -> str:
        """
        Formats the user's custom instructions (profile & response style) if memory_enabled is True.
        """
        if not preferences or not preferences.memory_enabled:
            return ""

        sections = []
        if preferences.custom_instructions_profile and preferences.custom_instructions_profile.strip():
            sections.append(
                f"### What You Know About The User:\n{preferences.custom_instructions_profile.strip()}"
            )
        if preferences.custom_instructions_style and preferences.custom_instructions_style.strip():
            sections.append(
                f"### How The User Prefers Responses:\n{preferences.custom_instructions_style.strip()}"
            )
        return "\n\n".join(sections)

    @staticmethod
    def format_system_context(
        preferences: Optional[UserPreferences],
        relevant_memories: List[str],
    ) -> str:
        """
        Formats the complete Markdown personalization block combining user preferences and memories.
        """
        user_instructions = MemoryService.format_user_instructions(preferences)
        memories = relevant_memories if (not preferences or preferences.memory_enabled) else []
        if not user_instructions and not memories:
            return ""

        parts = ["\n\n---\n## User Personalization & Persistent Context"]
        if user_instructions:
            parts.append(user_instructions)
        if memories:
            memory_lines = "\n".join(f"- {m}" for m in memories)
            parts.append(f"### Relevant Long-Term Memories:\n{memory_lines}")
        parts.append(
            "### Behavioral Personalization Rules:\n"
            "- Tailor answers, tone, tech stack choices, and code structure to these preferences.\n"
            "- Do not explicitly state 'According to your memory...' or 'Since you told me...'; "
            "naturally apply this context as an intelligent partner."
        )
        return "\n\n".join(parts)

    @staticmethod
    def persist_extracted_memories(
        db: Session,
        user_id: int,
        message: str,
        conversation_id: int,
    ) -> None:
        """
        Post-turn memory extraction: persists candidate facts only when memory_enabled is True.
        """
        prefs = MemoryCRUD.get_or_create_preferences(db, user_id)
        if not prefs.memory_enabled:
            return

        extracted = MemoryService.extract_memories_from_text(message)
        for item in extracted:
            MemoryCRUD.create_memory(
                db=db,
                user_id=user_id,
                content=item["content"],
                category=item["category"],
                conversation_id=conversation_id,
            )
