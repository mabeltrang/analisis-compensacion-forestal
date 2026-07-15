# -*- coding: utf-8 -*-
import os

# ─── Rutas ──────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR      = os.path.join(BASE_DIR, "config")
CREDENTIALS_DIR = os.path.join(BASE_DIR, "credentials")
OUTPUTS_DIR     = os.path.join(BASE_DIR, "outputs")

# ─── GEE Assets ─────────────────────────────────────────────────────────────
GEE_ASSETS = {
    "ecosistemas": "projects/ndvi-restauracion/assets/Shape_E_ECCMC_Ver21_100K",
    "zh":          "projects/ndvi-restauracion/assets/zh_colombia",
    "reaa":        "projects/ndvi-restauracion/assets/reaa_colombia",
    "hansen":      "UMD/hansen/global_forest_change_2023_v1_11",
    "sentinel":    "COPERNICUS/S2_SR_HARMONIZED",
    "municipios":  "projects/ndvi-restauracion/assets/Municipios_Abril_2026_shp",
    "sinap":       "WCMC/WDPA/current/polygons",
    # NUEVO — mismos assets que ya usa el script GEE de export R1-R6 para
    # las "iniciativas de conservación" (sección 5 del script, extraerIniciativas()).
    # Se agregan acá en vez de reutilizar "reaa"/"sinap" porque son shapes
    # distintos con campos distintos (ap_nombre/ap_categor, nombre_cap/aa, etc.)
    "runap":                "projects/ndvi-restauracion/assets/RUNAP",
    "reaa_excluir":         "projects/ndvi-restauracion/assets/REAA_excluir_simplificado",
    "omec":                 "projects/ndvi-restauracion/assets/OMEC_simplificado",
    "bst":                  "projects/ndvi-restauracion/assets/BST_simplificado",
    "reservas_forestales":  "projects/ndvi-restauracion/assets/forest_reserves",
}

# Portafolios regionales por CAR (Escenarios de Compensación) — mismo dict
# que PORTAFOLIOS_CAR en el script GEE. Se activa por departamento.
PORTAFOLIOS_CAR = {
    'CRA': {
        'asset':     "projects/ndvi-restauracion/assets/acciones_de_Compensacion_CRA",
        'campo_acc': 'AccionGen',
        'campo_esc': 'Escenarios',
        'campo_pri': 'Val_Priori',
        'deptos':    ['Atlántico'],  # con tilde, igual que en el shape
    }
    # Para agregar otra CAR: nueva entrada aquí, igual que en el script GEE.
}

# ─── Factores de rango Manual 2026 (Res. 0305/2026) ─────────────────────────
FACTORES_RANGO = {
    1: 0.0,
    2: 0.3,
    3: 0.6,
    4: 0.9,
    5: 0.9,
    6: 1.2,
}

# ─── Factores de efectividad (literatura científica) ────────────────────────
EFECTIVIDAD = {
    "preservacion":          0.90,
    "restauracion_pasiva":   0.60,
    "restauracion_asistida": 0.75,
    "restauracion_activa":   0.85,
}

# ─── Criterio B — Res. 0126/2024 MADS (Tabla 4, Manual 2026) ────────────────
# NT no aparece en el Manual ni en Res. 0126/2024 → valor 0
AMENAZA_VALORES = {
    "CR": 1.0,
    "EN": 0.6,
    "VU": 0.4,
    "NT": 0.0,
    "LC": 0.0,
    "DD": 0.0,
    "NE": 0.0,
}

# ─── Equivalencias CITES → Criterio B (escenario Unergy) ────────────────────
# Sin respaldo normativo directo en el Manual 2026.
# Presentar como escenario conservador complementario.
# Apéndice I  → equivale a EN (0.6)
# Apéndice II → equivale a VU (0.4)
# Apéndice III→ 0.0 (solo regulación comercial, no amenaza directa)
CITES_VALORES = {
    "I":   0.6,
    "II":  0.4,
    "III": 0.0,
}

# ─── Equivalencias UICN → Criterio B (escenario Unergy) ─────────────────────
# La UICN es la referencia global de la que se deriva Res. 0126/2024.
# Se usa como tercer escenario: toma el MAX(MADS, UICN) por individuo.
# Mismos valores que MADS porque las categorías son equivalentes.
UICN_VALORES = {
    "CR": 1.0,
    "EN": 0.6,
    "VU": 0.4,
    "NT": 0.0,
    "LC": 0.0,
    "DD": 0.0,
}

# ─── Configuración inventario ────────────────────────────────────────────────
DAP_MIN_DEFAULT    = 9.86   # cm  (CAP ≥ 31 cm → DAP = 31/π ≈ 9.87 cm)
HORIZONTE_TEMPORAL = 15     # años
