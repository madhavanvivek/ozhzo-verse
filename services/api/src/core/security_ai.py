import json
import re
from typing import Any, Dict, List, Optional, Union


# Dangerous system override patterns & injection tokens
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"forget\s+(all\s+)?(previous|prior|above)\s+(instructions|restrictions)?",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"system\s*prompt\s*override",
    r"system\s*override",
    r"you\s+are\s+now\s+(an?\s+)?(unrestricted|evil|dan|administrator|system)",
    r"###\s*system",
    r"<\s*\|\s*im_start\s*\|\s*>",
    r"<\s*\|\s*im_end\s*\|\s*>",
    r"\[\s*system\s*\]",
    r"\[\s*INST\s*\]",
    r"<\s*s\s*>",
    r"<\s*/\s*s\s*>",
    r"jailbreak",
]


COMPILED_INJECTION_REGEX = re.compile(
    "|".join(f"({p})" for p in PROMPT_INJECTION_PATTERNS),
    re.IGNORECASE,
)

MAX_PROMPT_LENGTH = 4000
MAX_ENTITY_STRING_LENGTH = 500


def sanitize_untrusted_input(text: Optional[str], max_length: int = MAX_ENTITY_STRING_LENGTH) -> str:
    """
    Sanitizes user-provided household strings (task titles, notes, bill names, item names, etc.)
    by stripping dangerous control characters, prompt injection delimiters, and enforcing length bounds.
    """
    if not text:
        return ""

    cleaned = str(text).strip()

    # 1. Enforce length boundary
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."

    # 2. Defang dangerous system prompt tokens
    cleaned = cleaned.replace("<|im_start|>", "[token_sanitized]")
    cleaned = cleaned.replace("<|im_end|>", "[token_sanitized]")
    cleaned = cleaned.replace("### System", "[system_marker_sanitized]")
    cleaned = cleaned.replace("### Human", "[human_marker_sanitized]")
    cleaned = cleaned.replace("### Assistant", "[assistant_marker_sanitized]")

    # 3. Neutralize explicit injection payloads
    cleaned = COMPILED_INJECTION_REGEX.sub("[sanitized_instruction]", cleaned)

    return cleaned


def demarcate_untrusted_content(domain: str, content: Any) -> str:
    """
    Encapsulates raw household data into explicit, non-executable data boundary tags.
    Instructs the AI model that enclosed data is passive context, NOT executable instructions.
    """
    if isinstance(content, (dict, list)):
        serialized = json.dumps(content, ensure_ascii=False, default=str)
    else:
        serialized = sanitize_untrusted_input(str(content))

    return (
        f'<untrusted_household_content domain="{domain}">\n'
        f"{serialized}\n"
        f"</untrusted_household_content>"
    )


def enforce_prompt_guardrails(prompt: str) -> str:
    """
    Enforces user query guardrails before model ingestion.
    """
    if not prompt or not prompt.strip():
        return ""

    cleaned = prompt.strip()
    if len(cleaned) > MAX_PROMPT_LENGTH:
        cleaned = cleaned[:MAX_PROMPT_LENGTH]

    # Neutralize structural injection markers in user query
    cleaned = cleaned.replace("<|im_start|>", "")
    cleaned = cleaned.replace("<|im_end|>", "")

    return cleaned
