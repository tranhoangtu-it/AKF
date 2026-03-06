"""AKF tools for CrewAI agents."""
from __future__ import annotations

from typing import Any, Optional, Type

try:
    from crewai.tools import BaseTool
except ImportError:
    raise ImportError("crewai is required: pip install crewai")

from pydantic import BaseModel, Field
import akf


class StampInput(BaseModel):
    content: str = Field(description="The content or claim to stamp with trust metadata")
    confidence: float = Field(default=0.8, description="Confidence score 0.0-1.0")
    source: Optional[str] = Field(default=None, description="Source of the claim")
    kind: Optional[str] = Field(default="claim", description="Kind: claim, code_change, decision, suggestion")


class AKFStampTool(BaseTool):
    name: str = "akf_stamp"
    description: str = "Stamp content with AKF trust metadata including confidence score, source, and provenance."
    args_schema: Type[BaseModel] = StampInput

    def _run(self, content: str, confidence: float = 0.8, source: Optional[str] = None, kind: Optional[str] = "claim") -> str:
        unit = akf.stamp(
            content,
            confidence=confidence,
            source=source,
            kind=kind,
            agent="crewai-agent",
        )
        return unit.to_json(compact=True)


class AuditInput(BaseModel):
    file_path: str = Field(description="Path to the file to audit")
    regulation: Optional[str] = Field(default=None, description="Regulation to check: eu_ai_act, hipaa, sox, gdpr")


class AKFAuditTool(BaseTool):
    name: str = "akf_audit"
    description: str = "Audit a file for AKF compliance against regulations like EU AI Act, HIPAA, SOX, GDPR."
    args_schema: Type[BaseModel] = AuditInput

    def _run(self, file_path: str, regulation: Optional[str] = None) -> str:
        if regulation:
            result = akf.check_regulation(file_path, regulation)
        else:
            result = akf.audit(file_path)

        lines = [f"Compliant: {result.compliant}", f"Score: {result.score:.0%}"]
        if result.recommendations:
            lines.append("Recommendations:")
            for rec in result.recommendations:
                lines.append(f"  - {rec}")
        return "\n".join(lines)


class ScanInput(BaseModel):
    file_path: str = Field(description="Path to the file or directory to scan for AKF metadata")


class AKFScanTool(BaseTool):
    name: str = "akf_scan"
    description: str = "Scan a file or directory for AKF trust metadata and return a summary report."
    args_schema: Type[BaseModel] = ScanInput

    def _run(self, file_path: str) -> str:
        report = akf.scan(file_path)
        lines = [
            f"Enriched: {report.enriched}",
            f"Format: {report.format}",
            f"Claims: {report.claim_count}",
            f"AI Claims: {report.ai_claim_count}",
            f"Trust: {report.overall_trust:.2f}",
            f"Classification: {report.classification or 'none'}",
        ]
        return "\n".join(lines)
