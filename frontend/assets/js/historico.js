/* CarePlus - Histórico: timeline agregada (consultas, exames, prescrições)
 * e arquivos em PDF. Comunica-se com as demais páginas via backend. */

let profile = { name: "Paciente" };

const KIND = {
  consulta:   { icon: "stethoscope",    color: "#1152d4" },
  exame:      { icon: "labs",           color: "#06b6d4" },
  prescricao: { icon: "prescriptions",  color: "#10b981" },
  alerta:     { icon: "smart_toy",      color: "#f59e0b" },
};
const BADGE = { ok: "chip-ok", warn: "chip-warn", bad: "chip-bad", muted: "chip-muted" };
// Quem realizou a ação: a IA monitora e alerta; o médico diagnostica e prescreve.
const ACTOR = {
  ia:      { label: "Ação da IA",     icon: "smart_toy", color: "#f59e0b" },
  medico:  { label: "Ação médica",    icon: "stethoscope", color: "#10b981" },
  sistema: { label: "Registro",       icon: "description", color: "#64748b" },
};

function el(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }
function fmt(iso) { try { return new Date(iso + "T00:00:00").toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" }); } catch (e) { return iso; } }

async function loadTimeline() {
  const wrap = document.getElementById("timeline");
  try {
    const items = await CareAPI.history();
    if (!items.length) { wrap.innerHTML = "<span class='text-slate-500 text-sm'>Sem registros ainda.</span>"; return; }
    wrap.innerHTML = "";
    items.forEach((it) => {
      const k = KIND[it.kind] || KIND.consulta;
      const ac = ACTOR[it.actor] || ACTOR.sistema;
      const chip = it.badge ? `<span class="chip ${BADGE[it.badge_kind] || "chip-muted"}">${it.badge}</span>` : "";
      const actorTag = `<span class="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full" style="background:${ac.color}1f;color:${ac.color}"><span class="material-symbols-outlined" style="font-size:13px">${ac.icon}</span>${ac.label}</span>`;
      wrap.appendChild(el(`
        <div class="tl-item">
          <div class="tl-dot" style="background:${ac.color}22;color:${ac.color}"><span class="material-symbols-outlined" style="font-size:18px">${k.icon}</span></div>
          <div class="card p-4">
            <div class="flex items-start justify-between gap-2 mb-1">
              <div><h4 class="font-bold leading-tight">${it.title}</h4><p class="text-xs text-slate-400">${it.subtitle}</p></div>
              <span class="text-xs text-slate-500 whitespace-nowrap">${fmt(it.date)}</span>
            </div>
            <p class="text-sm text-slate-300 mb-2">${it.detail}</p>
            <div class="flex items-center gap-2">${actorTag}${chip}</div>
          </div>
        </div>`));
    });
  } catch (e) {
    wrap.innerHTML = "<span class='text-amber-400 text-sm'>Backend offline. Inicie a API (python run.py).</span>";
  }
}

async function loadFiles() {
  const wrap = document.getElementById("files");
  try {
    const [prescriptions, exams] = await Promise.all([CareAPI.prescriptions(), CareAPI.exams()]);
    wrap.innerHTML = "";

    prescriptions.forEach((p) => {
      const card = el(`
        <button class="flex items-center gap-3 p-3 rounded-xl bg-slate-800/40 border border-slate-700/40 hover:border-primary/40 transition-colors text-left">
          <span class="size-9 grid place-items-center rounded-lg bg-emerald-500/15 text-emerald-400"><span class="material-symbols-outlined" style="font-size:18px">prescriptions</span></span>
          <span class="flex-1"><span class="block text-sm font-medium">Prescricao_${p.date}.pdf</span><span class="block text-[11px] text-slate-500">${p.doctor}</span></span>
          <span class="material-symbols-outlined text-slate-400" style="font-size:18px">download</span>
        </button>`);
      card.addEventListener("click", () => prescriptionPdf(p));
      wrap.appendChild(card);
    });

    exams.forEach((ex) => {
      const card = el(`
        <button class="flex items-center gap-3 p-3 rounded-xl bg-slate-800/40 border border-slate-700/40 hover:border-primary/40 transition-colors text-left">
          <span class="size-9 grid place-items-center rounded-lg bg-cyan-500/15 text-cyan-400"><span class="material-symbols-outlined" style="font-size:18px">description</span></span>
          <span class="flex-1"><span class="block text-sm font-medium">${ex.uploaded ? ex.name : ex.name + ".pdf"}</span><span class="block text-[11px] text-slate-500">${ex.category}</span></span>
          <a href="exames.html" class="material-symbols-outlined text-slate-400" style="font-size:18px" onclick="event.stopPropagation()">open_in_new</a>
        </button>`);
      wrap.appendChild(card);
    });

    const emitir = el(`
      <button id="btn-presc" class="btn btn-primary w-full mt-1"><span class="material-symbols-outlined" style="font-size:18px">note_add</span> Emitir prescrição (pós-consulta)</button>`);
    emitir.addEventListener("click", async () => {
      emitir.disabled = true; emitir.style.opacity = ".6";
      try { await CareAPI.createPrescription(); await loadFiles(); await loadTimeline(); }
      catch (e) {} finally { emitir.disabled = false; emitir.style.opacity = "1"; }
    });
    wrap.appendChild(emitir);
  } catch (e) {
    wrap.innerHTML = "<span class='text-amber-400 text-sm'>Backend offline.</span>";
  }
}

function prescriptionPdf(p) {
  const linhas = p.items.map((i) => `<tr><td>${i.name}</td><td>${i.instruction}</td></tr>`).join("");
  // Nome do médico para a assinatura cursiva (separa o nome do CRM, se houver).
  const docName = String(p.doctor || "Equipe Médica Care Plus").split("·")[0].trim();
  const html = `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>Prescrição CarePlus</title>
    <link href="https://fonts.googleapis.com/css2?family=Great+Vibes&display=swap" rel="stylesheet">
    <style>
      *{font-family:Arial,Helvetica,sans-serif;color:#0f172a}
      body{padding:40px;max-width:760px;margin:auto}
      .hd{display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #1152d4;padding-bottom:12px;margin-bottom:20px}
      .hd img{height:54px}
      h1{color:#1152d4;font-size:20px;margin:0}
      table{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}
      td{padding:8px;border-bottom:1px solid #eef2f7}
      td:first-child{font-weight:bold;width:45%}
      .meta{font-size:13px;color:#475569;margin-bottom:6px}
      .sign{margin-top:58px;width:300px;text-align:center}
      .sign-name{font-family:'Great Vibes',cursive;font-size:36px;line-height:1.1;color:#0f172a;margin-bottom:2px}
      .sign-line{border-top:1px solid #94a3b8;padding-top:6px;font-size:13px;color:#0f172a}
      .foot{margin-top:30px;font-size:10px;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:10px}
    </style></head><body>
    <div class="hd"><div><h1>Prescrição Digital</h1><div class="meta">CarePlus Health</div></div></div>
    <p class="meta"><b>Paciente:</b> ${profile.name || "-"}</p>
    <p class="meta"><b>Médico:</b> ${p.doctor}</p>
    <p class="meta"><b>Data:</b> ${fmt(p.date)}</p>
    <table><tr><td>Medicamento</td><td>Orientação</td></tr>${linhas}</table>
    <p class="meta" style="margin-top:16px"><b>Observações:</b> ${p.notes}</p>
    <div class="sign"><div class="sign-name">${docName}</div><div class="sign-line">${p.doctor}</div><span style="font-size:11px;color:#94a3b8">Assinatura digital validada</span></div>
    <div class="foot">Documento gerado pelo CarePlus. A prescrição é de responsabilidade do médico emissor. A IA não prescreve.</div>
    <script>function go(){window.print();}if(document.fonts&&document.fonts.ready){document.fonts.ready.then(function(){setTimeout(go,200);});}else{window.onload=go;}<\/script>
    </body></html>`;
  const w = window.open("", "_blank");
  w.document.write(html); w.document.close();
}

async function init() {
  try { if (window.CareReady) await window.CareReady; } catch (e) {}
  try { profile = await CareAPI.profile(); } catch (e) {}
  await loadTimeline();
  await loadFiles();
}
init();
