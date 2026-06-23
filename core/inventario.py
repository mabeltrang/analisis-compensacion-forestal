# -*- coding: utf-8 -*-
"""
inventario.py — Procesamiento del inventario forestal Unergy
Manual 2026 (Res. 0305/2026 MADS)

Escenarios de Criterio B:
  - B_oficial : solo Res. 0126/2024 MADS  (CR=1.0, EN=0.6, VU=0.4)
  - B_cites   : max(B_oficial, equivalencia CITES)  — escenario Unergy
  - B_uicn    : max(B_oficial, categoría UICN)      — escenario Unergy

Matching de especies:
  1. Especie exacta en especies_amenazadas_co.csv
  2. Nombre indeterminado (sp./spp.) → peor categoría del género
  3. Especie determinada sin match   → LC (sin penalización)
"""

import os
import pandas as pd
import numpy as np
from collections import defaultdict
from . import utils
from config import settings
from config.vedas import consultar_veda


def _norm(s):
    """Normaliza string: sin tildes, minúsculas, sin espacios extra."""
    import unicodedata
    s = str(s)
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    return s.lower().strip()


_SP_SUFIJOS = {'sp', 'sp.', 'spp', 'spp.', 'sp1', 'sp2', 'sp3'}


def _es_indeterminado(nombre_norm: str) -> bool:
    """True si el nombre es género + sufijo sp/spp (indeterminado)."""
    partes = nombre_norm.strip().split()
    return len(partes) == 2 and partes[1].lower() in _SP_SUFIJOS


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

    ea = pd.read_csv(os.path.join(settings.CONFIG_DIR, "especies_amenazadas_co.csv"))
    ea.columns = [_norm(c).replace(' ', '_') for c in ea.columns]
    ea.columns = [_norm(c) for c in ea.columns]

    # ── Índice MADS (Res. 0126/2024) ─────────────────────────────────────────
    amenaza_exact = {
        _norm(r['nombre_cientifico']): r['categoria_de_amenaza']
        for _, r in ea.iterrows()
    }
    # Fallback de género (solo para sp. indeterminados)
    CAT_ORDER = {'CR': 4, 'EN': 3, 'VU': 2, 'NT': 1, 'LC': 0}
    amenaza_genero = defaultdict(lambda: 'LC')
    for _, r in ea.iterrows():
        gen = _norm(r['nombre_cientifico']).split()[0]
        cat_nueva  = r['categoria_de_amenaza']
        if CAT_ORDER.get(cat_nueva, 0) > CAT_ORDER.get(amenaza_genero[gen], 0):
            amenaza_genero[gen] = cat_nueva

    # ── Índice CITES ──────────────────────────────────────────────────────────
    cites_exact = {}
    if 'cites' in ea.columns:
        for _, r in ea.iterrows():
            ap = str(r.get('cites', '')).strip().upper()
            if ap in ('I', 'II', 'III'):
                cites_exact[_norm(r['nombre_cientifico'])] = ap

    # ── Índice UICN ───────────────────────────────────────────────────────────
    uicn_exact = {}
    if 'uicn' in ea.columns:
        for _, r in ea.iterrows():
            cat = str(r.get('uicn', '')).strip().upper()
            if cat in ('CR', 'EN', 'VU', 'NT', 'LC', 'DD'):
                uicn_exact[_norm(r['nombre_cientifico'])] = cat

    # ── Función de lookup unificada ───────────────────────────────────────────
    def _lookup(nombre_sci):
        """
        Retorna (cat_mads, cites_ap, cat_uicn) para un nombre científico.

        Matching:
          1. Especie exacta en CSV
          2. Nombre indeterminado → peor del género (solo MADS)
          3. Determinada sin match → LC / None
        """
        n = _norm(nombre_sci)

        # MADS
        if n in amenaza_exact:
            cat_mads = amenaza_exact[n]
        elif _es_indeterminado(n):
            gen = n.split()[0]
            cat_mads = amenaza_genero[gen] if amenaza_genero[gen] != 'LC' else 'LC'
        else:
            cat_mads = 'LC'

        # CITES (solo especie exacta — ya resuelto en el CSV)
        cites_ap = cites_exact.get(n, None)

        # UICN (solo especie exacta)
        cat_uicn = uicn_exact.get(n, None)

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
        v = row['valor_b_oficial']
        ap = row['cites_apendice']
        if ap and str(ap) not in ('nan', 'None'):
            v = max(v, settings.CITES_VALORES.get(str(ap).strip(), 0.0))
        return v

    # B UICN: max(B_oficial, valor UICN)
    def _b_uicn(row):
        v = row['valor_b_oficial']
        cat = row['categoria_uicn']
        if cat and str(cat) not in ('nan', 'None'):
            v = max(v, settings.UICN_VALORES.get(str(cat).strip(), 0.0))
        return v

    df_filtrado['valor_b_cites'] = df_filtrado.apply(_b_cites, axis=1)
    df_filtrado['valor_b_uicn']  = df_filtrado.apply(_b_uicn,  axis=1)

    # ── Agrupación por cobertura ──────────────────────────────────────────────
    resultados = {}

    for cob, group in df_filtrado.groupby('Cobertura'):
        n  = len(group)
        s  = group['Nombre cientifico'].nunique()
        sn = s / n if n > 0 else 0

        # Criterio A
        val_a = coberturas_a[coberturas_a['cobertura'] == cob]['valor_a'].values
        a = float(val_a[0]) if len(val_a) > 0 else 0.0

        # Criterio B — tres escenarios
        b_oficial = float(group['valor_b_oficial'].sum() / n) if n > 0 else 0.0
        b_cites   = float(group['valor_b_cites'].sum()   / n) if n > 0 else 0.0
        b_uicn    = float(group['valor_b_uicn'].sum()    / n) if n > 0 else 0.0

        # Criterio C
        c_row = tabla_c[(tabla_c['sn_min'] <= sn) & (tabla_c['sn_max'] > sn)]
        c = 1.0 if sn == 1.0 else (
            float(c_row['valor_c'].values[0]) if not c_row.empty else 0.1
        )

        # FCAFU — tres escenarios
        fcafu_oficial = 1 + a + b_oficial + c
        fcafu_cites   = 1 + a + b_cites   + c
        fcafu_uicn    = 1 + a + b_uicn    + c

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
                return x if (x and str(x) not in ('nan','None')) else '—'

            amenazadas.append({
                'nombre_cientifico': sp_sci,
                'cat_mads':          cat_mads,
                'cat_uicn':          _clean(cat_uicn),
                'cites_apendice':    _clean(cites_sp),
                'n_individuos':      n_sp,
                # Valores B por escenario
                'valor_b_oficial':   v_ofic,
                'valor_b_cites':     v_cites,
                'valor_b_uicn':      v_uicn,
                # Aporte al B de la cobertura
                'aporte_b_oficial':  round(v_ofic  * n_sp / n, 4) if n > 0 else 0.0,
                'aporte_b_cites':    round(v_cites  * n_sp / n, 4) if n > 0 else 0.0,
                'aporte_b_uicn':     round(v_uicn   * n_sp / n, 4) if n > 0 else 0.0,
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
            'C':         c,
            # FCAFU — tres escenarios
            'FCAFU':        fcafu_oficial,
            'FCAFU_cites':  fcafu_cites,
            'FCAFU_uicn':   fcafu_uicn,
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
