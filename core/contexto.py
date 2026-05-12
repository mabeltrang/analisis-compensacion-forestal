# -*- coding: utf-8 -*-
import ee
import json
from shapely.geometry import shape
from config import settings

def obtener_contexto_impacto(gdf):
    """
    Cruza el polgono de impacto con assets de GEE para obtener:
    BIOMA-IAvH, Municipio, Departamento, ZH, SZH y reas por cobertura.
    """
    # Convertir GeoPandas a ee.Geometry
    # Reproyectar a WGS84 y forzar 2D (quitar Z)
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    else:
        gdf = gdf.to_crs("EPSG:4326")
        
    # Limpieza Crítica: Quitar coordenadas Z que rompen GEE
    gdf['geometry'] = gdf['geometry'].map(lambda g: shape(g.__geo_interface__))
    
    # Tomamos la union de todas las geometras y convertimos a JSON limpio
    # Usamos features individuales para evitar GeometryCollections complejas
    features = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom.is_empty: continue
        # GeoJSON estndar (2D)
        features.append(ee.Feature(ee.Geometry(row.geometry.__geo_interface__)))
        
    fc = ee.FeatureCollection(features)
    ee_geom = fc.geometry()
    
    # 1. Cruzar con Municipios (FAO GAUL)
    municipios = ee.FeatureCollection(settings.GEE_ASSETS['municipios'])
    mun_intersect = municipios.filterBounds(ee_geom)
    mun_data = mun_intersect.first().toDictionary().select(['ADM2_NAME', 'ADM1_NAME']).getInfo()
    
    # 2. Cruzar con ZH (Zonas Hidrogrficas)
    zh_col = ee.FeatureCollection(settings.GEE_ASSETS['zh'])
    zh_intersect = zh_col.filterBounds(ee_geom)
    zh_data = zh_intersect.first().toDictionary().select(['nom_zh', 'nom_szh', 'nom_ah']).getInfo()
    
    # 3. Cruzar con Ecosistemas (BIOMA-IAvH)
    ecosistemas = ee.FeatureCollection(settings.GEE_ASSETS['ecosistemas'])
    # Recortar ecosistemas al polgono de impacto
    eco_impacto = ecosistemas.filterBounds(ee_geom).map(lambda f: f.setGeometry(f.geometry().intersection(ee_geom, 1)))
    
    # Obtener Bioma Principal (el que tenga mayor rea)
    bioma_data = eco_impacto.reduceColumns(ee.Reducer.frequencyHistogram(), ['BIOMA_IAVH']).getInfo()
    biomas_hist = bioma_data['histogram']
    bioma_principal = max(biomas_hist, key=biomas_hist.get) if biomas_hist else "Desconocido"
    
    # Calcular reas por Cobertura
    # El asset debe tener una columna 'COBERTURA' o similar. Segn el Manual se usa la leyenda Corine.
    # Asumimos columna 'COBERTURA' y 'GRADO_TRAN'
    eco_info = eco_impacto.map(lambda f: f.set('area_ha', f.area().divide(10000)))
    
    # Agrupar reas por cobertura
    stats = eco_info.reduceColumns(ee.Reducer.sum().group(1, 'COBERTURA'), ['area_ha', 'COBERTURA']).getInfo()
    
    areas_cobertura = {}
    for group in stats['groups']:
        areas_cobertura[group['COBERTURA']] = group['sum']
        
    return {
        'municipio': mun_data.get('ADM2_NAME'),
        'departamento': mun_data.get('ADM1_NAME'),
        'zh': zh_data.get('nom_zh'),
        'szh': zh_data.get('nom_szh'),
        'ah': zh_data.get('nom_ah'),
        'bioma_principal': bioma_principal,
        'areas_cobertura': areas_cobertura
    }
