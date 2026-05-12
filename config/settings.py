import os

# Rutas de Archivos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
CREDENTIALS_DIR = os.path.join(BASE_DIR, "credentials")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

# GEE Assets (Unergy / Public)
GEE_ASSETS = {
    "ecosistemas": "projects/ndvi-restauracion/assets/Shape_E_ECCMC_Ver21_100K",
    "zh": "projects/ndvi-restauracion/assets/zh_colombia",
    "reaa": "projects/ndvi-restauracion/assets/reaa_colombia",
    "hansen": "UMD/hansen/global_forest_change_2023_v1_11",
    "sentinel": "COPERNICUS/S2_SR_HARMONIZED",
    "municipios": "FAO/GAUL/2015/level2",
    "sinap": "WCMC/WDPA/current/polygons"
}

# Factores Manual 2026 (Resolucin 0305/2026)
FACTORES_RANGO = {
    1: 0.0,
    2: 0.3,
    3: 0.6,
    4: 0.9,
    5: 0.9,
    6: 1.2
}

# Factores de Efectividad (Literatura)
EFECTIVIDAD = {
    "preservacion": 0.90,
    "restauracion_pasiva": 0.60,
    "restauracion_asistida": 0.75,
    "restauracion_activa": 0.85
}

# Valores Categoras Amenaza (Res. 0126/2024)
AMENAZA_VALORES = {
    "LC": 0.0,
    "NT": 0.1,
    "VU": 0.33,
    "EN": 0.66,
    "CR": 1.0
}

# Configuración Inventario
DAP_MIN_DEFAULT = 10.0  # cm
HORIZONTE_TEMPORAL = 15  # aos

# Coberturas excluidas para áreas candidatas
COBERTURAS_EXCLUIDAS = [
    "Tejido urbano continuo", "Tejido urbano discontinuo", 
    "Zonas industriales o comerciales", "Red vial, ferroviaria y terrenos asociados", 
    "Aeropuertos", "Lagunas, lagos y cinagas naturales", "Ros (50 m)", 
    "Cuerpos de agua artificiales", "Cultivos transitorios", 
    "Cultivos permanentes herbceos, arbustivos y arbreos", 
    "Cultivos agroforestales", "Cultivos confinados"
]
