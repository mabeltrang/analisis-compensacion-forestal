import ee
from config import settings

def obtener_url_mapa_estatico(gdf_impacto, bioma_principal):
    """
    Genera una URL de imagen estática de GEE con el impacto y el bioma principal.
    """
    try:
        # 1. Preparar Geometría de Impacto
        from shapely.geometry import mapping
        features = []
        for _, row in gdf_impacto.iterrows():
            features.append(ee.Feature(ee.Geometry(mapping(row.geometry))))
        ee_impacto = ee.FeatureCollection(features)
        
        # 2. Obtener Ecosistemas (Candidatas potenciales en el Bioma)
        ecosistemas = ee.FeatureCollection(settings.GEE_ASSETS['ecosistemas'])
        candidatas = ecosistemas.filter(ee.Filter.eq('BIOMA_IAvH', bioma_principal))
        
        # 3. Capa de Fondo (Satélite)
        # Usamos Sentinel-2 (S2_SR_HARMONIZED) para mejor visual
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
            .filterBounds(ee_impacto.geometry()) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
            .median()
            
        vis_params_s2 = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}
        img_base = s2.visualize(**vis_params_s2)
        
        # 4. Capas de Vectores pintadas sobre la imagen
        # Candidatas en Verde (Transparente)
        img_candidatas = candidatas.draw(color='00FF00', strokeWidth=1).visualize(opacity=0.4)
        
        # Impacto en Rojo (Borde grueso)
        img_impacto = ee_impacto.draw(color='FF0000', strokeWidth=3)
        
        # Combinar
        final_img = img_base.blend(img_candidatas).blend(img_impacto)
        
        # 5. Obtener URL de Miniatura (Thumbnail)
        # Ajustar region con un buffer mayor para contexto
        region = ee_impacto.geometry().buffer(5000).bounds()
        
        url = final_img.getThumbURL({
            'region': region,
            'dimensions': 800,
            'format': 'png'
        })
        
        return url
    except Exception as e:
        print(f"Error generando mapa: {e}")
        return None
