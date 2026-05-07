from __future__ import annotations

from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_aws import BedrockEmbeddings, ChatBedrock
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from hargus_api.config import get_settings


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    settings = get_settings()
    match settings.llm_provider:
        case "ollama":
            return ChatOllama(
                model=settings.llm_model,
                base_url=settings.ollama_base_url,
                temperature=settings.llm_temperature,
            )
        case "openai":
            return ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.openai_api_key,  # type: ignore[arg-type]
                temperature=settings.llm_temperature,
            )
        case "anthropic":
            return ChatAnthropic(
                model=settings.llm_model,
                api_key=settings.anthropic_api_key,  # type: ignore[arg-type]
            )
        case "bedrock":
            return ChatBedrock(
                model_id=settings.llm_model,
                region_name=settings.aws_region,
            )
        case _:
            raise ValueError(f"Unsupported LLM provider: {settings.llm_provider!r}")


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    settings = get_settings()
    match settings.embedding_provider:
        case "ollama":
            return OllamaEmbeddings(
                model=settings.embedding_model,
                base_url=settings.ollama_base_url,
            )
        case "openai":
            return OpenAIEmbeddings(
                model=settings.embedding_model,
                api_key=settings.openai_api_key,  # type: ignore[arg-type]
            )
        case "bedrock":
            return BedrockEmbeddings(
                model_id=settings.embedding_model,
                region_name=settings.aws_region,
            )
        case _:
            raise ValueError(
                f"Unsupported embedding provider: {settings.embedding_provider!r}"
            )
