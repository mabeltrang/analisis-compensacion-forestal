# -*- coding: utf-8 -*-
"""
Base de datos de vedas de flora en Colombia (revisión sep/2026).

NACIONALES (VEDAS_NACIONALES):
  - Res. 0316/1974 INDERENA (pino colombiano, nogal, hojarasco, molinillo,
    caparrapí, roble), modificada por Res. 1408/1975 (levanta roble en Ospina
    Pérez, Cabrera, Pandi y San Bernardo, Cund.), Res. 1132/1975 (levanta
    Podocarpus en El Tablón, Nariño) y Res. 096/2006 MAVDT (roble).
  - Res. 0213/1977 INDERENA (epífitas: musgos, líquenes, lamas, quiches,
    orquídeas, bromelias).
  - Res. 0801/1977 INDERENA (helechos arborescentes Cyatheaceae/Dicksoniaceae).
  - Ley 61/1985 (palma de cera Ceroxylon quindiuense).
  - Res. 1602/1995 + 020/1996 MMA (mangles).
  - Res. 0463/1982 INDERENA: veda en la Costa Pacífica para el producto "vara"
    y árboles con DAP < 15 cm (no es veda por especie; no se modela).
  Fuente de compilación: MADS – Dirección de Ecosistemas, "Vedas en Colombia".

REGIONALES (VEDAS_REGIONALES) con lista de especies verificada en fuente:
  CORANTIOQUIA Res. 040-RES2312-6645/2023 · CORNARE Acuerdo 404/2020 ·
  CORPOGUAJIRA Acuerdo 003/2012 · CORPOAMAZONIA Res. 0110/2015 ·
  CORPOCESAR Res. 0035/2026 · CAS Acuerdo 386-19/2019 · CAR Acuerdo 021/2018 ·
  CDMB Res. 1986/1984 · CARDER Res. 177/1997 · CVC Acuerdo 17/1973 ·
  CORTOLIMA Acuerdo 10/1983 · CORPOURABA Res. 076395/1995 + 126198/1998 ·
  CODECHOCO Res. 2535/1987 (solo Riosucio, Unguía, Acandí) · CRA Res. 0025/1996 ·
  CORPOCALDAS Res. 810/1996 (actualizada oct/2026).
  CRC: registro heredado, pendiente de re-verificar en fuente.

Con acto regional identificado pero lista no verificada: CORPOCHIVOR (Res.
  495/2015), CAM (Acuerdo 009/2018, estatuto forestal), CARSUCRE (Res.
  0617/2015). Se modelan como "solo_nacional" con nota de advertencia.

Sin veda regional por especie identificada (aplican solo nacionales):
  CORPOBOYACÁ, CORPORINOQUIA, CORMACARENA, CORPOGUAVIO, CVS, CARDIQUE, CSB,
  CORPOMOJANA, CORPAMAG, CORPONOR, CRQ, CDA, CORPONARIÑO, CORALINA, AMVA.
  (Varias tienen restricciones por área o por producto no maderable — ver
  la nota de cada una.)
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
        "nota": "Veda indefinida todo el territorio nacional (levantada solo en "
                "El Tablón, Nariño — Res. 1132/1975)"
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
                "(sin carbón/leña/pulpa) y levantada en Ospina Pérez, Cabrera, "
                "Pandi y San Bernardo (Res. 1408/1975); ver Res. 096/2006 MAVDT. "
                "Ojo: en Antioquia sigue vedado regionalmente por CORANTIOQUIA"
    },
    {
        "nombre_comun": "Palma de cera",
        "sci_fragmentos": ["ceroxylon quindiuense", "ceroxylon quindiuensis",
                           "klopstockia quindiuensis", "ceroxylon floccosum"],
        "norma": "Ley 61/1985",
        "nota": "Árbol nacional — prohíbe su tala en todo el país. Otras "
                "Ceroxylon (alpinum, vogelianum, parvifrons, sasaimae) están "
                "vedadas solo regionalmente (CORANTIOQUIA, CORNARE, CAS, CDMB)"
    },
    {
        "nombre_comun": "Mangles",
        "sci_fragmentos": ["rhizophora", "laguncularia", "avicennia",
                           "pelliciera", "mora megistosperma", "mora oleifera",
                           "conocarpus"],
        "norma": "Res. 1602/1995 + Res. 020/1996 MADS",
        "nota": "Prohíbe aprovechamiento forestal único e impactos directos/indirectos"
    },
    {
        "nombre_comun": "Helechos arborescentes / Palma boba",
        "sci_fragmentos": ["cyatheaceae", "dicksoniaceae", "cyathea", "alsophila",
                           "dicksonia", "cnemidaria", "nephelea", "sphaeropteris",
                           "trichipteris", "palma boba", "helecho arborescente",
                           "helecho macho", "palma de helecho"],
        "norma": "Res. 0801/1977 INDERENA",
        "nota": "Veda permanente en todo el territorio nacional: aprovechamiento, "
                "comercialización y movilización. Declarada planta protegida"
    },
    {
        "nombre_comun": "Epífitas (musgos, líquenes, orquídeas, bromelias)",
        "sci_fragmentos": ["orchidaceae", "bromeliaceae", "tillandsia", "guzmania",
                           "vriesea", "werauhia", "catopsis", "aechmea",
                           "orquidea", "bromelia", "musgo", "liquen", "quiche"],
        "norma": "Res. 0213/1977 INDERENA",
        "nota": "Veda nacional al aprovechamiento, transporte y comercialización "
                "de musgos, líquenes, lamas, quiches, orquídeas y demás especies "
                "que hacen parte de su hábitat. Requiere caracterización y medidas "
                "de manejo (Art. 125 Decreto 2106/2019)"
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# VEDAS REGIONALES — indexadas por código de CAR
#
# Campo "solo_nacional" (opcional, bool): cuando es True, indica que la CAR
# NO tiene una resolución de veda forestal regional propia identificada.
# En ese caso, consultar_veda() no busca coincidencias en "spp" (vacío) sino
# que, si la especie ya está en veda nacional, refleja esa veda nacional
# también como obligación aplicable en la jurisdicción de esta CAR (para que
# el resultado no aparezca como "sin veda" al seleccionar esta CAR).
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
        "norma": "Res. 1986 del 1 de diciembre de 1984 CDMB",
        "tipo": "indefinida",
        "nota": ("Prohíbe el aprovechamiento de flora silvestre y maderables "
                 "listados en su jurisdicción (norma señalada 'en revisión' por "
                 "MADS). Varias entradas son a nivel de género o familia "
                 "(Nectandra, Aniba, Ocotea, Guatteria, Picramnia, Protium, "
                 "Cedrela, Tabebuia, Jacaranda, Lecythidaceae). Incluye también "
                 "líquenes, musgos, helechos y palmas."),
        "spp": [
            {"nombre_comun": "Canelo de páramo", "sci_fragmentos": ["drimys granatensis"]},
            {"nombre_comun": "Roble", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Laurel comino / Jigua", "sci_fragmentos": ["nectandra"]},
            {"nombre_comun": "Laurel comino", "sci_fragmentos": ["aniba"]},
            {"nombre_comun": "Laurel", "sci_fragmentos": ["ocotea"]},
            {"nombre_comun": "Yaya / Cargadero", "sci_fragmentos": ["guatteria"]},
            {"nombre_comun": "Caoba", "sci_fragmentos": ["swietenia macrophylla"]},
            {"nombre_comun": "Cuasia", "sci_fragmentos": ["mauria amara"]},
            {"nombre_comun": "Fresno", "sci_fragmentos": ["picramnia", "picrammia"]},
            {"nombre_comun": "Anime", "sci_fragmentos": ["protium"]},
            {"nombre_comun": "Cedro", "sci_fragmentos": ["cedrela"]},
            {"nombre_comun": "Olleto (Lecythidaceae)",
             "sci_fragmentos": ["lecythidaceae", "lecythis", "eschweilera",
                                "gustavia", "couratari", "grias", "cariniana"]},
            {"nombre_comun": "Guayacán", "sci_fragmentos": ["tabebuia", "handroanthus"]},
            {"nombre_comun": "Gualanday", "sci_fragmentos": ["jacaranda"]},
            {"nombre_comun": "Carreto", "sci_fragmentos": ["aspidosperma dugandii"]},
            {"nombre_comun": "Canime", "sci_fragmentos": ["copaifera canime"]},
            {"nombre_comun": "Abarco", "sci_fragmentos": ["cariniana pyriformis"]},
            {"nombre_comun": "Palma de cera", "sci_fragmentos": ["ceroxylon"]},
        ]
    },
    "CORANTIOQUIA": {
        "norma": "Res. 040-RES2312-6645 del 14 de diciembre de 2023 CORANTIOQUIA",
        "tipo": "indefinida",
        "nota": ("Veda indefinida y prohibición del aprovechamiento en toda la "
                 "jurisdicción de CORANTIOQUIA (Art. 1°, 45 especies). El "
                 "aprovechamiento queda sujeto a levantamiento de veda y a las "
                 "medidas de manejo que imponga la Autoridad Ambiental (Parágrafo "
                 "Art. 1°). Deroga la Res. 10194/2008 (Art. 8°). Acoge además las "
                 "vedas nacionales (Res. 0316/1974, 1408/1975, 0213/1977 y 0801/1977 "
                 "INDERENA, Ley 61/1985, Res. 96/2006 MAVDT — Art. 3°), prohíbe el uso "
                 "de hojas de Ceroxylon y Attalea amygdalina para ramos (Art. 4°) y el "
                 "uso y comercialización de bromelias silvestres (Art. 5°)."),
        "spp": [
            # ANACARDIACEAE
            {"nombre_comun": "Diomato / Santacruz",
             "sci_fragmentos": ["astronium graveolens", "astronium conzattii",
                                "astronium gracile"]},
            # ARECACEAE
            {"nombre_comun": "Palma de cera",
             "sci_fragmentos": ["ceroxylon alpinum", "ceroxylon andicola",
                                "iriartea andicola"]},
            {"nombre_comun": "Palma de cera",
             "sci_fragmentos": ["ceroxylon quindiuense", "ceroxylon floccosum",
                                "klopstockia quindiuensis"]},
            {"nombre_comun": "Palma de cera", "sci_fragmentos": ["ceroxylon sasaimae"]},
            {"nombre_comun": "Palma de ramo",
             "sci_fragmentos": ["ceroxylon parvifrons", "ceroxylon latisectum",
                                "ceroxylon mooreanum", "klopstockia parvifrons"]},
            {"nombre_comun": "Palmito real",
             "sci_fragmentos": ["ceroxylon vogelianum", "ceroxylon coarctatum",
                                "ceroxylon crispum", "ceroxylon flexuosum",
                                "ceroxylon hexandrum", "ceroxylon sclerophyllum",
                                "ceroxylon verruculosum", "klopstockia coarctata",
                                "klopstockia vogeliana"]},
            {"nombre_comun": "Nolí",
             "sci_fragmentos": ["elaeis oleifera", "alfonsia oleifera",
                                "corozo oleifera", "elaeis melanococca"]},
            {"nombre_comun": "Pholidostachys sanluisensis",
             "sci_fragmentos": ["pholidostachys sanluisensis"]},
            {"nombre_comun": "Macana", "sci_fragmentos": ["wettinia hirsuta"]},
            {"nombre_comun": "Macana",
             "sci_fragmentos": ["wettinia kalbreyeri", "catoblastus inconstans",
                                "catoblastus kalbreyeri", "catoblastus megalocarpus",
                                "catoblastus microcaryus", "catoblastus sphaerocarpus",
                                "catostigma sphaerocarpum"]},
            # BIGNONIACEAE
            {"nombre_comun": "Guayacán amarillo",
             "sci_fragmentos": ["handroanthus chrysanthus", "tabebuia chrysantha",
                                "tabebuia chrysanta", "bignonia chrysantha",
                                "tecoma chrysantha"]},
            # CARYOCARACEAE
            {"nombre_comun": "Cagüí",
             "sci_fragmentos": ["caryocar amygdaliferum", "rhizobolus amygdaliferus"]},
            {"nombre_comun": "Cagüí",
             "sci_fragmentos": ["caryocar glabrum", "pekea ternata",
                                "rhizobolus glaber", "rhizobolus saouvari",
                                "rhizobolus souari", "saouari glabra"]},
            # CHRYSOBALANACEAE
            {"nombre_comun": "Caimo",
             "sci_fragmentos": ["moquilea cabrerae", "licania cabrerae"]},
            # LAURACEAE
            {"nombre_comun": "Comino crespo",
             "sci_fragmentos": ["aniba perutilis", "aniba compacta"]},
            {"nombre_comun": "Yumbe", "sci_fragmentos": ["caryodaphnopsis cogolloi"]},
            {"nombre_comun": "Piedro", "sci_fragmentos": ["persea rigens"]},
            # FABACEAE
            {"nombre_comun": "Tipiri / Balaústre / Guayacán hobo",
             "sci_fragmentos": ["centrolobium paraense", "centrolobium patinense"]},
            {"nombre_comun": "Sapán", "sci_fragmentos": ["clathrotropis brunnea"]},
            {"nombre_comun": "Sapán / Aramata",
             "sci_fragmentos": ["clathrotropis brachypetala"]},
            {"nombre_comun": "Choibá / Almendro",
             "sci_fragmentos": ["dipteryx oleifera", "dipteryx panamensis",
                                "dipterix panamensis", "coumarouna oleifera"]},
            {"nombre_comun": "Algarrobo",
             "sci_fragmentos": ["hymenaea courbaril", "hymenaea animifera",
                                "hymenaea candolleana", "hymenaea confertifolia"]},
            {"nombre_comun": "Nazareno", "sci_fragmentos": ["peltogyne paniculata"]},
            {"nombre_comun": "Cativo", "sci_fragmentos": ["prioria copaifera"]},
            # FAGACEAE
            {"nombre_comun": "Roble",
             "sci_fragmentos": ["quercus humboldtii", "erythrobalanus humboldtii",
                                "erythrobalanus duqueana", "erythrobalanus lindenii",
                                "erythrobalanus tolimensis", "quercus almaguerensis",
                                "quercus tolimensis", "quercus lindenii"]},
            {"nombre_comun": "Roble morado / Roble negro",
             "sci_fragmentos": ["trigonobalanus excelsa", "colombobalanus excelsa"]},
            # HUMIRIACEAE
            {"nombre_comun": "Aceituno / Chanul",
             "sci_fragmentos": ["humiriastrum colombianum", "sacoglottis excelsa"]},
            # JUGLANDACEAE
            {"nombre_comun": "Cedro negro",
             "sci_fragmentos": ["juglans neotropica", "juglans columbiensis",
                                "juglans equatoriensis", "juglans granatensis",
                                "juglans honorei"]},
            # LECYTHIDACEAE
            {"nombre_comun": "Abarco",
             "sci_fragmentos": ["cariniana pyriformis", "cariniana clavata",
                                "cariniana exigua"]},
            {"nombre_comun": "Olleto / Coco cristal",
             "sci_fragmentos": ["lecythis tuyrana", "chytroma glossiniformis",
                                "lecythis calycocarpa", "lecythis elata",
                                "lecythis melliana"]},
            # MAGNOLIACEAE
            {"nombre_comun": "Hojarasco",
             "sci_fragmentos": ["magnolia espinalii", "talauma espinalii"]},
            {"nombre_comun": "Almanegra", "sci_fragmentos": ["magnolia jardinensis"]},
            {"nombre_comun": "Almanegra de ventanas",
             "sci_fragmentos": ["magnolia polyhypsophylla", "talauma polyhypsophylla"]},
            {"nombre_comun": "Guanábano de monte",
             "sci_fragmentos": ["magnolia hernandezii", "talauma hernandezii",
                                "talauma hernandezi"]},
            {"nombre_comun": "Almanegra",
             "sci_fragmentos": ["magnolia urraoensis", "dugandiodendron urraoense"]},
            {"nombre_comun": "Almanegra",
             "sci_fragmentos": ["magnolia yarumalensis", "dugandiodendron yarumalense"]},
            # MELIACEAE
            {"nombre_comun": "Cedro de altura",
             "sci_fragmentos": ["cedrela montana", "cedrela bogotensis",
                                "cedrela rosei", "cedrela subandina",
                                "surenus bogotensis", "surenus montana"]},
            {"nombre_comun": "Cedro",
             "sci_fragmentos": ["cedrela odorata", "cedrela amara",
                                "cedrela brachystachya", "cedrela brownei",
                                "cedrela caldasana", "cedrela cedro",
                                "cedrela cubensis", "cedrela glaziovii",
                                "cedrela guianensis", "cedrela hassleri",
                                "cedrela huberi", "cedrela imparipinnata"]},
            {"nombre_comun": "Caoba",
             "sci_fragmentos": ["swietenia macrophylla", "swietenia belizensis",
                                "swietenia candollei", "swietenia krukovii",
                                "swietenia tessmannii"]},
            # OCHNACEAE
            {"nombre_comun": "Caunce",
             "sci_fragmentos": ["godoya antioquiensis", "godoya antioquensis"]},
            # PODOCARPACEAE
            {"nombre_comun": "Pino romerón / Chaquiro",
             "sci_fragmentos": ["podocarpus oleifolius", "nageia oleifolia"]},
            {"nombre_comun": "Romerillo azuceno / Chaquiro",
             "sci_fragmentos": ["prumnopitys montana", "podocarpus montanus",
                                "podocarpus taxifolius", "dacrydium distichum",
                                "stachycarpus meridensis", "taxus montana"]},
            {"nombre_comun": "Chaquiro / Romerón / Pino colombiano",
             "sci_fragmentos": ["retrophyllum rospigliosii", "decussocarpus rospigliosii",
                                "nageia rospigliosii", "podocarpus rospigliosii"]},
            # TRIGONIACEAE
            {"nombre_comun": "Marfil", "sci_fragmentos": ["isidodendron tripterocarpum"]},
            # ZAMIACEAE
            {"nombre_comun": "Zamia incognita", "sci_fragmentos": ["zamia incognita"]},
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
        "norma": "Acuerdo 10 del 11 de marzo de 1983 + Acuerdo 003/1994 CORTOLIMA",
        "tipo": "indefinida",
        "nota": ("Veda permanente y total en su jurisdicción (Acuerdo 10/1983). "
                 "El Acuerdo 003/1994 prohíbe además la tala de bosque natural y "
                 "suspende permisos persistentes y únicos en el departamento."),
        "spp": [
            {"nombre_comun": "Cedro (Cedrela sp.)", "sci_fragmentos": ["cedrela"]},
            {"nombre_comun": "Pino romerón / hayuelo / chaquiro",
             "sci_fragmentos": ["podocarpus", "retrophyllum", "prumnopitys", "decussocarpus"]},
            {"nombre_comun": "Roble", "sci_fragmentos": ["quercus humboldtii"]},
        ]
    },
    "CARDER": {
        "norma": "Res. 177 del 9 de abril de 1997 CARDER",
        "tipo": "indefinida",
        "nota": ("No pueden ser aprovechadas salvo investigación o plantaciones "
                 "registradas. El Acuerdo 022/1993 CARDER veda además todas las "
                 "briófitas (musgos)."),
        "spp": [
            {"nombre_comun": "Pino colombiano",
             "sci_fragmentos": ["decussocarpus", "retrophyllum rospigliosii",
                                "podocarpus rospigliosii", "podocarpus montanus",
                                "prumnopitys montana", "podocarpus oleifolius"]},
            {"nombre_comun": "Cedro negro", "sci_fragmentos": ["juglans neotropica"]},
            {"nombre_comun": "Hojarasco", "sci_fragmentos": ["talauma caricifragans",
                                                          "talauma caracifragans"]},
            {"nombre_comun": "Molinillo", "sci_fragmentos": ["talauma hernandezi"]},
            {"nombre_comun": "Caparrapí", "sci_fragmentos": ["ocotea caparrapi"]},
            {"nombre_comun": "Comino", "sci_fragmentos": ["aniba perutilis"]},
            {"nombre_comun": "Roble", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Chanul", "sci_fragmentos": ["humiriastrum procerum"]},
            {"nombre_comun": "Dinde", "sci_fragmentos": ["chlorophora tinctoria", "maclura tinctoria"]},
            {"nombre_comun": "Palma boba / Helecho macho",
             "sci_fragmentos": ["trichipteris frigida", "cyathea frigida"]},
            {"nombre_comun": "Peinemono", "sci_fragmentos": ["apeiba aspera"]},
            {"nombre_comun": "Palma de cera", "sci_fragmentos": ["ceroxylon quindiuense"]},
            {"nombre_comun": "Piedro (Licania sp.)", "sci_fragmentos": ["licania"]},
            {"nombre_comun": "Caimo (Pouteria sp.)", "sci_fragmentos": ["pouteria"]},
            {"nombre_comun": "Algarrobo", "sci_fragmentos": ["hymenaea courbaril"]},
            {"nombre_comun": "Cerezo", "sci_fragmentos": ["prunus serotina"]},
            {"nombre_comun": "Caoba", "sci_fragmentos": ["swietenia macrophylla"]},
            {"nombre_comun": "Musgos (Acuerdo 022/1993)",
             "sci_fragmentos": ["bryophyta", "briofita", "musgo"]},
        ]
    },
    "CVC": {
        "norma": "Acuerdo 17 del 11 de junio de 1973 CVC",
        "tipo": "indefinida",
        "nota": ("Prohíbe el aprovechamiento forestal de caracolí, ceiba, palma "
                 "corozo y samán en todo el Valle del Cauca (el acuerdo nombra "
                 "Anacardium sp. y Ceiba sp. a nivel de género). La veda de "
                 "manglar del Acuerdo 24/1997 fue temporal (3 años)."),
        "spp": [
            {"nombre_comun": "Caracolí", "sci_fragmentos": ["anacardium"]},
            {"nombre_comun": "Ceiba", "sci_fragmentos": ["ceiba"]},
            {"nombre_comun": "Palma corozo / Palma de puerco",
             "sci_fragmentos": ["scheelea butyracea", "attalea butyracea"]},
            {"nombre_comun": "Samán", "sci_fragmentos": ["samanea saman", "albizia saman"]},
        ]
    },
    "CRC": {
        "norma": "Acuerdo 17/1973 CRC",
        "tipo": "indefinida",
        "nota": "Veda al aprovechamiento de las especies en Cauca (registro heredado; no re-verificado en fuente en la revisión sep/2026 — la norma citada coincide con la de CVC, confirmar el acto propio de la CRC)",
        "spp": [
            {"nombre_comun": "Samán", "sci_fragmentos": ["albizia saman", "samanea saman"]},
            {"nombre_comun": "Caracolí", "sci_fragmentos": ["anacardium excelsum"]},
            {"nombre_comun": "Ceiba", "sci_fragmentos": ["ceiba pentandra"]},
            {"nombre_comun": "Palma de Cuezco", "sci_fragmentos": ["scheelea butyraceae", "attalea butyracea"]},
        ]
    },
    "CORPOCALDAS": {
        "norma": "Res. 810 de 1996 CORPOCALDAS",
        "tipo": "indefinida",
        "nota": ("Veda en la jurisdicción de CORPOCALDAS (Caldas) para tres grupos: "
                 "(1) maderables — pino colombiano, nogal/cedro negro, hojarasco, "
                 "molinillo, aceite de caparrapí y roble; (2) musgos, líquenes, "
                 "quiches y parásitas diferentes a las orquídeas, y productos "
                 "vegetales conocidos como lama, capote y broza; (3) palma boba / "
                 "helecho macho (Cyatheaceae y Dicksoniaceae). Las orquídeas no "
                 "están en esta resolución, pero siguen vedadas por la Res. "
                 "0213/1977 INDERENA (nacional)."),
        "spp": [
            {"nombre_comun": "Pino colombiano",
             "sci_fragmentos": ["podocarpus rospigliosii", "podocarpus montanus",
                                "podocarpus oleifolius", "retrophyllum rospigliosii",
                                "decussocarpus rospigliosii", "nageia rospigliosii",
                                "prumnopitys montana", "nageia oleifolia"]},
            {"nombre_comun": "Nogal / Cedro negro", "sci_fragmentos": ["juglans"]},
            {"nombre_comun": "Hojarasco",
             "sci_fragmentos": ["talauma caracifragans", "talauma caricifragans",
                                "talauma caricifragrans", "magnolia caricifragrans"]},
            {"nombre_comun": "Molinillo",
             "sci_fragmentos": ["talauma hernandezi", "magnolia hernandezii"]},
            {"nombre_comun": "Aceite de caparrapí", "sci_fragmentos": ["ocotea caparrapi"]},
            {"nombre_comun": "Roble",
             "sci_fragmentos": ["quercus humboldtii", "quercus lindenii",
                                "quercus tolimensis", "quercus almaguerensis"]},
            {"nombre_comun": "Musgos, líquenes, quiches y parásitas (excepto orquídeas); "
                             "lama, capote y broza",
             "sci_fragmentos": ["bryophyta", "briofita", "musgo", "liquen", "lichen",
                                "quiche", "bromeliaceae", "tillandsia", "guzmania",
                                "vriesea", "werauhia", "catopsis", "aechmea"]},
            # "lama", "capote" y "broza" son productos, no taxones: no se usan
            # como fragmentos ("lama" haría falso positivo con p. ej. Calamagrostis).
            {"nombre_comun": "Palma boba / Helecho macho / Palma de helecho",
             "sci_fragmentos": ["cyatheaceae", "dicksoniaceae", "dicksonia",
                                "alsophila", "cyathea", "nephelea", "sphaeropteris",
                                "trichipteris", "cnemidaria", "palma boba",
                                "helecho macho", "palma de helecho"]},
        ]
    },
    "CAS": {
        "norma": "Acuerdo CAS No. 386-19 del 19 de diciembre de 2019",
        "tipo": "indefinida",
        "nota": (
            "Veda permanente al aprovechamiento en la jurisdicción de la CAS. "
            "Incluye especies maderables, coníferas nativas, magnolias, robles y palmas."
        ),
        "spp": [
            {"nombre_comun": "Cedro caoba", "sci_fragmentos": ["swietenia macrophylla"]},
            {"nombre_comun": "Yumbe / Pateguara / Panela quemada",
             "sci_fragmentos": ["caryodaphnopsis cogolloi"]},
            {"nombre_comun": "Comino crespo", "sci_fragmentos": ["aniba perutilis"]},
            {"nombre_comun": "Abarco", "sci_fragmentos": ["cariniana pyriformis"]},
            {"nombre_comun": "Chagüi", "sci_fragmentos": ["caryocar amygdaliferum"]},
            {"nombre_comun": "Sapán", "sci_fragmentos": ["clathrotropis brunnea"]},
            {"nombre_comun": "Marfil", "sci_fragmentos": ["isidodendron tripterocarpum"]},
            {"nombre_comun": "Pino silvestre / Chaquiro",
             "sci_fragmentos": ["podocarpus oleifolius"]},
            {"nombre_comun": "Pino colombiano",
             "sci_fragmentos": ["retrophyllum rospigliosii"]},
            {"nombre_comun": "Pino montañero",
             "sci_fragmentos": ["prumnopitys montana"]},
            {"nombre_comun": "Magnolia", "sci_fragmentos": ["magnolia"]},
            {"nombre_comun": "Roble blanco", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Roble negro", "sci_fragmentos": ["colombobalanus excelsa"]},
            {"nombre_comun": "Palma de cera",
             "sci_fragmentos": ["ceroxylon quindiuense", "ceroxylon quindíuense"]},
            {"nombre_comun": "Palma de Jender", "sci_fragmentos": ["wettinia hirsuta"]},
            {"nombre_comun": "Palma de ramo", "sci_fragmentos": ["ceroxylon vogelianum"]},
            {"nombre_comun": "Palma boba", "sci_fragmentos": ["cyathea hirsuta"]},
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
    "CORPOBOYACA": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORPOBOYACÁ "
                 "que establezca veda forestal regional. En su jurisdicción aplican "
                 "las vedas nacionales vigentes (Res. 0316/1974 INDERENA, Ley 61/1985, "
                 "Res. 1602/1995 + 020/1996 MADS). Si se conoce una resolución "
                 "específica de CORPOBOYACÁ, actualizar este registro."),
        "spp": [],
        "solo_nacional": True,
    },
    "CARSUCRE": {
        "norma": "N/A — sin veda regional por especie verificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ('No se verificó veda regional por especie. CARSUCRE cita la Res. 0617 del 17 de julio de 2015 al clasificar maderas y su estado de veda; revisarla antes de radicar. Aplican las vedas nacionales, en particular mangles (Golfo de Morrosquillo).'),
        "spp": [],
        "solo_nacional": True,
    },
    "CAR": {
        "norma": "Acuerdo CAR N° 021 del 17 de julio de 2018 (Art. 7)",
        "tipo": "indefinida",
        "nota": ("El Art. 7 recoge como vedadas en la jurisdicción CAR las vedas "
                 "nacionales (pino colombiano, roble, nogal, palma de cera, "
                 "epífitas, helechos arborescentes) y el Acuerdo CAR 022/1993 "
                 "(musgos, líquenes, lama, broza y ramas usados como adorno "
                 "navideño)."),
        "spp": [
            {"nombre_comun": "Pino colombiano",
             "sci_fragmentos": ["podocarpus rospigliosii", "podocarpus montanus",
                                "podocarpus oleifolius", "retrophyllum rospigliosii",
                                "prumnopitys montana"]},
            {"nombre_comun": "Roble", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Nogal", "sci_fragmentos": ["juglans"]},
            {"nombre_comun": "Palma de cera", "sci_fragmentos": ["ceroxylon quindiuense"]},
            {"nombre_comun": "Helecho macho / Palma boba",
             "sci_fragmentos": ["cyatheaceae", "dicksoniaceae", "cyathea",
                                "alsophila", "dicksonia", "sphaeropteris"]},
        ],
    },
    "CORNARE": {
        "norma": "Acuerdo 404 del 29 de mayo de 2020 CORNARE",
        "tipo": "indefinida",
        "nota": ("Veda regional de 30 especies (listado del Anexo 7 TR-RN-03 de "
                 "Cornare). Para especies con veda regional Cornare exige "
                 "reposición 1:10 con mantenimiento mínimo de 3 años. El acuerdo "
                 "recopila además las vedas nacionales (Res. 0316/1974, "
                 "0213/1977, 0801/1977)."),
        "spp": [
            {"nombre_comun": "Sajo", "sci_fragmentos": ["campnosperma panamense"]},
            {"nombre_comun": "Palma de cera de Sasaima", "sci_fragmentos": ["ceroxylon sasaimae"]},
            {"nombre_comun": "Palma macana", "sci_fragmentos": ["wettinia hirsuta"]},
            {"nombre_comun": "Palma maray", "sci_fragmentos": ["aiphanes leiostachys"]},
            {"nombre_comun": "Palma tagua", "sci_fragmentos": ["phytelephas macrocarpa"]},
            {"nombre_comun": "Chicalá", "sci_fragmentos": ["tabebuia guayacan",
                                                        "handroanthus guayacan"]},
            {"nombre_comun": "Almendrón / Cagüí", "sci_fragmentos": ["caryocar amygdaliferum"]},
            {"nombre_comun": "Aceite maría", "sci_fragmentos": ["calophyllum mariae"]},
            {"nombre_comun": "Balaústre / Guayacán jobo", "sci_fragmentos": ["centrolobium paraense"]},
            {"nombre_comun": "Sapán", "sci_fragmentos": ["clathrotropis brachypetala"]},
            {"nombre_comun": "Roble negro / Roble morado",
             "sci_fragmentos": ["colombobalanus excelsa", "trigonobalanus excelsa"]},
            {"nombre_comun": "Yumbé", "sci_fragmentos": ["caryodaphnopsis cogolloi"]},
            {"nombre_comun": "Olleto / Olla de mono", "sci_fragmentos": ["lecythis tuyrana"]},
            {"nombre_comun": "Abarco", "sci_fragmentos": ["cariniana pyriformis"]},
            {"nombre_comun": "Cabuyo / Coco cazuelo", "sci_fragmentos": ["eschweilera coriacea"]},
            {"nombre_comun": "Coco / Olla de mono", "sci_fragmentos": ["lecythis minor"]},
            {"nombre_comun": "Almanegra", "sci_fragmentos": ["magnolia mahechae"]},
            {"nombre_comun": "Molinillo", "sci_fragmentos": ["magnolia silvioi"]},
            {"nombre_comun": "Almanegra de Guatapé", "sci_fragmentos": ["magnolia guatapensis"]},
            {"nombre_comun": "Sota", "sci_fragmentos": ["iryanthera megistocarpa"]},
            {"nombre_comun": "Castaño de río Claro", "sci_fragmentos": ["compsoneura claroensis"]},
            {"nombre_comun": "Cuángare de loma", "sci_fragmentos": ["iryanthera megistophylla"]},
            {"nombre_comun": "Otobo", "sci_fragmentos": ["otoba acuminata"]},
            {"nombre_comun": "Otobo", "sci_fragmentos": ["otoba gracilipes"]},
            {"nombre_comun": "Cuángare otobo", "sci_fragmentos": ["otoba lehmannii"]},
            {"nombre_comun": "Yaya", "sci_fragmentos": ["quiina pteridophylla"]},
            {"nombre_comun": "Pino chaquiro", "sci_fragmentos": ["prumnopitys harmsiana"]},
            {"nombre_comun": "Pino colombiano / Chaquiro",
             "sci_fragmentos": ["prumnopitys montana", "podocarpus montanus"]},
            # Especies de acuerdos anteriores (207/2008 y 262/2011) citadas en
            # actos de Cornare; no aparecen en el listado del Acuerdo 404.
            {"nombre_comun": "Comino crespo (Acuerdo 262/2011 — verificar vigencia)",
             "sci_fragmentos": ["aniba perutilis"]},
            {"nombre_comun": "Caunce (Acuerdo 262/2011 — verificar vigencia)",
             "sci_fragmentos": ["godoya antioquensis", "godoya antioquiensis"]},
        ],
    },
    "CORPORINOQUIA": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORPORINOQUIA que "
                 "establezca veda forestal regional por especie. En su jurisdicción "
                 "(Meta, Arauca, Casanare, Vichada) aplican las vedas nacionales vigentes. "
                 "Nota aparte: la Res. 200.15.07-0193/2007 suspende temporalmente el "
                 "trámite de aprovechamientos forestales comerciales en bosque natural, "
                 "pero no es una veda de especies puntuales."),
        "spp": [],
        "solo_nacional": True,
    },
    "CORPOGUAJIRA": {
        "norma": "Acuerdo 003 del 22 de febrero de 2012 CORPOGUAJIRA",
        "tipo": "indefinida",
        "nota": ("Veda regional de cuatro especies forestales amenazadas del "
                 "bosque seco de La Guajira. Aplican además las vedas "
                 "nacionales (incluida la de mangles)."),
        "spp": [
            {"nombre_comun": "Guayacán de bola",
             "sci_fragmentos": ["bulnesia arborea", "gonopterodendron arboreum"]},
            {"nombre_comun": "Puy",
             "sci_fragmentos": ["tabebuia billbergii", "handroanthus billbergii"]},
            {"nombre_comun": "Corazón fino", "sci_fragmentos": ["platymiscium pinnatum"]},
            {"nombre_comun": "Ollita de mono", "sci_fragmentos": ["lecythis minor"]},
        ],
    },
    "CORPAMAG": {
        "norma": "N/A — sin veda regional por especie verificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ('Sin veda por especie. La Res. 000463/1994 CORPAMAG suspende aprovechamientos forestales en la parte alta y media de las cuencas de la Sierra Nevada de Santa Marta (restricción por área). Aplican las vedas nacionales, incluida la de mangles.'),
        "spp": [],
        "solo_nacional": True,
    },
    "CORPONOR": {
        "norma": "N/A — sin veda regional por especie verificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ('Sin veda por especie. Las Res. 0565/1997 y 0208/1999 CORPONOR prohíben el aprovechamiento forestal en las cuencas de los ríos Pamplonita, Táchira, Zulia, Algodonal y Arauca (restricción por área, no por especie). Aplican las vedas nacionales.'),
        "spp": [],
        "solo_nacional": True,
    },
    "CVS": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CVS (Valles del "
                 "Sinú y San Jorge, Córdoba) que establezca veda forestal regional. "
                 "Aplican las vedas nacionales vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CARDIQUE": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CARDIQUE (Bolívar) "
                 "que establezca veda forestal regional. Aplican las vedas nacionales "
                 "vigentes, en particular la veda nacional de mangles."),
        "spp": [],
        "solo_nacional": True,
    },
    "CSB": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CSB (Sur de Bolívar) "
                 "que establezca veda forestal regional. Aplican las vedas nacionales "
                 "vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CORPOCHIVOR": {
        "norma": "N/A — sin veda regional por especie verificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ('CORPOCHIVOR expidió la Res. 495 del 2 de septiembre de 2015 de veda regional de especies forestales, pero su listado no se pudo verificar en fuente pública. Mientras se incorpora, solo se cruzan las vedas nacionales: revisar la Res. 495/2015 antes de radicar.'),
        "spp": [],
        "solo_nacional": True,
    },
    "CORPOGUAVIO": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORPOGUAVIO "
                 "(Cundinamarca — Guavio) que establezca veda forestal regional. "
                 "Aplican las vedas nacionales vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CORMACARENA": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORMACARENA (área "
                 "de manejo especial La Macarena, Meta) que establezca veda forestal "
                 "regional por especie. Aplican las vedas nacionales vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CDA": {
        "norma": "N/A — sin veda regional por especie verificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ('Sin veda forestal por especie. La Res. 526/1998 CDA veda la flor de Inírida (Guacamaya superba, Schoenocephalium) en Guainía. Aplican las vedas nacionales.'),
        "spp": [],
        "solo_nacional": True,
    },
    "CORPOAMAZONIA": {
        "norma": "Res. 0110 del 12 de febrero de 2015 CORPOAMAZONIA",
        "tipo": "indefinida",
        "nota": ("Veda del aprovechamiento de ocho especies en Amazonas, "
                 "Putumayo y Caquetá. Exige censo 100 % de fustales vedados y "
                 "plan de manejo (TdR de levantamiento de veda, 2019)."),
        "spp": [
            {"nombre_comun": "Cedro", "sci_fragmentos": ["cedrela odorata"]},
            {"nombre_comun": "Cedro de altura", "sci_fragmentos": ["cedrela montana"]},
            {"nombre_comun": "Canelo de los Andaquíes", "sci_fragmentos": ["ocotea quixos"]},
            {"nombre_comun": "Ceiba tolúa / Carrecillo",
             "sci_fragmentos": ["pachira quinata", "bombacopsis quinata"]},
            {"nombre_comun": "Nogal / Cedro negro", "sci_fragmentos": ["juglans neotropica"]},
            {"nombre_comun": "Volador / Ceiba", "sci_fragmentos": ["ceiba samauma"]},
            {"nombre_comun": "Palo de rosa", "sci_fragmentos": ["aniba rosaeodora",
                                                             "aniba roseadora"]},
            {"nombre_comun": "Pino colombiano", "sci_fragmentos": ["podocarpus oleifolius"]},
        ],
    },
    "CODECHOCO": {
        "norma": "Res. 2535 del 1 de septiembre de 1987 CODECHOCÓ",
        "tipo": "indefinida (solo municipios de Riosucio, Unguía y Acandí)",
        "nota": ("Prohíbe el aprovechamiento de guayaquil y pino amarillo SOLO en "
                 "Riosucio, Unguía y Acandí. En el resto del Chocó aplican las "
                 "vedas nacionales (y la Res. 0463/1982 INDERENA sobre 'vara' en "
                 "la Costa Pacífica)."),
        "spp": [
            {"nombre_comun": "Guayaquil", "sci_fragmentos": ["centrolobium paraense"]},
            {"nombre_comun": "Pino amarillo (Podocarpus sp.)", "sci_fragmentos": ["podocarpus"]},
        ],
    },
    "CORPONARINO": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORPONARIÑO que "
                 "establezca veda forestal regional. Aplican las vedas nacionales "
                 "vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CORALINA": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORALINA (San "
                 "Andrés, Providencia y Santa Catalina) que establezca veda forestal "
                 "regional por especie. Aplican las vedas nacionales vigentes, en "
                 "particular la veda nacional de mangles."),
        "spp": [],
        "solo_nacional": True,
    },
    "AMVA": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("Área Metropolitana del Valle de Aburrá — autoridad ambiental urbana "
                 "para el suelo urbano de los municipios del Valle de Aburrá. No se "
                 "identificó veda forestal regional propia por especie; aplican las "
                 "vedas nacionales vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CAM": {
        "norma": "N/A — sin veda regional por especie verificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ('Huila. El Acuerdo 009/2018 CAM (Estatuto Forestal) regula la flora silvestre; no se verificó un listado de vedas regionales por especie. Aplican las vedas nacionales.'),
        "spp": [],
        "solo_nacional": True,
    },
    "CRQ": {
        "norma": "N/A — sin veda regional por especie verificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ('Quindío. Sin veda forestal por especie identificada; el Acuerdo 06/1986 CRQ solo restringe horarios de transporte de guadua. Aplican las vedas nacionales (palma de cera, Ley 61/1985).'),
        "spp": [],
        "solo_nacional": True,
    },
    "CORPOMOJANA": {
        "norma": "N/A — sin veda regional por especie verificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ('La Mojana (Sucre). Sin veda regional por especie identificada. Aplican las vedas nacionales.'),
        "spp": [],
        "solo_nacional": True,
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
    car_norm = _normalizar(car).upper().replace("Ñ", "N") if car else ""
    if car_norm and car_norm in VEDAS_REGIONALES:
        reg = VEDAS_REGIONALES[car_norm]

        if reg.get("solo_nacional"):
            # Esta CAR no tiene veda regional propia: si la especie ya está
            # en veda nacional, se refleja también aquí para que el resultado
            # de "consultar por esta CAR" no aparezca como sin veda.
            if en_nac:
                en_reg = True
                info_reg = {
                    "norma": info_nac["norma"],
                    "nota": reg["nota"],
                    "tipo": reg["tipo"],
                    "nombre_comun": info_nac["nombre_comun"],
                }
        else:
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
    # Cuando la CAR es "solo_nacional", en_nac y en_reg siempre coinciden
    # (ambos True o ambos False), así que el nivel efectivo es "nacional".
    car_solo_nacional = (
        car_norm in VEDAS_REGIONALES
        and VEDAS_REGIONALES[car_norm].get("solo_nacional", False)
    )

    if en_nac and en_reg and not car_solo_nacional:
        nivel = "nacional+regional"
        alerta = (
            f"⚠️ VEDA NACIONAL ({info_nac['norma']}) + "
            f"VEDA REGIONAL ({info_reg['norma']}). "
            f"{info_reg['nota']}"
        )
    elif en_nac:
        nivel = "nacional"
        if car_solo_nacional:
            alerta = (
                f"⚠️ VEDA NACIONAL ({info_nac['norma']}). {info_nac['nota']}. "
                f"Nota: {car_norm} no tiene veda regional propia identificada; "
                f"aplica esta veda nacional en su jurisdicción."
            )
        else:
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
