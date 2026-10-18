// Portada: cabeza translúcida con el cerebro dentro, los 14 sensores en su sitio y pulsos de luz
// que salen de cada sensor. Es decorativo: los pulsos no son datos. Mallas de la plantilla
// fsaverage (las mismas del visor de Análisis) y posiciones de electrodos de EEG-Library.
import * as THREE from "three";

const portada = document.getElementById("portada");
const lienzo = document.getElementById("escena");
const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// ---- Tema: colores desde los tokens CSS, sin recargar ------------------------------------------------
function leerTema() {
  const s = getComputedStyle(document.documentElement);
  const acento = (s.getPropertyValue("--acento") || "#4cc9f0").trim();
  const fondo = (s.getPropertyValue("--fondo") || "#0b0f15").trim();
  const c = new THREE.Color(fondo);
  const oscuro = (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) < 0.5;
  portada.dataset.modo = oscuro ? "oscuro" : "claro";
  return { acento: new THREE.Color(acento), oscuro: oscuro };
}

// ---- Escena ---------------------------------------------------------------------------------------
function webglDisponible() {
  try {
    const prueba = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (prueba.getContext("webgl2") || prueba.getContext("webgl")));
  } catch (e) { return false; }
}

async function cargarMalla(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url);
  const buf = await r.arrayBuffer();
  const [nv, nt] = new Uint32Array(buf, 0, 2);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(buf, 8, nv * 3), 3));
  g.setIndex(new THREE.BufferAttribute(new Uint32Array(buf, 8 + nv * 12, nt * 3), 1));
  g.computeVertexNormals();
  return g;
}

// Curvas de nivel de una malla (cortes con planos x, y o z constantes): la misma rejilla del visor de Análisis.
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

const GLSL_PULSOS = `
  uniform vec3 uSens[14]; uniform float uFase[14]; uniform float uT; uniform vec3 uCentro;
  float pulsos(vec3 p) {
    vec3 d = normalize(p - uCentro); float s = 0.0;
    for (int i = 0; i < 14; i++) {
      float ang = acos(clamp(dot(d, uSens[i]), -1.0, 1.0));
      float t = fract(uT * 0.14 + uFase[i]);
      float w = 0.10 + 0.14 * t;
      float e = (ang - t * 1.7) / w;
      s += exp(-e * e) * (1.0 - t) * (1.0 - t);
    }
    return s;
  }`;

async function escena() {
  const [cabezaG, cerebroG, ficha] = await Promise.all([
    cargarMalla(portada.dataset.cabeza), cargarMalla(portada.dataset.cerebro),
    fetch(portada.dataset.electrodos).then(function (r) { return r.json(); }),
  ]);
  const centro = new THREE.Vector3(...ficha.centro);
  const nombres = Object.keys(ficha.canales);
  const pos = nombres.map(function (n) { return new THREE.Vector3(...ficha.canales[n].pos); });
  const normales = nombres.map(function (n) { return new THREE.Vector3(...ficha.canales[n].normal).normalize(); });

  const renderer = new THREE.WebGLRenderer({ canvas: lienzo, antialias: true, alpha: true, powerPreference: "high-performance" });
  let ratio = Math.min(window.devicePixelRatio || 1, 1.5);
  renderer.setPixelRatio(ratio);
  const camara = new THREE.PerspectiveCamera(28, 1, 0.1, 50);
  camara.position.set(0, -0.25, 7.0);
  const raiz = new THREE.Scene();

  const pivote = new THREE.Group();                 // giro y parallax
  const eje = new THREE.Group(); eje.rotation.x = -Math.PI / 2;   // z (arriba) pasa a y; la nariz queda en -z
  const modelo = new THREE.Group(); modelo.position.copy(centro).multiplyScalar(-1);
  pivote.add(eje); eje.add(modelo); raiz.add(pivote);

  const uni = {
    uSens: { value: pos.map(function (p) { return p.clone().sub(centro).normalize(); }) },
    uFase: { value: nombres.map(function (_, i) { return (i * 0.37) % 1; }) },
    uT: { value: 0 }, uCentro: { value: centro },
    uAcento: { value: new THREE.Color() }, uBase: { value: new THREE.Color() },
    uPulso: { value: new THREE.Color() }, uOscuro: { value: 1 },
  };

  const cerebro = new THREE.Mesh(cerebroG, new THREE.ShaderMaterial({
    uniforms: uni,
    vertexShader: `varying vec3 vP; varying vec3 vN; varying vec3 vV;
      void main(){ vP = position; vN = normalize(normalMatrix * normal);
        vec4 mv = modelViewMatrix * vec4(position, 1.0); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: GLSL_PULSOS + `
      uniform vec3 uAcento; uniform vec3 uBase; uniform vec3 uPulso; uniform float uOscuro;
      varying vec3 vP; varying vec3 vN; varying vec3 vV;
      void main(){
        float luz = 0.35 + 0.65 * max(dot(normalize(vN), normalize(vec3(0.4, 0.6, 0.7))), 0.0);
        float rim = pow(1.0 - max(dot(normalize(vN), normalize(vV)), 0.0), 2.5);
        float p = clamp(pulsos(vP), 0.0, 1.0);
        vec3 c = uBase * luz;
        c = uOscuro > 0.5 ? c + uAcento * rim * 0.35 + uPulso * p * 1.05 : mix(c, uPulso, p * 0.95) * (1.0 - rim * 0.25);
        gl_FragColor = vec4(c, 1.0);
      }`,
  }));
  cerebro.renderOrder = 0;
  modelo.add(cerebro);

  const cabeza = new THREE.Mesh(cabezaG, new THREE.ShaderMaterial({
    uniforms: uni, transparent: true, depthWrite: false,
    vertexShader: `varying vec3 vP; varying vec3 vN; varying vec3 vV;
      void main(){ vP = position; vN = normalize(normalMatrix * normal);
        vec4 mv = modelViewMatrix * vec4(position, 1.0); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: GLSL_PULSOS + `
      uniform vec3 uAcento; uniform vec3 uPulso; uniform float uOscuro;
      varying vec3 vP; varying vec3 vN; varying vec3 vV;
      void main(){
        float f = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.2);
        float p = clamp(pulsos(vP), 0.0, 1.0) * 0.45;
        if (uOscuro > 0.5) gl_FragColor = vec4(uAcento * f * 1.2 + uPulso * p, f * 0.9 + p * 0.5 + 0.03);
        else gl_FragColor = vec4(mix(uAcento * 0.7, uPulso, clamp(p * 2.0, 0.0, 1.0)), f * 0.75 + p * 0.5 + 0.05);
      }`,
  }));
  cabeza.renderOrder = 1;
  modelo.add(cabeza);

  // Malla de la cabeza, como en Análisis (mismos niveles de corte).
  const niveles = [];
  [-0.9, -0.45, 0, 0.45, 0.9].forEach(function (n) { niveles.push([2, n]); });
  [-0.8, -0.4, 0, 0.4, 0.8].forEach(function (n) { niveles.push([0, n]); });
  [-1.2, -0.8, -0.4, 0, 0.4, 0.8].forEach(function (n) { niveles.push([1, n]); });
  const matRejilla = new THREE.LineBasicMaterial({ transparent: true, opacity: 0.5, depthWrite: false });
  const rejilla = new THREE.LineSegments(contornos(cabezaG, niveles), matRejilla);
  rejilla.renderOrder = 2;
  modelo.add(rejilla);

  // Sensores como en el visor de Análisis: discos concentricos pegados al cuero cabelludo y orientados a él.
  const sensores = nombres.map(function (_, i) {
    const normal = normales[i], p = pos[i];
    let arriba = new THREE.Vector3(0, 0, 1).addScaledVector(normal, -normal.z);
    if (arriba.length() < 0.2) arriba = new THREE.Vector3(0, 1, 0).addScaledVector(normal, -normal.y);
    arriba.normalize();
    const derecha = new THREE.Vector3().crossVectors(arriba, normal).normalize();
    const q = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(derecha, arriba, normal));
    const disco = function (radio, altura, orden) {
      const m = new THREE.Mesh(new THREE.CircleGeometry(radio, 28), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide, transparent: true, depthWrite: false }));
      m.quaternion.copy(q); m.position.copy(p).addScaledVector(normal, altura); m.renderOrder = orden;
      modelo.add(m); return m;
    };
    return { halo: disco(0.075, 0.01, 3), aro: disco(0.064, 0.02, 4), centro: disco(0.044, 0.03, 5) };
  });

  // Tema
  function aplicarTema() {
    const t = leerTema();
    uni.uAcento.value.copy(t.acento);
    uni.uOscuro.value = t.oscuro ? 1 : 0;
    const fondo = new THREE.Color(getComputedStyle(document.documentElement).getPropertyValue("--fondo").trim() || "#0b0f15");
    if (t.oscuro) {
      uni.uBase.value.set(0.05, 0.16, 0.25);
      uni.uPulso.value.set(1.0, 0.55, 0.08);                 // ámbar: contrasta con el cian de la cabeza
    } else {
      uni.uBase.value.set(0.52, 0.72, 0.9);
      uni.uPulso.value.set(0.82, 0.3, 0.0);
    }
    matRejilla.color.copy(t.oscuro ? t.acento : new THREE.Color(0.1, 0.25, 0.45));
    matRejilla.opacity = t.oscuro ? 0.45 : 0.5;
    cabeza.material.blending = t.oscuro ? THREE.AdditiveBlending : THREE.NormalBlending;
    cabeza.material.needsUpdate = true;
    sensores.forEach(function (s) {
      s.halo.material.color.copy(t.acento); s.aro.material.color.copy(fondo); s.centro.material.color.copy(t.acento);
    });
  }
  aplicarTema();
  document.addEventListener("tema:cambio", aplicarTema);
  window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", aplicarTema);

  function ajustar() {
    const w = lienzo.clientWidth, h = lienzo.clientHeight;
    renderer.setSize(w, h, false);
    camara.aspect = w / h; camara.updateProjectionMatrix();
  }
  ajustar();
  window.addEventListener("resize", ajustar);

  let rx = 0, ry = 0, ox = 0, oy = 0;
  window.addEventListener("pointermove", function (e) {
    ox = (e.clientX / window.innerWidth - 0.5) * 2; oy = (e.clientY / window.innerHeight - 0.5) * 2;
  });

  // Animación: pausa fuera de pantalla o con la pestaña oculta; baja la calidad si va lenta.
  let visible = true, oculta = document.hidden, ultimo = 0, t0 = performance.now(), nivel = 0;
  let acum = 0, cuenta = 0;
  new IntersectionObserver(function (e) { visible = e[0].isIntersecting; if (visible) pedir(); }).observe(portada);
  document.addEventListener("visibilitychange", function () { oculta = document.hidden; if (!oculta) pedir(); });
  function pedir() { if (visible && !oculta && !reducido) requestAnimationFrame(cuadro); }

  function pintar(ms) {
    const t = ms / 1000;
    uni.uT.value = t;
    const base = Math.PI + 0.85;                            // tres cuartos: la nariz mira a la derecha
    rx += (oy * 0.12 - rx) * 0.05; ry += (ox * 0.25 - ry) * 0.05;
    pivote.rotation.y = base + Math.sin(t * 0.13) * 0.5 + ry;
    pivote.rotation.x = rx;
    sensores.forEach(function (s, i) {
      const k = 0.5 + 0.5 * Math.sin(t * 2.2 + i * 1.3);
      s.halo.scale.setScalar(1 + 0.45 * k); s.halo.material.opacity = 0.85 - 0.6 * k;
      s.halo.visible = nivel < 2;
    });
    renderer.render(raiz, camara);
  }

  function cuadro(ahora) {
    if (!visible || oculta) return;
    if (ultimo) {
      acum += ahora - ultimo; cuenta++;
      if (cuenta === 90) {                                  // ~1,5 s: ¿va fluido?
        if (acum / cuenta > 34) {
          nivel++;
          if (nivel === 1) { ratio = 1; renderer.setPixelRatio(1); ajustar(); }
          else if (nivel >= 3) { portada.dataset.sin3d = "1"; renderer.dispose(); return; }
        }
        acum = 0; cuenta = 0;
      }
    }
    ultimo = ahora;
    pintar(ahora - t0);
    requestAnimationFrame(cuadro);
  }
  document.addEventListener("visibilitychange", function () { ultimo = 0; });

  pintar(2500);                                             // primer fotograma, también sin animación
  portada.dataset.listo = "1";
  pedir();
}

if (!webglDisponible()) {
  leerTema();
  portada.dataset.sin3d = "1";
} else {
  escena().catch(function () { leerTema(); portada.dataset.sin3d = "1"; });
}
if (reducido) portada.dataset.reducido = "1";
