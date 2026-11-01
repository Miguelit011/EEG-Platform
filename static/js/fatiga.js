// Pestaña «Fatiga aguda»: reproduce la grabación en el cerebro 3D y en una cinta de tiempo.
// No calcula nada del modelo: la puntuación de cada ventana, la potencia relativa (ya suavizada)
// y la escala vienen del servidor, que las saca de EEG-Library. Aquí solo se interpola entre dos
// ventanas seguidas para que el movimiento sea continuo.
import { bandas, electrodos, estado, cambiar, suscribir, css, hexARgb } from "./visor-comun.js";
import { iniciar3D } from "./visor3d.js";

const datos = JSON.parse(document.getElementById("datos-fatiga").textContent);
const instantes = datos.instante_s;
const n = instantes.length;
const paso = n > 1 ? instantes[1] - instantes[0] : 2;
const DURACION_1X_MS = 20000;   // a 1× la grabación entera se recorre en unos 20 s, dure lo que dure

const botonPlay = document.getElementById("fa-play");
const textoPlay = document.getElementById("fa-play-texto");
const tiempo = document.getElementById("fa-tiempo");
const reloj = document.getElementById("fa-reloj");
const cinta = document.getElementById("fa-cinta");
const lienzo = document.getElementById("fa-cinta-lienzo");
const cabezal = document.getElementById("fa-cabezal");
const pestanas = document.getElementById("pestanas-banda");

// ---- Pestañas de banda --------------------------------------------------------------------
bandas.forEach(function (b) {
  const boton = document.createElement("button");
  boton.type = "button";
  boton.dataset.banda = b.clave;
  boton.innerHTML = b.nombre + " <small>" + b.rango + "</small>";
  boton.addEventListener("click", function () { cambiar({ banda: b.clave }); });
  pestanas.appendChild(boton);
});
function marcarPestana() {
  pestanas.querySelectorAll("button").forEach(function (b) {
    b.setAttribute("aria-pressed", b.dataset.banda === estado.banda ? "true" : "false");
  });
}
suscribir(marcarPestana);
marcarPestana();

// ---- Qué muestra el cerebro: cambio desde el principio o valor en cada momento ----------------
const tituloEscala = document.getElementById("fa-escala-titulo");
const TITULOS = {
  cambio: "Cambio de la potencia relativa respecto a la media del primer tercio, en puntos porcentuales: morado, baja; verde, sube",
  rel: "Potencia relativa de la banda elegida (% de la potencia total), con la misma escala en toda la grabación",
};
document.querySelectorAll('input[name="fa-metrica"]').forEach(function (r) {
  r.checked = r.value === estado.metrica;
  r.addEventListener("change", function () { cambiar({ metrica: r.value }); });
});
function rotularEscala() { tituloEscala.textContent = TITULOS[estado.metrica] || ""; }
suscribir(rotularEscala);
rotularEscala();

// ---- Tooltip (lo usa el cerebro 3D) ---------------------------------------------------------
const tip = document.createElement("div");
tip.className = "tip";
tip.hidden = true;
tip.setAttribute("role", "status");
document.body.appendChild(tip);
const ayudas = {
  mostrarTip: function (x, y, texto) { tip.textContent = texto; tip.style.left = x + "px"; tip.style.top = y + "px"; tip.hidden = false; },
  ocultarTip: function () { tip.hidden = true; },
};

// ---- Momento de la grabación ----------------------------------------------------------------
let posicion = 0;          // índice de ventana, con decimales entre dos ventanas
let reproduciendo = false;
let velocidad = 1;

function mmss(s) {
  s = Math.max(0, Math.round(s));
  return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
}
function instanteDe(pos) {
  const i = Math.min(n - 1, Math.floor(pos)), f = pos - i;
  return i + 1 < n ? instantes[i] + (instantes[i + 1] - instantes[i]) * f : instantes[i];
}

function aplicar(pos) {
  posicion = Math.min(n - 1, Math.max(0, pos));
  const i = Math.min(n - 1, Math.floor(posicion)), j = Math.min(n - 1, i + 1), f = posicion - i;
  electrodos.forEach(function (e) {
    bandas.forEach(function (b) {
      const serie = datos.fotogramas[b.clave][e.canal], cambio = datos.cambios[b.clave][e.canal];
      if (serie) e.rel[b.clave] = (serie[i] + (serie[j] - serie[i]) * f) / 100;
      if (cambio) e.cambio[b.clave] = cambio[i] + (cambio[j] - cambio[i]) * f;
    });
  });
  // El centro de la ventana de 4 s es el momento al que corresponde lo que se ve.
  const centro = instanteDe(posicion) + 2;
  const texto = mmss(centro);
  tiempo.textContent = texto;
  reloj.textContent = texto;
  cabezal.style.left = (100 * centro / datos.duracion_s) + "%";
  cinta.setAttribute("aria-valuenow", String(Math.round(posicion)));
  cinta.setAttribute("aria-valuetext", texto + " de " + mmss(datos.duracion_s));
  cambiar({ fotograma: Math.round(posicion * 100) / 100 });
}

// ---- Reproducción ---------------------------------------------------------------------------
let ultimo = null, acumulado = 0;
function ponerReproduccion(si) {
  reproduciendo = si;
  botonPlay.setAttribute("aria-label", si ? "Pausar" : "Reproducir");
  botonPlay.classList.toggle("en-pausa", si);
  textoPlay.textContent = si ? "Pausar" : "Reproducir";
  if (si) {
    if (posicion >= n - 1) aplicar(0);
    ultimo = null;
    requestAnimationFrame(bucle);
  }
}
function bucle(ahora) {
  if (!reproduciendo) return;
  if (ultimo === null) ultimo = ahora;
  const dt = ahora - ultimo;
  ultimo = ahora;
  acumulado += dt;
  const avance = dt * velocidad * (n - 1) / DURACION_1X_MS;
  posicion = Math.min(n - 1, posicion + avance);
  if (acumulado >= 33 || posicion >= n - 1) {   // ≈ 30 fotogramas por segundo bastan
    acumulado = 0;
    aplicar(posicion);
  }
  if (posicion >= n - 1) { ponerReproduccion(false); return; }
  requestAnimationFrame(bucle);
}
botonPlay.addEventListener("click", function () { ponerReproduccion(!reproduciendo); });

document.querySelectorAll(".fa-velocidad button").forEach(function (b) {
  b.addEventListener("click", function () {
    velocidad = parseFloat(b.dataset.velocidad);
    document.querySelectorAll(".fa-velocidad button").forEach(function (x) {
      x.setAttribute("aria-pressed", x === b ? "true" : "false");
    });
  });
});

// ---- Cinta de tiempo ------------------------------------------------------------------------
function mezclar(a, b, t) { return [0, 1, 2].map(function (k) { return Math.round(a[k] + (b[k] - a[k]) * t); }); }

function dibujarCinta() {
  const ancho = cinta.clientWidth, alto = cinta.clientHeight;
  if (!ancho || !alto) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  lienzo.width = Math.round(ancho * dpr);
  lienzo.height = Math.round(alto * dpr);
  const ctx = lienzo.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, ancho, alto);
  const neutro = hexARgb(css("--fa-neutro")), principio = hexARgb(css("--fa-principio")), final = hexARgb(css("--fa-final"));
  const x = function (t) { return ancho * t / datos.duracion_s; };
  for (let i = 0; i < n; i++) {
    const s = datos.puntuacion[i];
    const c = s < 0 ? mezclar(neutro, principio, -s) : mezclar(neutro, final, s);
    ctx.fillStyle = "rgb(" + c.join(",") + ")";
    const desde = x(instantes[i]), hasta = x(i + 1 < n ? instantes[i] + paso : datos.duracion_s);
    ctx.fillRect(Math.floor(desde), 0, Math.ceil(hasta - desde) + 1, alto);
  }
  // Tercios: el modelo compara el primero con el último.
  ctx.strokeStyle = css("--texto");
  ctx.globalAlpha = 0.55;
  ctx.setLineDash([3, 3]);
  datos.tercios_s.forEach(function (t) {
    const xt = Math.round(x(t + 2)) + 0.5;
    ctx.beginPath(); ctx.moveTo(xt, 0); ctx.lineTo(xt, alto); ctx.stroke();
  });
  ctx.setLineDash([]);
  ctx.globalAlpha = 1;
  // Rótulos de los tercios, debajo de la cinta y alineados con las líneas.
  const marcas = [0].concat(datos.tercios_s.map(function (t) { return (t + 2) / datos.duracion_s; }), [1]);
  document.querySelectorAll("#fa-tercios span").forEach(function (el, k) {
    el.style.left = (100 * marcas[k]) + "%";
    el.style.width = (100 * (marcas[k + 1] - marcas[k])) + "%";
  });
}
new ResizeObserver(dibujarCinta).observe(cinta);
document.addEventListener("tema:cambio", dibujarCinta);

function posicionDesde(evento) {
  const r = cinta.getBoundingClientRect();
  const t = (evento.clientX - r.left) / r.width * datos.duracion_s - 2;   // centro → inicio de ventana
  return (t - instantes[0]) / paso;
}
let arrastrando = false;
cinta.addEventListener("pointerdown", function (ev) {
  arrastrando = true;
  cinta.setPointerCapture(ev.pointerId);
  ponerReproduccion(false);
  aplicar(posicionDesde(ev));
});
cinta.addEventListener("pointermove", function (ev) { if (arrastrando) aplicar(posicionDesde(ev)); });
cinta.addEventListener("pointerup", function () { arrastrando = false; });
cinta.addEventListener("keydown", function (ev) {
  const saltos = { ArrowLeft: -1, ArrowRight: 1, PageDown: -Math.ceil(n / 10), PageUp: Math.ceil(n / 10) };
  let destino = null;
  if (ev.key in saltos) destino = Math.round(posicion) + saltos[ev.key];
  else if (ev.key === "Home") destino = 0;
  else if (ev.key === "End") destino = n - 1;
  else if (ev.key === " ") { ev.preventDefault(); ponerReproduccion(!reproduciendo); return; }
  if (destino === null) return;
  ev.preventDefault();
  ponerReproduccion(false);
  aplicar(destino);
});

// ---- Arranque -------------------------------------------------------------------------------
dibujarCinta();
iniciar3D(ayudas).then(function () { aplicar(0); }).catch(function () {
  document.getElementById("escena-3d").innerHTML =
    '<p class="aviso aviso-info">Este navegador no puede mostrar el cerebro en 3D. La cinta de tiempo y el resultado siguen siendo válidos.</p>';
  aplicar(0);
});
