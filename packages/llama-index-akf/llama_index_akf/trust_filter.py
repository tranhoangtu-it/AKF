"""AKF trust-based node filter for LlamaIndex."""
from __future__ import annotations

from typing import List, Optional

try:
    from llama_index.core.postprocessor.types import BaseNodePostprocessor
    from llama_index.core.schema import NodeWithScore, QueryBundle
except ImportError:
    raise ImportError("llama-index-core is required: pip install llama-index-core")


class AKFTrustFilter(BaseNodePostprocessor):
    """Filter retrieved nodes by AKF trust score.

    Nodes without akf_trust metadata are assigned a default score.
    """

    min_trust: float = 0.4
    default_trust: float = 0.5
    reject_unscored: bool = False

    class Config:
        arbitrary_types_allowed = True

    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        result: List[NodeWithScore] = []
        for node_with_score in nodes:
            metadata = node_with_score.node.metadata or {}
            trust = metadata.get("akf_trust")

            if trust is None:
                if self.reject_unscored:
                    continue
                trust = self.default_trust

            if trust >= self.min_trust:
                result.append(node_with_score)

        return result
