// Visor de potencia por banda: cuatro mapas 2D (vista desde arriba) y cabeza 3D.
import {
  bandas, electrodos, estado, cambiar, suscribir, geo, rango, valor, puntosBanda, estimar, opacidad,
  colorDeValor, fmt, decimales, textoValor, degradadoCss, css, hexARgb, dibujarCirculo2D,
} from "./visor-comun.js";

const controles = document.getElementById("controles-visor");
const cuerpo = document.getElementById("visor-cuerpo");
const contenedor2d = document.getElementById("mapas-2d");
const pestanas = document.getElementById("pestanas-banda");
if (!controles || !cuerpo) throw new Error("visor sin contenedor");

// ---- Controles de métrica y escala --------------------------------------
document.querySelectorAll('input[name="metrica"], input[name="escala"]').forEach(function (r) {
  r.addEventListener("change", function () {
    cambiar({ [r.name]: r.value });
  });
});

// ---- Pestañas de banda (para la cabeza 3D) ------------------------------
bandas.forEach(function (b) {
  const boton = document.createElement("button");
  boton.type = "button";
  boton.dataset.banda = b.clave;
  boton.innerHTML = b.nombre + " <small>" + b.rango + "</small>";
  boton.addEventListener("click", function () { cambiar({ banda: b.clave }); });
  pestanas.appendChild(boton);
});

// ---- Tooltip -------------------------------------------------------------
const tip = document.createElement("div");
tip.className = "tip";
tip.hidden = true;
tip.setAttribute("role", "status");
document.body.appendChild(tip);
function mostrarTip(x, y, texto) { tip.textContent = texto; tip.style.left = x + "px"; tip.style.top = y + "px"; tip.hidden = false; }
function ocultarTip() { tip.hidden = true; }

// ---- Mapas 2D ------------------------------------------------------------
const NOMBRE_METRICA = { rel: "potencia relativa", abs: "potencia absoluta" };
const mapas = bandas.map(function (b) {
  const figura = document.createElement("figure");
  figura.className = "mapa-banda";
  figura.innerHTML =
    '<figcaption>' + b.nombre + ' <small>' + b.rango + '</small></figcaption>' +
    '<div class="lienzo-2d cargando"><canvas role="img"></canvas></div>' +
    '<div class="escala-mapa"><span class="min"></span><div class="barra-escala"></div><span class="max"></span></div>';
  figura.querySelector(".barra-escala").style.background = degradadoCss();
  const seleccionar = function () { cambiar({ banda: b.clave }); };
  figura.addEventListener("click", seleccionar);
  contenedor2d.appendChild(figura);
  const lienzo = figura.querySelector("canvas");
  const mapa = { banda: b, figura: figura, lienzo: lienzo, marcadores: [] };
  lienzo.addEventListener("pointermove", function (ev) { moverSobre(mapa, ev); });
  lienzo.addEventListener("pointerleave", ocultarTip);
  return mapa;
});

function moverSobre(mapa, ev) {
  const r = mapa.lienzo.getBoundingClientRect();
  const x = ev.clientX - r.left, y = ev.clientY - r.top;
  let mejor = null, distMin = 16;
  mapa.marcadores.forEach(function (m) {
    const d = Math.hypot(m.x - x, m.y - y);
    if (d < distMin) { distMin = d; mejor = m; }
  });
  if (!mejor) { ocultarTip(); return; }
  const texto = mejor.v === null ? mejor.canal + ": descartado, sin dato"
    : mejor.canal + " · " + mapa.banda.nombre + " · " + textoValor(mejor.v);
  mostrarTip(ev.clientX, ev.clientY, texto);
}

let api2D = null;   // se rellena cuando cargan las mallas 3D

function dibujarMapa(mapa) {
  const b = mapa.banda.clave;
  const lienzo = mapa.lienzo;
  const lado = lienzo.clientWidth || 260;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  lienzo.width = Math.round(lado * dpr);
  lienzo.height = Math.round(lado * dpr);
  const ctx = lienzo.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, lado, lado);

  const [min, max] = rango(b);
  const puntos = puntosBanda(b);
  let proyectar;
  if (api2D) {
    // Cerebro real visto desde arriba (render de la malla fsaverage con el mapa encima).
    const res = Math.round(lado * dpr);
    const fuera = mapa.fuera || (mapa.fuera = document.createElement("canvas"));
    fuera.width = fuera.height = res;
    const aFraccion = api2D.dibujar(fuera, b);
    ctx.drawImage(fuera, 0, 0, lado, lado);
    proyectar = function (e) { const f = aFraccion(e); return [f[0] * lado, f[1] * lado]; };
  } else {
    proyectar = dibujarCirculo2D(ctx, lado, puntos, min, max);
  }

  // Sensores.
  const fuente = css("--fuente-datos") || "monospace";
  const fondo = css("--fondo"), texto = css("--texto"), descartado = css("--descartado");
  mapa.marcadores = [];
  ctx.font = "600 10.5px " + fuente;
  ctx.textAlign = "center";
  electrodos.forEach(function (e) {
    const pxy = proyectar(e), x = pxy[0], y = pxy[1];
    const v = valor(e, b);
    mapa.marcadores.push({ canal: e.canal, x: x, y: y, v: v });
    if (v === null) {
      // Descartado: una cruz dentro de un círculo.
      ctx.strokeStyle = descartado; ctx.lineWidth = 1.6; ctx.lineCap = "round";
      ctx.beginPath(); ctx.arc(x, y, 6.5, 0, 2 * Math.PI); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x - 2.8, y - 2.8); ctx.lineTo(x + 2.8, y + 2.8); ctx.moveTo(x + 2.8, y - 2.8); ctx.lineTo(x - 2.8, y + 2.8); ctx.stroke();
    } else {
      const c = colorDeValor(v, min, max);
      ctx.fillStyle = "rgb(" + c.map(Math.round).join(",") + ")";
      ctx.strokeStyle = texto; ctx.lineWidth = 1.8;
      ctx.beginPath(); ctx.arc(x, y, 5.5, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
    }
    // Etiqueta hacia fuera del centro del mapa, para que no choque con la del vecino.
    const dx = x - lado / 2, dy = y - lado / 2, norma = Math.hypot(dx, dy) || 1;
    const lx = x + (dx / norma) * 13, ly = y + (dy / norma) * 13 + 3.5;
    ctx.textAlign = Math.abs(dx / norma) > 0.35 ? (dx > 0 ? "left" : "right") : "center";
    ctx.lineWidth = 3; ctx.strokeStyle = fondo;
    ctx.strokeText(e.canal, lx, ly);
    ctx.fillStyle = v === null ? descartado : texto;
    ctx.fillText(e.canal, lx, ly);
  });

  // Escala y descripción accesible.
  const escala = mapa.figura.querySelector(".escala-mapa");
  escala.querySelector(".min").textContent = fmt(min, decimales());
  escala.querySelector(".max").textContent = fmt(max, decimales());
  const medidos = puntos.slice().sort(function (p, q) { return q.v - p.v; });
  lienzo.setAttribute("aria-label", "Mapa de " + NOMBRE_METRICA[estado.metrica] + " de " + mapa.banda.nombre.toLowerCase() +
    ", vista desde arriba." + (medidos.length ? " Máximo en " + medidos[0].canal + " (" + textoValor(medidos[0].v) +
    "), mínimo en " + medidos[medidos.length - 1].canal + " (" + textoValor(medidos[medidos.length - 1].v) + ")." : " Sin datos.") +
    " Todos los valores están en las tablas de la pantalla.");
}

function actualizarTextos() {
  document.querySelectorAll('input[name="metrica"]').forEach(function (r) { r.checked = r.value === estado.metrica; });
  document.querySelectorAll('input[name="escala"]').forEach(function (r) { r.checked = r.value === estado.escala; });
  pestanas.querySelectorAll("button").forEach(function (bt) {
    bt.setAttribute("aria-pressed", bt.dataset.banda === estado.banda ? "true" : "false");
  });
  mapas.forEach(function (m) {
    const activa = m.banda.clave === estado.banda;
    m.figura.classList.toggle("activa", activa);
  });
  const texto = estado.escala === "banda"
    ? "Cada mapa usa su propia escala, de su mínimo a su máximo en esta grabación: el color no se puede comparar entre bandas. Los números de debajo de cada mapa dan los extremos."
    : "Los cuatro mapas comparten escala: el mismo color significa el mismo valor en todas las bandas.";
  document.getElementById("leyenda-escala").textContent =
    (estado.metrica === "rel" ? "Potencia relativa: % de la potencia total de la grabación que cae en cada banda. "
                              : "Potencia absoluta: log₁₀ de la potencia en V², por sensor. ") + texto;
}

const escena3d = document.getElementById("escena-3d");
if (escena3d) escena3d.classList.add("cargando");
let listo = false;   // los mapas se dibujan cuando se sabe si hay cerebro 3D, para no mostrar antes el respaldo circular
function redibujar() { actualizarTextos(); if (listo) mapas.forEach(dibujarMapa); }
suscribir(redibujar);
document.addEventListener("tema:cambio", redibujar);
window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", function () { setTimeout(redibujar, 0); });
let pendiente = null;
window.addEventListener("resize", function () { clearTimeout(pendiente); pendiente = setTimeout(redibujar, 120); });
actualizarTextos();

// ---- Cabeza 3D (si el navegador lo permite) ------------------------------
import("./visor3d.js").then(function (m) { return m.iniciar3D({ mostrarTip, ocultarTip }); }).then(function (api) {
  api2D = api;
  listo = true;
  document.querySelectorAll(".cargando").forEach(function (el) { el.classList.remove("cargando"); });
  redibujar();
}).catch(function (error) {
  console.warn("Visor 3D no disponible:", error);
  listo = true;
  document.querySelectorAll(".cargando").forEach(function (el) { el.classList.remove("cargando"); });
  redibujar();
  const escena = document.getElementById("escena-3d");
  if (escena) escena.innerHTML = '<p class="sin-webgl">La vista 3D no está disponible en este navegador. Los mapas 2D muestran los mismos valores.</p>';
});
