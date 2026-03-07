# Agent Knowledge Format (AKF)

## Getting Started Guide

**Start trusting your AI output in 60 seconds.**

AKF is the open metadata standard for AI trust. Install once — trust scores, evidence, and provenance embed natively into Office docs, PDFs, images, and code.

```bash
pip install akf          # Python SDK
npm install akf-format   # TypeScript SDK
```

---

## Pick Your Path

### 1. Knowledge Workers — Trust What You Read

**The problem:** "Is this report real, or did an AI hallucinate it?"

```bash
# Open any document and check trust
akf read quarterly-report.docx

# Trust: 0.92 | Model: GPT-4o | Reviewed: Yes
```

**The outcome:** See trust scores, model provenance, and human-review status for every document you open.

---

### 2. AI Agents & Pipelines — Ship Trusted Output

**The problem:** "Our agent pipeline ships content with zero provenance."

```python
from akf import stamp_file

stamp_file("output.pdf",
    confidence=0.95,
    model="gpt-4o",
    source="internal-kb")
```

**The outcome:** Every file your agent produces carries embedded trust metadata automatically.

---

### 3. Security & CISOs — Detect What Others Miss

**The problem:** "Traditional DLP can't catch AI-specific threats."

```bash
# Scan for 10 classes of AI content risk
akf scan --recursive ./shared-drive/

# 3 files flagged: unreviewed AI content
```

**The outcome:** Detect unreviewed AI content, trust degradation, and classification drift across your org.

---

### 4. Governance & Compliance — Prove It. Automatically.

**The problem:** "We can't prove AI transparency to regulators."

```bash
# Generate compliance report for EU AI Act
akf audit --framework eu-ai-act ./reports/

# 47 files audited, 100% compliant
```

**The outcome:** Machine-readable audit trails that satisfy EU AI Act, HIPAA, SOX, and GDPR requirements.

---

### 5. Developers — Build Trust Into Everything

**The problem:** "Adding trust metadata means weeks of custom infrastructure."

```typescript
import { normalize } from 'akf-format';

const stamp = normalize({
    c: 0.9,
    t: 'analysis',
    src: 'internal-kb',
    model: 'claude-4'
});
```

**The outcome:** `pip install` or `npm install`, then one function call. No infra, no API keys, no config.

---

## The Format — 15 Tokens. That's It.

### Without AKF

```markdown
# quarterly-report.md

Revenue grew 23% YoY...
Customer retention improved...

---
Who wrote this? AI or human?
How confident should I be?
What sources back this up?
```

### With AKF

```markdown
# quarterly-report.md

Revenue grew 23% YoY...
Customer retention improved...

---
confidence: 0.92
model: "gpt-4o"
source: "finance-db"
reviewed: true
```

### Trust Score Color Guide

| Score      | Meaning        | Action          |
|------------|----------------|-----------------|
| **0.7+**   | High trust     | Safe to use     |
| **0.4-0.7**| Needs review   | Verify sources  |
| **< 0.4**  | Low confidence | Do not publish  |

---

## Enterprise Ready

### Compliance Frameworks

| Framework    | Coverage                          |
|-------------|-----------------------------------|
| EU AI Act   | Transparency & human oversight     |
| HIPAA       | Healthcare AI audit trails         |
| SOX         | Financial AI controls              |
| GDPR        | Data provenance tracking           |
| ISO 42001   | AI management systems              |
| NIST AI RMF | Risk management framework          |

### 10 AI-Specific Security Detections

1. Unreviewed AI content
2. Trust score degradation
3. Classification drift
4. Provenance gaps
5. Model hallucination risk
6. Knowledge laundering
7. Excessive AI concentration
8. Missing human review
9. Tampered metadata
10. Confidence inflation

---

## CLI Quick Reference

| Command                              | Description                        |
|--------------------------------------|------------------------------------|
| `akf stamp <file>`                   | Add trust metadata to a file       |
| `akf read <file>`                    | Read trust metadata from a file    |
| `akf audit <path>`                   | Generate compliance audit report   |
| `akf audit --framework <name> <path>`| Audit against a specific framework |
| `akf scan <path>`                    | Scan for AI content risks          |
| `akf scan --recursive <path>`        | Recursive security scan            |
| `akf detect <file>`                  | Detect AI-specific threats         |

---

## Resources

- **GitHub:** [github.com/HMAKT99/AKF](https://github.com/HMAKT99/AKF)
- **npm:** [npmjs.com/package/akf-format](https://www.npmjs.com/package/akf-format)
- **Website:** [akf.dev](https://akf.dev)
- **Schema:** `spec/akf-v1.1.schema.json`
- **License:** MIT

---

*Agent Knowledge Format — EXIF for AI. Open standard. MIT Licensed.*
