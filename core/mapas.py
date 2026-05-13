# -*- coding: utf-8 -*-
import ee
import requests
from shapely.geometry import mapping
from shapely.ops import transform as shp_transform
from config import settings

# Colores por rango para las zonas candidatas
COLORES_RANGO = {
    'Rango 1': 'FFFF00',  # amarillo
    'Rango 2': '00FFFF',  # cyan
    'Rango 3': 'FF00FF',  # magenta
    'Rango 4': 'FF8800',  # naranja
    'Rango 5': 'FFFFFF',  # blanco
}


def _strip_z(geom):
    return shp_transform(lambda x, y, z=None: (x, y), geom)


def _gdf_to_ee_fc(gdf_impacto):
    features = []
    for _, row in gdf_impacto.iterrows():
        geom = _strip_z(row.geometry)
        if not geom.is_empty:
            features.append(ee.Feature(ee.Geometry(mapping(geom))))
    return ee.FeatureCollection(features)


def _geojson_to_ee_geom(geojson_dict):
    """Convierte dict GeoJSON a ee.Geometry. Retorna None si falla."""
    if not geojson_dict:
        return None
    try:
        return ee.Geometry(geojson_dict)
    except Exception:
        return None


def _thumb_url(img, region_geom, dims=800):
    """Genera URL de thumbnail. Retorna None si falla."""
    try:
        coords = region_geom.bounds().coordinates().getInfo()[0]
        url = img.getThumbURL({
            'region':     {'type': 'Polygon', 'coordinates': [coords]},
            'dimensions': dims,
            'format':     'png',
        })
        return url
    except Exception as e:
        print(f"[mapas] getThumbURL error: {e}")
        return None


def obtener_url_mapa_estatico(gdf_impacto, bioma_principal):
    """
    Vista general: Sentinel-2 + bioma completo (verde) + polígono impacto (rojo).
    """
    try:
        ee_impacto = _gdf_to_ee_fc(gdf_impacto)
        region     = ee_impacto.geometry().buffer(5000).bounds()

        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(ee_impacto.geometry())
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
            .median()
        )
        img_rgb  = s2.visualize(bands=['B4', 'B3', 'B2'], min=0, max=3000)

        ecosistemas = ee.FeatureCollection(settings.GEE_ASSETS['ecosistemas'])
        candidatas  = ecosistemas.filter(ee.Filter.eq('BIOMA_IAvH', bioma_principal))
        img_cand    = candidatas.style(color='00FF00', fillColor='00FF0033', width=1)
        img_imp     = ee_impacto.style(color='FF0000', fillColor='FF000033', width=3)

        final = img_rgb.blend(img_cand).blend(img_imp)
        return _thumb_url(final, region)

    except Exception as e:
        print(f"[mapas] Error mapa general: {e}")
        return None


def obtener_mapas_por_rango(gdf_impacto, cand_results):
    """
    Genera una URL de thumbnail por rango.
    Cada imagen muestra:
      - Sentinel-2 de fondo
      - Zonas a Conservar (Natural) en VERDE
      - Zonas a Restaurar (Transformado) en NARANJA
      - Polígono de impacto en ROJO
    Retorna dict {rango: url_o_None}
    """
    try:
        ee_impacto = _gdf_to_ee_fc(gdf_impacto)
        img_imp    = ee_impacto.style(color='FF0000', fillColor='FF000066', width=3)
    except Exception as e:
        print(f"[mapas] Error preparando impacto: {e}")
        return {}

    mapas = {}

    for rango, datos in cand_results.items():
        try:
            geom_cons_dict = datos.get('geom_conservar_ee')
            geom_rest_dict = datos.get('geom_restaurar_ee')
            geom_tot_dict  = datos.get('geom_total')

            # Región de la imagen: bbox del área de búsqueda
            if geom_tot_dict:
                region = ee.Geometry(geom_tot_dict).bounds()
            else:
                region = ee_impacto.geometry().buffer(10000).bounds()

            # Imagen base Sentinel-2
            s2 = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(region)
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                .median()
            )
            img_rgb = s2.visualize(bands=['B4', 'B3', 'B2'], min=0, max=3000)
            final   = img_rgb

            # Capa Conservar (verde)
            if geom_cons_dict:
                try:
                    fc_cons  = ee.FeatureCollection([ee.Feature(ee.Geometry(geom_cons_dict))])
                    img_cons = fc_cons.style(color='00FF00', fillColor='00FF0066', width=2)
                    final    = final.blend(img_cons)
                except Exception:
                    pass

            # Capa Restaurar (naranja)
            if geom_rest_dict:
                try:
                    fc_rest  = ee.FeatureCollection([ee.Feature(ee.Geometry(geom_rest_dict))])
                    img_rest = fc_rest.style(color='FF8800', fillColor='FF880066', width=2)
                    final    = final.blend(img_rest)
                except Exception:
                    pass

            # Capa impacto (rojo)
            final = final.blend(img_imp)

            url = _thumb_url(final, region, dims=700)
            mapas[rango] = url

        except Exception as e:
            print(f"[mapas] Error rango {rango}: {e}")
            mapas[rango] = None

    return mapas
