"""
Cuántos procesos usar según el equipo donde se ejecuta.

EEG-Platform se usará en equipos distintos (el del autor, el portátil de la
defensa, los de Ciencias del Deporte), así que el valor por defecto no se fija
a mano: se calcula al arrancar el procesador a partir de los núcleos y de la
memoria libre de ese equipo. `EEG_PLATFORM_PROCESOS` o `--procesos` lo anulan.
"""

import ctypes
import os

# Más de 4 procesos apenas acelera (medido: 4 → 14,5 s, 6 → 12,7 s con 12 EDF).
MAXIMO_POR_DEFECTO = 4

# Memoria reservada por proceso. Pico medido de un análisis: ~0,35–0,4 GB
# (EDF de 380 s); se reserva más para EDF de 71 canales y para el propio
# procesador y la web.
MEMORIA_POR_PROCESO = 1024**3


def memoria_libre_bytes():
    """Memoria física disponible en Windows, o None si no se puede saber."""
    try:
        class Estado(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        estado = Estado()
        estado.dwLength = ctypes.sizeof(Estado)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado)):
            return None
        return int(estado.ullAvailPhys)
    except Exception:
        return None


_DETECTAR = object()


def procesos_automaticos(hilos=None, libre=_DETECTAR):
    """
    Procesos en paralelo recomendados para este equipo y el motivo.

    Devuelve `(n, explicacion)`. Se queda con la mitad de los hilos (para no
    ahogar la web ni el sistema), con un máximo de `MAXIMO_POR_DEFECTO`, y sin
    pasar de un proceso por cada `MEMORIA_POR_PROCESO` de memoria libre. Como
    mínimo, 1. `libre=None` significa «memoria desconocida»: solo cuentan los hilos.
    """
    hilos = hilos if hilos is not None else (os.cpu_count() or 2)
    if libre is _DETECTAR:
        libre = memoria_libre_bytes()

    por_cpu = max(1, min(MAXIMO_POR_DEFECTO, hilos // 2))
    n = por_cpu
    texto = f"{hilos} hilos"
    if libre is not None:
        por_memoria = max(1, libre // MEMORIA_POR_PROCESO)
        texto += f", {libre / 1024**3:.1f} GB libres"
        n = min(n, int(por_memoria))
    return n, texto
