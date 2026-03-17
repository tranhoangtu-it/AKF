# Changelog

## [1.1.0] - 2026-03-15

### Added

#### Zero-Touch Auto-Stamping
- **Background daemon**: `akf install` activates a file watcher that monitors directories and auto-stamps new/modified files
- **Shell hooks**: `eval "$(akf shell-hook)"` intercepts AI CLI tools (Claude, ChatGPT, Aider, Ollama, etc.) and stamps files they create or modify
- **Smart context detection**: automatically infers git author, download source (macOS xattr), project classification rules, and AI-generated flags
- **Content-based AI detection**: weighted text/code heuristic signals for identifying AI-generated content without tracking context
- **macOS creator app detection**: identifies files created by Claude, ChatGPT, Cursor via Spotlight metadata (`mdls`)
- **OS-native file monitoring**: kqueue on macOS for instant change detection, polling fallback for cross-platform
- **Project rules**: `.akf/config.json` with `fnmatch` patterns for automatic classification (e.g., `*/finance/*` → confidential)
- **Smart confidence scoring**: dynamic confidence adjustment based on evidence signals (+0.10 source, +0.05 git, -0.10 AI without source)
- **VS Code AI Monitor extension** (`editors/vscode/`): auto-stamps files edited by Copilot, Cursor, and other AI coding tools

#### CLI
- `akf doctor` — checks PATH, Python version, platform-specific fix instructions
- `akf quickstart` — one-command interactive demo (create → inspect → trust → security)
- `akf shell-hook` — outputs shell hook code for zsh/bash
- `akf watch` — watch directories and auto-stamp new/modified files
- `akf install` / `akf uninstall` — manage background watcher daemon

#### Extensions
- **Office Add-in**: 10 AI-specific detection classes (hallucination risk, knowledge laundering, classification downgrade, etc.)
- **Office Add-in**: Claim creation form with confidence slider, source attribution, and AI risk tagging
- **Office Add-in**: Detection tab in taskpane with severity badges and collapsible findings
- **Office Add-in**: `commands.html` for ribbon ExecuteFunction runtime
- **Office Add-in**: Compact format normalization (wire format → descriptive field names)
- **Google Workspace**: 10 AI-specific detection classes matching Office add-in
- **Google Workspace**: Claim creation form in sidebar
- **Google Workspace**: Detection tab in sidebar and Card Service
- **Google Workspace**: "Run Detections" menu item and card

#### Core
- v1.1 trust formula: origin weight, grounding bonus (+0.05 per evidence, max 0.15), review bonus
- Extended claim model: freshness, evidence, reasoning, origin, reviews, decay, fidelity, annotations
- Unit-level reviews support (`AKFMetadata.reviews`)

### Fixed
- XSS prevention: HTML escaping on all user-data rendered in Office taskpane and Google sidebar
- Trust formula upgraded from simplified `confidence × authority` to full v1.1 computation
- Detection 1 (AI without review): now checks unit-level reviews, not just claim-level
- Detection 6 (stale claims): uses freshness status (expired/stale/fresh) matching Python SDK
- Detection 10 (provenance gap): strict 1-based hop numbering
- Security classification hierarchy: replaced "secret" with "highly-confidential" to match Python SDK
- Error handling: try/catch around metadata read/write operations in Office taskpane

### Changed
- Website: Office Add-in and Google Workspace badges changed from "Coming Soon" to "Available"
- Google Workspace `addClaim()`: input validation (content required, confidence clamped to [0,1])
- Google Workspace `normalizeMetaGs()`: safe key iteration (collect first, then delete)

## [1.0.0] - 2026-03-04

### Added

#### Core
- AKF data model with claims, provenance, and classification
- Trust computation engine with authority tiers, temporal decay, and penalties
- Provenance chain tracking with SHA-256 integrity hashing
- Security classification hierarchy (public through restricted)
- Builder pattern for fluent AKF construction
- Transformer pattern for filtering and deriving units
- Preset templates for common document types
- Descriptive field names with backward-compatible compact aliases

#### Python SDK
- `akf.create()` and `akf.loads()` with secure defaults
- `akf.agent` module: consume, derive, generation_prompt, validate_output, response_schema, from_tool_call, to_context, detect
- `akf.compliance` module: audit, check_regulation (EU AI Act, SOX, HIPAA, GDPR, NIST AI), audit_trail, verify_human_oversight
- `akf.view` module: show, to_html, to_markdown, executive_summary
- `akf.data` module: load_dataset, quality_report, merge, filter_claims
- `akf.knowledge_base` module: KnowledgeBase class for persistent claim storage
- `akf.trust`: TrustLevel enum, explain_trust() human-readable breakdowns
- `akf.security`: security_score(), purview_signals(), detect_laundering()
- `akf.presets`: 9 built-in templates, register() for custom templates
- Universal format layer: embed/extract AKF into 12+ file formats
- CLI with create, validate, inspect, trust, consume, audit, kb, and more

#### TypeScript SDK
- Full AKF model with Zod validation
- Core create/load/validate functions
- Trust computation, provenance, security, transform modules
- Builder pattern

#### Specification
- AKF v1.0 specification document
- JSON Schema for validation
- Example .akf files
- LLM integration guide

#### Infrastructure
- Comprehensive test suite (497+ Python tests, TypeScript tests)
- CI/CD workflow
- Contributing guide and Code of Conduct
