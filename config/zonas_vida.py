# -*- coding: utf-8 -*-
"""
config/zonas_vida.py

Clasificador de Zona de Vida (Holdridge) del área de impacto, para
recomendar especies nativas de compensación/restauración por zona
(ver config/especies_por_zona_vida.csv).

Mismo enfoque que config/ecosistemas_k.py::detectar_ecosistema_por_bioma
(coincidencia de palabras clave sobre el texto BIOMA_IAvH), pero con
más categorías porque aquí el objetivo es otro: elegir qué fila del
catálogo de especies mostrar, no la curva de Chapman-Richards.
Se agrega el piso altitudinal (elevación media del polígono de
impacto, SRTM) porque el texto de BIOMA_IAvH por sí solo no siempre
distingue premontano / montano bajo / subpáramo.

IMPORTANTE: igual que en ecosistemas_k.py, si no hay coincidencia
razonable se devuelve (None, motivo) — NUNCA se asume una zona de
vida por defecto en silencio. La app debe pedir selección manual.
"""
import unicodedata


def _sin_tildes(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# Códigos que existen en config/especies_por_zona_vida.csv, con su
# nombre exacto tal como aparece en la columna "Zona de vida" de ese
# archivo (deben coincidir carácter por carácter para poder filtrar).
ZONAS_VIDA = {
    "md-T":   "Matorral desértico tropical",
    "me-T":   "Monte espinoso tropical",
    "bs-T":   "Bosque seco tropical",
    "bh-T":   "Bosque húmedo tropical",
    "bh-PM":  "Bosque húmedo premontano",
    "bs-MB":  "Bosque seco montano bajo",
    "bh-MB":  "Bosque húmedo montano bajo",
    "bh-Msp": "Bosque húmedo montano (subpáramo)",
}

# Pisos altitudinales aproximados para el trópico andino colombiano
# (IGAC/IDEAM, simplificado). Los límites son graduales en la realidad
# — se usan solo para desempatar entre pisos cuando el texto del bioma
# no distingue "premontano" de "montano bajo" de "subpáramo".
_PISO_POR_ALTITUD = [
    (0,    1000, "T"),     # tropical / tierra caliente
    (1000, 2000, "PM"),    # premontano
    (2000, 3000, "MB"),    # montano bajo
    (3000, 3500, "Msp"),   # subpáramo
]


def _piso_por_altitud(elevacion_m):
    if elevacion_m is None:
        return None
    for lo, hi, piso in _PISO_POR_ALTITUD:
        if lo <= elevacion_m < hi:
            return piso
    return "paramo"  # >3500 m — fuera del catálogo actual


def detectar_zona_vida(bioma_texto, elevacion_m=None):
    """
    Devuelve (codigo, motivo):
      - codigo: una clave de ZONAS_VIDA, o None si no se pudo determinar
                con confianza razonable.
      - motivo: texto corto explicando la inferencia (o por qué no se
                pudo), para mostrar en la UI.

    bioma_texto: ctx['bioma_principal'] (campo BIOMA_IAvH del Mapa de
                 Ecosistemas IDEAM/IAvH).
    elevacion_m: elevación media del polígono de impacto (SRTM), o None.
    """
    if not bioma_texto or bioma_texto == "Desconocido":
        return None, "No hay Bioma-Unidad Biótica detectado para el área de impacto."

    t = _sin_tildes(bioma_texto).lower()
    piso = _piso_por_altitud(elevacion_m)

    es_arido      = any(p in t for p in ("arido", "desertic"))
    es_espinoso   = any(p in t for p in ("espinoso", "subxerofit"))
    es_seco       = any(p in t for p in ("seco", "alternohigric", "xerofit")) and not es_arido and not es_espinoso
    es_muy_humedo = any(p in t for p in ("pluvial", "muy humedo", "higrofit"))
    es_humedo     = "humedo" in t and not es_muy_humedo
    es_alta_mont  = any(p in t for p in ("premontano", "montano", "andino", "orobioma", "paramo"))

    if piso == "paramo":
        return None, (
            f"Elevación media ≈ {elevacion_m:.0f} m corresponde a páramo — "
            f"no cubierto por el catálogo actual (solo hasta subpáramo). "
            f"Selecciona manualmente si aplica."
        )

    # ── Sin distinción de piso altitudinal disponible ──────────────
    if piso is None:
        if es_arido:
            return "md-T", f'Bioma "{bioma_texto}" → árido/desértico (sin elevación, se asume piso tropical).'
        if es_espinoso:
            return "me-T", f'Bioma "{bioma_texto}" → espinoso/subxerofítico (sin elevación, se asume piso tropical).'
        if es_seco and not es_alta_mont:
            return "bs-T", f'Bioma "{bioma_texto}" → seco, sin indicio de piso alto andino.'
        if es_humedo and not es_alta_mont:
            return "bh-T", f'Bioma "{bioma_texto}" → húmedo, sin indicio de piso alto andino.'
        return None, (
            f'Bioma "{bioma_texto}" no tiene elevación asociada y el texto no '
            f"alcanza para decidir el piso altitudinal. Selecciona manualmente."
        )

    # ── Piso tropical (tierra caliente, <1000 m) ───────────────────
    if piso == "T":
        if es_arido:
            return "md-T", f'Elevación ≈{elevacion_m:.0f} m (tropical) + bioma árido → Matorral desértico tropical.'
        if es_espinoso:
            return "me-T", f'Elevación ≈{elevacion_m:.0f} m (tropical) + bioma espinoso → Monte espinoso tropical.'
        if es_seco:
            return "bs-T", f'Elevación ≈{elevacion_m:.0f} m (tropical) + bioma seco → Bosque seco tropical.'
        if es_humedo or es_muy_humedo or not (es_seco or es_arido or es_espinoso):
            return "bh-T", f'Elevación ≈{elevacion_m:.0f} m (tropical) + bioma húmedo → Bosque húmedo tropical.'

    # ── Piso premontano (1000–2000 m) ──────────────────────────────
    if piso == "PM":
        if es_humedo or es_muy_humedo or not es_seco:
            return "bh-PM", f'Elevación ≈{elevacion_m:.0f} m (premontano) → Bosque húmedo premontano.'
        # bs-PM no está en el catálogo actual — cae a bs-MB como aproximación
        # más cercana disponible, con advertencia explícita.
        return None, (
            f"Elevación ≈{elevacion_m:.0f} m (premontano) con bioma seco — "
            f"el catálogo actual no tiene 'Bosque seco premontano'. "
            f"La opción más cercana es 'Bosque seco montano bajo'; confirma manualmente."
        )

    # ── Piso montano bajo (2000–3000 m) ────────────────────────────
    if piso == "MB":
        if es_seco:
            return "bs-MB", f'Elevación ≈{elevacion_m:.0f} m (montano bajo) + bioma seco → Bosque seco montano bajo.'
        return "bh-MB", f'Elevación ≈{elevacion_m:.0f} m (montano bajo) → Bosque húmedo montano bajo.'

    # ── Subpáramo (3000–3500 m) ─────────────────────────────────────
    if piso == "Msp":
        return "bh-Msp", f'Elevación ≈{elevacion_m:.0f} m (subpáramo) → Bosque húmedo montano (subpáramo).'

    return None, f'No se pudo clasificar "{bioma_texto}" (elevación ≈{elevacion_m}). Selecciona manualmente.'
