// Los cuatro mapas 2D de una grabación (uno por banda, vista desde arriba). Los usan la pestaña
// Análisis y la pestaña Fatiga aguda. Con `vista` (de visor3d.js) se dibuja el cerebro real; sin
// ella (sin WebGL), el círculo de respaldo de visor-comun.js. No calcula nada: pinta lo que hay en
// `estado` y en los electrodos.
import {
  bandas, electrodos, estado, rango, valor, puntosBanda, colorDeValor, fmt, decimales, textoValor,
  degradadoCss, css, dibujarCirculo2D,
} from "./visor-comun.js";

const NOMBRE_METRICA = {
  rel: "potencia relativa", abs: "potencia absoluta",
  cambio: "cambio de la potencia relativa desde el primer tercio",
};

// `opciones`: `alElegir(banda)` hace los mapas pulsables; `notaAria` se añade a la descripción
// accesible de cada mapa.
export function crearMapas(contenedor, ayudas, opciones) {
  opciones = opciones || {};
  const mapas = bandas.map(function (b) {
    const figura = document.createElement("figure");
    figura.className = "mapa-banda" + (opciones.alElegir ? " pulsable" : "");
    figura.innerHTML =
      '<figcaption>' + b.nombre + ' <small>' + b.rango + '</small></figcaption>' +
      '<div class="lienzo-2d cargando"><canvas role="img"></canvas></div>' +
      '<div class="escala-mapa"><span class="min"></span><div class="barra-escala"></div><span class="max"></span></div>';
    if (opciones.alElegir) figura.addEventListener("click", function () { opciones.alElegir(b.clave); });
    contenedor.appendChild(figura);
    const lienzo = figura.querySelector("canvas");
    const mapa = { banda: b, figura: figura, lienzo: lienzo, marcadores: [] };
    lienzo.addEventListener("pointermove", function (ev) { moverSobre(mapa, ev, ayudas); });
    lienzo.addEventListener("pointerleave", ayudas.ocultarTip);
    return mapa;
  });

  return {
    dibujar: function (vista) { mapas.forEach(function (m) { dibujarMapa(m, vista, opciones.notaAria || ""); }); },
    marcar: function (banda) { mapas.forEach(function (m) { m.figura.classList.toggle("activa", m.banda.clave === banda); }); },
  };
}

function moverSobre(mapa, ev, ayudas) {
  const r = mapa.lienzo.getBoundingClientRect();
  const x = ev.clientX - r.left, y = ev.clientY - r.top;
  let mejor = null, distMin = 16;
  mapa.marcadores.forEach(function (m) {
    const d = Math.hypot(m.x - x, m.y - y);
    if (d < distMin) { distMin = d; mejor = m; }
  });
  if (!mejor) { ayudas.ocultarTip(); return; }
  const texto = mejor.v === null ? mejor.canal + ": descartado, sin dato"
    : mejor.canal + " · " + mapa.banda.nombre + " · " + textoValor(mejor.v);
  ayudas.mostrarTip(ev.clientX, ev.clientY, texto);
}

function dibujarMapa(mapa, vista, notaAria) {
  const b = mapa.banda.clave;
  const lienzo = mapa.lienzo;
  const lado = lienzo.clientWidth || 260;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const res = Math.round(lado * dpr);
  if (lienzo.width !== res) { lienzo.width = res; lienzo.height = res; }
  const ctx = lienzo.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, lado, lado);

  const [min, max] = rango(b);
  const puntos = puntosBanda(b);
  let proyectar;
  if (vista) {
    // Cerebro real visto desde arriba (render de la malla fsaverage con el mapa encima).
    const fuera = mapa.fuera || (mapa.fuera = document.createElement("canvas"));
    if (fuera.width !== res) fuera.width = fuera.height = res;
    const aFraccion = vista.dibujar(fuera, b);
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
  escala.querySelector(".barra-escala").style.background = degradadoCss();
  const medidos = puntos.slice().sort(function (p, q) { return q.v - p.v; });
  lienzo.setAttribute("aria-label", "Mapa de " + NOMBRE_METRICA[estado.metrica] + " de " + mapa.banda.nombre.toLowerCase() +
    ", vista desde arriba." + (medidos.length ? " Máximo en " + medidos[0].canal + " (" + textoValor(medidos[0].v) +
    "), mínimo en " + medidos[medidos.length - 1].canal + " (" + textoValor(medidos[medidos.length - 1].v) + ")." : " Sin datos.") +
    notaAria);
}
