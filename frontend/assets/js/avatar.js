/* CarePlus - construtor de avatar dinâmico via API DiceBear (avataaars).
 * O avatar é humano, personalizável e a EXPRESSÃO reflete a saúde do gêmeo:
 * quanto pior o estado, mais preocupada/triste a face. */

const DICEBEAR = "https://api.dicebear.com/9.x/avataaars/svg";

// Expressão conforme o humor calculado pelo backend.
// O fundo é sempre transparente (sem aquele fundo verde). O humor é
// transmitido pela expressão e pelo anel/cores do card.
const MOOD_FACE = {
  "ótimo":   { mouth: "smile",   eyes: "happy",   eyebrows: "default" },
  "bem":     { mouth: "default", eyes: "default", eyebrows: "default" },
  "atenção": { mouth: "serious", eyes: "squint",  eyebrows: "raisedExcited" },
  "alerta":  { mouth: "sad",     eyes: "cry",     eyebrows: "sadConcerned" },
};

const DEFAULT_CUSTOM = {
  top: "shortFlat",
  hairColor: "2c1b18",
  skinColor: "edb98a",
  clothing: "blazerAndShirt",
  clothesColor: "5199e4",
  accessories: "blank",
  facialHair: "blank",
  facialHairColor: "2c1b18",
};

const STORAGE_KEY = "careplus_avatar_v1";

function loadAvatarConfig() {
  try {
    return { ...DEFAULT_CUSTOM, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") };
  } catch (e) {
    return { ...DEFAULT_CUSTOM };
  }
}

function saveAvatarConfig(cfg) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
}

function buildAvatarUrl(seed, custom, mood) {
  const face = MOOD_FACE[mood] || MOOD_FACE["bem"];
  const c = { ...DEFAULT_CUSTOM, ...(custom || {}) };
  const params = new URLSearchParams({
    seed: seed || "CarePlus",
    mouth: face.mouth,
    eyes: face.eyes,
    eyebrows: face.eyebrows,
    backgroundColor: "transparent",
    top: c.top,
    hairColor: c.hairColor,
    skinColor: c.skinColor,
    clothing: c.clothing,
    clothesColor: c.clothesColor,
    radius: "12",
  });
  // "blank" NÃO é um valor válido para accessories/facialHair na DiceBear.
  // Para ocultar, usamos a probabilidade 0 (sem enviar o valor inválido).
  if (c.accessories && c.accessories !== "blank") {
    params.set("accessories", c.accessories);
    params.set("accessoriesProbability", "100");
  } else {
    params.set("accessoriesProbability", "0");
  }
  if (c.facialHair && c.facialHair !== "blank") {
    params.set("facialHair", c.facialHair);
    params.set("facialHairProbability", "100");
    if (c.facialHairColor) params.set("facialHairColor", c.facialHairColor);
  } else {
    params.set("facialHairProbability", "0");
  }
  return DICEBEAR + "?" + params.toString();
}

// Opções oferecidas no modal de personalização.
const AVATAR_OPTIONS = {
  top: [
    { v: "shortFlat", label: "Curto" },
    { v: "shortCurly", label: "Cacheado" },
    { v: "theCaesar", label: "Raspado" },
    { v: "longButNotTooLong", label: "Longo" },
    { v: "bob", label: "Chanel" },
    { v: "bun", label: "Coque" },
    { v: "hat", label: "Touca" },
    { v: "turban", label: "Turbante" },
  ],
  hairColor: ["2c1b18", "724133", "b58143", "d6b370", "a55728", "ecdcbf", "e8e1e1", "f59797"],
  skinColor: ["ffdbb4", "edb98a", "fd9841", "d08b5b", "ae5d29", "614335"],
  clothing: [
    { v: "blazerAndShirt", label: "Blazer" },
    { v: "hoodie", label: "Moletom" },
    { v: "shirtCrewNeck", label: "Camiseta" },
    { v: "collarAndSweater", label: "Suéter" },
    { v: "overall", label: "Jardineira" },
    { v: "graphicShirt", label: "Estampada" },
  ],
  clothesColor: ["5199e4", "25557c", "3c4f5c", "262e33", "929598", "65c9ff", "ff5c5c", "a7ffc4", "ffafb9", "ffffb1"],
  accessories: [
    { v: "blank", label: "Nenhum" },
    { v: "prescription02", label: "Óculos grau" },
    { v: "round", label: "Redondo" },
    { v: "sunglasses", label: "Sol" },
    { v: "wayfarers", label: "Wayfarer" },
  ],
  facialHair: [
    { v: "blank", label: "Nenhuma" },
    { v: "beardLight", label: "Barba leve" },
    { v: "beardMedium", label: "Barba média" },
    { v: "beardMajestic", label: "Barba cheia" },
    { v: "moustacheFancy", label: "Bigode" },
  ],
  facialHairColor: ["2c1b18", "724133", "b58143", "d6b370", "a55728", "ecdcbf", "e8e1e1"],
};

// Predefinições por sexo (apenas ponto de partida; o usuário ajusta tudo).
const SEX_PRESETS = {
  masculino: { top: "shortFlat", facialHair: "beardLight" },
  feminino:  { top: "longButNotTooLong", facialHair: "blank" },
  outro:     { top: "shortCurly", facialHair: "blank" },
};

// Gera uma aparência aleatória (cabelo, pele, roupa, cores, barba).
function randomAvatarConfig() {
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
  const O = AVATAR_OPTIONS;
  const comBarba = Math.random() < 0.45;
  return {
    top: pick(O.top).v,
    hairColor: pick(O.hairColor),
    skinColor: pick(O.skinColor),
    clothing: pick(O.clothing).v,
    clothesColor: pick(O.clothesColor),
    accessories: Math.random() < 0.35 ? pick(O.accessories.filter((a) => a.v !== "blank")).v : "blank",
    facialHair: comBarba ? pick(O.facialHair.filter((f) => f.v !== "blank")).v : "blank",
    facialHairColor: pick(O.facialHairColor),
  };
}

window.CareAvatar = { buildAvatarUrl, loadAvatarConfig, saveAvatarConfig, AVATAR_OPTIONS, MOOD_FACE, SEX_PRESETS, randomAvatarConfig };

// No recarregamento (Ctrl+F5), sorteia uma nova aparência junto da nova identidade.
try {
  if (window.CareState && CareState.isReload) {
    saveAvatarConfig(randomAvatarConfig());
  }
} catch (e) {}
