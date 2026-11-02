// Visor de potencia por banda: cuatro mapas 2D (vista desde arriba) y cabeza 3D.
import { bandas, estado, cambiar, suscribir } from "./visor-comun.js";
import { crearMapas } from "./mapas2d.js";

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
const mapas = crearMapas(contenedor2d, { mostrarTip, ocultarTip }, {
  alElegir: function (banda) { cambiar({ banda: banda }); },
  notaAria: " Todos los valores están en las tablas de la pantalla.",
});
let api2D = null;   // se rellena cuando cargan las mallas 3D

function actualizarTextos() {
  document.querySelectorAll('input[name="metrica"]').forEach(function (r) { r.checked = r.value === estado.metrica; });
  document.querySelectorAll('input[name="escala"]').forEach(function (r) { r.checked = r.value === estado.escala; });
  pestanas.querySelectorAll("button").forEach(function (bt) {
    bt.setAttribute("aria-pressed", bt.dataset.banda === estado.banda ? "true" : "false");
  });
  mapas.marcar(estado.banda);
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
function redibujar() { actualizarTextos(); if (listo) mapas.dibujar(api2D); }
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
