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
    "municipios":  "FAO/GAUL/2015/level2",
    "sinap":       "WCMC/WDPA/current/polygons",
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
    "preservacion":         0.90,
    "restauracion_pasiva":  0.60,
    "restauracion_asistida":0.75,
    "restauracion_activa":  0.85,
}

# ─── Criterio B — valores por categoría amenaza ─────────────────────────────
# Fuente: Tabla 4, Manual 2026 (Res. 0305/2026 MADS)
# NT no aparece en el Manual ni en Res. 0126/2024 → valor 0
AMENAZA_VALORES = {
    "CR": 1.0,
    "EN": 0.6,
    "VU": 0.4,
    "NT": 0.0,   # No reconocida en Tabla 4 del Manual 2026
    "LC": 0.0,
    "NE": 0.0,
}

# ─── Equivalencias CITES → Criterio B (equiparación interna Unergy) ─────────
# No tiene respaldo normativo directo en el Manual.
# Se presenta como escenario alternativo ("con CITES") junto al oficial.
# Apéndice I  → equivale a EN (0.6)
# Apéndice II → equivale a VU (0.4)
# Apéndice III→ sin valor adicional (0.0)
CITES_VALORES = {
    "I":   0.6,
    "II":  0.4,
    "III": 0.0,
}

# ─── Configuración inventario ────────────────────────────────────────────────
DAP_MIN_DEFAULT      = 9.86   # cm  (CAP ≥ 31 cm → DAP = 31/π ≈ 9.87 cm)
HORIZONTE_TEMPORAL   = 15     # años

# ─── Coberturas excluidas para áreas candidatas ──────────────────────────────
COBERTURAS_EXCLUIDAS = [
    "Tejido urbano continuo",
    "Tejido urbano discontinuo",
    "Zonas industriales o comerciales",
    "Red vial, ferroviaria y terrenos asociados",
    "Aeropuertos",
    "Lagunas, lagos y cienagas naturales",
    "Rios (50 m)",
    "Cuerpos de agua artificiales",
    "Cultivos transitorios",
    "Cultivos permanentes herbaceos, arbustivos y arboreos",
    "Cultivos agroforestales",
    "Cultivos confinados",
]
