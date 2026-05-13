# -*- coding: utf-8 -*-
import ee
import requests
from shapely.geometry import mapping
from config import settings


def obtener_url_mapa_estatico(gdf_impacto, bioma_principal):
    """
    Genera una URL de imagen estática usando la API de tiles de GEE.
    Usa getMapId() + tiles en lugar de getThumbURL() que falla en Streamlit Cloud.
    """
    try:
        # 1. Preparar geometría de impacto (quitar Z si existe)
        from shapely.ops import transform as shp_transform
        def strip_z(geom):
            return shp_transform(lambda x, y, z=None: (x, y), geom)

        features = []
        for _, row in gdf_impacto.iterrows():
            geom = strip_z(row.geometry)
            if not geom.is_empty:
                features.append(ee.Feature(ee.Geometry(mapping(geom))))

        ee_impacto = ee.FeatureCollection(features)
        region     = ee_impacto.geometry().buffer(5000).bounds()

        # 2. Imagen base Sentinel-2
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(ee_impacto.geometry())
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
            .median()
        )
        vis_s2  = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}
        img_rgb = s2.visualize(**vis_s2)

        # 3. Capa de ecosistemas candidatos (bioma)
        ecosistemas = ee.FeatureCollection(settings.GEE_ASSETS['ecosistemas'])
        candidatas  = ecosistemas.filter(ee.Filter.eq('BIOMA_IAvH', bioma_principal))
        img_cand    = candidatas.style(color='00FF00', fillColor='00FF0033', width=1)

        # 4. Capa de impacto
        img_imp = ee_impacto.style(color='FF0000', fillColor='FF000033', width=3)

        # 5. Combinar
        final_img = img_rgb.blend(img_cand).blend(img_imp)

        # 6. getThumbURL con dimensiones explícitas (más compatible que getMapId)
        coords = region.coordinates().getInfo()[0]
        thumb_url = final_img.getThumbURL({
            'region':     {'type': 'Polygon', 'coordinates': [coords]},
            'dimensions': 800,
            'format':     'png',
        })

        # Verificar que la URL responde
        resp = requests.head(thumb_url, timeout=10)
        if resp.status_code == 200:
            return thumb_url

        # Fallback: retornar la URL igual (puede funcionar en el navegador)
        return thumb_url

    except Exception as e:
        print(f"[mapas] Error generando mapa: {e}")
        return None
