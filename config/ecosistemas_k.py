# -*- coding: utf-8 -*-
"""
config/ecosistemas_k.py

Constante k de la curva de Chapman-Richards [1 - e^(-k·n)] para la
RECUPERACIÓN DE COBERTURA VEGETAL (no biomasa) por tipo de ecosistema.

Categoría de referencia: "estructura" en Poorter et al. (2021, Science
374:1370-1376) — incluye cobertura de dosel, área basal, densidad de
tallos. Esta categoría recupera al 90% del valor de bosque maduro en
2.5 a 6 décadas, según el sitio — mucho más rápido que biomasa (>12
décadas) y más lento que suelo/funcionamiento de planta (<2.5 décadas).
DOI: 10.1126/science.abh3629

IMPORTANTE — nivel de confianza por ecosistema:
  alta   = existe cronosecuencia real (colombiana o muy cercana) que
           respalda directamente el valor.
  media  = interpolado del gradiente húmedo/seco de Poorter 2016/2021,
           razonable pero no ajustado a datos locales.
  baja   = extrapolación sin cronosecuencia de cobertura publicada
           específica para esa zona — usar con precaución y documentar
           como estimación propia si se reporta ante una CAR.

k se calcula como k = -ln(0.1) / t90, donde t90 es el tiempo (años)
para recuperar el 90% de la cobertura de referencia.
"""

ECOSISTEMAS_K = {
    "bs-T": {
        "nombre": "Bosque seco tropical",
        "k": 0.040,
        "t90_anios": 58,
        "confianza": "alta",
        "fuente": (
            "Poorter et al. (2016, Nature 530:211-214) — resiliencia de "
            "biomasa/estructura naturalmente más baja en zonas estacionalmente "
            "secas; Rozendaal et al. (2019, Sci. Adv. 5:eaau3114) — clima más "
            "duro implica recuperación más lenta; Avella, García, "
            "Fajardo-Gutiérrez & González-Melo (2019, Caldasia 41:12-27) — "
            "cronosecuencia real de bs-T interandino colombiano; "
            "González-M. et al. (2018, IAvH) — patrones de bs-T en Colombia."
        ),
    },
    "bh-T": {
        "nombre": "Bosque húmedo tropical",
        "k": 0.060,
        "t90_anios": 38,
        "confianza": "media",
        "fuente": (
            "Interpolado del gradiente de Poorter (2016/2021): la recuperación "
            "aumenta con la disponibilidad de agua. Sin cronosecuencia "
            "colombiana específica ajustada — valor estimado por posición en "
            "el gradiente húmedo/seco."
        ),
    },
    "bmh-T": {
        "nombre": "Bosque muy húmedo tropical",
        "k": 0.080,
        "t90_anios": 29,
        "confianza": "media",
        "fuente": (
            "Extremo húmedo del gradiente de Poorter (2016/2021) — mayor "
            "resiliencia estructural documentada con alta disponibilidad "
            "hídrica. Sin ajuste local colombiano."
        ),
    },
    "bh-PM": {
        "nombre": "Bosque húmedo premontano",
        "k": 0.050,
        "t90_anios": 46,
        "confianza": "baja",
        "fuente": (
            "Sin cronosecuencia de cobertura publicada específica para "
            "bh-PM en Colombia. Estimado entre bs-T y bh-T asumiendo que la "
            "menor temperatura (mayor altitud) modera parcialmente el efecto "
            "de mayor humedad sobre la velocidad de crecimiento. "
            "Revisar y reemplazar si se encuentra literatura directa."
        ),
    },
    "bmh-PM": {
        "nombre": "Bosque muy húmedo premontano",
        "k": 0.045,
        "t90_anios": 51,
        "confianza": "baja",
        "fuente": (
            "Mismo caso que bh-PM: sin dato local directo. Estimado "
            "ligeramente más lento por menor temperatura media."
        ),
    },
}

DEFAULT_ECOSISTEMA = "bs-T"


def k_por_ecosistema(codigo: str) -> float:
    """Devuelve el k de Chapman-Richards para el código de ecosistema dado.

    Si el código no está en el diccionario, cae de vuelta a bs-T (el más
    conservador y mejor documentado) en vez de fallar.
    """
    return ECOSISTEMAS_K.get(codigo, ECOSISTEMAS_K[DEFAULT_ECOSISTEMA])["k"]
