// Gráfica de barras de la potencia relativa por banda (Chart.js, servido desde static/).
(function () {
  var lienzo = document.getElementById("grafica-bandas");
  var datos = document.getElementById("datos-grafica");
  if (!lienzo || !datos || typeof Chart === "undefined") return;

  var grafica = JSON.parse(datos.textContent);
  new Chart(lienzo, {
    type: "bar",
    data: {
      labels: grafica.bandas,
      datasets: grafica.series.map(function (s) {
        return { label: s.etiqueta, data: s.valores, backgroundColor: s.color,
                 borderColor: s.color, borderWidth: 1 };
      })
    },
    options: {
      locale: "es",
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, title: { display: true, text: "% de la potencia total (1–30 Hz)" } }
      },
      plugins: {
        legend: { position: "bottom" },
        tooltip: {
          callbacks: {
            label: function (c) {
              var v = c.parsed.y;
              return c.dataset.label + ": " +
                (v === null ? "sin dato" : v.toLocaleString("es-ES", { maximumFractionDigits: 1 }) + " %");
            }
          }
        }
      }
    }
  });
})();
