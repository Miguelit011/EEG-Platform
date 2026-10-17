// Cabeza y cerebro reales (plantilla fsaverage) con el mapa de potencia de la banda elegida.
// Son plantillas promedio, no las de la persona grabada. El color sobre la superficie es una
// interpolación orientativa de 14 sensores: no localiza fuentes dentro del cerebro.
import * as THREE from "three";
import { OrbitControls } from "../vendor/three/controls/OrbitControls.js";
import {
  bandas, electrodos, estado, suscribir, geo, rango, valor, puntosBanda, estimar, opacidad,
  colorDeValor, fmt, decimales, textoValor, degradadoCss, css, hexARgb, enZona,
} from "./visor-comun.js";

const CENTRO = new THREE.Vector3(geo.centro[0], geo.centro[1], geo.centro[2]);

function mezclar(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; }
// sRGB (0-255) a componente lineal (0-1): los colores por vértice se interpretan como lineales.
function lineal(c) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }

async function cargarMalla(url) {
  const respuesta = await fetch(url);
  if (!respuesta.ok) throw new Error("No se pudo cargar " + url);
  const buf = await respuesta.arrayBuffer();
  const [nv, nt] = new Uint32Array(buf, 0, 2);
  const vertices = new Float32Array(buf, 8, nv * 3);
  const triangulos = new Uint32Array(buf, 8 + nv * 12, nt * 3);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(vertices, 3));
  g.setIndex(new THREE.BufferAttribute(triangulos, 1));
  g.computeVertexNormals();
  g.setAttribute("color", new THREE.BufferAttribute(new Float32Array(nv * 3), 3));
  // Dirección de cada vértice vista desde el centro del cerebro: con ella se interpola.
  const dirs = new Float32Array(nv * 3);
  for (let i = 0; i < nv; i++) {
    const x = vertices[i * 3] - CENTRO.x, y = vertices[i * 3 + 1] - CENTRO.y, z = vertices[i * 3 + 2] - CENTRO.z;
    const n = Math.hypot(x, y, z) || 1;
    dirs[i * 3] = x / n; dirs[i * 3 + 1] = y / n; dirs[i * 3 + 2] = z / n;
  }
  g.computeBoundingBox();
  return { geometria: g, dirs: dirs, n: nv };
}

// Colores por vértice de una banda; se guardan por estado para no recalcular al cambiar de vista.
const cache = new Map();
function coloresDe(malla, nombre, banda) {
  const clave = [nombre, banda, estado.metrica, estado.escala, css("--cabeza-vacia")].join("|");
  if (cache.has(clave)) return cache.get(clave);
  const [min, max] = rango(banda);
  const puntos = puntosBanda(banda);
  const vacia = hexARgb(css("--cabeza-vacia"));
  const salida = new Float32Array(malla.n * 3);
  const u = [0, 0, 0];
  for (let i = 0; i < malla.n; i++) {
    u[0] = malla.dirs[i * 3]; u[1] = malla.dirs[i * 3 + 1]; u[2] = malla.dirs[i * 3 + 2];
    let col = vacia;
    if (puntos.length) {
      const est = estimar(u, puntos);
      if (est.v !== null) col = mezclar(vacia, colorDeValor(est.v, min, max), opacidad(est.ang));
    }
    salida[i * 3] = lineal(col[0]); salida[i * 3 + 1] = lineal(col[1]); salida[i * 3 + 2] = lineal(col[2]);
  }
  if (cache.size > 40) cache.clear();
  cache.set(clave, salida);
  return salida;
}

function aplicar(geometria, colores) {
  geometria.attributes.color.array.set(colores);
  geometria.attributes.color.needsUpdate = true;
}

// Curvas de nivel de una malla (cortes con planos x, y o z constantes): una rejilla fina que deja ver
// el cerebro y a la vez muestra hacia dónde está orientada la cabeza.
function contornos(geometria, planos) {
  const pos = geometria.attributes.position.array, idx = geometria.index.array;
  const segmentos = [];
  planos.forEach(function (plano) {
    const eje = plano[0], nivel = plano[1];
    for (let t = 0; t < idx.length; t += 3) {
      const cortes = [];
      for (let k = 0; k < 3; k++) {
        const a = idx[t + k], b = idx[t + ((k + 1) % 3)];
        const da = pos[a * 3 + eje] - nivel, db = pos[b * 3 + eje] - nivel;
        if ((da < 0) !== (db < 0)) {
          const f = da / (da - db);
          cortes.push(pos[a * 3] + (pos[b * 3] - pos[a * 3]) * f,
                      pos[a * 3 + 1] + (pos[b * 3 + 1] - pos[a * 3 + 1]) * f,
                      pos[a * 3 + 2] + (pos[b * 3 + 2] - pos[a * 3 + 2]) * f);
        }
      }
      if (cortes.length === 6) segmentos.push.apply(segmentos, cortes);
    }
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(segmentos), 3));
  return g;
}

export async function iniciar3D(ayudas) {
  const raiz = document.getElementById("visor");
  const [cabeza, cerebro] = await Promise.all([cargarMalla(raiz.dataset.mallaCabeza), cargarMalla(raiz.dataset.mallaCerebro)]);

  const escena = document.getElementById("escena-3d");
  const capaEtiquetas = document.getElementById("etiquetas-3d");
  const barra = document.getElementById("herramientas-3d");
  const escala = document.getElementById("escala-3d");
  const selectorModo = document.getElementById("modo-3d");

  const renderizador = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderizador.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const lienzo = renderizador.domElement;
  lienzo.tabIndex = 0;
  lienzo.setAttribute("role", "img");
  escena.insertBefore(lienzo, capaEtiquetas);

  const tres = new THREE.Scene();
  const camara = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
  camara.up.set(0, 0, 1);              // los datos tienen z hacia arriba
  tres.add(camara);
  tres.add(new THREE.HemisphereLight(0xffffff, 0x8a96a8, 1.5));
  const foco = new THREE.DirectionalLight(0xffffff, 2.0);
  foco.position.set(0.4, 0.6, 1);
  camara.add(foco);

  const objetivo = new THREE.Vector3();
  cabeza.geometria.boundingBox.getCenter(objetivo);
  const controles = new OrbitControls(camara, lienzo);
  controles.target.copy(objetivo);
  controles.enablePan = false;
  controles.enableDamping = false;
  controles.minDistance = 2.6;
  controles.maxDistance = 12;
  controles.autoRotateSpeed = 1.6;

  // ---- Superficies ---------------------------------------------------------------
  const matCabeza = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.62, metalness: 0 });
  const mallaCabeza = new THREE.Mesh(cabeza.geometria, matCabeza);
  const matCerebro = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.78, metalness: 0 });
  const mallaCerebro = new THREE.Mesh(cerebro.geometria, matCerebro);
  tres.add(mallaCabeza, mallaCerebro);

  // Con el cerebro a la vista, la cabeza se reduce a una rejilla de contornos (sin relleno).
  const niveles = [];
  [-0.9, -0.45, 0, 0.45, 0.9].forEach(function (n) { niveles.push([2, n]); });
  [-0.8, -0.4, 0, 0.4, 0.8].forEach(function (n) { niveles.push([0, n]); });
  [-1.2, -0.8, -0.4, 0, 0.4, 0.8].forEach(function (n) { niveles.push([1, n]); });
  const matRejilla = new THREE.LineBasicMaterial({ transparent: true, opacity: 0.5, depthWrite: false });
  const rejilla = new THREE.LineSegments(contornos(cabeza.geometria, niveles), matRejilla);

  // Rótulos de orientación (frente y nuca) en los extremos de la cabeza.
  const extremos = [["Frente", 1, 1], ["Atrás", 1, -1]].map(function (d) {
    const pos = cabeza.geometria.attributes.position.array;
    let mejor = null, valorMejor = -Infinity;
    for (let i = 0; i < pos.length; i += 3) {
      const c = pos[i + d[1]] * d[2];
      if (c > valorMejor) { valorMejor = c; mejor = new THREE.Vector3(pos[i], pos[i + 1], pos[i + 2]); }
    }
    const dir = new THREE.Vector3(); dir.setComponent(d[1], d[2]);
    const el = document.createElement("span");
    el.className = "etq orient"; el.textContent = d[0];
    capaEtiquetas.appendChild(el);
    return { pos: mejor.addScaledVector(dir, 0.18), dir: dir, el: el };
  });
  tres.add(rejilla);

  // ---- Sensores: disco con el color del valor sobre la cabeza, orientado a la normal ----
  const z = new THREE.Vector3(0, 0, 1);
  const sensores = electrodos.map(function (e) {
    const c = geo.canales[e.canal];
    const normal = new THREE.Vector3(c.normal[0], c.normal[1], c.normal[2]);
    const pos = new THREE.Vector3(c.pos[0], c.pos[1], c.pos[2]);
    const orientacion = new THREE.Quaternion().setFromUnitVectors(z, normal);
    const disco = function (radio) {
      const m = new THREE.Mesh(new THREE.CircleGeometry(radio, 28), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide, transparent: true }));
      m.quaternion.copy(orientacion);
      tres.add(m);
      return m;
    };
    const halo = disco(0.1), aro = disco(0.085), centro = disco(0.058);
    halo.position.copy(pos).addScaledVector(normal, 0.01);
    aro.position.copy(pos).addScaledVector(normal, 0.02);
    centro.position.copy(pos).addScaledVector(normal, 0.03);
    const diana = new THREE.Mesh(new THREE.SphereGeometry(0.13, 8, 6), new THREE.MeshBasicMaterial({ visible: false }));
    diana.position.copy(pos); diana.userData.canal = e.canal;
    tres.add(diana);
    const etiqueta = document.createElement("span");
    etiqueta.className = "etq";
    capaEtiquetas.appendChild(etiqueta);
    return { e: e, pos: pos.clone().addScaledVector(normal, 0.03), normal: normal, halo: halo, aro: aro, centro: centro, diana: diana, etiqueta: etiqueta };
  });

  // ---- Qué se muestra: cabeza o cerebro ---------------------------------------------
  let modo = "cabeza";
  function ponerModo(nuevo) {
    modo = nuevo;
    const sobreCerebro = modo === "cerebro";
    mallaCabeza.visible = !sobreCerebro;
    rejilla.visible = sobreCerebro;
    mallaCerebro.visible = sobreCerebro;
    selectorModo.querySelectorAll("button").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.modo === modo ? "true" : "false"); });
    pintar();
  }
  [["cabeza", "Cabeza real"], ["cerebro", "Cerebro real"]].forEach(function (p) {
    const b = document.createElement("button");
    b.type = "button"; b.dataset.modo = p[0]; b.textContent = p[1];
    b.addEventListener("click", function () { ponerModo(p[0]); });
    selectorModo.appendChild(b);
  });

  // ---- Colores según estado y tema -----------------------------------------------------
  function pintar() {
    const b = estado.banda;
    const [min, max] = rango(b);
    aplicar(cabeza.geometria, coloresDe(cabeza, "cabeza", b));
    if (modo === "cerebro") aplicar(cerebro.geometria, coloresDe(cerebro, "cerebro", b));
    matRejilla.color.set(css("--texto-suave"));
    const rgbTexto = css("--texto"), descartado = css("--descartado");
    sensores.forEach(function (s) {
      const v = valor(s.e, b);
      s.halo.material.color.set(css("--fondo"));
      s.aro.material.color.set(v === null ? descartado : rgbTexto);
      if (v === null) s.centro.material.color.set(css("--fondo"));
      else { const c = colorDeValor(v, min, max); s.centro.material.color.setRGB(lineal(c[0]), lineal(c[1]), lineal(c[2]), THREE.LinearSRGBColorSpace); }
      const resaltado = enZona(s.e);
      [s.halo, s.aro, s.centro].forEach(function (m) { m.material.opacity = resaltado ? 1 : 0.2; });
      s.etiqueta.classList.toggle("descartado", v === null);
      s.etiqueta.classList.toggle("atenuada", !resaltado);
      s.etiqueta.innerHTML = v === null ? "<b>" + s.e.canal + "</b> ✕ descartado" : "<b>" + s.e.canal + "</b> " + fmt(v, decimales());
    });

    const nombre = bandas.find(function (x) { return x.clave === b; }).nombre;
    escala.innerHTML = '<span>' + fmt(min, decimales()) + '</span><div class="barra-escala"></div><span>' + fmt(max, decimales()) + '</span>';
    escala.querySelector(".barra-escala").style.background = degradadoCss();
    escala.setAttribute("aria-label", "Escala de color de " + nombre + ": de " + fmt(min, decimales()) + " a " + fmt(max, decimales()));
    lienzo.setAttribute("aria-label", (modo === "cabeza" ? "Cabeza real en 3D" : "Cerebro real en 3D") + " con el mapa de " + nombre.toLowerCase() +
      ". Se puede girar con el ratón o las flechas del teclado. Los mismos valores están en los mapas 2D y en las tablas.");
    renderizar();
  }

  // ---- Cámara y vistas (z arriba, y hacia la nariz; az=0 mira de frente) ------------------
  const VISTAS = {
    inicial: [-0.8, 1.2], frente: [0, 1.45], atras: [Math.PI, 1.45],
    izquierda: [-Math.PI / 2, 1.45], derecha: [Math.PI / 2, 1.45], arriba: [Math.PI, 0.01],
  };
  function colocar(az, pol, d) {
    pol = Math.min(Math.PI - 0.01, Math.max(0.01, pol));
    camara.position.set(objetivo.x + d * Math.sin(pol) * Math.sin(az), objetivo.y + d * Math.sin(pol) * Math.cos(az), objetivo.z + d * Math.cos(pol));
    camara.lookAt(objetivo);
    controles.update();
    renderizar();
  }
  function irA(nombre, distancia) { const [az, pol] = VISTAS[nombre]; colocar(az, pol, distancia); }
  function girar(daz, dpol, dzoom) {
    const rel = camara.position.clone().sub(objetivo);
    const radio = Math.min(controles.maxDistance, Math.max(controles.minDistance, rel.length() * (dzoom || 1)));
    const pol = Math.acos(rel.z / rel.length());
    const az = Math.atan2(rel.x, rel.y);
    colocar(az + daz, pol + dpol, radio);
  }

  // ---- Etiquetas y dibujo --------------------------------------------------------------------
  let verEtiquetas = window.innerWidth > 640;   // en pantallas estrechas se ven solo bajo petición
  const haciaCamara = new THREE.Vector3(), v = new THREE.Vector3();
  function renderizar() {
    renderizador.render(tres, camara);
    const ancho = escena.clientWidth, alto = escena.clientHeight;
    extremos.forEach(function (x) {
      v.copy(x.pos).project(camara);
      const visible = modo === "cerebro" && x.dir.dot(haciaCamara.copy(camara.position).sub(objetivo).normalize()) > -0.6 && v.z < 1;
      x.el.style.display = visible ? "block" : "none";
      if (visible) { x.el.style.left = ((v.x + 1) / 2) * ancho + "px"; x.el.style.top = ((1 - v.y) / 2) * alto + "px"; }
    });
    sensores.forEach(function (s) {
      v.copy(s.pos).project(camara);
      const de_frente = s.normal.dot(haciaCamara.copy(camara.position).sub(s.pos).normalize()) > 0.05;
      const visible = verEtiquetas && de_frente && v.z < 1 && enZona(s.e);
      s.etiqueta.style.display = visible ? "block" : "none";
      if (visible) {
        s.etiqueta.style.left = ((v.x + 1) / 2) * ancho + "px";
        s.etiqueta.style.top = ((1 - v.y) / 2) * alto + "px";
      }
    });
  }
  function ajustar() {
    const ancho = escena.clientWidth, alto = escena.clientHeight;
    if (!ancho || !alto) return;
    renderizador.setSize(ancho, alto, false);
    lienzo.style.width = "100%"; lienzo.style.height = "100%";
    camara.aspect = ancho / alto;
    camara.updateProjectionMatrix();
    renderizar();
  }
  new ResizeObserver(ajustar).observe(escena);
  controles.addEventListener("change", renderizar);

  // ---- Interacción ---------------------------------------------------------------------------------
  const rayo = new THREE.Raycaster(), puntero = new THREE.Vector2();
  lienzo.addEventListener("pointermove", function (ev) {
    const r = lienzo.getBoundingClientRect();
    puntero.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    rayo.setFromCamera(puntero, camara);
    const golpes = rayo.intersectObjects(sensores.map(function (s) { return s.diana; }), false);
    if (!golpes.length) { ayudas.ocultarTip(); return; }
    const canal = golpes[0].object.userData.canal;
    const s = sensores.find(function (x) { return x.e.canal === canal; });
    const val = valor(s.e, estado.banda);
    ayudas.mostrarTip(ev.clientX, ev.clientY, val === null ? canal + ": descartado, sin dato" : canal + " · " + textoValor(val));
  });
  lienzo.addEventListener("pointerleave", ayudas.ocultarTip);
  lienzo.addEventListener("keydown", function (ev) {
    const paso = Math.PI / 12;
    const acciones = { ArrowLeft: [paso, 0, 1], ArrowRight: [-paso, 0, 1], ArrowUp: [0, -paso, 1], ArrowDown: [0, paso, 1],
                       "+": [0, 0, 0.88], "=": [0, 0, 0.88], "-": [0, 0, 1.14] };
    if (acciones[ev.key]) { ev.preventDefault(); girar.apply(null, acciones[ev.key]); }
  });

  // ---- Barra de herramientas ---------------------------------------------------------------------------------
  function boton(texto, accion, alterna) {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = texto;
    if (alterna) b.setAttribute("aria-pressed", alterna === "on" ? "true" : "false");
    b.addEventListener("click", function () { accion(b); });
    barra.appendChild(b);
    return b;
  }
  [["Frente", "frente"], ["Arriba", "arriba"], ["Izquierda", "izquierda"], ["Derecha", "derecha"], ["Atrás", "atras"], ["Restablecer", "inicial"]]
    .forEach(function (p) { boton(p[0], function () { irA(p[1], 6.4); }); });
  barra.appendChild(Object.assign(document.createElement("span"), { className: "sep" }));
  boton("Etiquetas", function (b) { verEtiquetas = !verEtiquetas; b.setAttribute("aria-pressed", verEtiquetas); renderizar(); }, verEtiquetas ? "on" : "off");
  let girando = false;
  function bucle() { if (!girando) return; controles.update(); requestAnimationFrame(bucle); }
  boton("Girar solo", function (b) {
    girando = !girando; controles.autoRotate = girando; b.setAttribute("aria-pressed", girando);
    if (girando) bucle();
  }, "off");
  boton("Guardar imagen", function () {
    renderizar();
    const lado = document.createElement("canvas");
    lado.width = lienzo.width; lado.height = lienzo.height + 44;
    const c = lado.getContext("2d");
    c.fillStyle = css("--fondo"); c.fillRect(0, 0, lado.width, lado.height);
    c.drawImage(lienzo, 0, 0);
    c.fillStyle = css("--texto-suave"); c.font = "16px " + css("--fuente");
    const nombre = bandas.find(function (x) { return x.clave === estado.banda; }).nombre;
    c.fillText("Interpolación orientativa sobre 14 sensores, no localiza fuentes · plantilla fsaverage · " + nombre + " · " +
               (estado.metrica === "rel" ? "potencia relativa (%)" : "potencia absoluta (log10 V²)"), 12, lienzo.height + 28);
    const a = document.createElement("a");
    a.download = "cabeza-" + estado.banda + "-" + estado.metrica + ".png";
    a.href = lado.toDataURL("image/png");
    a.click();
  });

  // ---- Mapas 2D: el cerebro real visto desde arriba, renderizado aparte ----------------------------------------
  const r2d = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  const escena2d = new THREE.Scene();
  const mitad = 1.25;
  const camara2d = new THREE.OrthographicCamera(-mitad, mitad, mitad, -mitad, 0.1, 50);
  const centroVista = new THREE.Vector3(0, objetivo.y, 0);
  camara2d.position.set(centroVista.x, centroVista.y, 10);
  camara2d.up.set(0, 1, 0);
  camara2d.lookAt(centroVista.x, centroVista.y, 0);
  const geometria2d = new THREE.BufferGeometry();
  geometria2d.setAttribute("position", cerebro.geometria.attributes.position);
  geometria2d.setAttribute("normal", cerebro.geometria.attributes.normal);
  geometria2d.setIndex(cerebro.geometria.index);
  geometria2d.setAttribute("color", new THREE.BufferAttribute(new Float32Array(cerebro.n * 3), 3));
  const cerebro2d = new THREE.Mesh(geometria2d, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.8, metalness: 0 }));
  const sombra2d = new THREE.Mesh(cabeza.geometria, new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.13, depthTest: false, depthWrite: false }));
  sombra2d.renderOrder = -1;
  escena2d.add(sombra2d, cerebro2d);
  escena2d.add(new THREE.HemisphereLight(0xffffff, 0x8a96a8, 1.7));
  const foco2d = new THREE.DirectionalLight(0xffffff, 1.8);
  foco2d.position.set(0.3, 0.5, 1);
  escena2d.add(foco2d);

  const api = {
    // Dibuja la banda en `destino` (canvas 2D). Devuelve cómo pasar un electrodo a fracciones (0-1) de ese lienzo.
    dibujar: function (destino, banda) {
      const lado = destino.width;
      if (r2d.domElement.width !== lado) r2d.setSize(lado, lado, false);
      aplicar(geometria2d, coloresDe(cerebro, "cerebro", banda));
      sombra2d.material.color.set(css("--texto-suave"));
      r2d.render(escena2d, camara2d);
      const ctx = destino.getContext("2d");
      ctx.clearRect(0, 0, lado, lado);
      ctx.drawImage(r2d.domElement, 0, 0);
      return function (e) {
        const p = geo.canales[e.canal].pos;
        return [(p[0] - centroVista.x) / (2 * mitad) + 0.5, 0.5 - (p[1] - centroVista.y) / (2 * mitad)];
      };
    },
  };

  suscribir(pintar);
  document.addEventListener("tema:cambio", pintar);
  ponerModo("cabeza");
  irA("inicial", 6.4);
  ajustar();
  return api;
}
