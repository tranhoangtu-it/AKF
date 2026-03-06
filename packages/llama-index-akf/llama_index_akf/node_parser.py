"""AKF-aware node parser for LlamaIndex."""
from __future__ import annotations

from typing import Any, List, Optional, Sequence

try:
    from llama_index.core.node_parser import NodeParser
    from llama_index.core.schema import BaseNode, TextNode, Document
except ImportError:
    raise ImportError("llama-index-core is required: pip install llama-index-core")

import akf


class AKFNodeParser(NodeParser):
    """Parse documents and attach AKF trust metadata to resulting nodes.

    Extracts AKF metadata from document text or metadata, then propagates
    trust scores, sources, and classification to child nodes.
    """

    min_trust: float = 0.0
    default_trust: float = 0.5

    class Config:
        arbitrary_types_allowed = True

    def _parse_nodes(
        self,
        nodes: Sequence[BaseNode],
        show_progress: bool = False,
        **kwargs: Any,
    ) -> List[BaseNode]:
        result: List[BaseNode] = []
        for node in nodes:
            text = node.get_content()
            metadata = node.metadata or {}

            # Try to extract AKF metadata from node metadata
            akf_data = metadata.get("_akf") or metadata.get("akf")

            if akf_data:
                try:
                    if isinstance(akf_data, str):
                        unit = akf.from_json(akf_data)
                    elif isinstance(akf_data, dict):
                        unit = akf.load_dict(akf_data)
                    else:
                        unit = None
                except Exception:
                    unit = None
            else:
                # Try to detect AKF in the text itself
                try:
                    unit = akf.detect(text)
                except Exception:
                    unit = None

            if unit and unit.claims:
                for claim in unit.claims:
                    trust_result = akf.effective_trust(claim)
                    if trust_result.score < self.min_trust:
                        continue
                    child = TextNode(
                        text=claim.content or claim.c or "",
                        metadata={
                            **metadata,
                            "akf_trust": trust_result.score,
                            "akf_decision": trust_result.decision,
                            "akf_source": claim.source or claim.src or "",
                            "akf_tier": claim.authority_tier or claim.tier or 0,
                            "akf_ai": bool(claim.ai_generated if claim.ai_generated is not None else claim.ai),
                            "akf_classification": unit.label or "",
                        },
                    )
                    result.append(child)
            else:
                # No AKF metadata — pass through with default trust
                node.metadata = {
                    **metadata,
                    "akf_trust": self.default_trust,
                    "akf_decision": "LOW",
                }
                result.append(node)

        return result
