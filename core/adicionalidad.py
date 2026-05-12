import ee
from config import settings

def calcular_tasa_bau(bioma_nombre):
    """
    Calcula la tasa de prdida anual (BAU) para un bioma especfico en Colombia
    usando Hansen Global Forest Change.
    """
    # 1. Obtener la geometra del Bioma en todo el pas
    ecosistemas = ee.FeatureCollection(settings.GEE_ASSETS['ecosistemas'])
    geom_bioma = ecosistemas.filter(ee.Filter.eq('BIOMA_IAVH', bioma_nombre)).geometry()
    
    # 2. Dataset Hansen
    hansen = ee.Image(settings.GEE_ASSETS['hansen'])
    
    # 3. Bosque inicial ao 2000 (umbral 30% cobertura)
    tree_cover = hansen.select(['treecover2000'])
    forest_2000 = tree_cover.gte(30).selfMask()
    
    # rea bosque 2000 en hectareas
    area_pixel = ee.Image.pixelArea().divide(10000)
    area_inicial = forest_2000.multiply(area_pixel).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geom_bioma,
        scale=30,
        maxPixels=1e13
    ).get('treecover2000').getInfo()
    
    # 4. Prdida 2001-2023
    loss_year = hansen.select(['lossyear'])
    loss_mask = loss_year.gt(0).And(loss_year.lte(23))
    forest_lost = loss_mask.selfMask()
    
    area_perdida = forest_lost.multiply(area_pixel).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geom_bioma,
        scale=30,
        maxPixels=1e13
    ).get('lossyear').getInfo()
    
    # 5. Tasa BAU Anual
    if area_inicial and area_inicial > 0:
        tasa_total = area_perdida / area_inicial
        tasa_anual = tasa_total / 23
    else:
        tasa_anual = 0
        
    return {
        'bioma': bioma_nombre,
        'area_inicial_ha': area_inicial,
        'area_perdida_ha': area_perdida,
        'tasa_bau_anual': tasa_anual
    }
