# AKF — Office Add-in

Trust metadata viewer, embedder, and auditor for Microsoft Word, Excel, and PowerPoint.

## Features

- **AKF ribbon tab** in Word, Excel, and PowerPoint
- **View Trust** — opens taskpane showing claims, trust scores, provenance, and audit results
- **Embed** — stamps default AKF metadata into the document via OOXML Custom XML
- **Audit** — runs 7 compliance checks and shows recommendations

## Development

```bash
cd extensions/office-addin
npm install
npm run dev       # starts webpack dev server on https://localhost:3000
```

For local development, use the `manifest-dev.xml` approach:

1. Copy `manifest.xml` and change URLs back to `https://localhost:3000/`
2. In Office: `Insert` → `My Add-ins` → `Upload My Add-in` → select the dev manifest

## Build for production

```bash
npm run build     # outputs to dist/
```

Deploy the `dist/` folder to `https://addin.akf.dev/` (or update `manifest.xml` URLs to match your hosting).

## Publish to AppSource

1. Build and deploy to a public HTTPS URL
2. Update `manifest.xml` URLs to match
3. Submit via [Partner Center](https://partner.microsoft.com/dashboard/office/overview)
4. See [Microsoft docs](https://learn.microsoft.com/en-us/office/dev/store/submit-to-appsource-via-partner-center) for the full process

## Architecture

- `src/shared/akf-core.ts` — trust scoring, audit logic, types
- `src/shared/office-xml.ts` — read/write AKF via OOXML Custom XML parts
- `src/shared/ui.ts` — DOM rendering (claims, provenance, audit views)
- `src/taskpane/taskpane.ts` — main taskpane with tabbed UI
- `src/commands/commands.ts` — ribbon button command handlers
