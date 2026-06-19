# -*- coding: utf-8 -*-
"""
Módulo de contexto geográfico.
Cruza el polígono de impacto con assets de GEE para obtener:
  - Municipio, Departamento
  - BIOMA-IAvH
  - Zona Hidrográfica (ZH), Subzona (SZH)
  - Áreas por cobertura (IDEAM)
  - Tasa BAU de pérdida de bosque (Hansen) — por municipio, SZH y ZH
"""
import ee
import time
from shapely.geometry import mapping
from shapely.ops import transform
from config import settings

HANSEN_DATASET           = 'UMD/hansen/global_forest_change_2025_v1_13'
HANSEN_ANIOS_OBSERVACION = 25
TREECOVER_UMBRAL         = 30


def obtener_contexto_impacto(gdf):
    """
    Obtiene contexto geográfico completo del polígono de impacto.
    Usa el mínimo de llamadas .getInfo() posible para evitar Too Many Requests.
    """
    # ─── Preparar geometría ────────────────────────────────────────
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    else:
        gdf = gdf.to_crs("EPSG:4326")

    def strip_z(geom):
        return transform(lambda x, y, z=None: (x, y), geom)
    gdf['geometry'] = gdf['geometry'].apply(strip_z)

    features = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom.is_empty:
            continue
        features.append(ee.Feature(ee.Geometry(mapping(geom))))
    fc      = ee.FeatureCollection(features)
    ee_geom = fc.geometry()

    # ─── Assets ───────────────────────────────────────────────────
    municipios  = ee.FeatureCollection(settings.GEE_ASSETS['municipios'])
    zh_col      = ee.FeatureCollection(settings.GEE_ASSETS['zh'])
    ecosistemas = ee.FeatureCollection(settings.GEE_ASSETS['ecosistemas'])

    # ─── Municipio: el que tenga MAYOR área de intersección con el polígono
    # filterBounds().first() es no-determinístico cuando el polígono cruza
    # límites municipales — se selecciona por área para evitar falsos positivos.
    mun_candidatos = municipios.filterBounds(ee_geom).map(
        lambda f: f.set(
            'area_interseccion',
            f.geometry().intersection(ee_geom, ee.ErrorMargin(1)).area()
        )
    )
    mun_first = mun_candidatos.sort('area_interseccion', False).first()

    # ─── ZH/SZH: igual — mayor intersección
    zh_candidatos = zh_col.filterBounds(ee_geom).map(
        lambda f: f.set(
            'area_interseccion',
            f.geometry().intersection(ee_geom, ee.ErrorMargin(1)).area()
        )
    )
    zh_first = zh_candidatos.sort('area_interseccion', False).first()

    # ─── Ecosistemas recortados al área de impacto ─────────────────
    eco_impacto = ecosistemas.filterBounds(ee_geom).map(
        lambda f: f.setGeometry(
            f.geometry().intersection(ee_geom, 1)
        ).set(
            'area_ha',
            f.geometry().intersection(ee_geom, 1).area().divide(10000)
        )
    )

    # ─── LLAMADA 1 — contexto geográfico completo en un solo getInfo
    # Municipio + Depto + ZH + SZH + Bioma + Coberturas
    ctx_dict = ee.Dictionary({
        'municipio':  mun_first.get('ADM2_NAME'),
        'depto':      mun_first.get('ADM1_NAME'),
        'nom_zh':     zh_first.get('nom_zh'),
        'nom_szh':    zh_first.get('nom_szh'),
        'biomas':     eco_impacto.reduceColumns(
                          ee.Reducer.frequencyHistogram(), ['BIOMA_IAvH']
                      ).get('histogram'),
        'coberturas': eco_impacto.reduceColumns(
                          ee.Reducer.sum().group(1, 'COBERTURA'),
                          ['area_ha', 'COBERTURA']
                      ).get('groups'),
    })

    time.sleep(1)
    ctx_info = ctx_dict.getInfo()

    # ─── Parsear resultados ────────────────────────────────────────
    municipio    = ctx_info.get('municipio', 'Desconocido')
    departamento = ctx_info.get('depto', 'Desconocido')
    nom_zh       = ctx_info.get('nom_zh', 'Desconocido')
    nom_szh      = ctx_info.get('nom_szh', 'Desconocido')

    biomas_hist     = ctx_info.get('biomas') or {}
    bioma_principal = (
        max(biomas_hist, key=biomas_hist.get)
        if biomas_hist else 'Desconocido'
    )

    areas_cobertura = {}
    for group in (ctx_info.get('coberturas') or []):
        areas_cobertura[group['COBERTURA']] = group['sum']

    # ─── LLAMADA 2 — geometría del municipio para Hansen ──────────
    time.sleep(1)
    municipio_geom = municipios.filter(
        ee.Filter.eq('ADM2_NAME', municipio)
    ).first().geometry()

    # ─── LLAMADA 3 — geometría de la SZH para Hansen ──────────────
    # Usa first() porque cada SZH es un solo feature en el asset de ZH
    time.sleep(1)
    szh_geom = zh_col.filter(
        ee.Filter.eq('nom_szh', nom_szh)
    ).first().geometry()

    # ─── LLAMADA 4 — geometría de la ZH para Hansen ───────────────
    # Una ZH puede tener múltiples features (varias SZH) → dissolve
    time.sleep(1)
    zh_geom = zh_col.filter(
        ee.Filter.eq('nom_zh', nom_zh)
    ).geometry().dissolve(1)

    # ─── LLAMADA 5 — Hansen BAU por municipio ─────────────────────
    time.sleep(1)
    tasa_bau_mun, fuente_bau_mun = _calcular_tasa_bau(
        municipio_geom, municipio
    )

    # ─── LLAMADA 6 — Hansen BAU por SZH ───────────────────────────
    time.sleep(1)
    tasa_bau_szh, fuente_bau_szh = _calcular_tasa_bau(
        szh_geom, f"SZH {nom_szh}"
    )

    # ─── LLAMADA 7 — Hansen BAU por ZH ────────────────────────────
    time.sleep(1)
    tasa_bau_zh, fuente_bau_zh = _calcular_tasa_bau(
        zh_geom, f"ZH {nom_zh}"
    )

    return {
        'municipio':            municipio,
        'departamento':         departamento,
        'zh':                   nom_zh,
        'szh':                  nom_szh,
        'bioma_principal':      bioma_principal,
        'areas_cobertura':      areas_cobertura,
        # Tasa BAU por municipio (R1, R4)
        'tasa_bau':             tasa_bau_mun,
        'tasa_bau_fuente':      fuente_bau_mun,
        # Tasa BAU por SZH (R2, R5)
        'tasa_bau_szh':         tasa_bau_szh,
        'tasa_bau_szh_fuente':  fuente_bau_szh,
        # Tasa BAU por ZH (R3, R6)
        'tasa_bau_zh':          tasa_bau_zh,
        'tasa_bau_zh_fuente':   fuente_bau_zh,
    }


def _calcular_tasa_bau(geom, nombre):
    """
    Calcula tasa BAU con Hansen GFC sobre cualquier geometría de GEE.
    Consolida los dos reduceRegion en una sola llamada getInfo.

    Args:
        geom:   ee.Geometry — puede ser municipio, SZH o ZH
        nombre: str — nombre descriptivo para el mensaje de fuente/error
    """
    try:
        hansen      = ee.Image(HANSEN_DATASET)
        treecover   = hansen.select('treecover2000')
        loss        = hansen.select('loss')
        bosque_2000 = treecover.gt(TREECOVER_UMBRAL)
        perdida     = loss.And(bosque_2000)
        area_px_ha  = ee.Image.pixelArea().divide(10000)

        # Dos reducers en una sola imagen multibanda → 1 getInfo
        combined = (
            bosque_2000.multiply(area_px_ha).rename('bosque')
            .addBands(perdida.multiply(area_px_ha).rename('perdida'))
        )

        resultado = combined.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geom,
            scale=30,
            maxPixels=1e10,
            bestEffort=True
        ).getInfo()

        bosque_total  = float(resultado.get('bosque')  or 0)
        perdida_total = float(resultado.get('perdida') or 0)

        if bosque_total < 1000:
            return (
                0.005,
                f"{nombre}: bosque insuficiente ({bosque_total:.0f} ha en 2000). "
                f"Usando tasa estimada 0.5%."
            )

        tasa   = perdida_total / (bosque_total * HANSEN_ANIOS_OBSERVACION)
        fuente = (
            f"Hansen GFC 2001-2025 sobre {nombre}: "
            f"{bosque_total:,.0f} ha bosque inicial, "
            f"{perdida_total:,.0f} ha perdidas en {HANSEN_ANIOS_OBSERVACION} años."
        )
        return (tasa, fuente)

    except Exception as e:
        return (
            0.005,
            f"Error calculando Hansen para {nombre} ({str(e)[:80]}). "
            f"Usando 0.5% fallback."
        )
