---
target: la portada
total_score: 23
max_score: 32
na_heuristics: 7,10
p0_count: 0
p1_count: 2
target_identity: "file:C:\\Users\\migue\\Desktop\\TFG\\EEG-Platform\\templates\\inicio.html"
target_fingerprint: "sha256:f28065f37f230979ed37ca4f2e7c2666d499425690a94cadd932e1ca09b365d8"
target_path: "C:\\Users\\migue\\Desktop\\TFG\\EEG-Platform\\templates\\inicio.html"
timestamp: 2026-10-18T13-32-52Z
slug: templates-inicio-html
closed: true
---
# Crítica de la portada (EEG-Platform)

Method: dual-agent (A: revisión de diseño · B: detector y navegador)

## Design Health Score

| # | Heurístico | Nota | Problema clave |
|---|---|---|---|
| 1 | Visibilidad del estado | 3 | No muestra estado alguno (cola, últimas grabaciones). Aceptable en portada. |
| 2 | Coincidencia con el mundo real | 3 | Lenguaje claro; «potencia por banda» puede ser jerga para quien no sea de EEG. |
| 3 | Control y libertad | 3 | Un solo CTA, sin trampas. |
| 4 | Consistencia y estándares | 3 | CTA en pastilla (999 px) frente al radio de 8 px del resto de botones. |
| 5 | Prevención de errores | 3 | Sin formularios; respaldo WebP si falla WebGL. |
| 6 | Reconocer antes que recordar | 3 | Nav visible y un CTA. «Grabaciones» aparece dos veces (nav + botón). |
| 7 | Flexibilidad y eficiencia | n/a | Superficie de tipo Persuade. |
| 8 | Estética y minimalismo | 2 | Escena + neuronas + pulsos en movimiento compiten; el texto necesitaba text-shadow para leerse. |
| 9 | Recuperación de errores | 3 | Respaldo sin 3D correcto; la descripción accesible solo existe en el respaldo. |
| 10 | Ayuda y documentación | n/a | No aplica; no hay enlace a la guía ni a los límites del producto. |
| **Total** | | **23/32 (72 %, Bueno)** | |

## Especificidad de diseño
Parcialmente propio. Cabeza de rejilla con cerebro ámbar y neuronas es el lenguaje habitual de las webs de neurotecnología; lo que la ancla a este producto son los 14 sensores en su posición real, la etiqueta mono «EMOTIV EPOC X» y la promesa «Todo en tu equipo». El fondo de neuronas es decoración pura y el tuteo «Tu EEG» suena a SaaS.
Detector determinista: 0 hallazgos, pero no resolvió `{% static %}` y no vio el CSS ni el JS: solo cubre el marcado. Lighthouse 100/100/100.

## Qué funciona
1. Jerarquía clara: etiqueta mono, título grande, frase de 40 ch y un único botón; foco ámbar de 3 px muy visible.
2. Los dos temas sostienen la escena, con respaldo WebP en ambos.
3. Contrastes normales superan AA con holgura (título 16:1, frase 8,6:1/6,7:1, botón 8,8:1/5,9:1); sin desbordes; Lighthouse 100.

## Problemas prioritarios
- **[P1] Legibilidad bajo las neuronas.** El muestreo del canvas encontró píxeles de luminancia 255 bajo el h1 y contraste local de ~1,7–2:1 bajo la etiqueta en el peor caso. El hueco del texto no queda del todo limpio y el text-shadow es una muleta. Arreglo: borrado completo del núcleo del texto y quitar el text-shadow. Comando: polish.
- **[P1] Composición desequilibrada.** La cabeza mira hacia el margen derecho y deja un vacío entre texto y cabeza. Consecuencia de decisiones previas (perfil + fondo a la izquierda). Arreglo: girar el tres cuartos para que mire al texto o centrar la escena. Comando: layout.
- **[P2] Peso con movimiento reducido.** three.module.min.js (≈671 kB) se descarga aunque se use el respaldo, y las dos WebP se descargan siempre. Total ≈1,87 MB, 91 % en 3D. Arreglo: import dinámico de Three.js y carga diferida de las imágenes. Comando: optimize.
- **[P2] El mensaje de privacidad está enterrado.** «Todo en tu equipo» es el argumento diferencial y está al final de la frase en gris suave. Comando: clarify / typeset.
- **[P3] Móvil y detalles.** Escena de 56 vh alarga el scroll y corta la cabeza; «de» huérfano al final de la primera línea del título; CTA en pastilla frente al resto de botones. Comandos: adapt, typeset.
- **Nota de honestidad (decisión ya tomada por el usuario).** El mapa ámbar sobre el cerebro puede leerse como un resultado sin leyenda; el pie «Ilustración: los pulsos no son datos reales» se quitó a petición del usuario y no se repone.

## Personas
- **Jordan (primer uso):** entiende el único botón; no sabe si hay datos ni qué formato subir.
- **Sam (accesibilidad):** contraste y foco bien; falta Tab real y forced-colors; el respaldo explica la escena, el modo 3D no.
- **Casey (móvil):** CTA en primera pantalla; la escena queda abajo, cabeza cortada, cabecera de dos filas.
- **Investigador de Ciencias del Deporte:** lenguaje cercano; no sabe qué archivos subir (EDF) hasta entrar.
- **Tribunal en proyector:** a 1280×720 todo cabe sin scroll; el fondo oscuro-sobre-oscuro de neuronas se pierde con luz ambiente; el tema claro es el más legible desde lejos.

## Observaciones menores
- El área táctil del botón mide 41 px de alto en escritorio y la marca 34 (el umbral de 44 es de móvil).
- A 1280×720 la parte baja del lienzo de neuronas se corta de forma abrupta.
- La escena está acoplada a vh; con ventanas muy cortas puede recortar el título.

## Preguntas
1. Si quitaras la escena y dejaras etiqueta, título y botón, ¿qué perdería el producto?
2. ¿El ámbar del cerebro significa algo o es solo color? Es el mismo ámbar del aviso y del foco.
3. ¿Quién es «tú» en «Tu EEG»? Los EEG son de participantes, a menudo menores.
4. ¿La primera pantalla debería mostrar algo del estado real?
