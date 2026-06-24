# -*- coding: utf-8 -*-
"""
inventario.py — Procesamiento del inventario forestal Unergy
Manual 2026 (Res. 0305/2026 MADS)

Escenarios de Criterio B:
  - B_oficial : solo Res. 0126/2024 MADS  (CR=1.0, EN=0.6, VU=0.4)
  - B_cites   : max(B_oficial, equivalencia CITES)  — escenario Unergy
  - B_uicn    : max(B_oficial, categoría UICN)      — escenario Unergy

Matching de especies:
  1. Especie exacta en cada fuente
  2. Nombre indeterminado (sp./spp.) → peor categoría del género (MADS y CITES)
  3. Especie determinada sin match   → LC / None
"""

import os
import csv
import unicodedata
import pandas as pd
import numpy as np
from collections import defaultdict
from . import utils
from config import settings
from config.vedas import consultar_veda


def _norm(s):
    """Normaliza string: sin tildes, minúsculas, sin espacios extra."""
    s = str(s)
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    return s.lower().strip()


_SP_SUFIJOS = {'sp', 'sp.', 'spp', 'spp.', 'sp1', 'sp2', 'sp3'}


def _es_indeterminado(nombre_norm: str) -> bool:
    """True si el nombre es género + sufijo sp/spp (indeterminado)."""
    partes = nombre_norm.strip().split()
    return len(partes) == 2 and partes[1].lower() in _SP_SUFIJOS


# ── Mapa de categorías UICN (texto completo → código) ────────────────────────
_UICN_MAP = {
    'critically endangered':              'CR',
    'endangered':                         'EN',
    'vulnerable':                         'VU',
    'near threatened':                    'NT',
    'lower risk/near threatened':         'NT',
    'lower risk/conservation dependent':  'LC',
    'lower risk/least concern':           'LC',
    'least concern':                      'LC',
    'data deficient':                     'DD',
    'extinct in the wild':                'EW',
    'extinct':                            'EX',
}

# Orden de restricción para elegir el más restrictivo ante duplicados
_CAT_ORDER  = {'CR': 6, 'EN': 5, 'VU': 4, 'NT': 3, 'LC': 2, 'DD': 1, 'EW': 7, 'EX': 8}
_CITES_ORD  = {'I': 0, 'II': 1, 'III': 2}


def _cargar_indices(car: str = ""):
    """
    Carga los tres índices de amenaza desde sus archivos fuente separados.

    MADS  → config/especies_amenazadas_co.csv   (Res. 0126/2024)
    CITES → config/Listado_CITES.csv            (Genus+Species separados)
    UICN  → config/Listado_UICN.csv             (scientificName binomial)

    Retorna
    -------
    amenaza_exact  : {nombre_norm: cat_mads}
    amenaza_genero : {genero_norm: cat_mads}   # fallback sp. indeterminados
    cites_exact    : {nombre_norm: apendice}
    cites_genero   : {genero_norm: apendice}   # fallback si no hay especie propia
    uicn_exact     : {binomial_norm: cat_uicn}
    """
    # ── MADS ─────────────────────────────────────────────────────────────────
    amenaza_exact  = {}
    amenaza_genero = defaultdict(lambda: 'LC')

    try:
        ea = pd.read_csv(os.path.join(settings.CONFIG_DIR, "especies_amenazadas_co.csv"))
        ea.columns = [_norm(c) for c in ea.columns]
        col_nombre = next((c for c in ea.columns if 'nombre' in c and 'cientifico' in c.replace(' ', '')), None)
        col_cat    = next((c for c in ea.columns if 'categoria' in c and 'amenaza' in c.replace(' ', '')), None)
        if col_nombre and col_cat:
            for _, r in ea.iterrows():
                nombre = _norm(str(r[col_nombre]))
                cat    = str(r[col_cat]).strip()
                if nombre and cat:
                    amenaza_exact[nombre] = cat
                    gen = nombre.split()[0]
                    if _CAT_ORDER.get(cat, 0) > _CAT_ORDER.get(amenaza_genero[gen], 0):
                        amenaza_genero[gen] = cat
    except Exception as e:
        print(f"[inventario] No se pudo cargar MADS CSV: {e}")

    # ── CITES ─────────────────────────────────────────────────────────────────
    # Listado_CITES.csv tiene Genus y Species en columnas separadas.
    # RankName: SPECIES/SUBSPECIES → índice exacto; GENUS → fallback de género.
    # CurrentListing puede ser 'I/II' → se toma el más restrictivo.
    cites_exact  = {}
    cites_genero = {}

    try:
        with open(os.path.join(settings.CONFIG_DIR, "Listado_CITES.csv"),
                  newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rank    = row.get('RankName', '').strip().upper()
                genus   = _norm(row.get('Genus',   ''))
                species = _norm(row.get('Species', ''))
                listing = row.get('CurrentListing', '').strip()

                # Extraer el apéndice más restrictivo (ej. 'I/II' → 'I')
                partes = [p.strip() for p in listing.replace('NC', '').split('/')
                          if p.strip() in _CITES_ORD]
                if not partes:
                    continue
                ap = sorted(partes, key=lambda x: _CITES_ORD[x])[0]

                if rank in ('SPECIES', 'SUBSPECIES') and genus and species:
                    nombre = f"{genus} {species}"
                    if nombre not in cites_exact or _CITES_ORD[ap] < _CITES_ORD[cites_exact[nombre]]:
                        cites_exact[nombre] = ap
                elif rank == 'GENUS' and genus:
                    if genus not in cites_genero or _CITES_ORD[ap] < _CITES_ORD[cites_genero[genus]]:
                        cites_genero[genus] = ap
    except Exception as e:
        print(f"[inventario] No se pudo cargar CITES CSV: {e}")

    # ── UICN ──────────────────────────────────────────────────────────────────
    # Listado_UICN.csv: scientificName es binomial directo (dos palabras).
    # Si hay múltiples evaluaciones del mismo binomial, gana la más reciente
    # (último registro en el archivo).
    uicn_exact = {}

    try:
        with open(os.path.join(settings.CONFIG_DIR, "Listado_UICN.csv"),
                  newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                nombre_raw = row.get('scientificName', '').strip()
                cat_raw    = _norm(row.get('redlistCategory', ''))
                cat        = _UICN_MAP.get(cat_raw)
                if nombre_raw and cat:
                    # Solo binomial (primeras 2 palabras)
                    binomial = ' '.join(_norm(nombre_raw).split()[:2])
                    uicn_exact[binomial] = cat   # último gana (más reciente)
    except Exception as e:
        print(f"[inventario] No se pudo cargar UICN CSV: {e}")

    return amenaza_exact, amenaza_genero, cites_exact, cites_genero, uicn_exact


def procesar_inventario(excel_path, dap_min=settings.DAP_MIN_DEFAULT, car: str = ""):
    """
    Procesa el inventario forestal estándar de Unergy.
    Calcula N, S, SN, A, B_oficial, B_cites, B_uicn, C,
    FCAFU, FCAFU_cites y FCAFU_uicn por cobertura.

    Retorna dict: { cobertura: { ...métricas... } }
    """

    # ── Detectar fila de encabezado ──────────────────────────────────────────
    df_raw = pd.read_excel(excel_path, header=None)
    header_row = 0
    for i, row in df_raw.iterrows():
        row_str = [str(x).lower() for x in row.values]
        if any('cobertura' in s for s in row_str) or \
           any('nombre cientifico' in s or 'nombre_cientifico' in s for s in row_str):
            header_row = i
            break

    df = pd.read_excel(excel_path, header=header_row)
    df.columns = [_norm(c) for c in df.columns]

    # ── Mapeo de columnas ────────────────────────────────────────────────────
    col_map = {
        'nombre cientifico': [
            'nombre cientifico', 'nombre_cientifico',
            'nombre cientifico ', 'nombre_cientifico ',
            'nombre', 'sp', 'especie', 'species',
            'nombre sp', 'nombre_sp',
        ],
        'dap_m':     ['dap a (m)', 'dap a en metros', 'dap a (metros)', 'dap', 'dap_m', 'dap (m)'],
        'cobertura': ['cobertura', 'cobertura_id', 'tipo_cobertura', 'tipo cobertura'],
        'ab_total':  ['ab t (m2)', 'ab t en metros cuadrados', 'area basal total', 'ab_total', 'ab t'],
    }

    final_cols = {}
    for key, options in col_map.items():
        for opt in options:
            if _norm(opt) in df.columns:
                final_cols[key] = _norm(opt)
                break
        if key not in final_cols and key != 'ab_total':
            raise ValueError(
                f"No se encontró columna '{key}' en el inventario. "
                f"Buscadas: {options}. "
                f"Columnas disponibles: {list(df.columns)}"
            )

    # ── Limpieza ─────────────────────────────────────────────────────────────
    df['Nombre cientifico'] = (
        df[final_cols['nombre cientifico']]
        .fillna('').astype(str).str.strip().str.capitalize()
    )
    df['Cobertura'] = (
        df[final_cols['cobertura']]
        .fillna('').astype(str).str.strip()
    )
    df['DAP_cm'] = pd.to_numeric(df[final_cols['dap_m']], errors='coerce') * 100

    df_filtrado = df[
        (df['DAP_cm'] >= dap_min) &
        (df['Cobertura'] != '') &
        (df['Nombre cientifico'] != '')
    ].copy()

    if df_filtrado.empty:
        return {}

    # ── Cargar tablas de referencia ──────────────────────────────────────────
    coberturas_a = pd.read_csv(os.path.join(settings.CONFIG_DIR, "coberturas_a.csv"))
    tabla_c      = pd.read_csv(os.path.join(settings.CONFIG_DIR, "tabla_c.csv"))

    # ── Cargar índices MADS / CITES / UICN desde archivos separados ──────────
    amenaza_exact, amenaza_genero, cites_exact, cites_genero, uicn_exact = \
        _cargar_indices(car=car)

    # ── Función de lookup unificada ───────────────────────────────────────────
    def _lookup(nombre_sci):
        """
        Retorna (cat_mads, cites_ap, cat_uicn) para un nombre científico.

        MADS  : exacto → fallback género solo para sp./spp.
        CITES : exacto → fallback género (hereda listado del género CITES)
        UICN  : exacto binomial
        """
        n     = _norm(nombre_sci)
        gen   = n.split()[0] if n.split() else ''
        indet = _es_indeterminado(n)

        # MADS
        if n in amenaza_exact:
            cat_mads = amenaza_exact[n]
        elif indet:
            cat_mads = amenaza_genero[gen]
        else:
            cat_mads = 'LC'

        # CITES: especie exacta primero, luego fallback de género
        if n in cites_exact:
            cites_ap = cites_exact[n]
        else:
            cites_ap = cites_genero.get(gen, None)

        # UICN: solo binomial exacto
        binomial = ' '.join(n.split()[:2])
        cat_uicn = uicn_exact.get(binomial, None)

        return cat_mads, cites_ap, cat_uicn

    df_filtrado[['categoria_amenaza', 'cites_apendice', 'categoria_uicn']] = (
        df_filtrado['Nombre cientifico']
        .apply(lambda x: pd.Series(_lookup(x)))
    )

    # ── Valores numéricos B ───────────────────────────────────────────────────
    # B oficial (MADS)
    df_filtrado['valor_b_oficial'] = (
        df_filtrado['categoria_amenaza'].map(settings.AMENAZA_VALORES).fillna(0.0)
    )

    # B CITES: max(B_oficial, valor CITES)
    def _b_cites(row):
        v  = row['valor_b_oficial']
        ap = row['cites_apendice']
        if ap and str(ap) not in ('nan', 'None'):
            v = max(v, settings.CITES_VALORES.get(str(ap).strip(), 0.0))
        return v

    # B UICN: max(B_oficial, valor UICN)
    def _b_uicn(row):
        v   = row['valor_b_oficial']
        cat = row['categoria_uicn']
        if cat and str(cat) not in ('nan', 'None'):
            v = max(v, settings.UICN_VALORES.get(str(cat).strip(), 0.0))
        return v

    df_filtrado['valor_b_cites'] = df_filtrado.apply(_b_cites, axis=1)
    df_filtrado['valor_b_uicn']  = df_filtrado.apply(_b_uicn,  axis=1)

    # B max: el mayor de los tres escenarios por individuo
    df_filtrado['valor_b_max'] = df_filtrado[['valor_b_oficial','valor_b_cites','valor_b_uicn']].max(axis=1)

    # ── Agrupación por cobertura ──────────────────────────────────────────────
    resultados = {}

    for cob, group in df_filtrado.groupby('Cobertura'):
        n  = len(group)
        s  = group['Nombre cientifico'].nunique()
        sn = s / n if n > 0 else 0

        # Criterio A
        val_a = coberturas_a[coberturas_a['cobertura'] == cob]['valor_a'].values
        a = float(val_a[0]) if len(val_a) > 0 else 0.0

        # Criterio B — tres escenarios + máximo
        b_oficial = float(group['valor_b_oficial'].sum() / n) if n > 0 else 0.0
        b_cites   = float(group['valor_b_cites'].sum()   / n) if n > 0 else 0.0
        b_uicn    = float(group['valor_b_uicn'].sum()    / n) if n > 0 else 0.0
        b_max     = float(group['valor_b_max'].sum()     / n) if n > 0 else 0.0

        # Criterio C
        c_row = tabla_c[(tabla_c['sn_min'] <= sn) & (tabla_c['sn_max'] > sn)]
        c = 1.0 if sn == 1.0 else (
            float(c_row['valor_c'].values[0]) if not c_row.empty else 0.1
        )

        # FCAFU — tres escenarios + máximo
        fcafu_oficial = 1 + a + b_oficial + c
        fcafu_cites   = 1 + a + b_cites   + c
        fcafu_uicn    = 1 + a + b_uicn    + c
        fcafu_max     = 1 + a + b_max     + c

        # ── Desglose especies con estatus ────────────────────────────────────
        amenazadas = []
        mask = (
            (group['categoria_amenaza'] != 'LC') |
            (group['cites_apendice'].notna() & (group['cites_apendice'].astype(str) != 'nan')) |
            (group['categoria_uicn'].notna()   & (group['categoria_uicn'].astype(str).isin(['CR','EN','VU','NT'])))
        )
        for sp_sci, sp_grp in group[mask].groupby('Nombre cientifico'):
            n_sp     = len(sp_grp)
            cat_mads = sp_grp['categoria_amenaza'].iloc[0]
            cites_sp = sp_grp['cites_apendice'].iloc[0]
            cat_uicn = sp_grp['categoria_uicn'].iloc[0]
            v_ofic   = float(sp_grp['valor_b_oficial'].iloc[0])
            v_cites  = float(sp_grp['valor_b_cites'].iloc[0])
            v_uicn   = float(sp_grp['valor_b_uicn'].iloc[0])

            def _clean(x):
                return x if (x and str(x) not in ('nan', 'None')) else '—'

            # valor máximo entre los tres escenarios por individuo
            v_max = max(v_ofic, v_cites, v_uicn)

            amenazadas.append({
                'nombre_cientifico': sp_sci,
                'categoria_amenaza': cat_mads,       # clave consistente con app.py
                'cat_uicn':          _clean(cat_uicn),
                'cites_apendice':    _clean(cites_sp),
                'n_individuos':      n_sp,
                # Valores B por escenario
                'valor_b_oficial':   v_ofic,
                'valor_b_cites':     v_cites,
                'valor_b_uicn':      v_uicn,
                'valor_b_max':       v_max,
                # Aporte al B de la cobertura
                'aporte_b_oficial':  round(v_ofic  * n_sp / n, 4) if n > 0 else 0.0,
                'aporte_b_cites':    round(v_cites  * n_sp / n, 4) if n > 0 else 0.0,
                'aporte_b_uicn':     round(v_uicn   * n_sp / n, 4) if n > 0 else 0.0,
                'aporte_b_max':      round(v_max    * n_sp / n, 4) if n > 0 else 0.0,
            })

        # ── Vedas ────────────────────────────────────────────────────────────
        vedas_detectadas    = []
        n_ind_veda_nacional = 0
        n_ind_veda_regional = 0
        n_ind_veda_ambas    = 0

        for sp_sci, sp_group in group.groupby('Nombre cientifico'):
            n_sp   = len(sp_group)
            info_v = consultar_veda(sp_sci, car=car)
            if info_v['nivel'] != 'sin_veda':
                vedas_detectadas.append({
                    'nombre_cientifico': sp_sci,
                    'n_individuos':      n_sp,
                    'nivel':             info_v['nivel'],
                    'norma': (
                        info_v['veda_nacional_info']['norma']
                        if info_v['en_veda_nacional']
                        else info_v['veda_regional_info']['norma']
                    ),
                    'alerta': info_v['alerta'],
                })
                if info_v['nivel'] == 'nacional+regional':
                    n_ind_veda_ambas    += n_sp
                elif info_v['nivel'] == 'nacional':
                    n_ind_veda_nacional += n_sp
                elif info_v['nivel'] == 'regional':
                    n_ind_veda_regional += n_sp

        # Área basal
        area_basal = 0.0
        if 'ab_total' in final_cols:
            area_basal = float(
                pd.to_numeric(group[final_cols['ab_total']], errors='coerce').sum()
            )

        resultados[cob] = {
            # Conteos
            'N':   n,
            'S':   s,
            'SN':  sn,
            # Criterios
            'A':         a,
            'B':         b_oficial,    # alias compatibilidad
            'B_oficial': b_oficial,
            'B_cites':   b_cites,
            'B_uicn':    b_uicn,
            'B_max':     b_max,
            'C':         c,
            # FCAFU — tres escenarios + máximo
            'FCAFU':        fcafu_oficial,
            'FCAFU_cites':  fcafu_cites,
            'FCAFU_uicn':   fcafu_uicn,
            'FCAFU_max':    fcafu_max,
            # Desglose
            'amenazadas':       amenazadas,
            'area_basal_total': area_basal,
            # Vedas
            'hay_veda':            len(vedas_detectadas) > 0,
            'vedas_detectadas':    vedas_detectadas,
            'n_ind_veda_nacional': n_ind_veda_nacional,
            'n_ind_veda_regional': n_ind_veda_regional,
            'n_ind_veda_ambas':    n_ind_veda_ambas,
            'car':                 car,
        }

    return resultados
