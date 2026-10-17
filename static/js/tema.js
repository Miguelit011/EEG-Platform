// Botón de tema claro/oscuro: guarda la elección en este navegador (localStorage).
(function () {
  var boton = document.getElementById("tema-boton");
  if (!boton) return;
  function actual() {
    var fijado = document.documentElement.dataset.theme;
    if (fijado) return fijado;
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  boton.addEventListener("click", function () {
    var nuevo = actual() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = nuevo;
    try { localStorage.setItem("tema", nuevo); } catch (e) {}
    document.dispatchEvent(new CustomEvent("tema:cambio"));
  });
})();
