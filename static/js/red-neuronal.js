// Fondo de la portada (zona izquierda): neuronas con soma, dendritas ramificadas y axones, con pulsos de
// luz que viajan por los axones. Es decorativo y procedural: no representa datos. Canvas 2D.
const lienzo = document.getElementById("red-neuronal");
if (lienzo) {
  const ctx = lienzo.getContext("2d");
  const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let ancho = 0, alto = 0, ratio = 1;
  let nodos = [], aristas = [], pulsos = [];
  let oscuro = true, acento = [76, 201, 240];
  let ratonX = -9999, ratonY = -9999;     // posición del ratón en el lienzo; lejos = sin efecto
  const RADIO_LUZ = 260;                  // distancia (px) a la que una neurona se ilumina por el ratón
  let visible = !document.hidden, ultimo = 0, acumulado = 0, cuadros = 0;

  // Generador con semilla: la red es la misma en cada visita y al redimensionar.
  function semilla(n) { return function () { n |= 0; n = n + 0x6D2B79F5 | 0; let t = Math.imul(n ^ n >>> 15, 1 | n); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

  function leerTema() {
    const s = getComputedStyle(document.documentElement);
    const rgb = function (hex) { const h = hex.replace("#", ""); const v = h.length === 3 ? h.replace(/./g, "$&$&") : h; return [0, 2, 4].map(function (i) { return parseInt(v.substr(i, 2), 16); }); };
    const fr = rgb(s.getPropertyValue("--fondo").trim() || "#0b0f15");
    oscuro = (0.2126 * fr[0] + 0.7152 * fr[1] + 0.0722 * fr[2]) < 128;
    acento = rgb(s.getPropertyValue("--acento").trim() || "#4cc9f0");
  }

  function construir() {
    ratio = Math.min(window.devicePixelRatio || 1, 1.5);
    ancho = lienzo.clientWidth; alto = lienzo.clientHeight;
    lienzo.width = Math.round(ancho * ratio); lienzo.height = Math.round(alto * ratio);
    if (!ancho || !alto) return;
    const rnd = semilla(20261018);
    const n = Math.max(6, Math.min(20, Math.round(ancho * alto / 52000)));
    nodos = [];
    for (let intento = 0; nodos.length < n && intento < n * 80; intento++) {
      const x = 30 + rnd() * (ancho - 60), y = 30 + rnd() * (alto - 60);
      if (nodos.some(function (o) { return Math.hypot(o.x - x, o.y - y) < 150; })) continue;
      const z = 0.55 + rnd() * 0.45;
      const lobulos = 6 + Math.floor(rnd() * 3), blob = [];
      for (let i = 0; i < lobulos; i++) blob.push(0.78 + rnd() * 0.44);
      const dendritas = [], k = 5 + Math.floor(rnd() * 3), base = rnd() * 6.283;
      for (let i = 0; i < k; i++) {
        const ang = base + (i / k) * 6.283 + (rnd() - 0.5) * 0.5;
        const largo = (55 + rnd() * 60) * z;
        const ramas = [];
        const nr = 1 + Math.floor(rnd() * 2);
        for (let j = 0; j < nr; j++) ramas.push({ t: 0.45 + rnd() * 0.3, da: (rnd() < 0.5 ? -1 : 1) * (0.5 + rnd() * 0.6), l: largo * (0.35 + rnd() * 0.3) });
        dendritas.push({ a: ang, l: largo, c: (rnd() - 0.5) * 0.8, ramas: ramas });
      }
      nodos.push({ x: x, y: y, z: z, r: (7 + rnd() * 4) * z, blob: blob, rot: rnd() * 6.283,
                   ax: 8 + rnd() * 14, ay: 8 + rnd() * 14, w1: 0.05 + rnd() * 0.07, w2: 0.04 + rnd() * 0.07,
                   f1: rnd() * 6.28, f2: rnd() * 6.28, luz: 0, dendritas: dendritas, vecinos: [], px: x, py: y });
    }
    aristas = [];
    const yaHay = {};
    nodos.forEach(function (a, i) {
      nodos.map(function (b, j) { return { j: j, d: Math.hypot(a.x - b.x, a.y - b.y) }; })
        .filter(function (o) { return o.j !== i; }).sort(function (u, v) { return u.d - v.d; }).slice(0, 2)
        .forEach(function (o) {
          const clave = Math.min(i, o.j) + "-" + Math.max(i, o.j);
          if (yaHay[clave]) return;
          yaHay[clave] = true;
          const e = { a: i, b: o.j, curva: (rnd() - 0.5) * 0.5, id: aristas.length };
          aristas.push(e); nodos[i].vecinos.push(e); nodos[o.j].vecinos.push(e);
        });
    });
    pulsos = [];
    const np = Math.max(4, Math.round(aristas.length * 0.7));
    for (let i = 0; i < np && aristas.length; i++) {
      pulsos.push({ e: aristas[Math.floor(rnd() * aristas.length)], s: rnd() < 0.5 ? 0 : 1, u: rnd(), v: 0.09 + rnd() * 0.13, r: 0.85 + rnd() * 0.5 });
    }
  }

  function posicion(n, t) {
    n.px = n.x + Math.sin(t * n.w1 + n.f1) * n.ax * n.z;
    n.py = n.y + Math.cos(t * n.w2 + n.f2) * n.ay * n.z;
    const d = Math.hypot(n.px - ratonX, n.py - ratonY), k = Math.max(0, 1 - d / RADIO_LUZ);
    n.luz += (k * k - n.luz) * 0.12;       // se enciende y se apaga con suavidad
  }
  function control(e) {
    const a = nodos[e.a], b = nodos[e.b];
    const dx = b.px - a.px, dy = b.py - a.py;
    return [(a.px + b.px) / 2 - dy * e.curva, (a.py + b.py) / 2 + dx * e.curva];
  }
  function bez(x0, y0, cx, cy, x1, y1, u) {
    const v = 1 - u;
    return [v * v * x0 + 2 * v * u * cx + u * u * x1, v * v * y0 + 2 * v * u * cy + u * u * y1];
  }
  function col(rgb, a) { return "rgba(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + "," + a + ")"; }

  // Rama afinada: polígono relleno que va de un grosor w0 en la base a casi 0 en la punta.
  function afinada(x0, y0, cx, cy, x1, y1, w0) {
    const izq = [], der = [], pasos = 10;
    for (let i = 0; i <= pasos; i++) {
      const u = i / pasos, p = bez(x0, y0, cx, cy, x1, y1, u);
      const q = bez(x0, y0, cx, cy, x1, y1, Math.min(1, u + 0.02)), r = bez(x0, y0, cx, cy, x1, y1, Math.max(0, u - 0.02));
      let tx = q[0] - r[0], ty = q[1] - r[1]; const m = Math.hypot(tx, ty) || 1; tx /= m; ty /= m;
      const w = w0 * (1 - u) * (1 - u * 0.4) + 0.2;
      izq.push([p[0] - ty * w, p[1] + tx * w]); der.push([p[0] + ty * w, p[1] - tx * w]);
    }
    ctx.beginPath();
    ctx.moveTo(izq[0][0], izq[0][1]);
    for (let i = 1; i < izq.length; i++) ctx.lineTo(izq[i][0], izq[i][1]);
    for (let i = der.length - 1; i >= 0; i--) ctx.lineTo(der[i][0], der[i][1]);
    ctx.closePath(); ctx.fill();
  }

  function dibujar(t, dt) {
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, ancho, alto);
    const fibra = oscuro ? acento : [10, 95, 150];
    const pulso = oscuro ? [255, 140, 30] : [205, 75, 0];
    ctx.globalCompositeOperation = oscuro ? "lighter" : "source-over";
    nodos.forEach(function (n) { posicion(n, t); });
    const controles = aristas.map(control);

    // axones: resplandor ancho y trazo fino
    aristas.forEach(function (e, i) {
      const a = nodos[e.a], b = nodos[e.b], z = (a.z + b.z) / 2, c = controles[i];
      const lz = (a.luz + b.luz) / 2;
      [[5 * z * (1 + lz), 0.07 + 0.12 * lz], [1.6 * z * (1 + 0.5 * lz), Math.min(1, (oscuro ? 0.5 : 0.45) + 0.4 * lz)]].forEach(function (par) {
        ctx.strokeStyle = col(fibra, par[1]); ctx.lineWidth = par[0]; ctx.lineCap = "round";
        ctx.beginPath(); ctx.moveTo(a.px, a.py); ctx.quadraticCurveTo(c[0], c[1], b.px, b.py); ctx.stroke();
      });
    });

    // neuronas: dendritas ramificadas y soma
    nodos.forEach(function (n) {
      ctx.fillStyle = col(fibra, Math.min(1, ((oscuro ? 0.5 : 0.55) + 0.4 * n.luz) * n.z));
      n.dendritas.forEach(function (d) {
        const x2 = n.px + Math.cos(d.a) * d.l, y2 = n.py + Math.sin(d.a) * d.l;
        const cx = n.px + Math.cos(d.a + d.c) * d.l * 0.55, cy = n.py + Math.sin(d.a + d.c) * d.l * 0.55;
        afinada(n.px, n.py, cx, cy, x2, y2, 4.2 * n.z);
        d.ramas.forEach(function (r) {
          const p = bez(n.px, n.py, cx, cy, x2, y2, r.t), ang = d.a + r.da;
          const x3 = p[0] + Math.cos(ang) * r.l, y3 = p[1] + Math.sin(ang) * r.l;
          afinada(p[0], p[1], (p[0] + x3) / 2 + Math.sin(ang) * 6, (p[1] + y3) / 2 - Math.cos(ang) * 6, x3, y3, 2.4 * n.z);
        });
      });
      // soma: contorno irregular con un núcleo más claro
      const R = n.r, L = n.blob.length;
      ctx.beginPath();
      for (let i = 0; i <= L; i++) {
        const k = i % L, ang = n.rot + (k / L) * 6.283, rr = R * n.blob[k];
        const x = n.px + Math.cos(ang) * rr, y = n.py + Math.sin(ang) * rr;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.closePath();
      const g = ctx.createRadialGradient(n.px - R * 0.25, n.py - R * 0.25, 0, n.px, n.py, R * 1.2);
      g.addColorStop(0, col(oscuro ? [200, 240, 255] : fibra, oscuro ? 0.95 : 0.9));
      g.addColorStop(0.55, col(fibra, Math.min(1, (oscuro ? 0.7 : 0.8) + 0.3 * n.luz)));
      g.addColorStop(1, col(fibra, (oscuro ? 0.25 : 0.55) + 0.3 * n.luz));
      ctx.fillStyle = g; ctx.fill();
      const RH = R * (3 + 3.5 * n.luz);
      const h = ctx.createRadialGradient(n.px, n.py, R * 0.8, n.px, n.py, RH);
      h.addColorStop(0, col(fibra, (oscuro ? 0.22 : 0.12) + (oscuro ? 0.5 : 0.3) * n.luz)); h.addColorStop(1, col(fibra, 0));
      ctx.fillStyle = h; ctx.beginPath(); ctx.arc(n.px, n.py, RH, 0, 6.283); ctx.fill();
    });

    // pulsos con cola a lo largo de los axones
    pulsos.forEach(function (p) {
      p.u += p.v * dt;
      if (p.u >= 1) {
        const finIdx = p.s === 0 ? p.e.b : p.e.a, fin = nodos[finIdx];
        const opciones = fin.vecinos.filter(function (e) { return e !== p.e; });
        const sig = opciones.length ? opciones[Math.floor(Math.random() * opciones.length)] : p.e;
        p.s = sig.a === finIdx ? 0 : 1; p.e = sig; p.u = 0;
      }
      const a = nodos[p.e.a], b = nodos[p.e.b], c = controles[p.e.id];
      const tramo = function (u) { const w = p.s === 0 ? u : 1 - u; return bez(a.px, a.py, c[0], c[1], b.px, b.py, w); };
      const cola = 8;
      ctx.lineCap = "round";
      for (let i = 0; i < cola; i++) {
        const q0 = tramo(Math.max(0, p.u - (i + 1) * 0.02)), q1 = tramo(Math.max(0, p.u - i * 0.02));
        ctx.strokeStyle = col(pulso, (1 - i / cola) * 0.9);
        ctx.lineWidth = (3 - i * 0.3) * p.r;
        ctx.beginPath(); ctx.moveTo(q0[0], q0[1]); ctx.lineTo(q1[0], q1[1]); ctx.stroke();
      }
      const h = tramo(p.u), r = 11 * p.r;
      const g = ctx.createRadialGradient(h[0], h[1], 0, h[0], h[1], r);
      g.addColorStop(0, oscuro ? "rgba(255,240,215,0.98)" : col(pulso, 1));
      g.addColorStop(0.3, col(pulso, 0.55)); g.addColorStop(1, col(pulso, 0));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(h[0], h[1], r, 0, 6.283); ctx.fill();
    });
    ctx.globalCompositeOperation = "source-over";
  }

  function cuadro(ahora) {
    if (!visible) return;
    const dt = ultimo ? Math.min((ahora - ultimo) / 1000, 0.1) : 0.016;
    if (ultimo) {
      acumulado += ahora - ultimo; cuadros++;
      if (cuadros === 90) {                                  // si va lento, aligera: resolución 1 y menos pulsos
        if (acumulado / cuadros > 34 && ratio > 1) { ratio = 1; lienzo.width = ancho; lienzo.height = alto; pulsos.length = Math.ceil(pulsos.length / 2); }
        acumulado = 0; cuadros = 0;
      }
    }
    ultimo = ahora;
    dibujar(ahora / 1000, dt);
    requestAnimationFrame(cuadro);
  }

  window.addEventListener("pointermove", function (e) {
    const caja = lienzo.getBoundingClientRect();
    ratonX = e.clientX - caja.left; ratonY = e.clientY - caja.top;
  });
  document.addEventListener("pointerleave", function () { ratonX = ratonY = -9999; });
  let espera;
  window.addEventListener("resize", function () {
    clearTimeout(espera);
    espera = setTimeout(function () { construir(); if (reducido) dibujar(3, 0); }, 150);
  });
  document.addEventListener("tema:cambio", function () { leerTema(); if (reducido) dibujar(3, 0); });
  window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", function () { leerTema(); });
  document.addEventListener("visibilitychange", function () {
    visible = !document.hidden; ultimo = 0;
    if (visible && !reducido) requestAnimationFrame(cuadro);
  });
  leerTema(); construir();
  if (reducido) dibujar(3, 0); else requestAnimationFrame(cuadro);
}
