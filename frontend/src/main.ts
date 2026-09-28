import "./style.css";
import { evaluate, getEvaluations, getRfq, getRfqs, type Evaluation, type Rfq } from "./api";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

const rfqSelect = $<HTMLSelectElement>("rfq-select");
const rfqDetails = $<HTMLDivElement>("rfq-details");
const fileInput = $<HTMLInputElement>("file-input");
const vendorText = $<HTMLTextAreaElement>("vendor-text");
const charCount = $<HTMLSpanElement>("char-count");
const evaluateBtn = $<HTMLButtonElement>("evaluate-btn");
const statusEl = $<HTMLSpanElement>("status");
const errorEl = $<HTMLParagraphElement>("error");
const resultEl = $<HTMLElement>("result");
const historyEl = $<HTMLDivElement>("history");

let busy = false;

// Everything from the vendor text or the model is escaped before it goes into innerHTML.
function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}

function scoreClass(score: number): string {
  return score >= 70 ? "good" : score >= 40 ? "mid" : "bad";
}

function showError(message: string | null): void {
  errorEl.hidden = !message;
  errorEl.textContent = message ?? "";
}

function updateButton(): void {
  evaluateBtn.disabled = busy || !rfqSelect.value || vendorText.value.trim() === "";
  charCount.textContent = `${vendorText.value.length.toLocaleString()} characters`;
}

// ---- RFQ picker ---------------------------------------------------------------------------

function renderRfq(rfq: Rfq): void {
  const list = (title: string, items: string[]) =>
    items.length ? `<div><h4>${title}</h4><ul>${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul></div>` : "";
  rfqDetails.innerHTML = `
    <p class="meta"><b>${esc(rfq.category)}</b> · Quantity: ${esc(rfq.quantity)} · Delivery: ${esc(rfq.delivery)}</p>
    <p class="meta">Material: ${esc(rfq.material)}</p>
    <div class="tiers">
      ${list("Mandatory", rfq.mandatory)}${list("Technical", rfq.technical)}
      ${list("Required", rfq.required)}${list("Preferred", rfq.preferred)}
    </div>`;
}

async function loadRfqs(): Promise<void> {
  const rfqs = await getRfqs();
  rfqSelect.innerHTML = rfqs.map((r) => `<option value="${esc(r.id)}">${esc(r.id)}: ${esc(r.title)}</option>`).join("");
  await onRfqChange();
}

async function onRfqChange(): Promise<void> {
  updateButton();
  if (rfqSelect.value) renderRfq(await getRfq(rfqSelect.value));
}

// ---- Result -------------------------------------------------------------------------------

const VERDICT_LABEL: Record<string, string> = {
  met: "Met",
  partial: "Partial",
  not_met: "Not met",
  not_evidenced: "Not evidenced",
  not_applicable: "N/A",
};

function renderResult(ev: Evaluation): void {
  const failedMandatory = ev.criteria.filter((c) => c.tier === "mandatory" && c.verdict !== "met");
  const findings = (items: Evaluation["reasons"]) =>
    items.map((f) => `<li><span class="tag">${esc(f.criterion_id)}</span> ${esc(f.text)}</li>`).join("");

  const tiers = Object.entries(ev.breakdown)
    .filter(([, t]) => t.max > 0)
    .map(([name, t]) => `
      <div class="tier">
        <span class="tier-name">${esc(name)}</span>
        <span class="bar"><span style="width:${(100 * t.points) / t.max}%"></span></span>
        <span class="tier-pts">${t.points} / ${t.max}</span>
      </div>`)
    .join("");

  const rows = ev.criteria
    .map((c) => `
      <tr>
        <td>${esc(c.id)}</td>
        <td>${esc(c.text)}</td>
        <td><span class="verdict v-${c.verdict}">${VERDICT_LABEL[c.verdict]}</span>${c.downgraded ? ' <span class="muted" title="Changed by the evidence check">⚠</span>' : ""}</td>
        <td class="evidence">${c.evidence ? `“${esc(c.evidence)}”` : '<span class="muted">(none)</span>'}<div class="muted small">${esc(c.rationale)}</div></td>
      </tr>`)
    .join("");

  resultEl.innerHTML = `
    <div class="result-head">
      <div class="score ${scoreClass(ev.score)}">${ev.score}<small>/100</small></div>
      <div>
        <h2>${esc(ev.vendor_name)}</h2>
        <p class="muted">${esc(ev.rfq_id)} · ${new Date(ev.created_at).toLocaleString()} · ${esc(ev.model)} · prompt ${esc(ev.prompt_version)}</p>
      </div>
    </div>
    ${ev.gate_passed ? "" : `
      <div class="gate">Mandatory requirement not met: ${failedMandatory.map((c) => esc(c.text)).join(", ")}.
      Score capped at 30 (would have been ${ev.raw_score}).</div>`}
    <div class="columns">
      <div><h3>Supporting reasons</h3><ol>${findings(ev.reasons)}</ol></div>
      <div><h3>Gaps</h3><ol>${findings(ev.gaps)}</ol></div>
    </div>
    <div class="tiers-score">${tiers}</div>
    <details>
      <summary>Per-requirement breakdown (${ev.criteria.length} lines)</summary>
      <table>
        <thead><tr><th>Id</th><th>Requirement</th><th>Verdict</th><th>Evidence from the profile</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </details>`;
  resultEl.hidden = false;
}

// ---- History ------------------------------------------------------------------------------

let history: Evaluation[] = [];

async function loadHistory(): Promise<void> {
  history = await getEvaluations();
  if (!history.length) {
    historyEl.innerHTML = '<p class="muted">No evaluations yet.</p>';
    return;
  }
  historyEl.innerHTML = `
    <table class="history">
      <thead><tr><th>When</th><th>RFQ</th><th>Vendor</th><th>Score</th><th>Mandatory</th></tr></thead>
      <tbody>${history
        .map((e) => `
          <tr data-id="${e.id}" title="Show this evaluation">
            <td>${new Date(e.created_at).toLocaleString()}</td>
            <td>${esc(e.rfq_id)}</td>
            <td>${esc(e.vendor_name)}</td>
            <td><span class="pill ${scoreClass(e.score)}">${e.score}</span></td>
            <td>${e.gate_passed ? "✓ met" : '<span class="bad-text">✗ not met</span>'}</td>
          </tr>`)
        .join("")}</tbody>
    </table>`;
}

historyEl.addEventListener("click", (event) => {
  const row = (event.target as HTMLElement).closest("tr[data-id]");
  const ev = row && history.find((e) => e.id === Number(row.getAttribute("data-id")));
  if (ev) {
    renderResult(ev);
    resultEl.scrollIntoView({ behavior: "smooth" });
  }
});

// ---- Wiring -------------------------------------------------------------------------------

rfqSelect.addEventListener("change", () => onRfqChange().catch((e) => showError(String(e))));
vendorText.addEventListener("input", updateButton);

fileInput.addEventListener("change", async () => {
  const file = fileInput.files?.[0];
  if (!file) return;
  vendorText.value = await file.text(); // uploaded text goes into the same textarea as pasted text
  updateButton();
});

evaluateBtn.addEventListener("click", async () => {
  busy = true;
  updateButton();
  showError(null);
  statusEl.textContent = "Evaluating… (one AI call, usually 10–20 s)";
  try {
    const ev = await evaluate(rfqSelect.value, vendorText.value);
    renderResult(ev);
    await loadHistory();
    resultEl.scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    showError(e instanceof Error ? e.message : String(e));
  } finally {
    busy = false;
    statusEl.textContent = "";
    updateButton();
  }
});

Promise.all([loadRfqs(), loadHistory()]).catch((e) => showError(`Could not reach the backend. ${e}`));
