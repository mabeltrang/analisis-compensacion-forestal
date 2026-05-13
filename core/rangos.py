# -*- coding: utf-8 -*-
import ee
from shapely.geometry import mapping
from shapely.ops import transform
from config import settings


def construir_areas_candidatas(gdf, contexto):
    """
    Construye las áreas candidatas para los 5 rangos en GEE.
    Calcula áreas reales mediante intersección.
    Retorna también las geometrías de cada rango como GeoJSON
    para poder consultarlas en GBIF.
    """

    # Limpieza Crítica: Quitar coordenadas Z que rompen GEE
    def strip_z(geom):
        return transform(lambda x, y, z=None: (x, y), geom)

    gdf_2d = gdf.copy()
    gdf_2d['geometry'] = gdf_2d['geometry'].apply(strip_z)

    features = []
    for _, row in gdf_2d.iterrows():
        if row.geometry.is_empty:
            continue
        features.append(ee.Feature(ee.Geometry(mapping(row.geometry))))

    ee_geom = ee.FeatureCollection(features).geometry()
    bioma_impacto = contexto['bioma_principal']
    mun_nombre    = contexto['municipio']
    szh_nombre    = contexto['szh']
    zh_nombre     = contexto['zh']

    # Assets
    ecosistemas = ee.FeatureCollection(settings.GEE_ASSETS['ecosistemas'])
    municipios  = ee.FeatureCollection(settings.GEE_ASSETS['municipios'])
    zh_col      = ee.FeatureCollection(settings.GEE_ASSETS['zh'])
    sinap       = ee.FeatureCollection(settings.GEE_ASSETS['sinap'])

    # Geometrías de búsqueda — las guardamos para retornarlas
    geom_mun = municipios.filter(ee.Filter.eq('ADM2_NAME', mun_nombre)).geometry()
    geom_szh = zh_col.filter(ee.Filter.eq('nom_szh', szh_nombre)).geometry()
    geom_zh  = zh_col.filter(ee.Filter.eq('nom_zh', zh_nombre)).geometry()

    def filtrar_candidatas(area_busqueda, filtro_bioma, es_otro_bioma=False):
        candidatas = ecosistemas.filterBounds(area_busqueda)

        if es_otro_bioma:
            candidatas = candidatas.filter(ee.Filter.neq('BIOMA_IAvH', filtro_bioma))
        else:
            candidatas = candidatas.filter(ee.Filter.eq('BIOMA_IAvH', filtro_bioma))

        for cob in settings.COBERTURAS_EXCLUIDAS:
            candidatas = candidatas.filter(ee.Filter.neq('COBERTURA', cob))

        sinap_geom = sinap.filterBounds(area_busqueda).geometry()

        def procesar_geometria(f):
            geom_int   = f.geometry().intersection(area_busqueda, 1)
            geom_final = geom_int.difference(sinap_geom, 1)
            area_ha    = geom_final.area().divide(10000)
            return f.setGeometry(geom_final).set('area_ha_real', area_ha)

        procesados = (
            candidatas
            .map(procesar_geometria)
            .filter(ee.Filter.gt('area_ha_real', 0.01))
        )
        return procesados

    # Construir candidatas por rango
    r1 = filtrar_candidatas(geom_mun, bioma_impacto)
    r2 = filtrar_candidatas(geom_szh, bioma_impacto)
    r3 = filtrar_candidatas(geom_zh,  bioma_impacto)
    r4 = filtrar_candidatas(geom_mun, bioma_impacto, es_otro_bioma=True)
    r5 = filtrar_candidatas(geom_szh, bioma_impacto, es_otro_bioma=True)

    def clasificar_y_resumir(fc, geom_busqueda):
        """
        Suma ha_conservar y ha_restaurar según GRADO_TRAN.
        También retorna el bounding box de la geometría de búsqueda
        en formato GeoJSON para consultas GBIF posteriores.
        """
        conservar = fc.filter(ee.Filter.eq('GRADO_TRAN', 'Natural'))
        restaurar = fc.filter(ee.Filter.eq('GRADO_TRAN', 'Transformado'))

        n = fc.size().getInfo()
        ha_conservar = conservar.aggregate_sum('area_ha_real').getInfo() if n > 0 else 0
        ha_restaurar = restaurar.aggregate_sum('area_ha_real').getInfo() if n > 0 else 0

        # Extraer bounds de la geometría de búsqueda como GeoJSON
        # Usamos bounds() para obtener un rectángulo simple — más liviano para GBIF
        try:
            geom_geojson = geom_busqueda.bounds().getInfo()
        except Exception:
            geom_geojson = None

        return {
            'ha_conservar':  float(ha_conservar),
            'ha_restaurar':  float(ha_restaurar),
            'total':         float(ha_conservar + ha_restaurar),
            'geom_geojson':  geom_geojson,   # GeoJSON del área de búsqueda del rango
        }

    return {
        'Rango 1': clasificar_y_resumir(r1, geom_mun),
        'Rango 2': clasificar_y_resumir(r2, geom_szh),
        'Rango 3': clasificar_y_resumir(r3, geom_zh),
        'Rango 4': clasificar_y_resumir(r4, geom_mun),
        'Rango 5': clasificar_y_resumir(r5, geom_szh),
    }
