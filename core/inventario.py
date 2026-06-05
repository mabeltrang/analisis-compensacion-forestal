# -*- coding: utf-8 -*-
"""
inventario.py — Procesamiento del inventario forestal Unergy
Manual 2026 (Res. 0305/2026 MADS)

Cambios v7:
- Criterio B corregido: VU=0.4, EN=0.6, CR=1.0  (Tabla 4 del Manual 2026)
  NT ya NO aplica al criterio B (no está en Tabla 4 ni en Res. 0126/2024).
- Nuevo: criterio B_cites usando equivalencias CITES internas de Unergy
  (Apéndice I=0.6, II=0.4). Se calcula en paralelo como escenario alternativo.
- Cada cobertura retorna 'B_oficial' y 'B_cites', y dos FCAFU:
  'FCAFU' (oficial) y 'FCAFU_cites' (con CITES).
"""

import pandas as pd
import numpy as np
import os
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


def procesar_inventario(excel_path, dap_min=settings.DAP_MIN_DEFAULT, car: str = ""):
    """
    Procesa el inventario forestal estándar de Unergy.
    Calcula N, S, SN, A, B_oficial, B_cites, C, FCAFU y FCAFU_cites por cobertura.

    Retorna dict: { cobertura: { ...métricas... } }
    """

    # ── Detectar fila de encabezado ──────────────────────────────────────────
    df_raw = pd.read_excel(excel_path, header=None)
    header_row = 0
    for i, row in df_raw.iterrows():
        row_str = [str(x).lower() for x in row.values]
        if any('cobertura' in s for s in row_str) or \
           any('nombre cientifico' in s for s in row_str):
            header_row = i
            break

    df = pd.read_excel(excel_path, header=header_row)
    df.columns = [_norm(c) for c in df.columns]

    # ── Mapeo de columnas ────────────────────────────────────────────────────
    col_map = {
        'nombre cientifico': ['nombre cientifico', 'sp', 'especie'],
        'dap_m':   ['dap a (m)', 'dap a en metros', 'dap a (metros)', 'dap'],
        'cobertura': ['cobertura', 'cobertura_id', 'tipo_cobertura'],
        'ab_total': ['ab t (m2)', 'ab t en metros cuadrados', 'area basal total'],
    }

    final_cols = {}
    for key, options in col_map.items():
        for opt in options:
            if _norm(opt) in df.columns:
                final_cols[key] = _norm(opt)
                break
        if key not in final_cols and key != 'ab_total':
            raise ValueError(
                f"No se encontró columna equivalente a: {key} "
                f"(buscadas: {options})"
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

    # ── Tablas de referencia ─────────────────────────────────────────────────
    coberturas_a       = pd.read_csv(os.path.join(settings.CONFIG_DIR, "coberturas_a.csv"))
    especies_amenazadas = pd.read_csv(os.path.join(settings.CONFIG_DIR, "especies_amenazadas_co.csv"))
    tabla_c            = pd.read_csv(os.path.join(settings.CONFIG_DIR, "tabla_c.csv"))

    # ── Índices de amenaza ───────────────────────────────────────────────────
    # 1. Exacto: nombre_cientifico → categoria (CR/EN/VU/LC)
    amenaza_exact = {
        _norm(r['nombre_cientifico']): r['categoria']
        for _, r in especies_amenazadas.iterrows()
    }

    # 2. Por género → categoría más alta del género
    CAT_ORDER = {'CR': 4, 'EN': 3, 'VU': 2, 'NT': 1, 'LC': 0}
    amenaza_genero = defaultdict(lambda: 'LC')
    for _, r in especies_amenazadas.iterrows():
        genero     = _norm(r['nombre_cientifico']).split()[0]
        cat_nueva  = r['categoria']
        cat_actual = amenaza_genero[genero]
        if CAT_ORDER.get(cat_nueva, 0) > CAT_ORDER.get(cat_actual, 0):
            amenaza_genero[genero] = cat_nueva

    # 3. CITES: nombre_cientifico → apéndice ('I', 'II', 'III', None)
    #    Leemos desde el CSV si existe columna 'cites', si no → None para todos
    cites_exact = {}
    if 'cites' in especies_amenazadas.columns:
        for _, r in especies_amenazadas.iterrows():
            ap = str(r.get('cites', '')).strip().upper()
            if ap in ('I', 'II', 'III'):
                cites_exact[_norm(r['nombre_cientifico'])] = ap

    def _lookup_amenaza(nombre_sci):
        """Retorna (categoria_res0126, apendice_cites)."""
        n = _norm(nombre_sci)
        # Categoría amenaza oficial
        if n in amenaza_exact:
            cat = amenaza_exact[n]
        else:
            genero = n.split()[0] if n else ''
            cat = amenaza_genero[genero] if (genero and amenaza_genero[genero] != 'LC') else 'LC'

        # Apéndice CITES
        cites_ap = cites_exact.get(n, None)

        return cat, cites_ap

    df_filtrado[['categoria_amenaza', 'cites_apendice']] = df_filtrado[
        'Nombre cientifico'
    ].apply(lambda x: pd.Series(_lookup_amenaza(x)))

    # Valores numéricos
    # B oficial: solo CR/EN/VU según Tabla 4 Manual 2026 (NT=0)
    df_filtrado['valor_b_oficial'] = (
        df_filtrado['categoria_amenaza']
        .map(settings.AMENAZA_VALORES)
        .fillna(0.0)
    )

    # B cites: si hay apéndice CITES Y el valor CITES > valor oficial → usar CITES
    # Si no tiene apéndice, mantener el valor oficial
    def _valor_b_cites(row):
        v_oficial = row['valor_b_oficial']
        ap        = row['cites_apendice']
        if ap is None or str(ap) == 'nan':
            return v_oficial
        v_cites = settings.CITES_VALORES.get(ap, 0.0)
        return max(v_oficial, v_cites)   # no bajar si ya tiene categoría mayor

    df_filtrado['valor_b_cites'] = df_filtrado.apply(_valor_b_cites, axis=1)

    # ── Agrupación por cobertura ──────────────────────────────────────────────
    resultados = {}

    for cob, group in df_filtrado.groupby('Cobertura'):
        n  = len(group)
        s  = group['Nombre cientifico'].nunique()
        sn = s / n if n > 0 else 0

        # Criterio A
        val_a = coberturas_a[coberturas_a['cobertura'] == cob]['valor_a'].values
        a = float(val_a[0]) if len(val_a) > 0 else 0.0

        # Criterio B — oficial (Tabla 4 Manual 2026)
        b_oficial = float(group['valor_b_oficial'].sum() / n) if n > 0 else 0.0

        # Criterio B — con CITES (equiparación interna Unergy)
        b_cites   = float(group['valor_b_cites'].sum() / n) if n > 0 else 0.0

        # Criterio C
        c_row = tabla_c[(tabla_c['sn_min'] <= sn) & (tabla_c['sn_max'] > sn)]
        c = 1.0 if sn == 1.0 else (
            float(c_row['valor_c'].values[0]) if not c_row.empty else 0.1
        )

        # FCAFU
        fcafu_oficial = 1 + a + b_oficial + c
        fcafu_cites   = 1 + a + b_cites   + c

        # ── Desglose especies amenazadas ─────────────────────────────────────
        amenazadas = []
        mask_amenazadas = (
            (group['categoria_amenaza'] != 'LC') |
            (group['cites_apendice'].notna() & (group['cites_apendice'] != 'nan'))
        )
        amenazadas_group = group[mask_amenazadas].copy()

        for sp_sci, sp_grp in amenazadas_group.groupby('Nombre cientifico'):
            n_sp      = len(sp_grp)
            cat_sp    = sp_grp['categoria_amenaza'].iloc[0]
            cites_sp  = sp_grp['cites_apendice'].iloc[0]
            v_oficial = float(sp_grp['valor_b_oficial'].iloc[0])
            v_cites   = float(sp_grp['valor_b_cites'].iloc[0])
            amenazadas.append({
                'nombre_cientifico':  sp_sci,
                'categoria_amenaza':  cat_sp,
                'cites_apendice':     cites_sp if (cites_sp and str(cites_sp) != 'nan') else '—',
                'n_individuos':       n_sp,
                'valor_b_oficial':    v_oficial,
                'valor_b_cites':      v_cites,
                'aporte_b_oficial':   round(v_oficial * n_sp / n, 4) if n > 0 else 0.0,
                'aporte_b_cites':     round(v_cites   * n_sp / n, 4) if n > 0 else 0.0,
            })

        # ── Vedas ────────────────────────────────────────────────────────────
        vedas_detectadas     = []
        n_ind_veda_nacional  = 0
        n_ind_veda_regional  = 0
        n_ind_veda_ambas     = 0

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
            'N':              n,
            'S':              s,
            'SN':             sn,
            'A':              a,
            'B':              b_oficial,    # alias para compatibilidad
            'B_oficial':      b_oficial,
            'B_cites':        b_cites,
            'C':              c,
            'FCAFU':          fcafu_oficial,
            'FCAFU_cites':    fcafu_cites,
            'amenazadas':     amenazadas,
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
