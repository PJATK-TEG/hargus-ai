from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate


def build_json_chain(llm: BaseChatModel, system_prompt: str, human_template: str):
    """Return a prompt | llm | json_parser chain.

    SystemMessage is used for the system prompt so LangChain does not try to
    parse JSON examples in the prompt as Python f-string template variables.
    HumanMessagePromptTemplate still supports {variable} substitution.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            HumanMessagePromptTemplate.from_template(human_template),
        ]
    )
    return prompt | llm | JsonOutputParser()


def truncate(text: str, max_chars: int = 8000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated for context limit]"
