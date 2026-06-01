/* CarePlus - Gêmeo Digital: estado vivo, avatar dinâmico, chat e modais. */

const history = [];
let profile = { name: "CarePlus" };
let currentMood = "bem";
let avatarCfg = CareAvatar.loadAvatarConfig();
let lastTwin = null;
let lastReport = "";

const METRIC_META = {
  heart_rate:       { label: "Freq. cardíaca", unit: "bpm",  icon: "favorite",        color: "text-red-400" },
  spo2:             { label: "Oxigênio",       unit: "%",    icon: "air",             color: "text-cyan-400" },
  body_temp:        { label: "Temperatura",    unit: "°C",   icon: "thermostat",      color: "text-rose-400" },
  respiratory_rate: { label: "Respiração",     unit: "rpm",  icon: "pulmonology",     color: "text-teal-400" },
  steps:            { label: "Passos",         unit: "",     icon: "directions_walk", color: "text-emerald-400" },
  sleep_hours:      { label: "Sono",           unit: "h",    icon: "bedtime",         color: "text-indigo-400" },
  stress:           { label: "Estresse",       unit: "/100", icon: "psychology",      color: "text-amber-400" },
  hrv:              { label: "HRV",            unit: "ms",   icon: "monitor_heart",   color: "text-pink-400" },
};
const TILE_ORDER = ["heart_rate", "spo2", "body_temp", "steps", "sleep_hours", "stress"];

function el(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }

/* Markdown mínimo e seguro para o chat: escapa HTML (evita XSS) e converte
   **negrito**, *itálico*, marcadores de lista e quebras de linha. A IA responde
   em markdown, então sem isto os "**" apareciam crus na tela. */
function fmtMsg(text) {
  const esc = String(text == null ? "" : text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    // A IA costuma usar travessão (—) para separar frases; trocamos por vírgula
    // para um tom mais natural. (Não mexe no traço de intervalo "–", ex.: 2–3.)
    .replace(/\s*—\s*/g, ", ")
    .replace(/^,\s*/, "");
  return esc
    .split("\n")
    .map((line) => {
      line = line.replace(/^\s*[-*]\s+/, "• ");          // marcador de lista
      line = line.replace(/\*\*([^*]+?)\*\*/g, "<strong>$1</strong>"); // **negrito**
      line = line.replace(/(^|[^*])\*(?!\s)([^*]+?)\*(?!\*)/g, "$1<em>$2</em>"); // *itálico*
      return line;
    })
    .join("<br>");
}

/* ----------------------------- Modais ----------------------------- */
function openModal(id) { document.getElementById(id).classList.add("open"); if (window.CareLockScroll) CareLockScroll(true); }
function closeModal(id) { document.getElementById(id).classList.remove("open"); if (window.CareLockScroll) CareLockScroll(false); }
window.openModal = openModal; window.closeModal = closeModal;
document.addEventListener("keydown", (e) => { if (e.key === "Escape") document.querySelectorAll(".modal.open").forEach((m) => m.classList.remove("open")); });

/* ----------------------------- Avatar ----------------------------- */
function refreshAvatar() {
  const img = document.getElementById("avatar-img");
  img.onerror = () => {
    img.onerror = null;
    const ini = (profile.name || "C").trim().charAt(0).toUpperCase();
    img.src = "data:image/svg+xml;utf8," + encodeURIComponent(
      `<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><rect width='100%' height='100%' rx='16' fill='#1e293b'/><text x='50%' y='54%' font-size='80' fill='#3b82f6' font-family='Inter,sans-serif' font-weight='800' text-anchor='middle' dominant-baseline='middle'>${ini}</text></svg>`);
  };
  img.src = CareAvatar.buildAvatarUrl(profile.name, avatarCfg, currentMood);
}

function openAvatarModal() {
  buildAvatarControls();
  updateAvatarPreview();
  openModal("modal-avatar");
}
window.openAvatarModal = openAvatarModal;

function updateAvatarPreview() {
  document.getElementById("avatar-preview").src = CareAvatar.buildAvatarUrl(profile.name, avatarCfg, currentMood);
}

function buildAvatarControls() {
  const O = CareAvatar.AVATAR_OPTIONS;
  const wrap = document.getElementById("avatar-controls");
  const pillGroup = (key, items) => `
    <div><p class="text-xs font-bold text-slate-400 uppercase mb-2">${labelFor(key)}</p>
      <div class="flex flex-wrap gap-2">${items.map((it) => `
        <button data-key="${key}" data-val="${it.v}" class="opt-pill text-xs px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/60 ${avatarCfg[key] === it.v ? "sel" : ""}">${it.label}</button>`).join("")}</div></div>`;
  const swatchGroup = (key, colors) => `
    <div><p class="text-xs font-bold text-slate-400 uppercase mb-2">${labelFor(key)}</p>
      <div class="flex flex-wrap gap-2">${colors.map((c) => `
        <span data-key="${key}" data-val="${c}" class="swatch ${avatarCfg[key] === c ? "sel" : ""}" style="background:#${c}"></span>`).join("")}</div></div>`;
  const nameGroup = `
    <div><p class="text-xs font-bold text-slate-400 uppercase mb-2">Nome do gêmeo</p>
      <input id="twin-name-input" type="text" value="${(profile.name || '').replace(/"/g, '&quot;')}" placeholder="Como devo te chamar?"
        class="w-full bg-slate-800/80 border-slate-700 rounded-lg text-sm focus:ring-primary focus:border-primary"/></div>`;

  const sexGroup = `
    <div><p class="text-xs font-bold text-slate-400 uppercase mb-2">Sexo (para tratamento)</p>
      <div class="flex flex-wrap gap-2">${[["masculino","Masculino"],["feminino","Feminino"],["outro","Outro"]].map(([v,l]) =>
        `<button data-sex="${v}" class="opt-pill text-xs px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/60 ${(profile.sex||'').toLowerCase()===v?'sel':''}">${l}</button>`).join("")}</div></div>`;

  wrap.innerHTML =
    nameGroup +
    sexGroup +
    pillGroup("top", O.top) +
    swatchGroup("hairColor", O.hairColor) +
    swatchGroup("skinColor", O.skinColor) +
    pillGroup("clothing", O.clothing) +
    swatchGroup("clothesColor", O.clothesColor) +
    pillGroup("accessories", O.accessories) +
    pillGroup("facialHair", O.facialHair) +
    swatchGroup("facialHairColor", O.facialHairColor);

  wrap.querySelectorAll("[data-sex]").forEach((node) => {
    node.addEventListener("click", () => {
      const v = node.dataset.sex;
      profile.sex = v.charAt(0).toUpperCase() + v.slice(1);
      const preset = CareAvatar.SEX_PRESETS[v] || {};
      avatarCfg = { ...avatarCfg, ...preset };
      buildAvatarControls();
      updateAvatarPreview();
    });
  });

  wrap.querySelectorAll("[data-key]").forEach((node) => {
    node.addEventListener("click", () => {
      const { key, val } = node.dataset;
      avatarCfg[key] = val;
      wrap.querySelectorAll(`[data-key="${key}"]`).forEach((n) => n.classList.remove("sel"));
      node.classList.add("sel");
      updateAvatarPreview();
    });
  });
}
function labelFor(key) {
  return { top: "Cabelo", hairColor: "Cor do cabelo", skinColor: "Pele",
           clothing: "Roupa", clothesColor: "Cor da roupa", accessories: "Óculos",
           facialHair: "Barba", facialHairColor: "Cor da barba" }[key] || key;
}
async function saveAvatar() {
  const nameInput = document.getElementById("twin-name-input");
  if (nameInput && nameInput.value.trim()) profile.name = nameInput.value.trim();
  CareAvatar.saveAvatarConfig(avatarCfg);
  refreshAvatar();
  closeModal("modal-avatar");
  // Persiste nome e sexo no perfil para a IA usar o tratamento correto.
  try { profile = await CareAPI.updateProfile(profile); } catch (e) {}
  const cn = document.getElementById("cp-name"); if (cn) cn.textContent = profile.name;
}
window.saveAvatar = saveAvatar;

/* --------------------------- Estado do gêmeo --------------------------- */
function setTwin(state) {
  lastTwin = state;
  currentMood = state.mood;
  const c = state.color;
  document.documentElement.style.setProperty("--twin-color", c);
  document.getElementById("avatar-frame").style.setProperty("--twin-color", c);
  document.getElementById("score-ring").style.setProperty("--twin-color", c);

  document.getElementById("twin-mood").textContent = "Estou " + state.mood;
  document.getElementById("twin-mood").style.color = c;
  document.getElementById("twin-summary").textContent = state.summary;

  // anel
  const circ = 2 * Math.PI * 52;
  document.getElementById("score-ring").style.strokeDashoffset = circ * (1 - state.health_score / 100);
  document.getElementById("score-num").textContent = state.health_score;

  // vitais
  renderVitals(state.vitals);

  // alertas
  const list = document.getElementById("alerts-list");
  if (state.alerts && state.alerts.length) {
    list.innerHTML = state.alerts.map((a) => `<li class="flex gap-2"><span class="material-symbols-outlined text-amber-500 text-[18px]">chevron_right</span><span>${a}</span></li>`).join("");
  } else {
    list.innerHTML = `<li class="flex gap-2 text-emerald-400"><span class="material-symbols-outlined text-[18px]">check_circle</span><span>Tudo estável por aqui.</span></li>`;
  }
  refreshAvatar();
}

function renderVitals(v) {
  const wrap = document.getElementById("vitals");
  wrap.innerHTML = "";
  TILE_ORDER.forEach((key) => {
    const m = METRIC_META[key];
    wrap.appendChild(el(`
      <section class="card p-3">
        <div class="flex items-center gap-1.5 mb-1 ${m.color}">
          <span class="material-symbols-outlined text-[16px]">${m.icon}</span>
          <span class="text-[10px] text-slate-400 font-medium leading-tight">${m.label}</span>
        </div>
        <div class="text-lg font-black text-white leading-none">${v[key]}<span class="text-[11px] font-normal text-slate-500 ml-0.5">${m.unit}</span></div>
      </section>`));
  });
}

async function refreshTwin() {
  try { setTwin(await CareAPI.twinStateCached()); }
  catch (e) {
    document.getElementById("twin-mood").textContent = "Backend offline";
    document.getElementById("twin-summary").textContent = "Inicie a API (python run.py).";
  }
}

/* ------------------------------- Chat ------------------------------- */
function bubble(role, text) {
  const log = document.getElementById("chat-log");
  const mine = role === "user";
  const div = document.createElement("div");
  div.className = "flex " + (mine ? "justify-end" : "justify-start");
  div.innerHTML = `<div class="max-w-[82%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${mine ? "bg-primary text-white rounded-br-sm" : "bg-slate-800 text-slate-100 rounded-bl-sm"}">${fmtMsg(text)}</div>`;
  log.appendChild(div); log.scrollTop = log.scrollHeight; return div;
}
function escalationBubble(text, type) {
  const log = document.getElementById("chat-log");
  const tel = type === "saude_mental" ? "188" : "192";
  const label = type === "saude_mental" ? "Ligar CVV 188" : "Ligar SAMU 192";
  const div = document.createElement("div");
  div.className = "flex justify-start";
  div.innerHTML = `<div class="max-w-[88%] px-4 py-3 rounded-2xl rounded-bl-sm text-sm leading-relaxed bg-red-500/15 border border-red-500/40 text-red-100">
      <div class="flex items-center gap-2 mb-1 text-red-300 font-bold"><span class="material-symbols-outlined" style="font-size:18px">emergency</span> Atenção</div>
      ${fmtMsg(text)}
      <a href="tel:${tel}" class="mt-3 flex items-center justify-center gap-2 bg-red-500 hover:bg-red-600 text-white font-bold py-2 rounded-lg" style="text-decoration:none"><span class="material-symbols-outlined" style="font-size:18px">call</span> ${label}</a>
    </div>`;
  log.appendChild(div); log.scrollTop = log.scrollHeight;
}

function typing() {
  const log = document.getElementById("chat-log");
  const div = document.createElement("div");
  div.className = "flex justify-start";
  div.innerHTML = `<div class="bg-slate-800 px-4 py-3 rounded-2xl rounded-bl-sm typing flex gap-1"><span class="size-2 bg-slate-400 rounded-full"></span><span class="size-2 bg-slate-400 rounded-full"></span><span class="size-2 bg-slate-400 rounded-full"></span></div>`;
  log.appendChild(div); log.scrollTop = log.scrollHeight; return div;
}
async function send(message) {
  if (!message) return;
  bubble("user", message);
  history.push({ role: "user", content: message });
  // Compartilha o relato com o médico (RAM no backend, Zero-Data). Fire-and-forget.
  try {
    fetch("/api/twin/relato", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
  } catch (e) {}
  const t = typing();
  try {
    const r = await CareAPI.chat(message, history);
    t.remove();
    if (r.escalate) {
      escalationBubble(r.reply, r.escalation_type);
    } else {
      bubble("model", r.reply);
    }
    history.push({ role: "model", content: r.reply });
    CareState.setChat(history);
    refreshTwin();
  } catch (e) { t.remove(); bubble("model", "Não consegui responder agora. Verifique se o backend está rodando."); }
}
document.getElementById("chat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  const v = input.value.trim(); input.value = ""; send(v);
});
document.querySelectorAll(".sug").forEach((b) => b.addEventListener("click", () => send(b.textContent)));

/* ----------------------------- Análise ----------------------------- */
// Assinatura dos dados atuais. Enquanto não muda, reaproveitamos o resultado
// da IA (economia de tokens). Só muda com novos dados (Ctrl+F5 / anomalia).
function dataSig() {
  const v = lastTwin ? lastTwin.vitals : {};
  return [lastTwin && lastTwin.health_score, lastTwin && lastTwin.mood,
          v.heart_rate, v.spo2, v.body_temp, (profile.medications || []).length].join("|");
}
function cacheGet(key, sig) {
  try { const c = JSON.parse(sessionStorage.getItem(key) || "null"); return (c && c.sig === sig) ? c.data : null; } catch (e) { return null; }
}
function cacheSet(key, sig, data) {
  try { sessionStorage.setItem(key, JSON.stringify({ sig, data })); } catch (e) {}
}

async function runAnalysis() {
  const card = document.getElementById("analysis-card");
  const body = document.getElementById("analysis-body");
  card.classList.remove("hidden");
  const sig = dataSig();
  const cached = cacheGet("cp_analysis", sig);
  if (cached) { renderAnalysis(cached, body, true); return; }
  body.innerHTML = "<span class='text-slate-500'>Analisando…</span>";
  try {
    const a = await CareAPI.analyze();
    cacheSet("cp_analysis", sig, a);
    renderAnalysis(a, body, false);
  } catch (e) { body.innerHTML = "<span class='text-amber-400'>Backend offline.</span>"; }
}
function renderAnalysis(a, body, cached) {
  const rc = { baixo: "text-emerald-400", moderado: "text-amber-400", alto: "text-red-400" }[a.risk_level] || "text-slate-300";
  body.innerHTML = `
    <p class="mb-2">${a.analysis}</p>
    <p class="mb-3 text-xs">Risco: <span class="font-bold ${rc} uppercase">${a.risk_level}</span></p>
    <ul class="space-y-1.5">${a.recommendations.map((r) => `<li class="flex gap-2"><span class="material-symbols-outlined text-primary text-[18px]">check_circle</span><span>${r}</span></li>`).join("")}</ul>
    <p class="mt-3 text-[10px] text-slate-500">${a.powered_by}${cached ? " · em cache" : ""}</p>`;
}
window.runAnalysis = runAnalysis;

async function openReport() {
  openModal("modal-report");
  const body = document.getElementById("report-body");
  const by = document.getElementById("report-by");
  const sig = dataSig();
  const cached = cacheGet("cp_report", sig);
  if (cached) { lastReport = cached.report; body.textContent = cached.report; by.textContent = cached.powered_by + " · em cache"; return; }
  body.textContent = "Gerando…"; by.textContent = "";
  try {
    const r = await CareAPI.report();
    lastReport = r.report;
    body.textContent = r.report;
    by.textContent = r.powered_by;
    cacheSet("cp_report", sig, { report: r.report, powered_by: r.powered_by });
  } catch (e) { body.textContent = "Backend offline."; lastReport = ""; }
}
window.openReport = openReport;

function exportReportPdf() {
  if (!lastReport) { if (window.CareToast) CareToast("Gere o relatório antes de exportar.", "warn"); return; }
  const v = lastTwin ? lastTwin.vitals : {};
  const hoje = new Date().toLocaleString("pt-BR");
  const linha = (k, val) => `<tr><td>${k}</td><td>${val}</td></tr>`;
  const html = `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>Laudo CarePlus</title>
    <style>
      *{font-family:Arial,Helvetica,sans-serif;color:#0f172a}
      body{padding:40px;max-width:760px;margin:auto}
      .hd{display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #1152d4;padding-bottom:12px;margin-bottom:20px}
      .hd h1{color:#1152d4;font-size:22px;margin:0}
      .hd small{color:#64748b}
      .tag{display:inline-block;background:#1152d4;color:#fff;padding:2px 10px;border-radius:6px;font-size:11px;font-weight:bold}
      h2{font-size:14px;color:#1152d4;border-bottom:1px solid #e2e8f0;padding-bottom:6px;margin-top:24px}
      table{width:100%;border-collapse:collapse;font-size:13px}
      td{padding:6px 8px;border-bottom:1px solid #eef2f7}
      td:first-child{color:#64748b;width:45%}
      .report{white-space:pre-wrap;font-size:13px;line-height:1.6;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px}
      .foot{margin-top:30px;font-size:10px;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:10px}
    </style></head><body>
    <div class="hd"><div><h1>CarePlus Health</h1><small>Laudo do Gêmeo Digital</small></div><span class="tag">CONFIDENCIAL</span></div>
    <h2>Paciente</h2>
    <table>
      ${linha("Nome", profile.name || "-")}
      ${linha("Idade", (profile.age || "-") + " anos")}
      ${linha("Alergias", (profile.allergies || []).join(", ") || "nenhuma")}
      ${linha("Medicamentos", (profile.medications || []).join(", ") || "nenhum")}
      ${linha("Emitido em", hoje)}
    </table>
    <h2>Estado atual (wearables)</h2>
    <table>
      ${linha("Humor do gêmeo", lastTwin ? lastTwin.mood + " (" + lastTwin.health_score + "/100)" : "-")}
      ${linha("Freq. cardíaca", (v.heart_rate ?? "-") + " bpm")}
      ${linha("SpO₂", (v.spo2 ?? "-") + " %")}
      ${linha("Temperatura", (v.body_temp ?? "-") + " °C")}
      ${linha("Respiração", (v.respiratory_rate ?? "-") + " rpm")}
    </table>
    <h2>Relatório clínico (IA)</h2>
    <div class="report">${lastReport.replace(/</g, "&lt;")}</div>
    <div class="foot">Documento gerado automaticamente pelo CarePlus Gêmeo Digital. Não substitui avaliação médica presencial.</div>
    <script>window.onload=function(){window.print();}<\/script>
    </body></html>`;
  const w = window.open("", "_blank");
  w.document.write(html);
  w.document.close();
}
window.exportReportPdf = exportReportPdf;

async function simulate(kind) {
  try {
    await CareAPI.simulate(kind);
    // refreshTwin() lê do cache de sessão (cp_twin), que só zera no Ctrl+F5 —
    // por isso a tela só atualizava após recarregar. Aqui forçamos uma busca
    // nova no backend (CareAPI.refreshTwin também atualiza o cache) e já
    // re-renderizamos na hora.
    setTwin(await CareAPI.refreshTwin());
    // Dispara o popup de emergência/teleconsulta na hora (igual à página de
    // wearables). Sem isto, o alerta só aparecia na próxima carga da página.
    // O cache já foi atualizado acima, então o checkState() lê o estado novo.
    if (window.CareCheckEmergency) window.CareCheckEmergency();
  } catch (e) {}
}
window.simulate = simulate;

// Normaliza os vitais no backend (sem reiniciar o servidor) e fecha o alerta.
async function resetVitals() {
  try {
    await CareAPI._post("/api/wearables/reset");
    setTwin(await CareAPI.refreshTwin());
    closeEmergencyAlert();
    try { sessionStorage.removeItem("cp_emg_dismissed"); } catch (e) {}
    if (window.CareToast) CareToast("Sinais vitais normalizados.", "ok");
  } catch (e) {}
}
window.resetVitals = resetVitals;

// Fecha o popup de emergência (definido no shell.js) e libera o scroll.
function closeEmergencyAlert() {
  const emg = document.getElementById("cp-emergency");
  if (emg && emg.classList.contains("open")) {
    emg.classList.remove("open");
    if (window.CareLockScroll) CareLockScroll(false);
  }
}

// Atualização "viva": mantém o gêmeo respirando e deixa a anomalia injetada se
// dissipar sozinha (mean-reversion no backend). /api/twin/state não usa o
// Gemini, então não há custo de tokens. Pausa com a aba em segundo plano.
let liveTimer = null;
function startLiveUpdates() {
  if (liveTimer) return;
  liveTimer = setInterval(async () => {
    if (document.hidden) return;
    try {
      const st = await CareAPI.refreshTwin();  // busca nova + atualiza o cache
      setTwin(st);
      if (st.mood === "alerta") {
        if (window.CareCheckEmergency) window.CareCheckEmergency();  // reabre se piorar
      } else {
        closeEmergencyAlert();  // fecha o alerta quando o quadro normaliza
      }
    } catch (e) {}
  }, 8000);  // cadência da atualização ao vivo (8s); afeta a velocidade da recuperação
}

/* --------------------------- Wearables (modal) --------------------------- */
async function loadWearables() {
  const wrap = document.getElementById("wearables-list");
  try {
    const [devices, paired] = await Promise.all([CareAPI.catalog(), CareAPI.paired()]);
    wrap.innerHTML = "";
    devices.forEach((d) => {
      const on = paired.includes(d.brand);
      const card = el(`
        <div class="rounded-xl border border-slate-700 bg-slate-800/40 p-4 flex flex-col gap-3">
          <div class="flex items-center justify-between">
            <div class="size-10 rounded-lg grid place-items-center" style="background:${d.color}22;color:${d.color}"><span class="material-symbols-outlined">${d.icon}</span></div>
            <span class="text-[10px] font-bold uppercase px-2 py-1 rounded-full ${on ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-700 text-slate-400"}">${on ? "Conectado" : "Disponível"}</span>
          </div>
          <div><h4 class="font-bold text-sm leading-tight">${d.device_name}</h4><p class="text-[11px] text-slate-500">${d.metrics.length} métricas</p></div>
          <button class="pair-btn py-2 rounded-lg text-xs font-bold transition-colors ${on ? "bg-slate-700 text-slate-300 hover:bg-red-500/20 hover:text-red-300" : "bg-primary text-white hover:bg-primary/80"}">${on ? "Desconectar" : "Parear"}</button>
        </div>`);
      card.querySelector(".pair-btn").addEventListener("click", async () => {
        if (on) await CareAPI.unpair(d.brand); else await CareAPI.pair(d.brand);
        await loadWearables(); refreshTwin();
      });
      wrap.appendChild(card);
    });
  } catch (e) { wrap.innerHTML = `<span class="text-amber-400 text-sm col-span-full">Backend offline.</span>`; }
}
// recarrega a lista sempre que o modal de wearables abre
const _origOpen = window.openModal;
window.openModal = function (id) { _origOpen(id); if (id === "modal-wearables") loadWearables(); };

/* ------------------------------- Init ------------------------------- */
async function init() {
  try { if (window.CareReady) await window.CareReady; } catch (e) {}
  try {
    const s = await CareAPI.aiStatus();
    const enabled = s.enabled;
    const lbl = document.getElementById("ai-label");
    if (lbl) lbl.textContent = enabled ? "Powered by " + s.model : "Modo demo. Configure a chave Gemini";
  } catch (e) {}
  try { profile = await CareAPI.profile(); } catch (e) {}
  refreshAvatar();
  await refreshTwin();
  // Restaura a conversa da sessão; só zera no Ctrl+F5.
  const saved = CareState.getChat();
  if (saved.length) {
    saved.forEach((m) => { bubble(m.role === "user" ? "user" : "model", m.content); history.push(m); });
  } else {
    const oi = "Oi! Eu sou o seu gêmeo digital. Sinto o que você sente com base nos seus wearables. Pergunte como você está.";
    bubble("model", oi);
  }
  startLiveUpdates();
}
init();
