// Gráfica de barras de la potencia relativa por banda (Chart.js, servido desde static/).
(function () {
  var lienzo = document.getElementById("grafica-bandas");
  var datos = document.getElementById("datos-grafica");
  if (!lienzo || !datos || typeof Chart === "undefined") return;

  var grafica = JSON.parse(datos.textContent);

  function dibujar() {
    // Texto y rejilla salen de los tokens del tema, para que sigan al claro/oscuro.
    var estilo = getComputedStyle(document.documentElement);
    Chart.defaults.color = estilo.getPropertyValue("--texto-suave").trim();
    Chart.defaults.borderColor = estilo.getPropertyValue("--borde").trim();
    Chart.defaults.font.family = estilo.getPropertyValue("--fuente").trim();
    var anterior = Chart.getChart(lienzo);
    if (anterior) anterior.destroy();

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
          y: { beginAtZero: true, title: { display: true, text: "% de la potencia total" } }
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
  }

  dibujar();
  document.addEventListener("tema:cambio", dibujar);
})();
