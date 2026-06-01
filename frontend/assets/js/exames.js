/* CarePlus - Exames: lista, detalhe e interpretação por IA (integrado ao backend). */

let panels = [];
let activeId = null;

function el(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }

const STATUS = {
  normal: { chip: "chip-ok",   label: "Normal", color: "#10b981" },
  alto:   { chip: "chip-bad",  label: "Alto",   color: "#ef4444" },
  baixo:  { chip: "chip-warn", label: "Baixo",  color: "#f59e0b" },
};

function fmtDate(iso) {
  try { return new Date(iso + "T00:00:00").toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" }); }
  catch (e) { return iso; }
}
function fmtNum(n) { return Number.isInteger(n) ? n.toLocaleString("pt-BR") : n; }

async function loadSummary() {
  try {
    const s = await CareAPI.examsSummary();
    document.getElementById("sum-paineis").textContent = s.paineis;
    document.getElementById("sum-marcadores").textContent = s.marcadores;
    document.getElementById("sum-alterados").textContent = s.alterados;
  } catch (e) {}
}

function renderList() {
  const wrap = document.getElementById("panel-list");
  wrap.innerHTML = "";
  panels.forEach((p) => {
    const alterados = p.results.filter((r) => r.status !== "normal").length;
    const active = p.id === activeId;
    const item = el(`
      <button class="text-left p-3 rounded-xl border transition-all ${active ? "border-primary bg-primary/10" : "border-slate-700/50 bg-slate-800/30 hover:bg-slate-800/60"}">
        <div class="flex items-center justify-between gap-2">
          <span class="font-bold text-sm">${p.name}</span>
          ${alterados ? `<span class="chip chip-warn">${alterados} alt.</span>` : `<span class="chip chip-ok">ok</span>`}
        </div>
        <div class="text-[11px] text-slate-500 mt-1">${p.category} · ${fmtDate(p.collected_at)}</div>
      </button>`);
    item.addEventListener("click", () => { activeId = p.id; renderList(); renderDetail(p); });
    wrap.appendChild(item);
  });
}

function renderDetail(p) {
  const d = document.getElementById("panel-detail");

  if (p.uploaded || !p.results.length) {
    d.innerHTML = `
      <div class="flex items-start justify-between gap-3 mb-4">
        <div>
          <h2 class="text-xl font-black">${p.name}</h2>
          <p class="text-slate-400 text-sm">${p.category} · enviado em ${fmtDate(p.collected_at)}</p>
        </div>
        <span class="chip chip-muted shrink-0">Documento</span>
      </div>
      <div class="flex flex-col items-center justify-center text-center py-8 rounded-xl bg-slate-800/30 border border-dashed border-slate-700">
        <span class="material-symbols-outlined text-primary" style="font-size:48px">picture_as_pdf</span>
        <p class="text-slate-300 text-sm mt-2 max-w-sm">PDF recebido e guardado no seu dispositivo. A IA não lê nem diagnostica o arquivo; leve-o à sua teleconsulta para o médico avaliar.</p>
      </div>`;
    return;
  }

  const rows = p.results.map((r) => {
    const st = STATUS[r.status] || STATUS.normal;
    const span = r.ref_high - r.ref_low || 1;
    let pct = ((r.value - r.ref_low) / span) * 100;
    pct = Math.max(2, Math.min(98, pct));
    return `
      <div class="py-3 border-b border-slate-800 last:border-0">
        <div class="flex items-center justify-between mb-1.5">
          <span class="font-medium text-sm">${r.name}</span>
          <span class="text-sm"><b>${fmtNum(r.value)}</b> <span class="text-slate-500 text-xs">${r.unit}</span> <span class="chip ${st.chip} ml-1">${st.label}</span></span>
        </div>
        <div class="relative h-2 rounded-full bg-slate-700/50 overflow-hidden">
          <div class="absolute inset-y-0 left-1/4 right-1/4 bg-emerald-500/15"></div>
          <div class="absolute inset-y-0 left-0 rounded-full" style="width:${pct}%;background:${st.color}99"></div>
          <div class="absolute top-1/2 -translate-y-1/2 size-3 rounded-full border-2 border-slate-900" style="left:calc(${pct}% - 6px);background:${st.color}"></div>
        </div>
        <div class="text-[10px] text-slate-500 mt-1">Referência: ${fmtNum(r.ref_low)}–${fmtNum(r.ref_high)} ${r.unit}</div>
      </div>`;
  }).join("");

  d.innerHTML = `
    <div class="flex items-start justify-between gap-3 mb-4">
      <div>
        <h2 class="text-xl font-black">${p.name}</h2>
        <p class="text-slate-400 text-sm">${p.category} · coletado em ${fmtDate(p.collected_at)} · ${p.lab}</p>
      </div>
      <button id="btn-interpret" class="btn btn-primary shrink-0"><span class="material-symbols-outlined" style="font-size:18px">auto_awesome</span> Interpretar com IA</button>
    </div>
    <div>${rows}</div>
    <div id="interpret-box" class="hidden mt-5 p-4 rounded-xl bg-primary/10 border border-primary/20 text-sm text-slate-200 leading-relaxed whitespace-pre-wrap"></div>`;

  document.getElementById("btn-interpret").addEventListener("click", () => interpret(p.id));
}

async function interpret(id) {
  const box = document.getElementById("interpret-box");
  const btn = document.getElementById("btn-interpret");
  box.classList.remove("hidden");
  box.textContent = "Analisando seus resultados…";
  btn.disabled = true; btn.style.opacity = ".6";
  try {
    const r = await CareAPI.interpretExam(id);
    box.textContent = r.interpretation + "\n\n" + r.powered_by;
  } catch (e) {
    box.textContent = "Não foi possível interpretar (backend offline).";
  } finally { btn.disabled = false; btn.style.opacity = "1"; }
}

async function loadPanels() {
  panels = await CareAPI.exams();
  renderList();
}

function setupUpload() {
  const btn = document.getElementById("exam-upload");
  const file = document.getElementById("exam-file");
  if (!btn || !file) return;
  btn.addEventListener("click", () => file.click());
  file.addEventListener("change", async () => {
    if (!file.files.length) return;
    const name = file.files[0].name;
    btn.disabled = true; btn.style.opacity = ".6";
    try {
      const novo = await CareAPI.uploadExam(name);
      await loadPanels();
      await loadSummary();
      activeId = novo.id; renderList(); renderDetail(novo);
    } catch (e) { if (window.CareToast) CareToast("Não foi possível enviar (backend offline).", "bad"); }
    finally { btn.disabled = false; btn.style.opacity = "1"; file.value = ""; }
  });
}

async function init() {
  setupUpload();
  await loadSummary();
  try {
    await loadPanels();
    if (!panels.length) { document.getElementById("panel-list").innerHTML = "<span class='text-slate-500 text-sm'>Nenhum exame.</span>"; return; }
    activeId = panels[0].id;
    renderList();
    renderDetail(panels[0]);
  } catch (e) {
    document.getElementById("panel-list").innerHTML = "<span class='text-amber-400 text-sm'>Backend offline. Inicie a API (python run.py).</span>";
    document.getElementById("panel-detail").innerHTML = "<span class='text-amber-400 text-sm'>Sem conexão com o servidor.</span>";
  }
}
init();
