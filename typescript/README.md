<p align="center">
  <img src="https://img.shields.io/npm/v/akf-format?style=flat-square&label=npm" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" />
  <img src="https://img.shields.io/badge/format-.akf-blue?style=flat-square" />
</p>

# AKF — Agent Knowledge Format (TypeScript SDK)

**The trust metadata standard for AI-generated content.** AKF is to AI output what EXIF is to photos — trust scores, source provenance, and security classification in ~15 tokens of JSON.

## Install

```bash
npm install akf-format
```

## Staying Up to Date

AKF is actively developed. To get the latest features and fixes:

```bash
# Check your current version
npm list akf-format

# Update to the latest version
npm update akf-format

# Or install a specific version
npm install akf-format@1.2.0
```

**Tip:** If your `package.json` has `"akf-format": "^1.0.0"`, running `npm update` will automatically pull the latest 1.x release. We follow [semantic versioning](https://semver.org/) — patch and minor updates are always backward-compatible.

### Release notifications

- **GitHub Releases** — Watch the [AKF repo](https://github.com/HMAKT99/AKF) and select "Releases only" to get notified of every new version
- **npm** — Run `npm outdated` in your project to check for available updates
- **Automated** — Use [Renovate](https://github.com/renovatebot/renovate) or [Dependabot](https://docs.github.com/en/code-security/dependabot) to get automatic PRs when new versions are published

## Quick Start

```typescript
import { createClaim, createKnowledgeUnit, validate } from 'akf-format';

// Create a trust-stamped claim
const claim = createClaim({
  content: 'Revenue was $4.2B, up 12% YoY',
  confidence: 0.98,
  source: 'SEC 10-Q filing',
  authority_tier: 1,
  verified: true,
});

// Bundle into a knowledge unit
const unit = createKnowledgeUnit({
  claims: [claim],
  author: 'analyst@acme.com',
  classification: 'confidential',
});

// Validate against the AKF schema
const result = validate(unit);
console.log(result.valid); // true
```

## Core API

### Claims

```typescript
import { createClaim } from 'akf-format';

const claim = createClaim({
  content: 'Customer satisfaction increased 15%',
  confidence: 0.85,
  source: 'Q1 Survey Results',
  authority_tier: 2,
  ai_generated: false,
});
```

### Knowledge Units

```typescript
import { createKnowledgeUnit } from 'akf-format';

const unit = createKnowledgeUnit({
  claims: [claim1, claim2],
  author: 'research-bot',
  classification: 'internal',  // public | internal | confidential
});
```

### Validation

```typescript
import { validate } from 'akf-format';

const result = validate(unit);
if (!result.valid) {
  console.error(result.errors);
}
```

### Trust Scoring

```typescript
import { computeTrust } from 'akf-format';

const score = computeTrust(claim);
// score >= 0.7 → ACCEPT
// score >= 0.4 → LOW
// score <  0.4 → REJECT
```

### Compliance Checking

```typescript
import { checkCompliance } from 'akf-format';

const result = checkCompliance(unit, 'eu_ai_act');
console.log(result.compliant);   // true/false
console.log(result.findings);     // detailed findings
```

## Format

AKF metadata is ~15 tokens of JSON:

```json
{
  "v": "1.0",
  "claims": [
    { "c": "Revenue was $4.2B", "t": 0.98, "src": "SEC 10-Q", "tier": 1, "ver": true }
  ]
}
```

Both compact (`c`, `t`, `src`) and descriptive (`content`, `confidence`, `source`) field names are supported.

## Versioning

This package follows [semantic versioning](https://semver.org/):

- **Patch** (1.2.x) — Bug fixes, no API changes
- **Minor** (1.x.0) — New features, backward-compatible
- **Major** (x.0.0) — Breaking changes (we'll provide a migration guide)

See [CHANGELOG.md](https://github.com/HMAKT99/AKF/blob/main/typescript/CHANGELOG.md) for what's new in each release.

## Full Documentation

- [AKF Specification](https://github.com/HMAKT99/AKF/blob/main/spec/akf-v1.0-spec.md)
- [JSON Schema](https://github.com/HMAKT99/AKF/blob/main/spec/akf-v1.1.schema.json)
- [Python SDK](https://github.com/HMAKT99/AKF) (`pip install akf`)
- [Website](https://akf.dev)

## License

MIT
