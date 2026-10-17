// Mantiene al día la lista de grabaciones mientras hay cola. Sin dependencias.
(function () {
  var PERIODO_MS = 3000;

  function lista() { return document.getElementById("lista-viva"); }

  function actualizar() {
    var actual = lista();
    if (!actual || actual.dataset.activo !== "1") return;

    fetch(actual.dataset.url, { headers: { "X-Requested-With": "fetch" } })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (html) {
        if (!html) return;
        // No se pisa lo que la persona está escribiendo en una condición.
        var activo = document.activeElement;
        if (activo && activo.tagName === "INPUT" && actual.contains(activo)) return;
        var plantilla = document.createElement("template");
        plantilla.innerHTML = html.trim();
        var nueva = plantilla.content.firstElementChild;
        if (nueva && lista() === actual) actual.replaceWith(nueva);
      })
      .catch(function () { /* sin red: se reintenta en el siguiente ciclo */ });
  }

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
