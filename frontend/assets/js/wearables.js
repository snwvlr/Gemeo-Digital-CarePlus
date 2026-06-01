/* CarePlus - página de wearables: catálogo, pareamento e stream ao vivo. */

const METRIC_META = {
  heart_rate:      { label: "Freq. Cardíaca", unit: "bpm", icon: "favorite",       color: "text-red-500" },
  spo2:            { label: "Oxigênio (SpO₂)", unit: "%",   icon: "air",            color: "text-cyan-500" },
  steps:           { label: "Passos",          unit: "",    icon: "directions_walk", color: "text-emerald-500" },
  calories:        { label: "Calorias",        unit: "kcal", icon: "local_fire_department", color: "text-orange-500" },
  sleep_hours:     { label: "Sono",            unit: "h",   icon: "bedtime",        color: "text-indigo-400" },
  stress:          { label: "Estresse",        unit: "/100", icon: "psychology",    color: "text-amber-500" },
  hrv:             { label: "HRV",             unit: "ms",  icon: "monitor_heart",  color: "text-pink-400" },
  body_temp:       { label: "Temperatura",     unit: "°C",  icon: "thermostat",     color: "text-rose-400" },
  respiratory_rate:{ label: "Respiração",      unit: "rpm", icon: "pulmonology",    color: "text-teal-400" },
};

let pairedBrands = [];

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstChild;
}

async function loadAIBadge() {
  try {
    const s = await CareAPI.aiStatus();
    const badge = document.getElementById("ai-badge");
    const dot = s.enabled ? "bg-emerald-500" : "bg-amber-500";
    const txt = s.enabled ? s.model : "Modo demo (configure a chave Gemini)";
    badge.innerHTML = `<span class="size-2 ${dot} rounded-full"></span> ${txt}`;
  } catch (e) { /* backend offline */ }
}

async function loadCatalog() {
  const wrap = document.getElementById("catalog");
  try {
    const [devices, paired] = await Promise.all([CareAPI.catalog(), CareAPI.paired()]);
    pairedBrands = paired;
    wrap.innerHTML = "";
    devices.forEach((d) => {
      const isPaired = pairedBrands.includes(d.brand);
      const card = el(`
        <div class="glass-card rounded-2xl p-5 flex flex-col gap-3">
          <div class="flex items-center justify-between">
            <div class="size-12 rounded-xl flex items-center justify-center" style="background:${d.color}22;color:${d.color}">
              <span class="material-symbols-outlined">${d.icon}</span>
            </div>
            <span class="status-pill text-[10px] font-bold uppercase px-2 py-1 rounded-full ${isPaired ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-400'}">${isPaired ? 'Conectado' : 'Disponível'}</span>
          </div>
          <div>
            <h3 class="font-bold text-white leading-tight">${d.device_name}</h3>
            <p class="text-xs text-slate-500 mt-1">${d.metrics.length} métricas</p>
          </div>
          <button class="pair-btn mt-2 w-full py-2 rounded-lg text-xs font-bold transition-colors ${isPaired ? 'bg-slate-800 text-slate-300 hover:bg-red-500/20 hover:text-red-400' : 'bg-primary text-white hover:bg-primary/80'}">
            ${isPaired ? 'Desconectar' : 'Parear'}
          </button>
        </div>`);
      card.querySelector(".pair-btn").addEventListener("click", () => togglePair(d, isPaired));
      wrap.appendChild(card);
    });
  } catch (e) {
    wrap.innerHTML = `<div class="col-span-full text-amber-400 text-sm">Backend offline. Inicie a API: <code>python run.py</code></div>`;
  }
}

async function togglePair(device, isPaired) {
  if (isPaired) {
    await CareAPI.unpair(device.brand);
    await loadCatalog();
    return;
  }
  const ov = document.getElementById("pair-overlay");
  document.getElementById("pair-title").textContent = "Pareando " + device.device_name + "…";
  document.getElementById("pair-msg").textContent = "Estabelecendo conexão Bluetooth…";
  ov.classList.remove("hidden"); ov.classList.add("flex");
  await CareAPI.pair(device.brand);
  setTimeout(async () => {
    document.getElementById("pair-title").textContent = "Conectado!";
    document.getElementById("pair-msg").textContent = device.device_name + " está enviando dados.";
    setTimeout(() => { ov.classList.add("hidden"); ov.classList.remove("flex"); loadCatalog(); }, 1100);
  }, 1600);
}

function renderVitals(reading) {
  const grid = document.getElementById("vitals-grid");
  const v = reading.vitals;
  const order = ["heart_rate", "spo2", "body_temp", "respiratory_rate", "steps", "calories", "sleep_hours", "stress", "hrv"];
  grid.innerHTML = "";
  order.forEach((key) => {
    const m = METRIC_META[key];
    const val = v[key];
    grid.appendChild(el(`
      <div class="glass-card rounded-xl p-4 metric">
        <div class="flex items-center gap-2 mb-2 ${m.color}">
          <span class="material-symbols-outlined text-lg">${m.icon}</span>
          <span class="text-xs text-slate-400 font-medium">${m.label}</span>
        </div>
        <div class="text-2xl font-black text-white">${val}<span class="text-sm font-normal text-slate-500 ml-1">${m.unit}</span></div>
      </div>`));
  });
}

async function poll() {
  try {
    const stream = await CareAPI.stream();
    if (stream && stream.length) {
      renderVitals(stream[0]);
      document.getElementById("live-label").textContent =
        "transmitindo · " + stream.map((s) => s.device_name).join(", ");
    }
  } catch (e) {
    document.getElementById("live-dot").className = "size-2 bg-slate-500 rounded-full";
    document.getElementById("live-label").textContent = "backend offline";
    document.getElementById("live-label").className = "text-slate-500 font-medium";
  }
}

async function injetar(kind) {
  try {
    await CareAPI.simulate(kind);
    await poll();
    // Atualiza o snapshot do gêmeo e revalida o alerta de emergência.
    if (CareAPI.refreshTwin) await CareAPI.refreshTwin();
    if (window.CareCheckEmergency) window.CareCheckEmergency();
  } catch (e) {}
}
window.injetar = injetar;

// init
loadAIBadge();
loadCatalog();
poll();
setInterval(poll, 3000);
