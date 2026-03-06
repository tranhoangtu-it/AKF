import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
    console.log('AKF extension activated');

    // Register hover provider for .akf files
    const hoverProvider = vscode.languages.registerHoverProvider('akf', {
        provideHover(document, position) {
            const line = document.lineAt(position).text;

            // Trust score hover
            const trustMatch = line.match(/"(?:t|confidence)"\s*:\s*([\d.]+)/);
            if (trustMatch) {
                const score = parseFloat(trustMatch[1]);
                let level: string;
                if (score >= 0.7) level = 'ACCEPT - Acceptable for use';
                else if (score >= 0.4) level = 'LOW - Use with caution';
                else level = 'REJECT - Do not use without verification';
                return new vscode.Hover(`**Trust Score: ${score}**\n\n${level}`);
            }

            // Authority tier hover
            const tierMatch = line.match(/"(?:tier|authority_tier)"\s*:\s*(\d)/);
            if (tierMatch) {
                const tier = parseInt(tierMatch[1]);
                const descriptions: Record<number, string> = {
                    1: 'Primary source (SEC, court records)',
                    2: 'Professional analysis (audited reports)',
                    3: 'Standard reporting (news, press)',
                    4: 'Secondary analysis (AI synthesis)',
                    5: 'Unverified (social media, inference)',
                };
                return new vscode.Hover(`**Authority Tier ${tier}**\n\n${descriptions[tier] || 'Unknown tier'}`);
            }

            return undefined;
        }
    });

    // Register validate command
    const validateCmd = vscode.commands.registerCommand('akf.validate', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        try {
            const json = JSON.parse(editor.document.getText());
            const hasVersion = json.v || json.version;
            const hasClaims = Array.isArray(json.claims) && json.claims.length > 0;

            if (hasVersion && hasClaims) {
                vscode.window.showInformationMessage(
                    `Valid AKF: ${json.claims.length} claim(s)`
                );
            } else {
                vscode.window.showWarningMessage('Invalid AKF: missing version or claims');
            }
        } catch {
            vscode.window.showErrorMessage('Invalid JSON');
        }
    });

    // Register inspect command
    const inspectCmd = vscode.commands.registerCommand('akf.inspect', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        try {
            const json = JSON.parse(editor.document.getText());
            const claims = json.claims;
            if (!Array.isArray(claims) || claims.length === 0) {
                vscode.window.showWarningMessage('No claims found in this AKF file');
                return;
            }

            const lines: string[] = [];
            for (const claim of claims) {
                const content = claim.c || claim.content || '(no content)';
                const trust = claim.t ?? claim.confidence ?? '?';
                const src = claim.src || claim.source || 'unspecified';
                lines.push(`[${trust}] ${content} (source: ${src})`);
            }

            const channel = vscode.window.createOutputChannel('AKF Inspector');
            channel.clear();
            channel.appendLine(`AKF Inspect: ${claims.length} claim(s)\n`);
            for (const line of lines) {
                channel.appendLine(line);
            }
            channel.show();
        } catch {
            vscode.window.showErrorMessage('Invalid JSON');
        }
    });

    context.subscriptions.push(hoverProvider, validateCmd, inspectCmd);
}

export function deactivate() {}
