import { createDefaultMetadata, audit } from "../shared/akf-core";
import { extractAKF, embedAKF } from "../shared/office-xml";

Office.onReady(() => {
  // Register command handlers
});

async function embedMetadata(event: Office.AddinCommands.Event): Promise<void> {
  try {
    let meta = await extractAKF();
    if (!meta) {
      meta = createDefaultMetadata();
    }
    await embedAKF(meta);
    event.completed({ allowEvent: true });
  } catch {
    event.completed({ allowEvent: false });
  }
}

async function auditMetadata(event: Office.AddinCommands.Event): Promise<void> {
  try {
    const meta = await extractAKF();
    if (!meta) {
      event.completed({ allowEvent: true });
      return;
    }
    const result = audit(meta);
    const status = result.compliant ? "COMPLIANT" : "NON-COMPLIANT";
    // Show notification via Office API
    if (Office.context.mailbox) {
      // Outlook context — skip
    }
    // In document context, the result is shown in the taskpane
    event.completed({ allowEvent: true });
  } catch {
    event.completed({ allowEvent: false });
  }
}

// Expose to Office runtime
(globalThis as Record<string, unknown>).embedMetadata = embedMetadata;
(globalThis as Record<string, unknown>).auditMetadata = auditMetadata;
