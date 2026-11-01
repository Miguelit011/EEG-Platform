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
// Escala divergente (PRGn) para «cambio desde el principio» en la pestaña Fatiga aguda: morado =
// baja, verde = sube. Distinta de la cinta de tiempo (azul/naranja) para no mezclar significados.
export const DIVERGENTE = ["#762a83", "#9970ab", "#c2a5cf", "#e7d4e8", "#f7f7f7",
                           "#d9f0d3", "#a6dba0", "#5aae61", "#1b7837"];
const DIVERGENTE_RGB = DIVERGENTE.map(hexARgb);

// Anchura (rad) del núcleo gaussiano de la interpolación. Lejos de todo sensor válido la
// superficie se muestra apagada (ver `opacidad`), no inventada.
export const SIGMA = 0.8;

// `fotograma` solo cambia en la pestaña Fatiga aguda, al reproducir la grabación.
export const estado = { metrica: datos.metrica_inicial || "rel", escala: "banda", banda: datos.banda_inicial, fotograma: 0 };
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

export function decimales() { return estado.metrica === "abs" ? 2 : 1; }
export function unidad() { return { rel: "%", abs: "log₁₀ V²", cambio: "pp" }[estado.metrica]; }
export function textoValor(v) {
  if (estado.metrica === "cambio") return (v > 0 ? "+" : "") + fmt(v, 1) + " pp";
  return fmt(v, decimales()) + (estado.metrica === "rel" ? " %" : " log₁₀ V²");
}

// Valor medido de un electrodo en una banda (null si fue descartado o no hay dato).
export function valor(e, banda) {
  if (!e.valido) return null;
  if (estado.metrica === "cambio") {
    const c = e.cambio ? e.cambio[banda] : null;
    return c === null || c === undefined ? null : c;
  }
  const v = estado.metrica === "rel" ? e.rel[banda] : e.log_abs[banda];
  if (v === null || v === undefined) return null;
  return estado.metrica === "rel" ? v * 100 : v;
}

export function validos(banda) {
  return electrodos.filter(function (e) { return valor(e, banda) !== null; });
}

// Rango de color: de esa banda, o común a las cuatro. Si la página trae `rango_fijo` (la pestaña
// Fatiga aguda, que anima la grabación), se usa ese, el mismo en todos los momentos.
export function rango(banda) {
  const lista = estado.escala === "comun" ? bandas.map(function (b) { return b.clave; }) : [banda];
  if (estado.metrica === "cambio" && datos.rango_cambio) {
    const tope = Math.max.apply(null, lista.map(function (b) { return datos.rango_cambio[b][1]; }));
    return [-tope, tope];
  }
  if (datos.rango_fijo && estado.metrica === "rel") {
    const fijos = lista.map(function (b) { return datos.rango_fijo[b]; }).filter(Boolean);
    if (fijos.length) {
      const min = Math.min.apply(null, fijos.map(function (r) { return r[0]; }));
      const max = Math.max.apply(null, fijos.map(function (r) { return r[1]; }));
      return max - min < 1e-9 ? [min - 0.5, max + 0.5] : [min, max];
    }
  }
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
  const paleta = estado.metrica === "cambio" ? DIVERGENTE_RGB : ESCALA_RGB;
  t = Math.min(1, Math.max(0, t)) * (paleta.length - 1);
  const i = Math.min(Math.floor(t), paleta.length - 2), f = t - i;
  return paleta[i].map(function (c, k) { return c + (paleta[i + 1][k] - c) * f; });
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

export function degradadoCss() {
  return "linear-gradient(to right, " + (estado.metrica === "cambio" ? DIVERGENTE : ESCALA).join(", ") + ")";
}

// Respaldo sin WebGL: círculo con nariz y orejas y el calor interpolado en el plano. Lo usan los
// mapas 2D de Análisis y el cerebro de la pestaña Fatiga aguda. Devuelve cómo pasar un electrodo
// a coordenadas del lienzo.
const RESOLUCION = 132;
export function dibujarCirculo2D(ctx, lado, puntos, min, max) {
  const vacia = hexARgb(css("--cabeza-vacia"));
  const R = lado * 0.34;
  const cx = lado / 2, cy = lado * 0.54;
  const fuera = document.createElement("canvas");
  fuera.width = fuera.height = RESOLUCION;
  const fctx = fuera.getContext("2d");
  const img = fctx.createImageData(RESOLUCION, RESOLUCION);
  for (let iy = 0; iy < RESOLUCION; iy++) {
    for (let ix = 0; ix < RESOLUCION; ix++) {
      const x = ((ix + 0.5) / RESOLUCION) * 2 - 1, y = 1 - ((iy + 0.5) / RESOLUCION) * 2;
      const rr = Math.hypot(x, y);
      const k = (iy * RESOLUCION + ix) * 4;
      if (rr > 1) { img.data[k + 3] = 0; continue; }
      const theta = rr * geo.borde_2d, s = Math.sin(theta);
      const u = rr === 0 ? [0, 0, 1] : [s * x / rr, s * y / rr, Math.cos(theta)];
      const est = puntos.length ? estimar(u, puntos) : { v: null, ang: Infinity };
      let col = vacia;
      if (est.v !== null) {
        const o = opacidad(est.ang);
        const c = colorDeValor(est.v, min, max);
        col = [vacia[0] + (c[0] - vacia[0]) * o, vacia[1] + (c[1] - vacia[1]) * o, vacia[2] + (c[2] - vacia[2]) * o];
      }
      img.data[k] = col[0]; img.data[k + 1] = col[1]; img.data[k + 2] = col[2]; img.data[k + 3] = 255;
    }
  }
  fctx.putImageData(img, 0, 0);
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(fuera, cx - R, cy - R, 2 * R, 2 * R);
  ctx.strokeStyle = css("--texto-suave"); ctx.lineWidth = 2; ctx.lineJoin = "round";
  ctx.beginPath(); ctx.arc(cx, cy, R, 0, 2 * Math.PI); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(cx - R * 0.17, cy - R * 0.985); ctx.lineTo(cx, cy - R * 1.2); ctx.lineTo(cx + R * 0.17, cy - R * 0.985); ctx.stroke();
  [-1, 1].forEach(function (lado2) {
    ctx.beginPath(); ctx.ellipse(cx + lado2 * (R + 5), cy, 5, R * 0.2, 0, 0, 2 * Math.PI); ctx.stroke();
  });
  return function (e) { return [cx + e.p2[0] * R, cy - e.p2[1] * R]; };
}
