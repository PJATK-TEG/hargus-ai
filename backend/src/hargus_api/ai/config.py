"""Analysis configuration: prompts and tuning knobs for the AI pipeline.

Override any value via a YAML file at backend/src/hargus_api/analysis_config.yml,
or the HARGUS_ANALYSIS_PROMPT environment variable.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Default analysis coordinator prompt
# ---------------------------------------------------------------------------

DEFAULT_ANALYSIS_PROMPT = """\
You are a senior technical recruiter performing a comprehensive candidate evaluation.

Analyse the candidate's full profile and produce a structured assessment that covers:
1. Technical skill coverage against the job requirements — name matched and missing skills explicitly.
2. Depth and relevance of professional experience relative to the seniority level required.
3. Communication quality and behavioural signals from any interview transcripts.
4. Inconsistencies, employment gaps, or risk factors detected across all documents.
5. An overall recommendation (strong_match | possible | weak | manual_review) with
   clear, evidence-based rationale.

Be specific and objective. Cite the source document for every claim. Do not infer
facts that are not present in the documents.
"""

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent.parent / "analysis_config.yml"


@lru_cache(maxsize=1)
def _load_yaml_config() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        with _CONFIG_PATH.open() as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def get_analysis_prompt() -> str:
    """Return the analysis coordinator prompt.

    Resolution order:
      1. YAML file analysis.prompt
      2. HARGUS_ANALYSIS_PROMPT environment variable
      3. DEFAULT_ANALYSIS_PROMPT
    """
    cfg = _load_yaml_config()
    return (
        cfg.get("analysis", {}).get("prompt", "")
        or os.environ.get("HARGUS_ANALYSIS_PROMPT", "")
        or DEFAULT_ANALYSIS_PROMPT
    ).strip()


def get_rag_k() -> int:
    """Number of pgvector chunks to retrieve for RAG context."""
    cfg = _load_yaml_config()
    return int(cfg.get("analysis", {}).get("rag_k", 5))


def get_chunk_size() -> int:
    cfg = _load_yaml_config()
    return int(cfg.get("analysis", {}).get("chunk_size", 512))


def get_chunk_overlap() -> int:
    cfg = _load_yaml_config()
    return int(cfg.get("analysis", {}).get("chunk_overlap", 64))
