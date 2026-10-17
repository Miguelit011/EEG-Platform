// Mapa de calidad de los electrodos sobre el cerebro real (plantilla fsaverage) visto desde arriba.
// Sustituye al SVG si el navegador tiene WebGL; el SVG sigue siendo el respaldo.
import * as THREE from "three";

const contenedor = document.getElementById("mapa-calidad");
const datos = JSON.parse(document.getElementById("datos-calidad-mapa").textContent);
const geo = datos.geometria;
const svg = contenedor.querySelector("svg");

function css(nombre) { return getComputedStyle(document.documentElement).getPropertyValue(nombre).trim(); }

async function cargarMalla(url) {
  const respuesta = await fetch(url);
  if (!respuesta.ok) throw new Error("No se pudo cargar " + url);
  const buf = await respuesta.arrayBuffer();
  const [nv, nt] = new Uint32Array(buf, 0, 2);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(buf, 8, nv * 3), 3));
  g.setIndex(new THREE.BufferAttribute(new Uint32Array(buf, 8 + nv * 12, nt * 3), 1));
  g.computeVertexNormals();
  g.computeBoundingBox();
  return g;
}

async function iniciar() {
  const [cabeza, cerebro] = await Promise.all([cargarMalla(contenedor.dataset.mallaCabeza), cargarMalla(contenedor.dataset.mallaCerebro)]);
  const render = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  const escena = new THREE.Scene();
  const mitad = 1.25;
  const centro = new THREE.Vector3();
  cabeza.boundingBox.getCenter(centro);
  const camara = new THREE.OrthographicCamera(-mitad, mitad, mitad, -mitad, 0.1, 50);
  camara.position.set(0, centro.y, 10);
  camara.lookAt(0, centro.y, 0);

  const matCerebro = new THREE.MeshStandardMaterial({ roughness: 0.8, metalness: 0 });
  const matSombra = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.13, depthTest: false, depthWrite: false });
  const sombra = new THREE.Mesh(cabeza, matSombra);
  sombra.renderOrder = -1;
  escena.add(sombra, new THREE.Mesh(cerebro, matCerebro));
  escena.add(new THREE.HemisphereLight(0xffffff, 0x8a96a8, 1.7));
  const foco = new THREE.DirectionalLight(0xffffff, 1.8);
  foco.position.set(0.3, 0.5, 1);
  escena.add(foco);

  const lienzo = document.createElement("canvas");
  lienzo.className = "mapa-cabeza mapa-real";
  lienzo.setAttribute("role", "img");
  const descartados = datos.electrodos.filter(function (e) { return !e.bueno; }).map(function (e) { return e.canal; });
  lienzo.setAttribute("aria-label", "Mapa de calidad de los electrodos sobre el cerebro, vista desde arriba. " + datos.titular + "." +
    (descartados.length ? " Descartados: " + descartados.join(", ") + "." : "") + " El detalle está en la tabla.");
  contenedor.insertBefore(lienzo, svg);
  svg.hidden = true;
  svg.style.display = "none";   // `.mapa-cabeza` fija display y anula `hidden`

  function dibujar() {
    const lado = Math.round(Math.min(contenedor.clientWidth || 420, 420));
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const px = Math.round(lado * dpr);
    lienzo.width = lienzo.height = px;
    lienzo.style.width = lienzo.style.height = lado + "px";
    render.setSize(px, px, false);
    const vacia = new THREE.Color(css("--cabeza-vacia"));
    matCerebro.color.copy(vacia).lerp(new THREE.Color(0xffffff), 0.25);
    matSombra.color.set(css("--texto-suave"));
    render.render(escena, camara);
    const ctx = lienzo.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, lado, lado);
    ctx.drawImage(render.domElement, 0, 0, lado, lado);

    const texto = css("--texto"), fondo = css("--fondo"), acento = css("--acento"), descartado = css("--descartado");
    ctx.font = "600 11px " + (css("--fuente-datos") || "monospace");
    datos.electrodos.forEach(function (e) {
      const p = geo.canales[e.canal].pos;
      const x = ((p[0]) / (2 * mitad) + 0.5) * lado, y = (0.5 - (p[1] - centro.y) / (2 * mitad)) * lado;
      if (e.bueno) {
        ctx.fillStyle = acento; ctx.strokeStyle = texto; ctx.lineWidth = 1.8;
        ctx.beginPath(); ctx.arc(x, y, 9, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
        ctx.strokeStyle = css("--sobre-acento"); ctx.lineWidth = 2; ctx.lineCap = "round"; ctx.lineJoin = "round";
        ctx.beginPath(); ctx.moveTo(x - 3.5, y); ctx.lineTo(x - 1, y + 3); ctx.lineTo(x + 4, y - 3); ctx.stroke();
      } else {
        ctx.fillStyle = fondo; ctx.strokeStyle = descartado; ctx.lineWidth = 2; ctx.setLineDash([4, 3]);
        ctx.beginPath(); ctx.moveTo(x, y - 11); ctx.lineTo(x + 11, y); ctx.lineTo(x, y + 11); ctx.lineTo(x - 11, y); ctx.closePath(); ctx.fill(); ctx.stroke();
        ctx.setLineDash([]);
        ctx.beginPath(); ctx.moveTo(x - 4, y - 4); ctx.lineTo(x + 4, y + 4); ctx.moveTo(x + 4, y - 4); ctx.lineTo(x - 4, y + 4); ctx.stroke();
      }
      const dx = x - lado / 2, dy = y - lado / 2, n = Math.hypot(dx, dy) || 1;
      const lx = x + (dx / n) * 17, ly = y + (dy / n) * 17 + 4;
      ctx.textAlign = Math.abs(dx / n) > 0.35 ? (dx > 0 ? "left" : "right") : "center";
      ctx.lineWidth = 3; ctx.strokeStyle = fondo; ctx.lineJoin = "round";
      ctx.strokeText(e.canal, lx, ly);
      ctx.fillStyle = e.bueno ? texto : descartado;
      ctx.fillText(e.canal, lx, ly);
    });
    // Orientación.
    ctx.font = "500 12px " + css("--fuente"); ctx.fillStyle = css("--texto-suave"); ctx.textAlign = "center";
    ctx.fillText("Frente", lado / 2, 14);
    ctx.textAlign = "left"; ctx.fillText("◄ Izquierda", 4, lado - 6);
    ctx.textAlign = "right"; ctx.fillText("Derecha ►", lado - 4, lado - 6);
  }

  dibujar();
  document.addEventListener("tema:cambio", dibujar);
  let espera = null;
  window.addEventListener("resize", function () { clearTimeout(espera); espera = setTimeout(dibujar, 120); });
}

iniciar().catch(function (error) {
  console.warn("Mapa 3D no disponible, se queda el SVG:", error);
});
