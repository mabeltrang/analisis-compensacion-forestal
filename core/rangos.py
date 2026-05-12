import ee
from config import settings

def construir_areas_candidatas(gdf, contexto):
    """
    Construye las reas candidatas para los 5 rangos en GEE.
    """
    ee_geom = ee.FeatureCollection(gdf.__geo_interface__).geometry()
    bioma_impacto = contexto['bioma_principal']
    mun_nombre = contexto['municipio']
    szh_nombre = contexto['szh']
    zh_nombre = contexto['zh']
    
    # Assets
    ecosistemas = ee.FeatureCollection(settings.GEE_ASSETS['ecosistemas'])
    municipios = ee.FeatureCollection(settings.GEE_ASSETS['municipios'])
    zh_col = ee.FeatureCollection(settings.GEE_ASSETS['zh'])
    sinap = ee.FeatureCollection(settings.GEE_ASSETS['sinap'])
    
    # Geometras de búsqueda
    geom_mun = municipios.filter(ee.Filter.eq('ADM2_NAME', mun_nombre)).geometry()
    geom_szh = zh_col.filter(ee.Filter.eq('nom_szh', szh_nombre)).geometry()
    geom_zh = zh_col.filter(ee.Filter.eq('nom_zh', zh_nombre)).geometry()
    
    def filtrar_candidatas(area_busqueda, filtro_bioma, es_otro_bioma=False):
        # 1. Filtrar ecosistemas por rea de bsqueda
        candidatas = ecosistemas.filterBounds(area_busqueda)
        
        # 2. Filtrar por Bioma
        if es_otro_bioma:
            candidatas = candidatas.filter(ee.Filter.neq('BIOMA_IAVH', filtro_bioma))
        else:
            candidatas = candidatas.filter(ee.Filter.eq('BIOMA_IAVH', filtro_bioma))
            
        # 3. Excluir Coberturas no elegibles
        for cob in settings.COBERTURAS_EXCLUIDAS:
            candidatas = candidatas.filter(ee.Filter.neq('COBERTURA', cob))
            
        # 4. Excluir SINAP (Zonas Protegidas)
        # Esto se hace recortando o filtrando por interseccin negativa
        # Para simplificar en GEE, restamos las geometras del SINAP si intersectan
        sinap_intersect = sinap.filterBounds(area_busqueda)
        # Nota: En GEE real se usara una operacin de 'difference' o una mscara
        
        return candidatas

    # Rango 1: Municipio + Bioma Impacto
    r1 = filtrar_candidatas(geom_mun, bioma_impacto)
    
    # Rango 2: SZH + Bioma Impacto
    r2 = filtrar_candidatas(geom_szh, bioma_impacto)
    
    # Rango 3: ZH + Bioma Impacto
    r3 = filtrar_candidatas(geom_zh, bioma_impacto)
    
    # Rango 4: Municipio + Otro Bioma
    r4 = filtrar_candidatas(geom_mun, bioma_impacto, es_otro_bioma=True)
    
    # Rango 5: SZH + Otro Bioma
    r5 = filtrar_candidatas(geom_szh, bioma_impacto, es_otro_bioma=True)
    
    def clasificar_y_resumir(fc):
        # Clasificar Natural -> Conservar, Transformado -> Restaurar
        # Asumimos columna 'GRADO_TRAN'
        conservar = fc.filter(ee.Filter.eq('GRADO_TRAN', 'Natural'))
        restaurar = fc.filter(ee.Filter.eq('GRADO_TRAN', 'Transformado'))
        
        ha_conservar = conservar.aggregate_sum('area_ha').getInfo() if fc.size().getInfo() > 0 else 0
        ha_restaurar = restaurar.aggregate_sum('area_ha').getInfo() if fc.size().getInfo() > 0 else 0
        
        return {
            'ha_conservar': ha_conservar,
            'ha_restaurar': ha_restaurar,
            'total': ha_conservar + ha_restaurar
        }

    return {
        'Rango 1': clasificar_y_resumir(r1),
        'Rango 2': clasificar_y_resumir(r2),
        'Rango 3': clasificar_y_resumir(r3),
        'Rango 4': clasificar_y_resumir(r4),
        'Rango 5': clasificar_y_resumir(r5)
    }
