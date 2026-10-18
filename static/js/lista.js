// Mantiene al día la lista de grabaciones mientras hay cola. Sin dependencias.
(function () {
  var PERIODO_MS = 3000;

  function lista() { return document.getElementById("lista-viva"); }

  // Comparar sin el token CSRF (cambia en cada respuesta) ni los espacios: solo se repinta si hay un cambio real.
  function normal(html) {
    return html.replace(/(name="csrfmiddlewaretoken"\s+value=")[^"]*"/g, '$1"').replace(/\s+/g, " ").trim();
  }
  var ultimoHtml = lista() ? normal(lista().outerHTML) : null;
  var ignorarScrollHasta = 0;   // restaurar el scroll al repintar no debe cerrar los menús que se reabren

  // Lo que la persona tiene abierto o desplazado se conserva al repintar la lista.
  function guardarEstado(actual) {
    return {
      abiertos: Array.prototype.map.call(actual.querySelectorAll("details[open][data-pk]"), function (d) {
        return d.className + ":" + d.dataset.pk;
      }),
      scroll: Array.prototype.map.call(actual.querySelectorAll(".tabla-ancha"), function (t) { return t.scrollLeft; }),
    };
  }
  function restaurarEstado(nueva, estado) {
    ignorarScrollHasta = Date.now() + 250;
    estado.abiertos.forEach(function (clave) {
      var partes = clave.split(":");
      var d = nueva.querySelector("details." + partes[0] + "[data-pk='" + partes[1] + "']");
      if (d) { d.setAttribute("open", ""); if (partes[0] === "menu") colocar(d); }
    });
    nueva.querySelectorAll(".tabla-ancha").forEach(function (t, i) { t.scrollLeft = estado.scroll[i] || 0; });
  }

  function actualizar() {
    var actual = lista();
    if (!actual || actual.dataset.activo !== "1") return;

    fetch(actual.dataset.url, { headers: { "X-Requested-With": "fetch" } })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (html) {
        if (!html) return;
        // Si nada ha cambiado no se repinta: así no se reinician las animaciones ni se mueve nada.
        var comparable = normal(html);
        if (comparable === ultimoHtml) return;
        ultimoHtml = comparable;
        // No se pisa lo que la persona está escribiendo en una condición.
        var activo = document.activeElement;
        if (activo && activo.tagName === "INPUT" && actual.contains(activo)) return;
        var estado = guardarEstado(actual);
        var plantilla = document.createElement("template");
        plantilla.innerHTML = html.trim();
        var nueva = plantilla.content.firstElementChild;
        if (nueva && lista() === actual) { actual.replaceWith(nueva); restaurarEstado(nueva, estado); }
      })
      .catch(function () { /* sin red: se reintenta en el siguiente ciclo */ });
  }

  // El menú «···» se coloca con posición fija junto a su botón: así no lo recorta el contenedor con
  // scroll de la tabla y, si abajo no cabe, se abre hacia arriba.
  function colocar(menu) {
    var caja = menu.querySelector(".menu-lista"), boton = menu.querySelector("summary");
    if (!caja || !boton) return;
    var r = boton.getBoundingClientRect();
    caja.classList.remove("colocado");
    caja.style.left = "0px"; caja.style.top = "0px";
    var ancho = caja.offsetWidth, alto = caja.offsetHeight;
    var izquierda = Math.max(8, Math.min(r.right - ancho, window.innerWidth - ancho - 8));
    var abajo = r.bottom + 4, arriba = r.top - alto - 4;
    caja.style.left = izquierda + "px";
    caja.style.top = ((abajo + alto > window.innerHeight - 8 && arriba > 8) ? arriba : abajo) + "px";
    caja.classList.add("colocado");
  }
  document.addEventListener("toggle", function (ev) {
    var d = ev.target;
    if (d.matches && d.matches("details.menu") && d.open) colocar(d);
  }, true);
  function cerrarMenus() {
    if (Date.now() < ignorarScrollHasta) return;
    document.querySelectorAll("details.menu[open]").forEach(function (m) { m.removeAttribute("open"); });
  }
  window.addEventListener("scroll", cerrarMenus, true);
  window.addEventListener("resize", cerrarMenus);

  // Un temporizador permanente: solo actúa si hay cola (data-activo="1"). Así
  // también se reactiva tras pulsar «Reintentar» sin recargar a mano.
  setInterval(actualizar, PERIODO_MS);

  // Menús «más acciones»: se cierran al pulsar fuera, al elegir una opción o con Escape.
  document.addEventListener("click", function (ev) {
    document.querySelectorAll("details.menu[open]").forEach(function (m) {
      if (!m.contains(ev.target)) m.removeAttribute("open");
    });
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Escape") return;
    document.querySelectorAll("details.menu[open], details.condicion[open]").forEach(function (m) {
      m.removeAttribute("open");
      var resumen = m.querySelector("summary");
      if (resumen) resumen.focus();
    });
  });
})();
