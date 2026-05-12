import ee
from config import settings

def calcular_adicionalidad_biotica(bd_results):
    """
    Calcula un factor de ganancia biótica basado en los resultados de GBIF.
    """
    if not bd_results:
        return 1.0, "Básica (Solo cobertura)"
        
    score = 1.0
    razones = []
    
    # 1. Por Especies Amenazadas (Peso Alto)
    amenazadas = len(bd_results.get('especies_amenazadas', []))
    if amenazadas > 5:
        score += 0.3
        razones.append("Alta presencia de especies amenazadas (+0.3)")
    elif amenazadas > 0:
        score += 0.15
        razones.append("Presencia de especies amenazadas (+0.15)")
        
    # 2. Por Riqueza de Especies
    riqueza = bd_results.get('riqueza_total', 0)
    if riqueza > 200:
        score += 0.15
        razones.append("Hotspot de biodiversidad regional (+0.15)")
    elif riqueza > 50:
        score += 0.05
        razones.append("Diversidad regional moderada (+0.05)")
        
    # 3. Por presencia de Taxones Clave (Conectividad)
    taxones = bd_results.get('taxones', {})
    if taxones.get('Mamíferos', 0) > 5:
        score += 0.05
        razones.append("Hábitat funcional para mamíferos (+0.05)")
        
    return round(score, 2), " | ".join(razones) if razones else "Estándar"

def analizar_balance_biodiversidad(candidatas_rango, bd_results):
    """
    Analiza el balance entre Ganancia Neta (Restauración) y Pérdida Evitada (Conservación).
    """
    ha_cons = candidatas_rango.get('ha_conservar', 0)
    ha_rest = candidatas_rango.get('ha_restaurar', 0)
    
    bd = bd_results if bd_results else {}
    amenazadas = len(bd.get('especies_amenazadas', []))
    riqueza = bd.get('riqueza_total', 0)
    
    if ha_cons > ha_rest:
        return f"🛡️ Protección: Refugio para {riqueza} especies."
    else:
        return f"🌱 Recuperación: Ganancia de {ha_rest:.1f} ha de hábitat."

def calcular_tasa_bau(bioma_nombre):
    """
    Calcula la tasa de pérdida anual (BAU) para un bioma específico en Colombia.
    """
    try:
        # 1. Obtener la geometría del bioma
        biomas = ee.FeatureCollection(settings.GEE_ASSETS['ecosistemas'])
        geom_bioma = biomas.filter(ee.Filter.eq('BIOMA_IAvH', bioma_nombre)).geometry()
        
        # 2. Dataset Hansen
        hansen = ee.Image(settings.GEE_ASSETS['hansen'])
        
        # 3. Bosque inicial año 2000
        tree_cover = hansen.select(['treecover2000'])
        forest_2000 = tree_cover.gte(30).selfMask()
        
        area_pixel = ee.Image.pixelArea().divide(10000)
        area_inicial = forest_2000.multiply(area_pixel).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geom_bioma,
            scale=100, # Bajamos escala para evitar timeouts en biomas grandes
            maxPixels=1e13
        ).get('treecover2000').getInfo()
        
        # 4. Pérdida 2001-2023
        loss_year = hansen.select(['lossyear'])
        loss_mask = loss_year.gt(0).And(loss_year.lte(23))
        forest_lost = loss_mask.selfMask()
        
        area_perdida = forest_lost.multiply(area_pixel).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geom_bioma,
            scale=100,
            maxPixels=1e13
        ).get('lossyear').getInfo()
        
        if area_inicial and area_inicial > 0:
            tasa_total = area_perdida / area_inicial
            tasa_anual = tasa_total / 23
        else:
            tasa_anual = 0.001 # Valor por defecto si falla
            
        return {
            'bioma': bioma_nombre,
            'area_inicial_ha': area_inicial,
            'area_perdida_ha': area_perdida,
            'tasa_bau_anual': tasa_anual
        }
    except Exception as e:
        print(f"Error en BAU: {e}")
        return {'bioma': bioma_nombre, 'tasa_bau_anual': 0.001}
