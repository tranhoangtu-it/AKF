# AKF Validate — GitHub Action

Validate `.akf` files in your repository. Fails the build if any file has invalid structure or untrusted claims.

## Usage

```yaml
- uses: HMAKT99/AKF/extensions/github-action@main
  with:
    paths: "**/*.akf"           # glob pattern (default: **/*.akf)
    fail-on-untrusted: true     # fail if any claim below threshold
    trust-threshold: "0.5"      # minimum trust score (default: 0.5)
    classification: ""          # required classification level (optional)
```

## Example workflow

```yaml
name: Validate AKF
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: HMAKT99/AKF/extensions/github-action@main
        with:
          fail-on-untrusted: true
          trust-threshold: "0.7"
```

## What it checks

- Valid JSON structure
- Required fields: `version`, `claims` array
- Trust scores in range 0–1
- Valid classification labels (public, internal, confidential, highly-confidential, restricted)
- AI-generated claims have risk descriptions (warning)
- Trust threshold enforcement (when `fail-on-untrusted` is enabled)

## Outputs

Uses GitHub Actions annotations (`::error`, `::warning`) so validation results appear inline on PRs.
