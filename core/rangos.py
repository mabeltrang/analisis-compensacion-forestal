# -*- coding: utf-8 -*-
import ee
from shapely.geometry import mapping
from shapely.ops import transform
from config import settings


def construir_areas_candidatas(gdf, contexto):
    """
    Construye las áreas candidatas para los 5 rangos en GEE.
    Retorna por rango:
        ha_conservar      : hectáreas de cobertura Natural
        ha_restaurar      : hectáreas de cobertura Transformada
        total             : suma
        geom_conservar    : GeoJSON Polygon (bbox con buffer 10 km del centroide) → GBIF
        geom_restaurar    : GeoJSON Polygon (bbox con buffer 10 km del centroide) → GBIF
        geom_total        : GeoJSON Polygon del área de búsqueda del rango → mapa
        geom_conservar_ee : GeoJSON de la unión real de features Naturales → mapa
        geom_restaurar_ee : GeoJSON de la unión real de features Transformadas → mapa
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
            cands = cands.filter(ee.Filter.eq('BIOMA_IAvH', filtro_bioma))
        for cob in settings.COBERTURAS_EXCLUIDAS:
            cands = cands.filter(ee.Filter.neq('COBERTURA', cob))

        sinap_geom = sinap.filterBounds(area_busqueda).geometry()

        # TODO: agregar exclusión por REAA cuando esté disponible
        # var reaa = ee.FeatureCollection('projects/ndvi-restauracion/assets/REAA_simplified');
        # cands = cands.filter(ee.Filter.bounds(reaa).not())

        def procesar(f):
            geom_int   = f.geometry().intersection(area_busqueda, 1)
            geom_final = geom_int.difference(sinap_geom, 1)
            area_ha    = geom_final.area().divide(10000)
            return f.setGeometry(geom_final).set('area_ha_real', area_ha)

        return cands.map(procesar).filter(ee.Filter.gt('area_ha_real', 0.01))

    def _centroid_buffer_geojson(fc, buffer_m=10000):
        """
        Buffer de buffer_m metros alrededor del centroide de la FC.
        Mucho más pequeño que el bbox completo → GBIF funciona mejor.
        Retorna dict GeoJSON Polygon o None si FC vacía.
        """
        try:
            n = fc.size().getInfo()
            if n == 0:
                return None
            centroid = fc.geometry().centroid(100)
            buffered = centroid.buffer(buffer_m).bounds()
            geom = buffered.getInfo()
            if geom and geom.get('type') in ('Polygon', 'MultiPolygon'):
                return geom
            if geom and geom.get('type') == 'Feature':
                return geom.get('geometry')
            return geom
        except Exception:
            return None

    def _fc_union_geojson(fc):
        """
        Unión real de todas las geometrías de la FC → para visualizar en mapa.
        Retorna dict GeoJSON o None.
        """
        try:
            n = fc.size().getInfo()
            if n == 0:
                return None
            geom = fc.geometry().getInfo()
            if geom and geom.get('type') in ('Polygon', 'MultiPolygon',
                                              'GeometryCollection'):
                return geom
            if geom and geom.get('type') == 'Feature':
                return geom.get('geometry')
            return geom
        except Exception:
            return None

    def _geom_to_geojson(ee_geom_obj):
        """Convierte ee.Geometry a dict GeoJSON. Retorna None si falla."""
        try:
            geom = ee_geom_obj.bounds().getInfo()
            if geom and geom.get('type') in ('Polygon', 'MultiPolygon'):
                return geom
            if geom and geom.get('type') == 'Feature':
                return geom.get('geometry')
            return geom
        except Exception:
            return None

    def clasificar_y_resumir(fc, geom_busqueda):
        conservar_fc = fc.filter(ee.Filter.eq('GRADO_TRAN', 'Natural'))
        restaurar_fc = fc.filter(ee.Filter.eq('GRADO_TRAN', 'Transformado'))

        n = fc.size().getInfo()
        ha_conservar = conservar_fc.aggregate_sum('area_ha_real').getInfo() if n > 0 else 0.0
        ha_restaurar = restaurar_fc.aggregate_sum('area_ha_real').getInfo() if n > 0 else 0.0
        ha_conservar = float(ha_conservar) if ha_conservar is not None else 0.0
        ha_restaurar = float(ha_restaurar) if ha_restaurar is not None else 0.0

        return {
            'ha_conservar':      ha_conservar,
            'ha_restaurar':      ha_restaurar,
            'total':             ha_conservar + ha_restaurar,
            # Para GBIF: buffer 10 km del centroide (zona manejable)
            'geom_conservar':    _centroid_buffer_geojson(conservar_fc, 10000),
            'geom_restaurar':    _centroid_buffer_geojson(restaurar_fc, 10000),
            # Para el mapa: bbox del área de búsqueda
            'geom_total':        _geom_to_geojson(geom_busqueda),
            # Para el mapa: geometría real de las features (polígonos reales)
            'geom_conservar_ee': _fc_union_geojson(conservar_fc),
            'geom_restaurar_ee': _fc_union_geojson(restaurar_fc),
            'geom_runap_ee':     _geom_to_geojson(sinap.filterBounds(geom_busqueda).geometry()),
        }

    r1 = filtrar_candidatas(geom_mun, bioma_impacto)
    r2 = filtrar_candidatas(geom_szh, bioma_impacto)
    r3 = filtrar_candidatas(geom_zh,  bioma_impacto)
    r4 = filtrar_candidatas(geom_mun, bioma_impacto, es_otro_bioma=True)
    r5 = filtrar_candidatas(geom_szh, bioma_impacto, es_otro_bioma=True)
    r6 = filtrar_candidatas(geom_zh,  bioma_impacto, es_otro_bioma=True)

    return {
        'Rango 1': clasificar_y_resumir(r1, geom_mun),
        'Rango 2': clasificar_y_resumir(r2, geom_szh),
        'Rango 3': clasificar_y_resumir(r3, geom_zh),
        'Rango 4': clasificar_y_resumir(r4, geom_mun),
        'Rango 5': clasificar_y_resumir(r5, geom_szh),
        'Rango 6': clasificar_y_resumir(r6, geom_zh),
    }
