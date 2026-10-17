// Datos y cálculo de presentación del visor de potencia por banda (mapas 2D y cabeza 3D).
// No calcula potencias: recibe de la librería el valor medido en cada electrodo y solo
// lo interpola de forma suave sobre la superficie para poder dibujarlo. Es orientativo.

const datos = JSON.parse(document.getElementById("datos-visor").textContent);
export const geo = datos.geometria;
export const bandas = datos.bandas;

// Escala inferno recortada (la misma que el servidor, grabaciones/analisis_espectral.py).
export const ESCALA = ["#1b0c41", "#4a0c6b", "#781c6d", "#a52c60", "#cf4446",
                       "#ed6925", "#fb9b06", "#f7d13d", "#fcffa4"];
const ESCALA_RGB = ESCALA.map(hexARgb);

// Anchura (rad) del núcleo gaussiano de la interpolación. Lejos de todo sensor válido la
// superficie se muestra apagada (ver `opacidad`), no inventada.
const SIGMA = 0.8;

export const estado = { metrica: "rel", escala: "banda", banda: datos.banda_inicial, zona: null };
const oyentes = new Set();
export function suscribir(fn) { oyentes.add(fn); }
export function cambiar(parcial) {
  Object.assign(estado, parcial);
  oyentes.forEach(function (fn) { fn(); });
}

export const electrodos = datos.electrodos.map(function (e) {
  const g = geo.canales[e.canal];
  return Object.assign({}, e, { u: g.u, p2: g.p2 });
});

export function hexARgb(hex) {
  return [1, 3, 5].map(function (i) { return parseInt(hex.slice(i, i + 2), 16); });
}

export function css(nombre) {
  return getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
}

export function fmt(n, decimales) {
  return n.toLocaleString("es-ES", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
}

export function decimales() { return estado.metrica === "rel" ? 1 : 2; }
export function unidad() { return estado.metrica === "rel" ? "%" : "log₁₀ V²"; }
export function textoValor(v) { return fmt(v, decimales()) + (estado.metrica === "rel" ? " %" : " log₁₀ V²"); }

// Valor medido de un electrodo en una banda (null si fue descartado o no hay dato).
export function valor(e, banda) {
  if (!e.valido) return null;
  const v = estado.metrica === "rel" ? e.rel[banda] : e.log_abs[banda];
  if (v === null || v === undefined) return null;
  return estado.metrica === "rel" ? v * 100 : v;
}

export function validos(banda) {
  return electrodos.filter(function (e) { return valor(e, banda) !== null; });
}

// Rango de color: de esa banda, o común a las cuatro.
export function rango(banda) {
  const lista = estado.escala === "comun" ? bandas.map(function (b) { return b.clave; }) : [banda];
  let min = Infinity, max = -Infinity;
  lista.forEach(function (b) {
    electrodos.forEach(function (e) {
      const v = valor(e, b);
      if (v !== null) { min = Math.min(min, v); max = Math.max(max, v); }
    });
  });
  if (!isFinite(min)) return [0, 1];
  if (max - min < 1e-9) { min -= 0.5; max += 0.5; }
  return [min, max];
}

export function colorDeT(t) {
  t = Math.min(1, Math.max(0, t)) * (ESCALA_RGB.length - 1);
  const i = Math.min(Math.floor(t), ESCALA_RGB.length - 2), f = t - i;
  return ESCALA_RGB[i].map(function (c, k) { return c + (ESCALA_RGB[i + 1][k] - c) * f; });
}

export function colorDeValor(v, min, max) { return colorDeT((v - min) / (max - min)); }

// Valor suavizado en una dirección u de la superficie y confianza (cercanía al sensor válido más próximo).
export function estimar(u, puntos) {
  let sw = 0, sv = 0, amin = Infinity;
  for (let i = 0; i < puntos.length; i++) {
    const p = puntos[i];
    const d = Math.min(1, Math.max(-1, u[0] * p.u[0] + u[1] * p.u[1] + u[2] * p.u[2]));
    const ang = Math.acos(d);
    const w = Math.exp(-(ang * ang) / (SIGMA * SIGMA));
    sw += w; sv += w * p.v;
    if (ang < amin) amin = ang;
  }
  return sw > 1e-12 ? { v: sv / sw, ang: amin } : { v: null, ang: Infinity };
}

// Opacidad según la distancia angular (rad) al sensor válido más cercano: llena hasta ~63°
// (entre sensores y su interior), y se apaga hacia ~92°, en la nuca y bajo las orejas.
export function opacidad(ang) {
  const t = Math.min(1, Math.max(0, (ang - 1.1) / 0.5));
  return 1 - t * t * (3 - 2 * t);
}

export function puntosBanda(banda) {
  return validos(banda).map(function (e) { return { u: e.u, v: valor(e, banda), canal: e.canal }; });
}

export function degradadoCss() { return "linear-gradient(to right, " + ESCALA.join(", ") + ")"; }

// Zonas de la librería (frontal, frontocentral, temporal, posterior), en el orden en que salen.
export const zonas = electrodos.reduce(function (lista, e) {
  if (e.zona && lista.indexOf(e.zona) < 0) lista.push(e.zona);
  return lista;
}, []);

// ¿Debe destacarse este electrodo? Sí si no hay zona elegida o es de la zona elegida.
export function enZona(e) { return !estado.zona || e.zona === estado.zona; }
