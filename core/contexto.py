# -*- coding: utf-8 -*-
"""
Módulo de contexto geográfico.

Cruza el polígono de impacto con assets de GEE para obtener:
  - Municipio, Departamento
  - BIOMA-IAvH
  - Zona Hidrográfica (ZH), Subzona (SZH)
  - Áreas por cobertura (IDEAM)
  - Tasa BAU de pérdida de bosque (Hansen) — por municipio
"""
import ee
import json
from shapely.geometry import shape, mapping
from shapely.ops import transform
from config import settings


# Hansen Global Forest Change v1.12 (datos 2000-2024)
HANSEN_DATASET = 'UMD/hansen/global_forest_change_2024_v1_12'
HANSEN_ANIOS_OBSERVACION = 24  # 2001-2024 (loss del año 2001 hasta 2024)
TREECOVER_UMBRAL = 30  # % canopy para considerar "bosque" (estándar internacional)


def obtener_contexto_impacto(gdf):
    """
    Obtiene contexto geográfico completo del polígono de impacto.

    Retorna dict con:
        municipio, departamento, zh, szh, bioma_principal,
        areas_cobertura, tasa_bau (anual), tasa_bau_fuente
    """
    # ─── Preparar geometría ────────────────────────────────────────
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    else:
        gdf = gdf.to_crs("EPSG:4326")

    # Quitar coordenadas Z (rompen GEE)
    def strip_z(geom):
        return transform(lambda x, y, z=None: (x, y), geom)
    gdf['geometry'] = gdf['geometry'].apply(strip_z)

    # Convertir a ee.FeatureCollection
    features = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom.is_empty:
            continue
        features.append(ee.Feature(ee.Geometry(mapping(geom))))
    fc = ee.FeatureCollection(features)
    ee_geom = fc.geometry()

    # ─── 1. Cruzar con Municipios ──────────────────────────────────
    municipios = ee.FeatureCollection(settings.GEE_ASSETS['municipios'])
    mun_intersect = municipios.filterBounds(ee_geom)
    mun_first = mun_intersect.first()
    mun_data = mun_first.toDictionary().select(['ADM2_NAME', 'ADM1_NAME']).getInfo()
    municipio_geom = mun_first.geometry()  # geometría del municipio para BAU

    # ─── 2. Cruzar con ZH ──────────────────────────────────────────
    zh_col = ee.FeatureCollection(settings.GEE_ASSETS['zh'])
    zh_intersect = zh_col.filterBounds(ee_geom)
    zh_data = zh_intersect.first().toDictionary().select(['nom_zh', 'nom_szh']).getInfo()

    # ─── 3. Cruzar con Ecosistemas (BIOMA-IAvH) ────────────────────
    ecosistemas = ee.FeatureCollection(settings.GEE_ASSETS['ecosistemas'])
    eco_impacto = ecosistemas.filterBounds(ee_geom).map(
        lambda f: f.setGeometry(f.geometry().intersection(ee_geom, 1))
    )
    bioma_data = eco_impacto.reduceColumns(
        ee.Reducer.frequencyHistogram(), ['BIOMA_IAvH']
    ).getInfo()
    biomas_hist = bioma_data['histogram']
    bioma_principal = max(biomas_hist, key=biomas_hist.get) if biomas_hist else "Desconocido"

    # ─── 4. Áreas por cobertura ────────────────────────────────────
    eco_info = eco_impacto.map(lambda f: f.set('area_ha', f.area().divide(10000)))
    stats = eco_info.reduceColumns(
        ee.Reducer.sum().group(1, 'COBERTURA'),
        ['area_ha', 'COBERTURA']
    ).getInfo()
    areas_cobertura = {}
    for group in stats['groups']:
        areas_cobertura[group['COBERTURA']] = group['sum']

    # ─── 5. TASA BAU — Pérdida anual de bosque (Hansen) ────────────
    tasa_bau, fuente_bau = _calcular_tasa_bau(
        municipio_geom,
        mun_data.get('ADM2_NAME', 'Desconocido')
    )

    return {
        'municipio': mun_data.get('ADM2_NAME'),
        'departamento': mun_data.get('ADM1_NAME'),
        'zh': zh_data.get('nom_zh'),
        'szh': zh_data.get('nom_szh'),
        'ah': zh_data.get('nom_ah'),
        'bioma_principal': bioma_principal,
        'areas_cobertura': areas_cobertura,
        'tasa_bau': tasa_bau,
        'tasa_bau_fuente': fuente_bau
    }


def _calcular_tasa_bau(geom_municipio, nombre_municipio):
    """
    Calcula la tasa anual de pérdida de bosque (BAU) sobre el municipio
    usando Hansen Global Forest Change.

    Lógica:
      1. Bosque año 2000 (umbral 30% canopy)
      2. Pérdida acumulada 2001-2024
      3. Tasa anual = pérdida_total / (bosque_2000 × años_observación)

    Si el municipio tiene poco bosque (<1000 ha), usa tasa departamental
    estimada fallback de 0.5%.

    Retorna: (tasa_anual_decimal, fuente_str)
        Ej: (0.0062, "Hansen 2001-2024 sobre municipio Bosconia: 5230 ha bosque, 78 ha perdidas")
    """
    try:
        hansen = ee.Image(HANSEN_DATASET)
        treecover = hansen.select('treecover2000')
        loss = hansen.select('loss')

        # Bosque inicial (binario: 1 si >umbral, 0 si no)
        bosque_2000 = treecover.gt(TREECOVER_UMBRAL)

        # Pérdida solo sobre lo que era bosque
        perdida_bosque = loss.And(bosque_2000)

        # Áreas en ha
        area_pixel_ha = ee.Image.pixelArea().divide(10000)

        bosque_ha_img = bosque_2000.multiply(area_pixel_ha)
        perdida_ha_img = perdida_bosque.multiply(area_pixel_ha)

        # Reducir sobre el municipio
        bosque_total = bosque_ha_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geom_municipio,
            scale=30,
            maxPixels=1e10,
            bestEffort=True
        ).get('treecover2000').getInfo()

        perdida_total = perdida_ha_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geom_municipio,
            scale=30,
            maxPixels=1e10,
            bestEffort=True
        ).get('loss').getInfo()

        bosque_total = float(bosque_total or 0)
        perdida_total = float(perdida_total or 0)

        # Si bosque inicial muy bajo, no es confiable
        if bosque_total < 1000:
            return (
                0.005,  # fallback 0.5%
                f"Municipio con poco bosque ({bosque_total:.0f} ha en 2000). "
                f"Usando tasa departamental estimada 0.5%."
            )

        # Tasa anual promedio
        tasa = perdida_total / (bosque_total * HANSEN_ANIOS_OBSERVACION)
        fuente = (
            f"Hansen GFC 2001-2024 sobre {nombre_municipio}: "
            f"{bosque_total:,.0f} ha bosque inicial, "
            f"{perdida_total:,.0f} ha perdidas en {HANSEN_ANIOS_OBSERVACION} años."
        )
        return (tasa, fuente)

    except Exception as e:
        # Si falla, usar fallback
        return (
            0.005,
            f"Error calculando Hansen ({str(e)[:80]}). Usando 0.5% fallback."
        )
