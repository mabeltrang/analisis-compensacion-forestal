import pandas as pd
import numpy as np
import os
from . import utils
from config import settings
from config.vedas import consultar_veda


def procesar_inventario(excel_path, dap_min=settings.DAP_MIN_DEFAULT, car: str = ""):
    """
    Procesa el inventario forestal estándar de Unergy.
    Calcula N, S, SN, A, B, C y FCAFU por cobertura.

    Robusto contra:
      - Encabezados en fila distinta a la primera
      - Nombres de columna con/sin tildes
      - Celdas vacías (NaN) en columnas de texto
      - DAP con strings vacíos o no-numéricos
    """
    # Detectar fila de encabezado
    df_raw = pd.read_excel(excel_path, header=None)
    header_row = 0
    for i, row in df_raw.iterrows():
        row_str = [str(x).lower() for x in row.values]
        if any('cobertura' in s for s in row_str) or any('nombre cientifico' in s for s in row_str):
            header_row = i
            break

    df = pd.read_excel(excel_path, header=header_row)

    # Normalizar nombres de columnas
    def normalize(s):
        import unicodedata
        return "".join(c for c in unicodedata.normalize('NFD', str(s))
                       if unicodedata.category(c) != 'Mn').lower().strip()

    df.columns = [normalize(c) for c in df.columns]

    # Mapeo de columnas esperadas
    col_map = {
        'nombre cientifico': ['nombre cientifico', 'nombre cientifico', 'sp', 'especie'],
        'dap_m': ['dap a (m)', 'dap a en metros', 'dap a (metros)', 'dap'],
        'cobertura': ['cobertura', 'cobertura_id', 'tipo_cobertura'],
        'ab_total': ['ab t (m2)', 'ab t en metros cuadrados', 'area basal total']
    }

    final_cols = {}
    for key, options in col_map.items():
        found = False
        for opt in options:
            norm_opt = normalize(opt)
            if norm_opt in df.columns:
                final_cols[key] = norm_opt
                found = True
                break
        if not found and key != 'ab_total':
            raise ValueError(
                f"No se encontró una columna equivalente a: {key} "
                f"(Opciones buscadas: {options})"
            )

    # ────────────────────────────────────────────────────────────────
    # LIMPIEZA ROBUSTA: convertir a string ANTES de .str.strip()
    # Convierte NaN, números, todo a string. Si era NaN queda como ''.
    # ────────────────────────────────────────────────────────────────
    df['Nombre cientifico'] = (
        df[final_cols['nombre cientifico']]
        .fillna('')
        .astype(str)
        .str.strip()
        .str.capitalize()
    )
    df['Cobertura'] = (
        df[final_cols['cobertura']]
        .fillna('')
        .astype(str)
        .str.strip()
    )

    # DAP a cm — convertir a numérico de forma segura
    df['DAP_cm'] = pd.to_numeric(df[final_cols['dap_m']], errors='coerce') * 100

    # Filtrar filas válidas: DAP >= mínimo Y con datos en cobertura/especie
    df_filtrado = df[
        (df['DAP_cm'] >= dap_min) &
        (df['Cobertura'] != '') &
        (df['Nombre cientifico'] != '')
    ].copy()

    if df_filtrado.empty:
        return {}

    # Cargar tablas de referencia
    coberturas_a = pd.read_csv(os.path.join(settings.CONFIG_DIR, "coberturas_a.csv"))
    especies_amenazadas = pd.read_csv(
        os.path.join(settings.CONFIG_DIR, "especies_amenazadas_co.csv")
    )
    tabla_c = pd.read_csv(os.path.join(settings.CONFIG_DIR, "tabla_c.csv"))

    # Mapear valor de amenaza — con fallback por género
    # 1. Mapa exacto normalizado
    def _norm(s):
        import unicodedata as _ud
        s = str(s)
        s = ''.join(c for c in _ud.normalize('NFD', s)
                    if _ud.category(c) != 'Mn')
        return s.lower().strip()

    amenaza_exact = {
        _norm(r['nombre_cientifico']): r['categoria']
        for _, r in especies_amenazadas.iterrows()
    }

    # 2. Mapa por género → categoría más alta encontrada en ese género
    #    solo para filas con match_genero == 1 o donde haya ≥ 1 sp. del género
    from collections import defaultdict
    CAT_ORDER = {'CR': 4, 'EN': 3, 'VU': 2, 'NT': 1, 'LC': 0}
    amenaza_genero = defaultdict(lambda: 'LC')
    for _, r in especies_amenazadas.iterrows():
        genero = _norm(r['nombre_cientifico']).split()[0]
        cat_nueva = r['categoria']
        cat_actual = amenaza_genero[genero]
        if CAT_ORDER.get(cat_nueva, 0) > CAT_ORDER.get(cat_actual, 0):
            amenaza_genero[genero] = cat_nueva

    def _lookup_amenaza(nombre_sci):
        n = _norm(nombre_sci)
        # Exacto primero
        if n in amenaza_exact:
            return amenaza_exact[n]
        # Fallback género (funciona para "Juglans sp", "Juglans cf. neotropica", etc.)
        genero = n.split()[0] if n else ''
        if genero and genero in amenaza_genero and amenaza_genero[genero] != 'LC':
            return amenaza_genero[genero]
        return 'LC'

    df_filtrado['categoria_amenaza'] = df_filtrado['Nombre cientifico'].apply(_lookup_amenaza)
    df_filtrado['valor_amenaza'] = (
        df_filtrado['categoria_amenaza']
        .map(settings.AMENAZA_VALORES)
        .fillna(0.0)
    )

    resultados = {}

    # Agrupar por cobertura
    for cob, group in df_filtrado.groupby('Cobertura'):
        n = len(group)
        s = group['Nombre cientifico'].nunique()
        sn = s / n if n > 0 else 0

        # Criterio A — desde CSV de coberturas
        val_a = coberturas_a[coberturas_a['cobertura'] == cob]['valor_a'].values
        a = float(val_a[0]) if len(val_a) > 0 else 0.0

        # Criterio B — proporción ponderada de amenaza
        b = float(group['valor_amenaza'].sum() / n) if n > 0 else 0.0

        # Criterio C — buscar intervalo en tabla_c
        c_row = tabla_c[(tabla_c['sn_min'] <= sn) & (tabla_c['sn_max'] > sn)]
        if sn == 1.0:
            c = 1.0
        else:
            c = float(c_row['valor_c'].values[0]) if not c_row.empty else 0.1

        # FCAFU = 1 + A + B + C
        fcafu = 1 + a + b + c

        # Especies amenazadas — desglose completo para fórmula B
        # B = Σ(valor_amenaza_i) / N  para todos los individuos de la cobertura
        amenazadas_group = group[group['categoria_amenaza'] != 'LC'].copy()
        amenazadas = []
        for sp_sci, sp_grp in amenazadas_group.groupby('Nombre cientifico'):
            n_sp = len(sp_grp)
            cat_sp = sp_grp['categoria_amenaza'].iloc[0]
            val_sp = float(sp_grp['valor_amenaza'].iloc[0])
            aporte_b = round(val_sp * n_sp / n, 4) if n > 0 else 0.0
            amenazadas.append({
                'nombre_cientifico': sp_sci,
                'categoria_amenaza': cat_sp,
                'n_individuos': n_sp,
                'valor_amenaza': val_sp,
                'aporte_b': aporte_b,
            })

        # ── CRUCE CON VEDAS ─────────────────────────────────────────────────
        # Por cada especie única en esta cobertura, consulta veda
        vedas_detectadas = []
        n_ind_veda_nacional = 0
        n_ind_veda_regional = 0
        n_ind_veda_ambas = 0

        for sp_sci, sp_group in group.groupby('Nombre cientifico'):
            n_sp = len(sp_group)
            info_v = consultar_veda(sp_sci, car=car)
            if info_v['nivel'] != 'sin_veda':
                vedas_detectadas.append({
                    'nombre_cientifico': sp_sci,
                    'n_individuos': n_sp,
                    'nivel': info_v['nivel'],
                    'norma': (
                        info_v['veda_nacional_info']['norma']
                        if info_v['en_veda_nacional']
                        else info_v['veda_regional_info']['norma']
                    ),
                    'alerta': info_v['alerta'],
                })
                if info_v['nivel'] == 'nacional+regional':
                    n_ind_veda_ambas += n_sp
                elif info_v['nivel'] == 'nacional':
                    n_ind_veda_nacional += n_sp
                elif info_v['nivel'] == 'regional':
                    n_ind_veda_regional += n_sp

        hay_veda = len(vedas_detectadas) > 0

        # Área basal total (opcional)
        area_basal = 0.0
        if 'ab_total' in final_cols:
            area_basal = float(
                pd.to_numeric(group[final_cols['ab_total']], errors='coerce').sum()
            )

        resultados[cob] = {
            'N': n,
            'S': s,
            'SN': sn,
            'A': a,
            'B': b,
            'C': c,
            'FCAFU': fcafu,
            'amenazadas': amenazadas,
            'area_basal_total': area_basal,
            # ── Veda ────────────────────────────────────────────────────────
            'hay_veda': hay_veda,
            'vedas_detectadas': vedas_detectadas,
            'n_ind_veda_nacional': n_ind_veda_nacional,
            'n_ind_veda_regional': n_ind_veda_regional,
            'n_ind_veda_ambas': n_ind_veda_ambas,
            'car': car,
        }

    return resultados
