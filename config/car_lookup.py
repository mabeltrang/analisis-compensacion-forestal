# -*- coding: utf-8 -*-
"""
Determina la CAR competente a partir de (municipio, departamento).

Dos fuentes, en este orden de prioridad:

1. municipios_car.csv — municipio a municipio, para los departamentos
   repartidos entre 2+ CAR (Sucre, Boyacá, Cundinamarca, Santander,
   Antioquia, y los municipios de Arauca/Casanare/Vichada/Meta que le
   corresponden a CORPORINOQUIA). Generado cruzando el excel
   "Municipios_por_CAR" contra municipios_colombia.fgb — ver
   scripts/build_municipio_car.py para el detalle de cómo se construyó
   y qué filas quedaron sin match automático.

2. DEPARTAMENTO_CAR_UNICA — para departamentos donde una sola CAR tiene
   jurisdicción sobre TODO el territorio (ej. CORPOCESAR en Cesar), no
   hace falta ir municipio a municipio: basta el departamento.

Si un departamento no aparece en ninguna de las dos fuentes, se devuelve
None y se le pide al usuario seleccionar la CAR manualmente (ver app.py).
"""

import os
import unicodedata
import pandas as pd

_DIR = os.path.dirname(os.path.abspath(__file__))
_CSV_PATH = os.path.join(_DIR, "municipios_car.csv")

_df_cache = None


def _normalizar(s: str) -> str:
    if not s:
        return ""
    s = str(s)
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    return s.lower().strip()


# ─────────────────────────────────────────────────────────────────────────────
# Departamentos donde UNA SOLA CAR cubre todo el territorio.
# No requieren desglose municipio a municipio.
# Fuente: jurisdicciones oficiales publicadas por cada corporación / ASOCARS.
# Si un proyecto cae en Antioquia, Bolívar o Valle del Cauca, OJO: esos
# departamentos SÍ están repartidos entre varias autoridades
# (Antioquia: CORANTIOQUIA/CORNARE/CORPOURABA/AMVA:
#  Bolívar: CARDIQUE/CSB; Valle del Cauca: CVC/DAGMA-Cali) y no deben
# agregarse aquí sin la tabla municipio a municipio correspondiente.
# ─────────────────────────────────────────────────────────────────────────────
DEPARTAMENTO_CAR_UNICA = {
    "cesar":                     "CORPOCESAR",
    "la guajira":                 "CORPOGUAJIRA",
    "atlantico":                  "CRA",
    "magdalena":                  "CORPAMAG",
    "cordoba":                    "CVS",
    "norte de santander":         "CORPONOR",
    "tolima":                     "CORTOLIMA",
    "cauca":                      "CRC",
    "narino":                     "CORPONARINO",
    "quindio":                    "CRQ",
    "risaralda":                  "CARDER",
    "caldas":                     "CORPOCALDAS",
    "meta":                       "CORMACARENA",
    "choco":                      "CODECHOCO",
    "san andres y providencia":   "CORALINA",
    "guainia":                    "CDA",
    "guaviare":                   "CDA",
    "vaupes":                     "CDA",
    "putumayo":                   "CORPOAMAZONIA",
    "caqueta":                    "CORPOAMAZONIA",
    "amazonas":                   "CORPOAMAZONIA",
}
# Nota Meta: la mayoría del departamento es CORMACARENA, salvo un puñado de
# municipios fronterizos con Casanare/Arauca que caen bajo CORPORINOQUIA.
# Esos municipios puntuales, si aparecen en municipios_car.csv, tienen
# prioridad sobre esta tabla (ver orden de búsqueda en obtener_car()).


def _cargar_tabla():
    global _df_cache
    if _df_cache is None:
        df = pd.read_csv(_CSV_PATH, encoding="utf-8")
        df["dep_norm"] = df["departamento"].apply(_normalizar)
        df["mun_norm"] = df["municipio"].apply(_normalizar)
        _df_cache = df
    return _df_cache


def obtener_car(municipio: str, departamento: str) -> dict:
    """
    Determina la CAR competente para un municipio/departamento dado.

    Orden de búsqueda (importante):
      1. Departamento de jurisdicción ÚNICA (ej. Cesar → CORPOCESAR):
         se resuelve de una vez, sin tocar la tabla CSV. Esto garantiza
         que un problema de lectura del CSV, una fila faltante, o un
         desajuste de nombre en el excel NUNCA rompa el caso simple
         (una sola CAR por departamento).
      2. Solo si el departamento NO es de jurisdicción única, se busca
         en la tabla municipio a municipio (departamentos repartidos
         entre 2+ CAR).

    Returns:
        dict con:
            car (str | None): código de la CAR (ej. 'CORPOCESAR') o None
                               si no se pudo determinar.
            fuente (str): 'departamento_unico', 'municipio_car_csv', o
                          'no_encontrado'.
            mensaje (str): texto explicativo para mostrar al usuario.
    """
    dep_norm = _normalizar(departamento)
    mun_norm = _normalizar(municipio)

    # 1) Departamento de jurisdicción única — PRIMERO, sin depender del CSV.
    if dep_norm in DEPARTAMENTO_CAR_UNICA:
        car = DEPARTAMENTO_CAR_UNICA[dep_norm]
        return {
            "car": car,
            "fuente": "departamento_unico",
            "mensaje": f"{departamento} → {car} "
                       f"(jurisdicción sobre todo el departamento).",
        }

    # 2) Tabla municipio a municipio (departamentos con reparto entre CAR)
    try:
        df = _cargar_tabla()
        match = df[(df["dep_norm"] == dep_norm) & (df["mun_norm"] == mun_norm)]
    except Exception as e:
        return {
            "car": None,
            "fuente": "error_csv",
            "mensaje": f"⚠️ No se pudo leer municipios_car.csv ({e}). "
                       f"Selecciona la CAR manualmente.",
        }

    if len(match) == 1:
        car = match.iloc[0]["car"]
        return {
            "car": car,
            "fuente": "municipio_car_csv",
            "mensaje": f"{municipio} ({departamento}) → {car} "
                       f"(tabla municipio a municipio).",
        }
    if len(match) > 1:
        # No debería pasar; se deja como salvavidas.
        return {
            "car": None,
            "fuente": "ambiguo",
            "mensaje": f"⚠️ Más de una CAR posible para {municipio} "
                       f"({departamento}). Selecciona manualmente.",
        }

    # 3) No encontrado — requiere selección manual
    return {
        "car": None,
        "fuente": "no_encontrado",
        "mensaje": (
            f"No se encontró CAR automática para {municipio} "
            f"({departamento}). Este departamento puede estar repartido "
            f"entre varias autoridades (ej. Antioquia, Bolívar, Valle del "
            f"Cauca) sin tabla municipio a municipio cargada aún, o el "
            f"municipio no coincide exactamente con el listado oficial. "
            f"Selecciona la CAR manualmente."
        ),
    }
