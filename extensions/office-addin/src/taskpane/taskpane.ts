import { AKFMetadata, audit, createDefaultMetadata } from "../shared/akf-core";
import { extractAKF, embedAKF } from "../shared/office-xml";
import {
  renderHeader,
  renderClaims,
  renderProvenance,
  renderAudit,
  renderEmpty,
} from "../shared/ui";

let currentMetadata: AKFMetadata | null = null;
let currentView = "overview";

Office.onReady(async () => {
  await loadMetadata();
  setupTabs();
});

async function loadMetadata(): Promise<void> {
  currentMetadata = await extractAKF();
  renderCurrentView();
}

function setupTabs(): void {
  document.querySelectorAll<HTMLButtonElement>(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".tab")
        .forEach((t) => t.classList.remove("active"));
      btn.classList.add("active");
      currentView = btn.dataset.view ?? "overview";
      renderCurrentView();
    });
  });
}

function renderCurrentView(): void {
  const content = document.getElementById("content");
  if (!content) return;

  if (!currentMetadata) {
    renderEmpty(content);
    const embedBtn = document.getElementById("embed-cta");
    if (embedBtn) {
      embedBtn.addEventListener("click", async () => {
        const meta = createDefaultMetadata();
        await embedAKF(meta);
        currentMetadata = meta;
        renderCurrentView();
      });
    }
    return;
  }

  switch (currentView) {
    case "overview":
      renderHeader(content, currentMetadata);
      break;
    case "claims":
      renderClaims(content, currentMetadata.claims);
      break;
    case "provenance":
      renderProvenance(content, currentMetadata);
      break;
    case "audit": {
      const result = audit(currentMetadata);
      renderAudit(content, result);
      break;
    }
  }
}
