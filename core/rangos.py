# -*- coding: utf-8 -*-
import ee
from shapely.geometry import mapping
from shapely.ops import transform
from config import settings


def construir_areas_candidatas(gdf, contexto):
    """
    Construye las áreas candidatas para los 5 rangos en GEE.
    Retorna por rango:
        ha_conservar   : hectáreas de cobertura Natural (a conservar)
        ha_restaurar   : hectáreas de cobertura Transformada (a restaurar)
        total          : suma de las anteriores
        geom_conservar : GeoJSON bounds de las features Naturales   → para GBIF
        geom_restaurar : GeoJSON bounds de las features Transformadas → para GBIF
        geom_total     : GeoJSON bounds del área de búsqueda del rango
    """

    def strip_z(geom):
        return transform(lambda x, y, z=None: (x, y), geom)

    gdf_2d = gdf.copy()
    gdf_2d['geometry'] = gdf_2d['geometry'].apply(strip_z)

    features = []
    for _, row in gdf_2d.iterrows():
        if row.geometry.is_empty:
            continue
        features.append(ee.Feature(ee.Geometry(mapping(row.geometry))))

    ee_geom       = ee.FeatureCollection(features).geometry()
    bioma_impacto = contexto['bioma_principal']
    mun_nombre    = contexto['municipio']
    szh_nombre    = contexto['szh']
    zh_nombre     = contexto['zh']

    ecosistemas = ee.FeatureCollection(settings.GEE_ASSETS['ecosistemas'])
    municipios  = ee.FeatureCollection(settings.GEE_ASSETS['municipios'])
    zh_col      = ee.FeatureCollection(settings.GEE_ASSETS['zh'])
    sinap       = ee.FeatureCollection(settings.GEE_ASSETS['sinap'])

    geom_mun = municipios.filter(ee.Filter.eq('ADM2_NAME', mun_nombre)).geometry()
    geom_szh = zh_col.filter(ee.Filter.eq('nom_szh', szh_nombre)).geometry()
    geom_zh  = zh_col.filter(ee.Filter.eq('nom_zh',  zh_nombre)).geometry()

    def filtrar_candidatas(area_busqueda, filtro_bioma, es_otro_bioma=False):
        cands = ecosistemas.filterBounds(area_busqueda)
        if es_otro_bioma:
            cands = cands.filter(ee.Filter.neq('BIOMA_IAvH', filtro_bioma))
        else:
            cands = cands.filter(ee.Filter.eq('BIOMA_IAvH',  filtro_bioma))
        for cob in settings.COBERTURAS_EXCLUIDAS:
            cands = cands.filter(ee.Filter.neq('COBERTURA', cob))

        sinap_geom = sinap.filterBounds(area_busqueda).geometry()

        def procesar(f):
            geom_int   = f.geometry().intersection(area_busqueda, 1)
            geom_final = geom_int.difference(sinap_geom, 1)
            area_ha    = geom_final.area().divide(10000)
            return f.setGeometry(geom_final).set('area_ha_real', area_ha)

        return cands.map(procesar).filter(ee.Filter.gt('area_ha_real', 0.01))

    def _fc_bounds_geojson(fc):
        """Bounding box de un FeatureCollection como dict GeoJSON. None si vacío."""
        try:
            if fc.size().getInfo() == 0:
                return None
            return fc.geometry().bounds().getInfo()
        except Exception:
            return None

    def clasificar_y_resumir(fc, geom_busqueda):
        conservar_fc = fc.filter(ee.Filter.eq('GRADO_TRAN', 'Natural'))
        restaurar_fc = fc.filter(ee.Filter.eq('GRADO_TRAN', 'Transformado'))

        n            = fc.size().getInfo()
        ha_conservar = conservar_fc.aggregate_sum('area_ha_real').getInfo() if n > 0 else 0.0
        ha_restaurar = restaurar_fc.aggregate_sum('area_ha_real').getInfo() if n > 0 else 0.0

        try:
            geom_total = geom_busqueda.bounds().getInfo()
        except Exception:
            geom_total = None

        return {
            'ha_conservar':   float(ha_conservar),
            'ha_restaurar':   float(ha_restaurar),
            'total':          float(ha_conservar + ha_restaurar),
            'geom_conservar': _fc_bounds_geojson(conservar_fc),
            'geom_restaurar': _fc_bounds_geojson(restaurar_fc),
            'geom_total':     geom_total,
        }

    r1 = filtrar_candidatas(geom_mun, bioma_impacto)
    r2 = filtrar_candidatas(geom_szh, bioma_impacto)
    r3 = filtrar_candidatas(geom_zh,  bioma_impacto)
    r4 = filtrar_candidatas(geom_mun, bioma_impacto, es_otro_bioma=True)
    r5 = filtrar_candidatas(geom_szh, bioma_impacto, es_otro_bioma=True)

    return {
        'Rango 1': clasificar_y_resumir(r1, geom_mun),
        'Rango 2': clasificar_y_resumir(r2, geom_szh),
        'Rango 3': clasificar_y_resumir(r3, geom_zh),
        'Rango 4': clasificar_y_resumir(r4, geom_mun),
        'Rango 5': clasificar_y_resumir(r5, geom_szh),
    }
