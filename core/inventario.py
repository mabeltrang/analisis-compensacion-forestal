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

    # Mapear valor de amenaza
    amenaza_map = especies_amenazadas.set_index('nombre_cientifico')['categoria'].to_dict()
    df_filtrado['categoria_amenaza'] = (
        df_filtrado['Nombre cientifico']
        .map(amenaza_map)
        .fillna('LC')
    )
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

        # Especies amenazadas detectadas (no LC)
        amenazadas = (
            group[group['categoria_amenaza'] != 'LC']
            [['Nombre cientifico', 'categoria_amenaza']]
            .drop_duplicates()
            .to_dict('records')
        )

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
