// Arrastrar y soltar para la subida de EDF. Sin dependencias.
(function () {
  var zona = document.getElementById("zona-soltar");
  var entrada = document.getElementById("archivos");
  var resumen = document.getElementById("resumen-archivos");
  if (!zona || !entrada) return;

  function actualizarResumen() {
    var n = entrada.files.length;
    resumen.textContent = n === 0 ? "Ningún archivo elegido."
      : n === 1 ? "1 archivo elegido: " + entrada.files[0].name
      : n + " archivos elegidos.";
  }

  entrada.addEventListener("change", actualizarResumen);

  ["dragenter", "dragover"].forEach(function (nombre) {
    zona.addEventListener(nombre, function (e) {
      e.preventDefault();
      zona.classList.add("sobre");
    });
  });
  ["dragleave", "drop"].forEach(function (nombre) {
    zona.addEventListener(nombre, function () { zona.classList.remove("sobre"); });
  });
  zona.addEventListener("drop", function (e) {
    e.preventDefault();
    if (e.dataTransfer && e.dataTransfer.files.length) {
      entrada.files = e.dataTransfer.files;
      actualizarResumen();
    }
  });
})();
