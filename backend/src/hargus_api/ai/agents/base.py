from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


def _normalize_llm_json_slice(s: str) -> str:
    """Best-effort fixes for common model JSON mistakes (trailing commas)."""
    return _TRAILING_COMMA.sub(r"\1", s)


def stringify_llm_content(content: Any) -> str:
    """Turn AIMessage.content (str or OpenAI-style blocks) into plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if isinstance(block.get("text"), str):
                    parts.append(block["text"])
                elif isinstance(block.get("content"), str):
                    parts.append(block["content"])
                else:
                    parts.append(str(block))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def parse_llm_json(text: Any) -> Any:
    """Parse JSON from model output that may include fences, preamble, or trailing prose."""
    raw = stringify_llm_content(text)
    if not raw.strip():
        raise ValueError("empty LLM output")

    stripped = raw.strip()
    m = _JSON_FENCE.search(stripped)
    if m:
        stripped = m.group(1).strip()

    decoder = json.JSONDecoder()

    def _try_load(s: str) -> Any:
        s = _normalize_llm_json_slice(s)
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        for i, ch in enumerate(s):
            if ch in "{[":
                try:
                    return decoder.raw_decode(s[i:])[0]
                except json.JSONDecodeError:
                    continue
        raise json.JSONDecodeError("No JSON object or array found in model output", s, 0)

    return _try_load(stripped)


class LenientJsonOutputParser(BaseOutputParser):
    """Like JsonOutputParser but tolerates markdown fences and conversational wrappers."""

    def parse(self, text: Any) -> Any:
        return parse_llm_json(text)

    @property
    def _type(self) -> str:
        return "lenient_json"


def build_json_chain(llm: BaseChatModel, system_prompt: str, human_template: str):
    """Return a prompt | llm | json_parser chain.

    SystemMessage is used for the system prompt so LangChain does not try to
    parse JSON examples in the prompt as Python f-string template variables.
    HumanMessagePromptTemplate still supports {variable} substitution.
    """
    dated_prompt = system_prompt + f"\n\nToday's date: {date.today().isoformat()}"
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=dated_prompt),
            HumanMessagePromptTemplate.from_template(human_template),
        ]
    )
    return prompt | llm | LenientJsonOutputParser()


def truncate(text: str, max_chars: int = 8000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated for context limit]"
