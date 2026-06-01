/* CarePlus - Medicamentos & Biometria: integração real com /api/twin/profile.
 * Cada alteração faz um PUT e o motor do gêmeo recalcula a saúde do paciente. */

let profile = null;

function el(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }
function flash(msg) {
  const f = document.getElementById("save-flash");
  document.getElementById("save-flash-msg").textContent = msg;
  f.classList.remove("hidden");
  clearTimeout(window.__ff); window.__ff = setTimeout(() => f.classList.add("hidden"), 2600);
}

function renderMeds() {
  const list = document.getElementById("med-list");
  const meds = (profile && profile.medications) || [];
  document.getElementById("med-count").textContent = meds.length;
  if (!meds.length) { list.innerHTML = `<span class="text-slate-500 text-sm">Nenhum medicamento cadastrado.</span>`; return; }
  list.innerHTML = "";
  meds.forEach((m, i) => {
    const row = el(`
      <div class="flex items-center justify-between p-3 rounded-xl bg-slate-800/40 border border-slate-700/40">
        <div class="flex items-center gap-3">
          <span class="size-9 grid place-items-center rounded-lg bg-primary/15 text-primary"><span class="material-symbols-outlined" style="font-size:18px">pill</span></span>
          <span class="font-medium text-sm">${m}</span>
        </div>
        <button class="rm text-slate-400 hover:text-red-400 transition-colors"><span class="material-symbols-outlined" style="font-size:20px">delete</span></button>
      </div>`);
    row.querySelector(".rm").addEventListener("click", () => removeMed(i));
    list.appendChild(row);
  });
}

async function save(reason) {
  try {
    profile = await CareAPI.updateProfile(profile);
    renderMeds();
    flash(reason || "Dados atualizados, gêmeo recalculado.");
    return true;
  } catch (e) { flash("Erro ao salvar (backend offline)."); return false; }
}

async function addMed() {
  const nome = document.getElementById("med-nome").value.trim();
  const dose = document.getElementById("med-dose").value.trim();
  const hora = document.getElementById("med-hora").value.trim();
  const freq = document.getElementById("med-freq").value;
  if (!nome) { document.getElementById("med-nome").focus(); return; }

  // IA verifica interações ANTES de salvar (prescrição segura).
  const ok = await checkInteractionFlow(nome);
  if (!ok) return; // usuário cancelou

  let txt = nome;
  if (dose) txt += " " + dose;
  const det = [freq, hora ? "às " + hora : ""].filter(Boolean).join(" · ");
  if (det) txt += " (" + det + ")";
  profile.medications = [...(profile.medications || []), txt];
  document.getElementById("med-nome").value = "";
  document.getElementById("med-dose").value = "";
  document.getElementById("med-hora").value = "";
  await save("Medicamento adicionado.");
}

// Modal de verificação de interações: mostra "IA analisando..." e o resultado.
function checkInteractionFlow(nome) {
  return new Promise(async (resolve) => {
    const m = document.getElementById("modal-interacao");
    const body = document.getElementById("interacao-body");
    const foot = document.getElementById("interacao-foot");
    body.innerHTML = `<div class="flex items-center gap-3 text-slate-300 text-sm">
      <span class="size-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin"></span>
      <span><span class="material-symbols-outlined align-middle text-[18px] text-primary">settings</span> IA analisando interações de <b>${nome}</b>…</span></div>`;
    foot.innerHTML = "";
    m.classList.add("open"); if (window.CareLockScroll) CareLockScroll(true);

    let res;
    try { res = await CareAPI.checkInteractions(nome); } catch (e) { res = { has_warning: false, warnings: [] }; }
    await new Promise((r) => setTimeout(r, 1100)); // tempo p/ visualizar a análise

    const close = (val) => { m.classList.remove("open"); if (window.CareLockScroll) CareLockScroll(false); resolve(val); };

    if (res.has_warning) {
      body.innerHTML = `
        <div class="flex items-start gap-3 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-200 text-sm">
          <span class="material-symbols-outlined text-red-400">warning</span>
          <div><b>Atenção: possível interação detectada.</b>
            <ul class="mt-1 space-y-1 list-disc pl-4">${res.warnings.map((w) => `<li>${w}</li>`).join("")}</ul>
            <p class="mt-2 text-red-300/80">Consulte seu médico antes de usar. A IA apenas alerta, não prescreve.</p></div>
        </div>`;
      foot.innerHTML = `
        <button id="int-cancel" class="btn btn-soft flex-1">Cancelar</button>
        <button id="int-ok" class="btn btn-primary flex-1">Adicionar mesmo assim</button>`;
      document.getElementById("int-cancel").addEventListener("click", () => close(false));
      document.getElementById("int-ok").addEventListener("click", () => close(true));
    } else {
      body.innerHTML = `<div class="flex items-center gap-3 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-200 text-sm">
        <span class="material-symbols-outlined text-emerald-400">check_circle</span>
        <span>Nenhuma interação relevante encontrada com seus medicamentos atuais.</span></div>`;
      foot.innerHTML = `<button id="int-ok" class="btn btn-primary w-full">Adicionar</button>`;
      document.getElementById("int-ok").addEventListener("click", () => close(true));
    }
  });
}
async function removeMed(i) {
  profile.medications = profile.medications.filter((_, idx) => idx !== i);
  await save("Medicamento removido.");
}

function fillBio() {
  document.getElementById("bio-weight").value = profile.weight_kg ?? "";
  document.getElementById("bio-height").value = profile.height_cm ?? "";
  document.getElementById("bio-allergies").value = (profile.allergies || []).join(", ");
  document.getElementById("bio-symptoms").value = (profile.symptoms || []).join(", ");
}

async function saveBio() {
  const toList = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);
  profile.weight_kg = parseFloat(document.getElementById("bio-weight").value) || profile.weight_kg;
  profile.height_cm = parseInt(document.getElementById("bio-height").value) || profile.height_cm;
  profile.allergies = toList(document.getElementById("bio-allergies").value);
  profile.symptoms = toList(document.getElementById("bio-symptoms").value);
  const ok = await save("Biometria atualizada.");
  if (ok) {
    const fb = document.getElementById("bio-feedback");
    fb.classList.remove("hidden");
    try {
      const st = await CareAPI.twinState();
      const colors = { "ótimo": "text-emerald-400", "bem": "text-primary", "atenção": "text-amber-400", "alerta": "text-red-400" };
      fb.innerHTML = `Seu gêmeo agora está <b class="${colors[st.mood] || ''}">${st.mood}</b> (saúde ${st.health_score}/100).`;
    } catch (e) {}
  }
}

async function init() {
  try { if (window.CareReady) await window.CareReady; } catch (e) {}
  try {
    profile = await CareAPI.profile();
    renderMeds();
    fillBio();
  } catch (e) {
    document.getElementById("med-list").innerHTML = `<span class="text-amber-400 text-sm">Backend offline. Inicie a API (python run.py).</span>`;
    return;
  }
  document.getElementById("med-add").addEventListener("click", addMed);
  document.getElementById("med-nome").addEventListener("keydown", (e) => { if (e.key === "Enter") addMed(); });
  document.getElementById("bio-save").addEventListener("click", saveBio);
}
init();
