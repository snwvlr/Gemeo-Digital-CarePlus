// =========================================================
//  CarePlus · Painel do Médico
//  - Mostra o MESMO paciente do app (perfil + avatar + vitais ao vivo).
//  - URLs relativas: funciona servido pelo backend (python run.py -> :8000).
//  - Zero-Data Footprint: prescrição só em RAM do servidor + sessionStorage.
//  - Depende de assets/js/avatar.js (CareAvatar) e assets/js/shell.js (CareToast),
//    carregados antes deste arquivo.
// =========================================================

const API = "";  // mesma origem (servido pelo FastAPI)
const DOCTOR = "Dra. Helena Costa · CRM 123.456-SP";

let profile = null;
let twin = null;
let currentMood = "bem";
let currentDraft = null;     // { medications, guidance, return_criteria, allergy_note, text }
let lastProfileSig = "";
let notesTouched = false;
let latestRelatoText = "";

const $ = (id) => document.getElementById(id);
const MOOD_LABEL = { "ótimo": "ÓTIMO", "bem": "BEM", "atenção": "ATENÇÃO", "alerta": "ALERTA" };
const MOOD_COLOR = { "ótimo": "#10b981", "bem": "#1152d4", "atenção": "#f59e0b", "alerta": "#ef4444" };
const MOOD_CHIP  = { "ótimo": "chip-ok", "bem": "chip-muted", "atenção": "chip-warn", "alerta": "chip-bad" };

function initialsSvg(name) {
  const ini = (name || "P").trim().charAt(0).toUpperCase();
  return "data:image/svg+xml;utf8," + encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><rect width='100%' height='100%' rx='18' fill='#1e293b'/><text x='50%' y='55%' font-size='74' fill='#3b82f6' font-family='Inter,sans-serif' font-weight='800' text-anchor='middle' dominant-baseline='middle'>${ini}</text></svg>`);
}

// Avatar IDÊNTICO ao do paciente: mesma seed (nome), mesma config (localStorage) e
// mesma expressão (humor). CareAvatar vem de assets/js/avatar.js.
function renderAvatar() {
  const img = $("rx-avatar");
  const name = (profile && profile.name) || "Paciente";
  img.onerror = () => { img.onerror = null; img.src = initialsSvg(name); };
  if (window.CareAvatar) {
    img.src = CareAvatar.buildAvatarUrl(name, CareAvatar.loadAvatarConfig(), currentMood);
  } else {
    img.src = initialsSvg(name);
  }
}

function listOrDash(arr) { return (arr && arr.length) ? arr.join(", ") : "—"; }

function renderProfile(p) {
  const sig = JSON.stringify([p.name, p.age, p.sex, p.weight_kg, p.height_cm, p.allergies, p.conditions, p.medications, p.symptoms]);
  if (sig === lastProfileSig) return;   // evita re-render desnecessário (anti-flicker)
  lastProfileSig = sig;

  $("p-name").textContent = p.name || "Paciente";
  $("p-sub").textContent = `${p.age ?? "?"} anos · ${p.sex || "—"} · ${p.weight_kg ?? "?"} kg · ${p.height_cm ?? "?"} cm`;
  $("p-allergies").textContent = listOrDash(p.allergies);
  $("p-conditions").textContent = listOrDash(p.conditions);
  $("p-meds").textContent = listOrDash(p.medications);
  $("p-symptoms").textContent = listOrDash(p.symptoms);
  renderAvatar();
}

// Cor de cada vital conforme limiares clínicos (igual à lógica do backend).
function vitalColor(key, v) {
  const n = Number(v);
  switch (key) {
    case "heart_rate":       return n > 110 ? "#f87171" : n > 95 ? "#fbbf24" : "#e2e8f0";
    case "spo2":             return n < 92 ? "#f87171" : n < 95 ? "#fbbf24" : "#34d399";
    case "body_temp":        return n >= 38 ? "#f87171" : n >= 37.5 ? "#fbbf24" : "#e2e8f0";
    case "respiratory_rate": return n > 22 ? "#f87171" : n > 20 ? "#fbbf24" : "#e2e8f0";
    case "stress":           return n > 75 ? "#f87171" : n > 60 ? "#fbbf24" : "#e2e8f0";
    case "hrv":              return n < 30 ? "#fbbf24" : "#e2e8f0";
    default:                 return "#e2e8f0";
  }
}
const VITALS_META = [
  { key: "heart_rate",       label: "FC",       unit: "bpm" },
  { key: "spo2",             label: "SpO₂",     unit: "%" },
  { key: "body_temp",        label: "Temp",     unit: "°C" },
  { key: "respiratory_rate", label: "FR",       unit: "rpm" },
  { key: "stress",           label: "Estresse", unit: "/100" },
  { key: "hrv",              label: "HRV",      unit: "ms" },
];

function renderState(t) {
  currentMood = t.mood || "bem";
  const color = t.color || MOOD_COLOR[currentMood] || "#1152d4";

  const badge = $("twin-badge");
  badge.className = "chip " + (MOOD_CHIP[currentMood] || "chip-muted");
  badge.textContent = (currentMood === "alerta" || currentMood === "atenção" ? "⚠ " : "") + (MOOD_LABEL[currentMood] || currentMood.toUpperCase());

  $("health-bar").style.width = (t.health_score ?? 0) + "%";
  $("health-bar").style.background = `linear-gradient(to right, ${color}99, ${color})`;
  $("health-score").textContent = `${t.health_score ?? "–"}/100`;
  $("health-score").style.color = color;
  $("twin-summary").textContent = t.summary || "";
  $("doc-avatar").style.setProperty("--twin-color", color);

  const v = t.vitals || {};
  $("vitals-grid").innerHTML = VITALS_META.map((m) => {
    const val = v[m.key] ?? "–";
    return `<div class="vital-card p-3">
      <div class="text-[10px] text-slate-500 uppercase tracking-wide">${m.label}</div>
      <div class="text-xl font-black" style="color:${vitalColor(m.key, val)}">${val}<span class="text-xs font-normal text-slate-500 ml-0.5">${m.unit}</span></div>
    </div>`;
  }).join("");

  const box = $("alerts-box");
  if (t.alerts && t.alerts.length) {
    box.innerHTML = t.alerts.map((a) =>
      `<div class="flex items-start gap-2 text-xs text-amber-300 bg-amber-500/10 rounded-lg px-2 py-1.5">
        <span class="material-symbols-outlined shrink-0" style="font-size:14px">warning</span><span>${a}</span>
      </div>`).join("");
  } else {
    box.innerHTML = `<div class="flex items-center gap-2 text-xs text-emerald-300 bg-emerald-500/10 rounded-lg px-2 py-1.5">
      <span class="material-symbols-outlined" style="font-size:14px">check_circle</span> Sem alertas no momento.</div>`;
  }
  renderAvatar();
}

// Pré-preenche as anotações com base no paciente real (editável).
function prefillNotes() {
  if (notesTouched || !profile || !twin) return;
  const ta = $("consulta-notes");
  if (ta.value.trim()) return;
  const v = twin.vitals || {};
  const queixas = latestRelatoText
    || ((profile.symptoms && profile.symptoms.length) ? profile.symptoms.join(", ") : "febre e dor no corpo");
  let txt = `Paciente em teleconsulta. Relato: ${queixas}. `;
  txt += `Ao exame (wearable): FC ${v.heart_rate ?? "?"} bpm, SpO₂ ${v.spo2 ?? "?"}%, Temp ${v.body_temp ?? "?"}°C, FR ${v.respiratory_rate ?? "?"} rpm. `;
  if (twin.alerts && twin.alerts.length) txt += "Alertas: " + twin.alerts.join("; ") + " ";
  txt += "Nega dispneia e sinais de alarme no momento.";
  ta.value = txt;
}

function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Relato do paciente (o que ele escreveu no Gêmeo Digital) — vem do backend (RAM).
async function loadRelato() {
  try {
    const d = await fetchJSON("/api/twin/relato");
    renderRelato(d.reports || []);
  } catch (e) {}
}
function renderRelato(reports) {
  const box = $("relato-box");
  if (!reports.length) {
    box.innerHTML = `<p class="text-xs text-slate-500">Sem relatos do paciente ainda. O que ele escrever no Gêmeo Digital aparece aqui.</p>`;
    latestRelatoText = "";
    return;
  }
  latestRelatoText = reports[0].text || "";
  box.innerHTML = reports.map((r) => {
    let h = "";
    try { h = new Date(r.at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }); } catch (e) {}
    const tag = r.source === "medico" ? `<span class="text-[9px] font-bold uppercase text-emerald-400 mr-1">médico</span>` : "";
    return `<div class="relato-item px-3 py-2 text-xs text-slate-200"><span class="text-slate-500 mr-1">${h}</span>${tag}${escapeHtml(r.text)}</div>`;
  }).join("");
}

// Relatório clínico do paciente gerado pela IA (apoio à decisão do médico).
async function generateReport() {
  const btn = $("btn-report");
  const box = $("report-box");
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="cp-spin"></span> Gerando…`;
  box.classList.remove("hidden");
  box.textContent = "Gerando relatório clínico com base nos sinais vitais e no perfil…";
  try {
    const r = await fetchJSON("/api/ai/report", { method: "POST" });
    box.textContent = (r.report || "") + "\n\n· " + (r.powered_by || "IA");
  } catch (e) {
    box.textContent = "Não foi possível gerar o relatório agora (verifique o backend).";
  } finally {
    btn.disabled = false; btn.innerHTML = orig;
  }
}

// ---------------- Carga + atualização ao vivo ----------------
async function fetchJSON(path, opts) {
  const res = await fetch(API + path, opts);
  if (!res.ok) throw new Error("HTTP " + res.status + " em " + path);
  return res.json();
}

async function loadAll() {
  try {
    const [p, t] = await Promise.all([fetchJSON("/api/twin/profile"), fetchJSON("/api/twin/state")]);
    profile = p; twin = t;
    renderProfile(p); renderState(t);
    await loadRelato();   // carrega o relato antes de pré-preencher as anotações
    prefillNotes();
    setModelLabelFromStatus();
  } catch (e) {
    $("p-name").textContent = "Backend offline";
    $("p-sub").textContent = "Inicie a API (python run.py) e abra via http://localhost:8000";
  }
}

async function pollState() {
  if (document.hidden) return;
  try {
    const [p, t] = await Promise.all([fetchJSON("/api/twin/profile"), fetchJSON("/api/twin/state")]);
    profile = p; twin = t;
    renderProfile(p);   // re-renderiza só se mudou (segue o mesmo paciente do app)
    renderState(t);
    loadRelato();       // mantém o relato do paciente atualizado ao vivo
  } catch (e) {
    // backend indisponível nesta sondagem; a próxima tentativa reconecta.
  }
}

async function setModelLabelFromStatus() {
  try {
    const s = await fetchJSON("/api/ai/status");
    $("doc-name").textContent = DOCTOR + (s.enabled ? "" : " · IA em modo demo");
  } catch (e) { $("doc-name").textContent = DOCTOR; }
}

// ---------------- Sugerir prescrição ----------------
async function suggestPrescription() {
  const notes = $("consulta-notes").value.trim();
  if (!notes) { $("consulta-notes").focus(); return; }
  if (!twin) { return; }

  const btn = $("btn-ai-rx");
  const btnR = $("btn-regenerate");
  [btn, btnR].forEach((b) => b && (b.disabled = true));
  btn.innerHTML = `<span class="cp-spin"></span> Consultando IA…`;

  $("rx-section").classList.remove("hidden");
  $("rx-cards").innerHTML = `<div class="text-slate-400 text-sm flex items-center gap-2"><span class="cp-spin"></span> Gerando rascunho com base nos sinais vitais e anotações…</div>`;
  $("rx-edit").value = "";
  $("sent-banner").classList.add("hidden");

  try {
    const data = await fetchJSON("/api/ai/prescricao-draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        twin_summary: {
          mood: twin.mood,
          health_score: twin.health_score,
          vitals: twin.vitals,
          alerts: twin.alerts || [],
        },
        consulta_notes: notes,
      }),
    });
    currentDraft = data;
    renderDraft(data);
    $("rx-model-label").textContent = "Gerado por: " + (data.powered_by || "IA");
  } catch (e) {
    $("rx-cards").innerHTML = `<div class="text-amber-300 text-sm">Não foi possível gerar agora. Verifique se o backend está rodando (python run.py) e tente novamente.</div>`;
  } finally {
    [btn, btnR].forEach((b) => b && (b.disabled = false));
    btn.innerHTML = `<span class="material-symbols-outlined" style="font-size:18px">auto_awesome</span> Sugerir Prescrição com IA`;
  }
}

function renderDraft(data) {
  const meds = data.medications || [];
  let html = "";

  if (meds.length) {
    html += `<div class="flex flex-col gap-2">` + meds.map((m, i) => `
      <div class="med-card p-3.5">
        <div class="flex items-start gap-2">
          <span class="size-7 shrink-0 grid place-items-center rounded-lg bg-emerald-500/15 text-emerald-300 text-xs font-black">${i + 1}</span>
          <div class="flex-1 min-w-0">
            <div class="font-bold text-sm text-emerald-100">${m.name || "—"}</div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-1 mt-1.5 text-[11px]">
              ${m.dosage ? `<div><span class="text-slate-500">Dosagem:</span> <span class="text-slate-200">${m.dosage}</span></div>` : ""}
              ${m.frequency ? `<div><span class="text-slate-500">Frequência:</span> <span class="text-slate-200">${m.frequency}</span></div>` : ""}
              ${m.duration ? `<div><span class="text-slate-500">Duração:</span> <span class="text-slate-200">${m.duration}</span></div>` : ""}
            </div>
          </div>
        </div>
      </div>`).join("") + `</div>`;
  }

  if (data.guidance && data.guidance.length) {
    html += `<div class="rx-box p-3.5">
      <div class="text-[11px] font-bold uppercase tracking-wide text-slate-400 mb-1.5 flex items-center gap-1"><span class="material-symbols-outlined" style="font-size:14px">tips_and_updates</span> Orientações gerais</div>
      <ul class="text-xs text-slate-200 space-y-1">${data.guidance.map((g) => `<li class="flex gap-1.5"><span class="text-primary">•</span><span>${g}</span></li>`).join("")}</ul>
    </div>`;
  }

  if (data.return_criteria && data.return_criteria.length) {
    html += `<div class="p-3.5 rounded-xl border border-red-500/25 bg-red-500/5">
      <div class="text-[11px] font-bold uppercase tracking-wide text-red-300 mb-1.5 flex items-center gap-1"><span class="material-symbols-outlined" style="font-size:14px">emergency</span> Critérios de retorno / urgência</div>
      <ul class="text-xs text-slate-200 space-y-1">${data.return_criteria.map((r) => `<li class="flex gap-1.5"><span class="text-red-400">•</span><span>${r}</span></li>`).join("")}</ul>
    </div>`;
  }

  if (data.allergy_note) {
    html += `<div class="p-3 rounded-xl border border-amber-500/30 bg-amber-500/10 text-xs text-amber-200 flex items-start gap-2">
      <span class="material-symbols-outlined shrink-0" style="font-size:15px">warning</span><span>${data.allergy_note}</span></div>`;
  }

  $("rx-cards").innerHTML = html || `<div class="text-slate-400 text-sm">Sem itens sugeridos.</div>`;
  $("rx-edit").value = data.prescription_draft || "";
}

// ---------------- Assinar e enviar ----------------
async function signAndSend() {
  const finalRx = $("rx-edit").value.trim() || (currentDraft && currentDraft.prescription_draft) || "";
  if (!finalRx) return;

  const btn = $("btn-sign");
  btn.disabled = true;
  btn.innerHTML = `<span class="cp-spin"></span> Enviando…`;

  const d = currentDraft || {};
  const structured = {
    medications: d.medications || [],
    guidance: d.guidance || [],
    return_criteria: d.return_criteria || [],
    allergy_note: d.allergy_note || "",
  };
  const payload = {
    prescription_text: finalRx,
    ...structured,
    doctor: DOCTOR,
    consulta_notes: $("consulta-notes").value.trim(),
  };

  let ok = false;
  try { await fetchJSON("/api/ai/prescricao-assinar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }); ok = true;
  } catch (e) { ok = false; }

  // Fallback na mesma aba (Zero-Data Footprint: RAM do browser).
  try {
    sessionStorage.setItem("cp_prescricao_pendente", JSON.stringify({
      texto: finalRx, medico: DOCTOR, data: new Date().toISOString(), lida: false, structured,
    }));
  } catch (e) {}

  // Avisa a aba do paciente na hora (mesmo navegador) — entrega instantânea.
  try {
    const bc = new BroadcastChannel("careplus_rx");
    bc.postMessage({ type: "nova-prescricao", at: Date.now() });
    bc.close();
  } catch (e) {}

  $("rx-section").classList.add("hidden");
  $("sent-banner").classList.remove("hidden");
  $("sent-time").textContent = "Enviada em: " + new Date().toLocaleString("pt-BR") + (ok ? "" : " · (backend offline — salvo localmente)");
  btn.disabled = false;
  btn.innerHTML = `<span class="material-symbols-outlined" style="font-size:18px">verified</span> Assinar e Enviar ao Paciente`;
}

// ---------------- Inserir relato manual (recebido por fora) ----------------
async function addManualRelato() {
  const input = $("relato-input");
  const txt = (input.value || "").trim();
  if (!txt) { input.focus(); return; }
  const btn = $("relato-add");
  btn.disabled = true;
  try {
    await fetchJSON("/api/twin/relato", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: txt, source: "medico" }),
    });
    input.value = "";
    await loadRelato();
    // Atualiza o perfil para refletir os sintomas extraídos do relato.
    try { const p = await fetchJSON("/api/twin/profile"); profile = p; renderProfile(p); } catch (e) {}
    if (window.CareToast) CareToast("Relato inserido. Sintomas atualizados.", "ok");
  } catch (e) {} finally { btn.disabled = false; }
}

// ---------------- Eventos + init ----------------
$("btn-ai-rx").addEventListener("click", suggestPrescription);
$("btn-regenerate").addEventListener("click", suggestPrescription);
$("btn-sign").addEventListener("click", signAndSend);
$("btn-report").addEventListener("click", generateReport);
$("consulta-notes").addEventListener("input", () => { notesTouched = true; });
$("relato-add").addEventListener("click", addManualRelato);
$("relato-input").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); addManualRelato(); } });

loadAll();
setInterval(pollState, 5000);   // atualização ao vivo (pausa com a aba em segundo plano)
