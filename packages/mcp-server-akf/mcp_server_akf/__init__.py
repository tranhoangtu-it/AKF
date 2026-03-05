"""MCP Server for AKF — Agent Knowledge Format.

Exposes AKF trust metadata operations via Model Context Protocol (MCP).
Compatible with Claude Desktop, Cursor, and any MCP-compatible client.

Tools:
    create_claim  — Create an AKF claim with trust metadata
    validate_file — Validate an .akf file against the spec
    scan_file     — Security scan any file for AKF metadata
    trust_score   — Compute effective trust score for a claim
"""

__version__ = "0.1.0"
