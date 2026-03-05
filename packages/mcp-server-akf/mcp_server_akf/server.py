"""MCP server implementation for AKF — Agent Knowledge Format.

Exposes 4 tools via Model Context Protocol:
  - create_claim: Create AKF trust metadata
  - validate_file: Validate an .akf file
  - scan_file: Security scan any file
  - trust_score: Compute effective trust score
"""

from __future__ import annotations

import asyncio
import json
import sys

import akf
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def create_claim(content: str, confidence: float, source: str | None = None, ai_generated: bool = True) -> dict:
    """Create an AKF claim and return as JSON."""
    unit = akf.create(
        content,
        confidence=confidence,
        source=source or "mcp-tool",
        ai_generated=ai_generated,
    )
    return unit.to_dict()


def validate_file(path: str) -> dict:
    """Validate an .akf file."""
    result = akf.validate(path)
    return {
        "valid": result.valid,
        "level": result.level,
        "errors": result.errors,
        "warnings": result.warnings,
    }


def scan_file(path: str) -> dict:
    """Security scan any file for AKF metadata."""
    from akf import universal
    report = universal.scan(path)
    return {
        "enriched": report.enriched,
        "format": report.format,
        "claim_count": report.claim_count,
        "classification": report.classification,
        "overall_trust": report.overall_trust,
        "ai_contribution": report.ai_contribution,
    }


def trust_score(content: str, confidence: float, authority_tier: int = 3) -> dict:
    """Compute effective trust score for a claim."""
    from akf.models import Claim
    from akf.trust import effective_trust

    claim = Claim(content=content, confidence=confidence, authority_tier=authority_tier)
    result = effective_trust(claim)
    return {
        "score": result.score,
        "decision": result.decision,
        "breakdown": result.breakdown,
    }


# ---------------------------------------------------------------------------
# MCP tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="create_claim",
        description="Create an AKF claim with trust metadata. Returns a JSON object with the claim, trust score, and provenance.",
        inputSchema={
            "type": "object",
            "required": ["content", "confidence"],
            "properties": {
                "content": {"type": "string", "description": "The factual claim to create"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Trust score 0.0-1.0"},
                "source": {"type": "string", "description": "Information source (e.g., 'SEC 10-Q')"},
                "ai_generated": {"type": "boolean", "default": True, "description": "Whether this claim is AI-generated"},
            },
        },
    ),
    Tool(
        name="validate_file",
        description="Validate an .akf file against the AKF specification. Returns validity status, validation level (0-3), errors, and warnings.",
        inputSchema={
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "Path to the .akf file to validate"},
            },
        },
    ),
    Tool(
        name="scan_file",
        description="Security scan any file for AKF trust metadata. Works with .akf, .docx, .pdf, .html, .md, .json, images, and any format with a sidecar.",
        inputSchema={
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "Path to the file to scan"},
            },
        },
    ),
    Tool(
        name="trust_score",
        description="Compute the effective trust score for a claim using AKF's trust computation engine. Factors in confidence, authority tier, and temporal decay.",
        inputSchema={
            "type": "object",
            "required": ["content", "confidence"],
            "properties": {
                "content": {"type": "string", "description": "The claim to score"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Base confidence score"},
                "authority_tier": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3, "description": "Authority tier 1-5 (1=official records, 5=AI inference)"},
            },
        },
    ),
]

# Map tool names to handler functions
HANDLERS = {
    "create_claim": create_claim,
    "validate_file": validate_file,
    "scan_file": scan_file,
    "trust_score": trust_score,
}


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("akf")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        handler = HANDLERS.get(name)
        if not handler:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

        try:
            result = handler(**arguments)
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    return server


async def run_server():
    """Run the MCP server over stdio."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Entry point for the MCP server."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
