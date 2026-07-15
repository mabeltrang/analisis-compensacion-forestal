# -*- coding: utf-8 -*-
"""
Iniciativas de conservación cercanas al proyecto (RUNAP, REAA, OMEC, BST,
Reservas Forestales Ley 2a, Portafolio CAR) — corre en vivo desde la app
usando earthengine-api. Port del extraerIniciativas() del script GEE
(analisis-compensacion-forestal, sección 5 y 2 del .js).

No hace exportación a Drive ni CSV manual: se llama directamente con las
geometrías de municipio/SZH que ya calcula contexto.obtener_contexto_impacto(),
y se muestra en la app.

DEDUPLICACIÓN
--------------
OMEC y REAA en el asset fuente vienen "disueltas" por combinación única de
capas de zonificación superpuestas — por eso una misma figura aparece varias
veces con 'nombre' = 'Omec', 'Omec,PDET', 'Omec,Humedales V3', etc. Esas NO
son iniciativas distintas, son la misma capa con distintas superposiciones.
deduplicar_iniciativas() las colapsa en una sola fila por (nivel, figura,
categoria) mostrando el set único de tags. Las figuras con nombre propio
(RUNAP, Reserva Forestal, BST, Portafolio CAR) se dejan intactas — ya vienen
deduplicadas de verdad por el .distinct() que se aplica en GEE.
"""
import ee
import pandas as pd
from config import settings

# Figuras cuyo campo 'nombre' es una concatenación de tags de zonificación
# superpuesta (no un nombre propio) → se colapsan agresivamente.
_FIGURAS_COMBO = {'REAA', 'OMEC'}


def _mapper_simple(nivel_label, figura, campo_nombre, campo_categoria, entidad):
    """Genera la función de mapeo Feature -> {nivel, figura, nombre, categoria, entidad}."""
    def _mapear(f):
        return ee.Feature(None, {
            'nivel':     nivel_label,
            'figura':    figura,
            'nombre':    f.get(campo_nombre),
            'categoria': f.get(campo_categoria),
            'entidad':   entidad,
        })
    return _mapear


def _extraer_nivel(geom, nivel_label, car_detectada=None, config_portafolio=None):
    """Port 1:1 de extraerIniciativas(geom, nivelLabel) del script JS."""

    runap = (ee.FeatureCollection(settings.GEE_ASSETS['runap'])
             .filterBounds(geom)
             .map(_mapper_simple(nivel_label, 'Area Protegida SINAP',
                                  'ap_nombre', 'ap_categor', 'MADS / PNN Colombia')))

    reaa = (ee.FeatureCollection(settings.GEE_ASSETS['reaa_excluir'])
            .filterBounds(geom)
            .map(_mapper_simple(nivel_label, 'REAA', 'nombre_cap', 'aa', 'MADS')))

    omec = (ee.FeatureCollection(settings.GEE_ASSETS['omec'])
            .filterBounds(geom)
            .map(_mapper_simple(nivel_label, 'OMEC', 'nombre_cap', 'aa', 'MADS')))

    def _mapear_bst(f):
        return ee.Feature(None, {
            'nivel':     nivel_label,
            'figura':    'Ecosistema Prioritario',
            'nombre':    ee.String('Bosque Seco Tropical - ').cat(ee.String(f.get('Region'))),
            'categoria': 'Bosque Seco Tropical',
            'entidad':   'IAvH',
        })
    bst = ee.FeatureCollection(settings.GEE_ASSETS['bst']).filterBounds(geom).map(_mapear_bst)

    reservas = (ee.FeatureCollection(settings.GEE_ASSETS['reservas_forestales'])
                .filterBounds(geom)
                .map(_mapper_simple(nivel_label, 'Reserva Forestal Ley 2a',
                                     'name', 'category', 'MADS')))

    base = runap.merge(reaa).merge(omec).merge(bst).merge(reservas)

    if config_portafolio is not None:
        cfg = config_portafolio

        def _mapear_cra(f):
            return ee.Feature(None, {
                'nivel':     nivel_label,
                'figura':    ee.String('Portafolio ' + car_detectada + ' - ')
                                .cat(ee.String(f.get(cfg['campo_esc']))),
                'nombre':    f.get('AccRegDesc'),
                'categoria': f.get(cfg['campo_acc']),
                'entidad':   car_detectada,
            })

        cra = (ee.FeatureCollection(cfg['asset'])
               .filterBounds(geom)
               .filter(ee.Filter.inList(cfg['campo_esc'],
                                         ['Escenario I', 'Escenario II', 'Escenario III']))
               .distinct(['AccRegDesc'])
               .map(_mapear_cra))
        base = base.merge(cra)

    return base.distinct(['figura', 'nombre', 'categoria'])


def obtener_iniciativas(ctx):
    """
    Punto de entrada — se le pasa el ctx que ya devuelve
    contexto.obtener_contexto_impacto() (necesita 'municipio_geom',
    'szh_geom', 'municipio', 'szh' y opcionalmente 'departamento').

    Hace UNA sola llamada .getInfo() (municipio + SZH combinados) para no
    multiplicar la latencia de red — igual que ctx_dict.getInfo() en
    contexto.py.

    Retorna una lista de dicts: [{nivel, figura, nombre, categoria, entidad}, ...]
    """
    departamento = ctx.get('departamento')
    car_detectada, config_portafolio = None, None
    for car, cfg in settings.PORTAFOLIOS_CAR.items():
        if departamento in cfg['deptos']:
            car_detectada, config_portafolio = car, cfg
            break

    fc_municipio = _extraer_nivel(
        ctx['municipio_geom'], f"Municipio - {ctx.get('municipio', 'n/d')}",
        car_detectada, config_portafolio
    )
    fc_szh = _extraer_nivel(
        ctx['szh_geom'], f"SZH - {ctx.get('szh', 'n/d')}",
        car_detectada, config_portafolio
    )

    fc_total = fc_municipio.merge(fc_szh)
    info = fc_total.getInfo()
    return [f['properties'] for f in info.get('features', [])]


def _nivel_tipo(nivel_label):
    """'Municipio - Gamarra' -> 'Municipio' ; 'SZH - Quebrada X' -> 'SZH'."""
    return nivel_label.split(' - ', 1)[0]


def deduplicar_iniciativas(filas):
    """
    Versión simplificada al máximo: colapsa TANTO los combos OMEC/REAA
    COMO los niveles (Municipio/SZH). Como el municipio está contenido
    dentro de la SZH, casi todo lo que sale a nivel Municipio vuelve a
    salir a nivel SZH — mostrarlo dos veces es ruido, no información nueva.

    En vez de una fila por nivel, cada iniciativa aparece UNA sola vez con
    una columna 'niveles' que dice en cuáles jerarquías se encontró
    (ej. 'Municipio, SZH' o solo 'SZH' si es exclusiva de esa zona).

    Retorna un DataFrame con columnas: figura, categoria, nombre, entidad, niveles.
    """
    df = pd.DataFrame(filas)
    if df.empty:
        return df

    df['nivel_tipo'] = df['nivel'].map(_nivel_tipo)
    es_combo = df['figura'].isin(_FIGURAS_COMBO)

    # ── Figuras con nombre propio (RUNAP, Reserva Forestal, BST, CAR) ──
    # Se colapsan por (figura, categoria, nombre) ignorando el nivel;
    # 'niveles' junta en qué jerarquías apareció cada una.
    filas_propias = []
    for (figura, categoria, nombre), grupo in df[~es_combo].groupby(
        ['figura', 'categoria', 'nombre']
    ):
        niveles = sorted(set(grupo['nivel_tipo']), key=lambda x: (x != 'Municipio', x))
        filas_propias.append({
            'figura':    figura,
            'categoria': categoria,
            'nombre':    nombre,
            'entidad':   grupo['entidad'].iloc[0],
            'niveles':   ', '.join(niveles),
        })

    # ── OMEC/REAA: colapsar también los tags, ahora across niveles ──
    filas_combo = []
    for (figura, categoria), grupo in df[es_combo].groupby(['figura', 'categoria']):
        tags = set()
        for nombre in grupo['nombre'].dropna():
            tags.update(t.strip() for t in str(nombre).split(',') if t.strip())
        niveles = sorted(set(grupo['nivel_tipo']), key=lambda x: (x != 'Municipio', x))
        filas_combo.append({
            'figura':    figura,
            'categoria': categoria,
            'nombre':    ', '.join(sorted(tags)),
            'entidad':   grupo['entidad'].iloc[0],
            'niveles':   ', '.join(niveles),
        })

    cols = ['figura', 'categoria', 'nombre', 'entidad', 'niveles']
    resultado = pd.DataFrame(filas_propias + filas_combo, columns=cols)
    return resultado.sort_values(['figura', 'categoria']).reset_index(drop=True)
