/* CarePlus - Agendamento de consultas (funcional). */

const SPECIALTIES = {
  "Clínica Geral": ["Dr. Ricardo Silva", "Dra. Júlia Mendes", "Dr. Bruno Carvalho"],
  "Cardiologia": ["Dr. Marcos Antunes", "Dra. Helena Costa"],
  "Endocrinologia": ["Dra. Patrícia Lima", "Dr. Felipe Ramos"],
  "Dermatologia": ["Dr. André Souza", "Dra. Carla Nunes"],
  "Pediatria": ["Dra. Camila Rocha"],
  "Pneumologia": ["Dr. Eduardo Pires", "Dra. Aline Castro"],
  "Neurologia": ["Dr. Henrique Dias", "Dra. Larissa Gomes"],
  "Ortopedia": ["Dr. Rodrigo Tavares"],
  "Psiquiatria": ["Dra. Fernanda Lopes", "Dr. Thiago Moraes"],
  "Ginecologia": ["Dra. Beatriz Almeida"],
  "Gastroenterologia": ["Dr. Marcelo Faria"],
  "Nutrição": ["Dra. Renata Vieira"],
};
const SLOTS = ["08:00", "09:00", "10:30", "11:30", "14:00", "15:30", "16:45", "18:00"];

const state = { type: "Telemedicina", specialty: "", doctor: "", date: "", time: "" };

function fillSelect(id, items) {
  const s = document.getElementById(id);
  s.innerHTML = items.map((i) => `<option value="${i}">${i}</option>`).join("");
}

function renderSlots() {
  const wrap = document.getElementById("slots");
  wrap.innerHTML = SLOTS.map((t) =>
    `<button data-time="${t}" class="slot text-xs py-2 rounded-lg border ${state.time === t ? "border-primary bg-primary/15 text-white" : "border-slate-700 bg-slate-800/60 text-slate-300"}">${t}</button>`).join("");
  wrap.querySelectorAll(".slot").forEach((b) => b.addEventListener("click", () => { state.time = b.dataset.time; renderSlots(); summary(); }));
}

function summary() {
  document.getElementById("r-type").textContent = state.type;
  document.getElementById("r-spec").textContent = state.specialty || "-";
  document.getElementById("r-doc").textContent = state.doctor || "-";
  document.getElementById("r-date").textContent = state.date ? new Date(state.date + "T00:00:00").toLocaleDateString("pt-BR") : "-";
  document.getElementById("r-time").textContent = state.time || "-";
}

function refreshDoctors() {
  const docs = SPECIALTIES[state.specialty] || [];
  fillSelect("doctor", docs);
  state.doctor = docs[0] || "";
}

async function confirmar() {
  if (!state.date || !state.time) { if (window.CareToast) CareToast("Escolha a data e o horário.", "warn"); return; }
  let proto = "AG-" + Math.floor(10000 + Math.random() * 89999);
  const msg = `${state.type} de ${state.specialty} com ${state.doctor} em ${new Date(state.date + "T00:00:00").toLocaleDateString("pt-BR")} às ${state.time}.`;
  // Salva a consulta no backend (aparece no Histórico).
  try {
    const appt = await CareAPI.createAppointment({
      type: state.type, specialty: state.specialty, doctor: state.doctor,
      date: state.date, time: state.time, reason: document.getElementById("reason").value.trim(),
    });
    proto = appt.protocol;
  } catch (e) {}
  document.getElementById("ok-msg").textContent = msg;
  document.getElementById("ok-proto").textContent = proto;
  document.getElementById("modal-ok").classList.add("open");
  if (window.CareLockScroll) CareLockScroll(true);
}

function init() {
  document.querySelectorAll(".type-btn").forEach((b) => {
    if (b.hasAttribute("data-default")) b.classList.add("border-primary");
    b.addEventListener("click", () => {
      document.querySelectorAll(".type-btn").forEach((x) => x.classList.remove("border-primary"));
      b.classList.add("border-primary");
      state.type = b.dataset.type; summary();
    });
  });

  const specs = Object.keys(SPECIALTIES);
  fillSelect("specialty", specs);
  state.specialty = specs[0];
  refreshDoctors();

  document.getElementById("specialty").addEventListener("change", (e) => { state.specialty = e.target.value; refreshDoctors(); summary(); });
  document.getElementById("doctor").addEventListener("change", (e) => { state.doctor = e.target.value; summary(); });

  const dt = document.getElementById("date");
  const amanha = new Date(); amanha.setDate(amanha.getDate() + 1);
  dt.min = new Date().toISOString().split("T")[0];
  dt.value = amanha.toISOString().split("T")[0];
  state.date = dt.value;
  dt.addEventListener("change", (e) => { state.date = e.target.value; summary(); });

  renderSlots();
  document.getElementById("confirm").addEventListener("click", confirmar);
  summary();
  preencherMotivoIA();
}

// O Gêmeo "passa o bastão" para o médico: pré-preenche o motivo com o resumo da IA.
async function preencherMotivoIA() {
  try {
    if (window.CareReady) await window.CareReady;
    const st = await CareAPI.twinStateCached();
    if (!st || st.mood === "ótimo" || st.mood === "bem") return;
    const v = st.vitals || {};
    const alertas = (st.alerts || []).join(" ");
    let esp = "Clínica Geral";
    if (v.heart_rate > 110 || v.hrv < 30) esp = "Cardiologia";
    else if (v.spo2 < 94 || v.respiratory_rate > 20) esp = "Clínica Geral";
    // ajusta especialidade sugerida
    if (SPECIALTIES[esp]) {
      state.specialty = esp;
      document.getElementById("specialty").value = esp;
      refreshDoctors();
    }
    const resumo = `Resumo gerado pelo Gêmeo Digital: paciente com estado "${st.mood}". ` +
      `Sinais recentes: FC ${v.heart_rate} bpm, SpO₂ ${v.spo2}%, Temp ${v.body_temp} °C. ` +
      (alertas ? `Pontos de atenção: ${alertas} ` : "") +
      `Encaminhamento sugerido para avaliação de ${esp}. (A IA não diagnostica; conduta a cargo do médico.)`;
    const ta = document.getElementById("reason");
    if (ta && !ta.value.trim()) ta.value = resumo;
    summary();
  } catch (e) {}
}
init();
