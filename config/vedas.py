# -*- coding: utf-8 -*-
"""
Base de datos de vedas de flora arbórea en Colombia.
Fuentes:
  - Nacional: Res. 0316/1974 INDERENA, Ley 61/1985, Res. 1602/1995 + 020/1996 MADS
  - CORPOCESAR: Res. 0035 del 28 de enero de 2026 (veda temporal)
  - CDMB, CORANTIOQUIA, CORPOURABA, CORTOLIMA, CARDER, CVC, CORPOCALDAS, CRA:
    inventario MADS/Dirección General Ecosistemas
"""

import unicodedata


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
# VEDAS NACIONALES — aplican en toda la jurisdicción colombiana
# Clave: fragmentos del nombre científico en minúsculas sin tildes
# ─────────────────────────────────────────────────────────────────────────────
VEDAS_NACIONALES = [
    {
        "nombre_comun": "Pino colombiano",
        "sci_fragmentos": ["podocarpus rospigliosii", "podocarpus montanus",
                           "podocarpus oleifolius", "retrophyllum rospigliosii",
                           "decussocarpus"],
        "norma": "Res. 0316/1974 INDERENA",
        "nota": "Veda indefinida todo el territorio nacional"
    },
    {
        "nombre_comun": "Nogal / Cedro negro",
        "sci_fragmentos": ["juglans"],
        "norma": "Res. 0316/1974 INDERENA",
        "nota": "Veda indefinida todo el territorio nacional"
    },
    {
        "nombre_comun": "Hojarasco",
        "sci_fragmentos": ["talauma caricifragans", "talauma caracifragans"],
        "norma": "Res. 0316/1974 INDERENA",
        "nota": "Veda indefinida todo el territorio nacional"
    },
    {
        "nombre_comun": "Molinillo",
        "sci_fragmentos": ["talauma hernandezi"],
        "norma": "Res. 0316/1974 INDERENA",
        "nota": "Veda indefinida todo el territorio nacional"
    },
    {
        "nombre_comun": "Caparrapí",
        "sci_fragmentos": ["ocotea caparrapi"],
        "norma": "Res. 0316/1974 INDERENA",
        "nota": "Veda indefinida todo el territorio nacional"
    },
    {
        "nombre_comun": "Roble andino",
        "sci_fragmentos": ["quercus humboldtii"],
        "norma": "Res. 0316/1974 INDERENA",
        "nota": "Veda indefinida. Exceptuado en Cauca, Nariño y Antioquia "
                "(sin carbón/leña/pulpa)"
    },
    {
        "nombre_comun": "Palma de cera",
        "sci_fragmentos": ["ceroxylon quindiuense", "ceroxylon alpinum",
                           "ceroxylon vogelianum"],
        "norma": "Ley 61/1985",
        "nota": "Árbol nacional — veda total e indefinida en todo el país"
    },
    {
        "nombre_comun": "Mangles",
        "sci_fragmentos": ["rhizophora", "laguncularia", "avicennia",
                           "pelliciera", "mora megistosperma", "mora oleifera",
                           "conocarpus"],
        "norma": "Res. 1602/1995 + Res. 020/1996 MADS",
        "nota": "Prohíbe aprovechamiento forestal único e impactos directos/indirectos"
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# VEDAS REGIONALES — indexadas por código de CAR
# ─────────────────────────────────────────────────────────────────────────────
VEDAS_REGIONALES = {
    "CORPOCESAR": {
        "norma": "Res. 0035 del 28 de enero de 2026 CORPOCESAR",
        "tipo": "temporal",
        "nota": ("Veda temporal. La intervención requiere concepto técnico "
                 "favorable del GIT Forestal de CORPOCESAR + justificación "
                 "de interés público o riesgo (Art. 4° Res. 0035/2026)"),
        "spp": [
            {
                "nombre_comun": "Algarrobillo / Campano",
                "sci_fragmentos": ["samanea saman", "albizia saman",
                                   "pithecellobium saman"],
            },
            {
                "nombre_comun": "Caracolí",
                "sci_fragmentos": ["anacardium excelsum"],
            },
            {
                "nombre_comun": "Roble caribeño",
                "sci_fragmentos": ["tabebuia rosea", "handroanthus roseus"],
            },
            {
                "nombre_comun": "Orejero",
                "sci_fragmentos": ["enterolobium cyclocarpum"],
            },
        ]
    },
    "CDMB": {
        "norma": "Res. 1986/1984 CDMB",
        "tipo": "indefinida",
        "nota": "Prohíbe aprovechamiento de flora silvestre y maderables en su jurisdicción",
        "spp": [
            {"nombre_comun": "Canelo de páramo", "sci_fragmentos": ["drimys granatensis"]},
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Laurel comino / Jigua", "sci_fragmentos": ["nectandra"]},
            {"nombre_comun": "Laurel comino", "sci_fragmentos": ["aniba"]},
            {"nombre_comun": "Yaya / Cargadero", "sci_fragmentos": ["guatteria"]},
            {"nombre_comun": "Caoba", "sci_fragmentos": ["swietenia macrophylla"]},
            {"nombre_comun": "Cedro", "sci_fragmentos": ["cedrela"]},
            {"nombre_comun": "Guayacán", "sci_fragmentos": ["tabebuia", "handroanthus"]},
            {"nombre_comun": "Abarco", "sci_fragmentos": ["cariniana pyriformis"]},
            {"nombre_comun": "Canime", "sci_fragmentos": ["copaifera canime"]},
            {"nombre_comun": "Palma de cera", "sci_fragmentos": ["ceroxylon"]},
        ]
    },
    "CORANTIOQUIA": {
        "norma": "Res. 3183/2000 CORANTIOQUIA",
        "tipo": "indefinida",
        "nota": "Veda y restricción al aprovechamiento en toda la jurisdicción",
        "spp": [
            {"nombre_comun": "Comino crespo", "sci_fragmentos": ["aniba perutilis"]},
            {"nombre_comun": "Cedro negro", "sci_fragmentos": ["juglans neotropica"]},
            {"nombre_comun": "Cedro de altura", "sci_fragmentos": ["cedrela montana"]},
            {"nombre_comun": "Abarco", "sci_fragmentos": ["cariniana pyriformis"]},
            {"nombre_comun": "Algarrobo", "sci_fragmentos": ["hymenaea courbaril"]},
            {"nombre_comun": "Guayacán amarillo", "sci_fragmentos": ["tabebuia chrysanta", "handroanthus chrysanthus"]},
            {"nombre_comun": "Chaquiro", "sci_fragmentos": ["podocarpus oleifolius"]},
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Cativo", "sci_fragmentos": ["prioria copaifera"]},
            {"nombre_comun": "Diomato", "sci_fragmentos": ["astronium graveolens"]},
        ]
    },
    "CORPOURABA": {
        "norma": "Res. 076395/1995 + Res. 126198/1998 CORPOURABA",
        "tipo": "indefinida",
        "nota": "Prohíbe aprovechamiento bajo cualquier modalidad",
        "spp": [
            {"nombre_comun": "Comino crespo", "sci_fragmentos": ["aniba perutilis"]},
            {"nombre_comun": "Abarco", "sci_fragmentos": ["cariniana pyriformis"]},
            {"nombre_comun": "Caoba", "sci_fragmentos": ["swietenia macrophylla"]},
            {"nombre_comun": "Nogal / Cedro negro", "sci_fragmentos": ["juglans neotropica"]},
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Cativo", "sci_fragmentos": ["prioria copaifera"]},
            {"nombre_comun": "Choibá", "sci_fragmentos": ["dipterix panamensis"]},
            {"nombre_comun": "Ebano", "sci_fragmentos": ["caesalpinia ebano"]},
            {"nombre_comun": "Guayacán hobo", "sci_fragmentos": ["centrolobium paraense"]},
            {"nombre_comun": "Güino", "sci_fragmentos": ["carapa guianensis"]},
        ]
    },
    "CORTOLIMA": {
        "norma": "Acuerdo 10/1983 + Acuerdo 003/1994 CORTOLIMA",
        "tipo": "indefinida",
        "nota": "Veda permanente y total en su jurisdicción",
        "spp": [
            {"nombre_comun": "Cedro", "sci_fragmentos": ["cedrela"]},
            {"nombre_comun": "Pino romerón / hayuelo", "sci_fragmentos": ["podocarpus rospigliosii"]},
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
        ]
    },
    "CARDER": {
        "norma": "Res. 177/1997 CARDER",
        "tipo": "indefinida",
        "nota": "No pueden ser aprovechadas salvo investigación o plantaciones registradas",
        "spp": [
            {"nombre_comun": "Cedro negro", "sci_fragmentos": ["juglans neotropica"]},
            {"nombre_comun": "Comino", "sci_fragmentos": ["aniba perutilis"]},
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Chanul", "sci_fragmentos": ["humiriastrum procerum"]},
            {"nombre_comun": "Dinde", "sci_fragmentos": ["chlorophora tinctoria", "maclura tinctoria"]},
            {"nombre_comun": "Caoba", "sci_fragmentos": ["swietenia macrophylla"]},
            {"nombre_comun": "Algarrobo", "sci_fragmentos": ["hymenaea courbaril"]},
            {"nombre_comun": "Cerezo", "sci_fragmentos": ["prunus serotina"]},
        ]
    },
    "CVC": {
        "norma": "Acuerdo 17/1973 CVC",
        "tipo": "indefinida",
        "nota": "Veda al aprovechamiento forestal en todo el Valle del Cauca",
        "spp": [
            {"nombre_comun": "Caracolí", "sci_fragmentos": ["anacardium excelsum"]},
            {"nombre_comun": "Ceiba", "sci_fragmentos": ["ceiba pentandra"]},
            {"nombre_comun": "Samán", "sci_fragmentos": ["samanea saman", "albizia saman"]},
        ]
    },
    "CRC": {
        "norma": "Acuerdo 17/1973 CRC",
        "tipo": "indefinida",
        "nota": "Veda al aprovechamiento de las especies en Cauca",
        "spp": [
            {"nombre_comun": "Samán", "sci_fragmentos": ["albizia saman", "samanea saman"]},
            {"nombre_comun": "Caracolí", "sci_fragmentos": ["anacardium excelsum"]},
            {"nombre_comun": "Ceiba", "sci_fragmentos": ["ceiba pentandra"]},
        ]
    },
    "CORPOCALDAS": {
        "norma": "Res. 810/1996 CORPOCALDAS",
        "tipo": "indefinida",
        "nota": "Veda indefinida en todo el territorio de Caldas",
        "spp": [
            {"nombre_comun": "Nogal / Cedro negro", "sci_fragmentos": ["juglans"]},
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Caparrapí", "sci_fragmentos": ["ocotea caparrapi"]},
        ]
    },
    "CRA": {
        "norma": "Res. 0025/1996 CRA",
        "tipo": "indefinida",
        "nota": "Prohíbe comercialización de productos de mangles en Atlántico",
        "spp": [
            {"nombre_comun": "Mangle amarillo", "sci_fragmentos": ["laguncularia racemosa"]},
            {"nombre_comun": "Mangle colorado", "sci_fragmentos": ["rhizophora mangle"]},
            {"nombre_comun": "Mangle salado", "sci_fragmentos": ["avicennia nitida"]},
        ]
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN DE CONSULTA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
def consultar_veda(nombre_cientifico: str, nombre_comun: str = "",
                   car: str = "") -> dict:
    """
    Determina si una especie está en veda nacional, regional, o ninguna.

    Args:
        nombre_cientifico: nombre científico de la especie
        nombre_comun: nombre común (opcional, se usa como apoyo de búsqueda)
        car: código de la CAR competente (ej: 'CORPOCESAR', 'CDMB')

    Returns:
        dict con:
            en_veda_nacional (bool)
            en_veda_regional (bool)
            veda_nacional_info (dict | None): norma, nota
            veda_regional_info (dict | None): norma, nota, tipo
            nivel (str): 'nacional', 'regional', 'nacional+regional', 'sin_veda'
            alerta (str): texto para mostrar al usuario
    """
    sci_norm = _normalizar(nombre_cientifico)
    com_norm = _normalizar(nombre_comun)
    texto = sci_norm + " " + com_norm

    # ── Veda nacional ────────────────────────────────────────────────────────
    en_nac = False
    info_nac = None
    for v in VEDAS_NACIONALES:
        if any(_normalizar(f) in texto or texto in _normalizar(f)
               or any(_normalizar(f) in _normalizar(k)
                      for k in [nombre_cientifico, nombre_comun])
               for f in v["sci_fragmentos"]):
            # Matching más preciso: al menos un fragmento está en el texto
            match = False
            for frag in v["sci_fragmentos"]:
                frag_n = _normalizar(frag)
                if frag_n in texto:
                    match = True
                    break
            if match:
                en_nac = True
                info_nac = {"norma": v["norma"], "nota": v["nota"],
                             "nombre_comun": v["nombre_comun"]}
                break

    # ── Veda regional ────────────────────────────────────────────────────────
    en_reg = False
    info_reg = None
    car_norm = car.upper().strip() if car else ""
    if car_norm and car_norm in VEDAS_REGIONALES:
        reg = VEDAS_REGIONALES[car_norm]
        for sp in reg["spp"]:
            match = False
            for frag in sp["sci_fragmentos"]:
                frag_n = _normalizar(frag)
                if frag_n in texto:
                    match = True
                    break
            if match:
                en_reg = True
                info_reg = {
                    "norma": reg["norma"],
                    "nota": reg["nota"],
                    "tipo": reg["tipo"],
                    "nombre_comun": sp["nombre_comun"]
                }
                break

    # ── Nivel y alerta ───────────────────────────────────────────────────────
    if en_nac and en_reg:
        nivel = "nacional+regional"
        alerta = (
            f"⚠️ VEDA NACIONAL ({info_nac['norma']}) + "
            f"VEDA REGIONAL ({info_reg['norma']}). "
            f"{info_reg['nota']}"
        )
    elif en_nac:
        nivel = "nacional"
        alerta = (
            f"⚠️ VEDA NACIONAL ({info_nac['norma']}). "
            f"{info_nac['nota']}"
        )
    elif en_reg:
        nivel = "regional"
        alerta = (
            f"⚠️ VEDA REGIONAL ({info_reg['norma']}). "
            f"{info_reg['nota']}"
        )
    else:
        nivel = "sin_veda"
        alerta = ""

    return {
        "en_veda_nacional": en_nac,
        "en_veda_regional": en_reg,
        "veda_nacional_info": info_nac,
        "veda_regional_info": info_reg,
        "nivel": nivel,
        "alerta": alerta,
    }


def resumen_vedas_inventario(df_especies, car: str = "") -> dict:
    """
    Dado un DataFrame con columnas 'nombre_cientifico' y 'nombre_comun',
    devuelve un resumen de cuántas especies/individuos están en veda.

    Args:
        df_especies: DataFrame con al menos ['nombre_cientifico', 'n_individuos']
                     y opcionalmente ['nombre_comun']
        car: código CAR del proyecto

    Returns:
        dict con listas de especies en cada categoría y conteos
    """
    resultado = {
        "sin_veda": [],
        "veda_nacional": [],
        "veda_regional": [],
        "veda_nacional_y_regional": [],
        "n_ind_sin_veda": 0,
        "n_ind_veda_nacional": 0,
        "n_ind_veda_regional": 0,
        "n_ind_veda_ambas": 0,
        "hay_alerta": False,
    }

    for _, row in df_especies.iterrows():
        sci = str(row.get("nombre_cientifico", ""))
        nom = str(row.get("nombre_comun", ""))
        n = int(row.get("n_individuos", 1))
        info = consultar_veda(sci, nom, car)
        entrada = {
            "nombre_cientifico": sci,
            "nombre_comun": nom,
            "n_individuos": n,
            "nivel": info["nivel"],
            "alerta": info["alerta"],
        }
        if info["nivel"] == "nacional+regional":
            resultado["veda_nacional_y_regional"].append(entrada)
            resultado["n_ind_veda_ambas"] += n
            resultado["hay_alerta"] = True
        elif info["nivel"] == "nacional":
            resultado["veda_nacional"].append(entrada)
            resultado["n_ind_veda_nacional"] += n
            resultado["hay_alerta"] = True
        elif info["nivel"] == "regional":
            resultado["veda_regional"].append(entrada)
            resultado["n_ind_veda_regional"] += n
            resultado["hay_alerta"] = True
        else:
            resultado["sin_veda"].append(entrada)
            resultado["n_ind_sin_veda"] += n

    return resultado
