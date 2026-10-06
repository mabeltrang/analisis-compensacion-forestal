# -*- coding: utf-8 -*-
"""
Especies que NO deben recomendarse para restauración en Colombia.

Se usan como filtro de seguridad en _cargar_especies_por_zona_vida() (app.py):
cualquier fila de config/especies_por_zona_vida.csv que coincida se descarta
antes de mostrarse o exportarse, aunque alguien la agregue por error al csv.

Dos grupos:
  - NO_PRESENTES_EN_COLOMBIA: nativas de otros países que no se distribuyen
    en Colombia (ni siquiera como introducidas).
  - INTRODUCIDAS_EN_COLOMBIA: exóticas cultivadas o naturalizadas en Colombia
    (no son nativas; varias son invasoras).
Fuente de verificación: POWO (Kew) y Catálogo de Plantas y Líquenes de
Colombia (Bernal et al. 2015/2016).

Los géneros en GENEROS_EXOTICOS se excluyen completos (ningún representante
nativo en Colombia).
"""

NO_PRESENTES_EN_COLOMBIA = {
    "kageneckia lanceolata",
}

INTRODUCIDAS_EN_COLOMBIA = {
    "schinus molle",
    "prunus serotina",            # incluye subsp. capuli
    "prunus capuli",
    "prunus salicifolia",
    "leucaena leucocephala",
    "fraxinus uhdei",
    "acacia melanoxylon",
    "acacia mangium",
    "acacia decurrens",
    "acacia auriculiformis",
    "spathodea campanulata",
    "terminalia catappa",
    "melia azedarach",
    "mangifera indica",
    "syzygium jambos",
}

GENEROS_EXOTICOS = {
    "eucalyptus", "pinus", "cupressus", "casuarina", "grevillea", "tectona",
    "gmelina", "azadirachta", "ulex", "ligustrum", "pittosporum",
}


def _norm(s):
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or ""))
                if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().split())


def es_no_apta_colombia(nombre_cientifico):
    """True si la especie no es nativa de Colombia o no se distribuye en el país."""
    n = _norm(nombre_cientifico)
    if not n:
        return False
    genero = n.split()[0]
    if genero in GENEROS_EXOTICOS:
        return True
    return any(n == sp or n.startswith(sp + " ")
               for sp in NO_PRESENTES_EN_COLOMBIA | INTRODUCIDAS_EN_COLOMBIA)
