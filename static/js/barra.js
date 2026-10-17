// Selector de grabación de la cabecera: un panel con buscador. Sin JavaScript sigue siendo una lista
// de enlaces que se abre y se cierra (un <details>); aquí se añaden el buscador, el teclado y el cierre.
(function () {
  var selector = document.querySelector(".selector-grabacion");
  if (!selector) return;
  var buscador = selector.querySelector(".buscar");
  var campo = buscador.querySelector("input");
  var enlaces = Array.prototype.slice.call(selector.querySelectorAll(".panel-grabaciones a"));
  var sinResultados = selector.querySelector(".vacio-filtro");
  buscador.hidden = false;

  function visibles() { return enlaces.filter(function (a) { return !a.parentElement.hidden; }); }

  function filtrar() {
    var q = campo.value.trim().toLowerCase();
    enlaces.forEach(function (a) { a.parentElement.hidden = q !== "" && a.dataset.texto.indexOf(q) < 0; });
    selector.querySelectorAll(".grupo-lote").forEach(function (g) { g.hidden = !g.querySelector("li:not([hidden])"); });
    sinResultados.hidden = visibles().length > 0;
  }

  function cerrar(devolverFoco) {
    selector.removeAttribute("open");
    if (devolverFoco) selector.querySelector("summary").focus();
  }

  selector.addEventListener("toggle", function () {
    if (!selector.open) return;
    campo.value = "";
    filtrar();
    campo.focus();
    var actual = selector.querySelector('a[aria-current="true"]');
    if (actual) actual.scrollIntoView({ block: "center" });
  });
  campo.addEventListener("input", filtrar);

  selector.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") { cerrar(true); return; }
    if (ev.key !== "ArrowDown" && ev.key !== "ArrowUp") return;
    var lista = visibles();
    if (!lista.length) return;
    var i = lista.indexOf(document.activeElement);
    var siguiente = ev.key === "ArrowDown" ? (i < 0 ? 0 : Math.min(i + 1, lista.length - 1))
                                           : (i <= 0 ? -1 : i - 1);
    ev.preventDefault();
    if (siguiente < 0) campo.focus(); else lista[siguiente].focus();
  });

  document.addEventListener("click", function (ev) {
    if (selector.open && !selector.contains(ev.target)) cerrar(false);
  });
})();
