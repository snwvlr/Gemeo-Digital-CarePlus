/* CarePlus - Dashboard: dados ao vivo do gêmeo, vitais, alertas e IA. */

let profile = { name: "Paciente" };
let currentMood = "bem";
const avatarCfg = window.CareAvatar ? CareAvatar.loadAvatarConfig() : {};

const METRIC_META = {
  heart_rate:  { label: "Cardíaca",  unit: "bpm", icon: "favorite",        color: "text-red-400" },
  spo2:        { label: "Oxigênio",  unit: "%",   icon: "air",             color: "text-cyan-400" },
  body_temp:   { label: "Temp.",     unit: "°C",  icon: "thermostat",      color: "text-rose-400" },
  steps:       { label: "Passos",    unit: "",    icon: "directions_walk", color: "text-emerald-400" },
  sleep_hours: { label: "Sono",      unit: "h",   icon: "bedtime",         color: "text-indigo-400" },
  stress:      { label: "Estresse",  unit: "/100", icon: "psychology",     color: "text-amber-400" },
};
const ORDER = ["heart_rate", "spo2", "body_temp", "steps", "sleep_hours", "stress"];

function el(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }

function setAvatarFallback(img, name) {
  img.onerror = () => {
    img.onerror = null;
    const ini = (name || "C").trim().charAt(0).toUpperCase();
    img.src = "data:image/svg+xml;utf8," + encodeURIComponent(
      `<svg xmlns='http://www.w3.org/2000/svg' width='150' height='150'><rect width='100%' height='100%' rx='16' fill='#1e293b'/><text x='50%' y='54%' font-size='64' fill='#3b82f6' font-family='Inter,sans-serif' font-weight='800' text-anchor='middle' dominant-baseline='middle'>${ini}</text></svg>`);
  };
}

function refreshAvatar() {
  const img = document.getElementById("avatar-img");
  setAvatarFallback(img, profile.name);
  if (window.CareAvatar) img.src = CareAvatar.buildAvatarUrl(profile.name, avatarCfg, currentMood);
}

function renderVitals(v) {
  const grid = document.getElementById("vitals-grid");
  grid.innerHTML = "";
  ORDER.forEach((k) => {
    const m = METRIC_META[k];
    grid.appendChild(el(`
      <div class="rounded-xl bg-slate-800/40 border border-slate-700/40 p-3">
        <div class="flex items-center gap-1.5 mb-1 ${m.color}"><span class="material-symbols-outlined" style="font-size:18px">${m.icon}</span><span class="text-[11px] text-slate-400 font-medium">${m.label}</span></div>
        <div class="text-lg font-black text-white">${v[k]}<span class="text-xs font-normal text-slate-500 ml-0.5">${m.unit}</span></div>
      </div>`));
  });
}

function setTwin(s) {
  currentMood = s.mood;
  const c = s.color;
  document.documentElement.style.setProperty("--twin-color", c);
  document.getElementById("avatar-frame").style.setProperty("--twin-color", c);
  document.getElementById("score-ring").style.setProperty("--twin-color", c);
  const mood = document.getElementById("twin-mood");
  mood.textContent = "Estou " + s.mood; mood.style.color = c;
  document.getElementById("twin-summary").textContent = s.summary;
  const circ = 2 * Math.PI * 52;
  document.getElementById("score-ring").style.strokeDashoffset = circ * (1 - s.health_score / 100);
  document.getElementById("score-num").textContent = s.health_score;
  renderVitals(s.vitals);

  const list = document.getElementById("alerts-list");
  if (s.alerts && s.alerts.length) {
    list.innerHTML = s.alerts.map((a) => `<li class="flex gap-2"><span class="material-symbols-outlined text-amber-500" style="font-size:18px">chevron_right</span><span>${a}</span></li>`).join("");
  } else {
    list.innerHTML = `<li class="flex gap-2 text-emerald-400"><span class="material-symbols-outlined" style="font-size:18px">check_circle</span><span>Tudo estável por aqui.</span></li>`;
  }
  refreshAvatar();
}

async function refreshTwin() {
  try { setTwin(await CareAPI.twinStateCached()); }
  catch (e) {
    document.getElementById("twin-mood").textContent = "Backend offline";
    document.getElementById("twin-summary").textContent = "Inicie a API (python run.py).";
    document.getElementById("alerts-list").innerHTML = `<li class="text-amber-400">Sem conexão com o servidor.</li>`;
  }
}

async function analyze() {
  const sum = document.getElementById("ai-summary");
  const recs = document.getElementById("ai-recs");
  const chip = document.getElementById("risk-chip");
  sum.textContent = "Analisando…"; recs.innerHTML = "";
  try {
    const a = await CareAPI.analyze();
    sum.textContent = a.analysis;
    const map = { baixo: "chip-ok", moderado: "chip-warn", alto: "chip-bad" };
    chip.className = "chip " + (map[a.risk_level] || "chip-muted");
    chip.textContent = "Risco " + a.risk_level;
    recs.innerHTML = a.recommendations.map((r) => `<li class="flex gap-2"><span class="material-symbols-outlined text-primary" style="font-size:18px">check_circle</span><span>${r}</span></li>`).join("");
  } catch (e) { sum.textContent = "Não foi possível analisar (backend offline)."; }
}

/* ============================================================
   Prescrição recebida do médico (entregue no Dashboard).
   Zero-Data Footprint: checa RAM do backend + sessionStorage.
   Entrega instantânea via BroadcastChannel quando o médico assina.
   ============================================================ */
const RX_API = "";
let _rxCurrent = null, _rxDismissed = null, _rxWired = false;

function fmtRxDate(rx) { return rx && rx.data ? new Date(rx.data).toLocaleString("pt-BR") : "agora"; }
function escapeRx(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

function renderRxModalCards(rx) {
  const cards = document.getElementById("rx-modal-cards");
  if (!cards) return;
  const s = (rx && rx.structured) || {};
  const meds = s.medications || [], guide = s.guidance || [], ret = s.return_criteria || [];
  if (!meds.length && !guide.length && !ret.length && !s.allergy_note) {
    cards.innerHTML = `<pre class="rounded-xl p-4 text-xs text-slate-100 whitespace-pre-wrap font-mono" style="background:rgba(30,41,59,0.7)">${escapeRx((rx && rx.texto) || "(sem conteúdo)")}</pre>`;
    return;
  }
  let html = "";
  if (meds.length) {
    html += meds.map((m, i) => `
      <div class="p-3 rounded-xl border border-emerald-500/25" style="background:rgba(16,185,129,0.06)">
        <div class="flex items-start gap-2">
          <span class="size-6 shrink-0 grid place-items-center rounded-lg bg-emerald-500/15 text-emerald-300 text-[11px] font-black">${i + 1}</span>
          <div class="flex-1 min-w-0">
            <div class="font-bold text-sm text-emerald-100">${escapeRx(m.name || "—")}</div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-1 mt-1 text-[11px]">
              ${m.dosage ? `<div><span class="text-slate-500">Dosagem:</span> ${escapeRx(m.dosage)}</div>` : ""}
              ${m.frequency ? `<div><span class="text-slate-500">Frequência:</span> ${escapeRx(m.frequency)}</div>` : ""}
              ${m.duration ? `<div><span class="text-slate-500">Duração:</span> ${escapeRx(m.duration)}</div>` : ""}
            </div>
          </div>
        </div>
      </div>`).join("");
  }
  if (guide.length) {
    html += `<div class="p-3 rounded-xl border border-slate-700/50 bg-slate-800/40">
      <div class="text-[11px] font-bold uppercase tracking-wide text-slate-400 mb-1">Orientações</div>
      <ul class="text-xs text-slate-200 space-y-1">${guide.map((g) => `<li class="flex gap-1.5"><span class="text-primary">•</span><span>${escapeRx(g)}</span></li>`).join("")}</ul></div>`;
  }
  if (ret.length) {
    html += `<div class="p-3 rounded-xl border border-red-500/25" style="background:rgba(239,68,68,0.05)">
      <div class="text-[11px] font-bold uppercase tracking-wide text-red-300 mb-1">Quando procurar ajuda</div>
      <ul class="text-xs text-slate-200 space-y-1">${ret.map((r) => `<li class="flex gap-1.5"><span class="text-red-400">•</span><span>${escapeRx(r)}</span></li>`).join("")}</ul></div>`;
  }
  if (s.allergy_note) {
    html += `<div class="p-3 rounded-xl border border-amber-500/30 bg-amber-500/10 text-xs text-amber-200 flex items-start gap-2"><span class="material-symbols-outlined shrink-0" style="font-size:15px">warning</span><span>${escapeRx(s.allergy_note)}</span></div>`;
  }
  cards.innerHTML = html;
}

/* Baixa a prescrição em PDF no próprio dispositivo do paciente (Zero-Data
   Footprint): abre uma janela já pronta para imprimir/salvar como PDF, montada
   a partir dos dados estruturados que o médico assinou. Nada é enviado ao servidor. */
function downloadRxPdf(rx) {
  const s = (rx && rx.structured) || {};
  const meds = s.medications || [], guide = s.guidance || [], ret = s.return_criteria || [];
  const docName = String((rx && rx.medico) || "Equipe Médica Care Plus").split("·")[0].trim();
  const list = (arr) => arr.map((x) => `<li>${escapeRx(x)}</li>`).join("");

  let corpo = "";
  if (meds.length) {
    const rows = meds.map((m, i) => `<tr>
        <td>${i + 1}. ${escapeRx(m.name || "-")}</td>
        <td>${[m.dosage, m.frequency, m.duration].filter(Boolean).map(escapeRx).join(" · ") || "-"}</td>
      </tr>`).join("");
    corpo += `<h2>Medicamentos</h2><table><tr><td><b>Medicamento</b></td><td><b>Posologia</b></td></tr>${rows}</table>`;
  }
  if (guide.length) corpo += `<h2>Orientações</h2><ul>${list(guide)}</ul>`;
  if (ret.length)   corpo += `<h2>Quando procurar ajuda</h2><ul>${list(ret)}</ul>`;
  if (s.allergy_note) corpo += `<p class="warn"><b>Alergias:</b> ${escapeRx(s.allergy_note)}</p>`;
  if (!corpo) corpo = `<pre class="raw">${escapeRx((rx && rx.texto) || "(sem conteúdo)")}</pre>`;

  const html = `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>Prescrição CarePlus</title>
    <link href="https://fonts.googleapis.com/css2?family=Great+Vibes&display=swap" rel="stylesheet">
    <style>
      *{font-family:Arial,Helvetica,sans-serif;color:#0f172a}
      body{padding:40px;max-width:760px;margin:auto}
      .hd{display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #1152d4;padding-bottom:12px;margin-bottom:18px}
      h1{color:#1152d4;font-size:20px;margin:0}
      h2{font-size:14px;color:#1152d4;border-bottom:1px solid #e2e8f0;padding-bottom:6px;margin-top:22px}
      .tag{display:inline-block;background:#10b981;color:#fff;padding:2px 10px;border-radius:6px;font-size:11px;font-weight:bold}
      .meta{font-size:13px;color:#475569;margin:2px 0}
      table{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}
      td{padding:8px;border-bottom:1px solid #eef2f7;vertical-align:top}
      td:first-child{width:45%}
      ul{font-size:13px;line-height:1.6;margin:6px 0 0;padding-left:18px}
      .warn{font-size:12px;color:#92400e;background:#fef3c7;border:1px solid #fde68a;border-radius:8px;padding:8px 10px;margin-top:14px}
      .raw{white-space:pre-wrap;font-size:12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px}
      .sign{margin-top:54px;width:300px;text-align:center}
      .sign-name{font-family:'Great Vibes',cursive;font-size:34px;line-height:1.1;color:#0f172a;margin-bottom:2px}
      .sign-line{border-top:1px solid #94a3b8;padding-top:6px;font-size:13px;color:#0f172a}
      .foot{margin-top:28px;font-size:10px;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:10px}
    </style></head><body>
    <div class="hd"><div><h1>Prescrição Digital</h1><div class="meta">CarePlus Health · Teleconsulta</div></div><span class="tag">VALIDADA PELO MÉDICO</span></div>
    <p class="meta"><b>Paciente:</b> ${escapeRx(profile.name || "-")}</p>
    <p class="meta"><b>Médico:</b> ${escapeRx((rx && rx.medico) || "-")}</p>
    <p class="meta"><b>Data:</b> ${escapeRx(fmtRxDate(rx))}</p>
    ${corpo}
    <div class="sign"><div class="sign-name">${escapeRx(docName)}</div><div class="sign-line">${escapeRx((rx && rx.medico) || "")}</div><span style="font-size:11px;color:#94a3b8">Assinatura digital validada</span></div>
    <div class="foot">Documento gerado pelo CarePlus no dispositivo do paciente. A prescrição é de responsabilidade do médico emissor. A IA não prescreve.</div>
    <script>function go(){window.print();}if(document.fonts&&document.fonts.ready){document.fonts.ready.then(function(){setTimeout(go,200);});}else{window.onload=go;}<\/script>
    </body></html>`;
  const w = window.open("", "_blank");
  if (!w) { if (window.CareToast) CareToast("Permita pop-ups para baixar o PDF.", "warn"); return; }
  w.document.write(html); w.document.close();
}

async function fetchPrescricaoPendente() {
  try {
    const stored = sessionStorage.getItem("cp_prescricao_pendente");
    if (stored) { const p = JSON.parse(stored); if (!p.lida) return p; }
  } catch (e) {}
  try {
    const res = await fetch(`${RX_API}/api/ai/prescricao`);
    if (res.ok) { const d = await res.json(); if (d.pendente && d.prescricao && !d.prescricao.lida) return d.prescricao; }
  } catch (e) {}
  return null;
}

function wireRxUi() {
  if (_rxWired) return; _rxWired = true;
  const g = (id) => document.getElementById(id);
  const card = g("rx-card"), modal = g("rx-modal");
  if (!card || !modal) return;
  g("rx-card-ver").addEventListener("click", () => {
    if (!_rxCurrent) return;
    renderRxModalCards(_rxCurrent);
    g("rx-modal-meta").textContent = `${_rxCurrent.medico || "Médico"} · ${fmtRxDate(_rxCurrent)}`;
    modal.classList.remove("hidden");
  });
  g("rx-modal-pdf").addEventListener("click", () => { if (_rxCurrent) downloadRxPdf(_rxCurrent); });
  g("rx-card-fechar").addEventListener("click", () => {
    if (_rxCurrent) _rxDismissed = _rxCurrent.data || "x";
    card.classList.add("hidden");
  });
  g("rx-modal-fechar").addEventListener("click", () => modal.classList.add("hidden"));
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.add("hidden"); });
  g("rx-modal-lida").addEventListener("click", async () => {
    if (_rxCurrent) _rxDismissed = _rxCurrent.data || "x";
    try { const st = sessionStorage.getItem("cp_prescricao_pendente"); if (st) { const pp = JSON.parse(st); pp.lida = true; sessionStorage.setItem("cp_prescricao_pendente", JSON.stringify(pp)); } } catch (e) {}
    try { await fetch(`${RX_API}/api/ai/prescricao-marcar-lida`, { method: "POST" }); } catch (e) {}
    modal.classList.add("hidden"); card.classList.add("hidden");
  });
}

function showRxCard(rx) {
  const card = document.getElementById("rx-card");
  if (!card) return;
  _rxCurrent = rx;
  document.getElementById("rx-card-info").textContent = `${rx.medico || "Seu médico"} · ${fmtRxDate(rx)}`;
  card.classList.remove("hidden");
}

async function pollPrescricao() {
  if (document.hidden) return;
  const rx = await fetchPrescricaoPendente();
  if (!rx) return;
  const sig = rx.data || "x";
  if (sig === _rxDismissed) return;
  showRxCard(rx);
}

function startPrescricaoPolling() {
  wireRxUi();
  try {
    const bc = new BroadcastChannel("careplus_rx");
    bc.onmessage = (ev) => { if (ev && ev.data && ev.data.type === "nova-prescricao") { _rxDismissed = null; pollPrescricao(); } };
  } catch (e) {}
  pollPrescricao();
  setInterval(pollPrescricao, 4000);
}

async function init() {
  document.getElementById("greet-date").textContent =
    new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });
  try { if (window.CareReady) await window.CareReady; } catch (e) {}
  try { profile = await CareAPI.profile(); } catch (e) {}
  const h = new Date().getHours();
  const saud = h >= 5 && h < 12 ? "Bom dia" : h >= 12 && h < 18 ? "Boa tarde" : "Boa noite";
  const nome = (profile.name || "").split(" ")[0];
  document.getElementById("greeting").textContent = nome ? `${saud}, ${nome}` : saud;
  refreshAvatar();
  await refreshTwin();
  document.getElementById("btn-analyze").addEventListener("click", analyze);
  startPrescricaoPolling();

  // Aviso de perfil de demonstração (mostra uma vez por sessão).
  let avisou = false;
  try { avisou = sessionStorage.getItem("cp_demo_aviso") === "1"; } catch (e) {}
  if (!avisou && window.CareInfoModal) {
    CareInfoModal("Perfil de demonstração", `
      Para fins de demonstração, geramos um paciente aleatório:
      <b>${profile.name || "Paciente"}, ${profile.age || "?"} anos</b>.
      Nome, idade, medicamentos e exames são fictícios e mudam a cada recarregamento (Ctrl+F5).
      Você pode personalizar o gêmeo (nome, aparência) na aba <b>Gêmeo Digital</b>.`);
    try { sessionStorage.setItem("cp_demo_aviso", "1"); } catch (e) {}
  }
}
init();
