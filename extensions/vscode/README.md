# AKF — VS Code Extension

Syntax highlighting, validation, and hover info for `.akf` files (Agent Knowledge Format).

## Features

- Syntax highlighting for `.akf` files (trust scores, claims, provenance, classification)
- Hover info on trust scores (ACCEPT/LOW/REJECT) and authority tiers (1–5)
- **AKF: Validate Current File** — checks structure, version, and claims
- **AKF: Inspect Claims** — lists all claims with trust scores in the Output panel

## Install from source

```bash
cd extensions/vscode
npm install
npm run compile
npm run package    # creates akf-vscode-0.1.0.vsix
```

Then in VS Code: `Extensions` → `...` → `Install from VSIX...` → select the `.vsix` file.

## Publish to Marketplace

1. Create a publisher at https://marketplace.visualstudio.com/manage
2. Update `"publisher"` in `package.json` to match
3. Add an `icon.png` (128x128 min) to this directory
4. Run:

```bash
npx vsce login <publisher-name>
npm run publish
```

## Development

```bash
npm run watch    # recompile on changes
```

Press `F5` in VS Code to launch the Extension Development Host.
