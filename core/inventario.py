import pandas as pd
import numpy as np
import os
from . import utils
from config import settings

def procesar_inventario(excel_path, dap_min=settings.DAP_MIN_DEFAULT):
    """
    Procesa el inventario forestal estndar de Unergy.
    Calcula N, S, SN, A, B, C y FCAFU por cobertura.
    """
    # Leer el excel - Intentar detectar la fila de encabezado
    # Primero leemos sin encabezado para buscar la fila que contiene 'ID' o 'Cobertura'
    df_raw = pd.read_excel(excel_path, header=None)
    header_row = 0
    for i, row in df_raw.iterrows():
        row_str = [str(x).lower() for x in row.values]
        if any('cobertura' in s for s in row_str) or any('nombre cientifico' in s for s in row_str):
            header_row = i
            break
            
    df = pd.read_excel(excel_path, header=header_row)
    
    # Normalizar nombres de columnas (quitar tildes, espacios y a minsculas)
    def normalize(s):
        import unicodedata
        return "".join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn').lower().strip()
    
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
        if not found and key != 'ab_total': # AB total puede ser opcional
            raise ValueError(f"No se encontr una columna equivalente a: {key} (Opciones buscadas: {options})")

    # Limpieza de datos usando los nombres encontrados
    df['Nombre cientifico'] = df[final_cols['nombre cientifico']].str.strip().str.capitalize()
    df['Cobertura'] = df[final_cols['cobertura']].str.strip()
    
    # Convertir DAP a cm
    df['DAP_cm'] = df[final_cols['dap_m']] * 100
    
    # Filtrar por DAP mnimo
    df_filtrado = df[df['DAP_cm'] >= dap_min].copy()
    
    # Cargar tablas de referencia
    coberturas_a = pd.read_csv(os.path.join(settings.CONFIG_DIR, "coberturas_a.csv"))
    especies_amenazadas = pd.read_csv(os.path.join(settings.CONFIG_DIR, "especies_amenazadas_co.csv"))
    tabla_c = pd.read_csv(os.path.join(settings.CONFIG_DIR, "tabla_c.csv"))
    
    # Mapear valor de amenaza
    amenaza_map = especies_amenazadas.set_index('nombre_cientifico')['categoria'].to_dict()
    df_filtrado['categoria_amenaza'] = df_filtrado['Nombre cientifico'].map(amenaza_map).fillna('LC')
    df_filtrado['valor_amenaza'] = df_filtrado['categoria_amenaza'].map(settings.AMENAZA_VALORES).fillna(0.0)
    
    resultados = {}
    
    # Agrupar por cobertura
    for cob, group in df_filtrado.groupby('Cobertura'):
        n = len(group)
        s = group['Nombre cientifico'].nunique()
        sn = s / n if n > 0 else 0
        
        # Criterio A
        val_a = coberturas_a[coberturas_a['cobertura'] == cob]['valor_a'].values
        a = val_a[0] if len(val_a) > 0 else None
        
        if a is None:
            # Si no se encuentra la cobertura, se marca para mapeo manual
            a = 0.0 # Valor por defecto o error manejado en UI
            
        # Criterio B
        b = group['valor_amenaza'].sum() / n if n > 0 else 0
        
        # Criterio C
        c_row = tabla_c[(tabla_c['sn_min'] <= sn) & (tabla_c['sn_max'] > sn)]
        if sn == 1.0: # Caso borde
            c = 1.0
        else:
            c = c_row['valor_c'].values[0] if not c_row.empty else 0.1
            
        # FCAFU = 1 + A + B + C
        fcafu = 1 + a + b + c
        
        # Especies amenazadas detectadas
        amenazadas = group[group['categoria_amenaza'] != 'LC'][['Nombre cientifico', 'categoria_amenaza']].drop_duplicates().to_dict('records')
        
        resultados[cob] = {
            'N': n,
            'S': s,
            'SN': sn,
            'A': a,
            'B': b,
            'C': c,
            'FCAFU': fcafu,
            'amenazadas': amenazadas,
            'area_basal_total': group[final_cols['ab_total']].sum() if 'ab_total' in final_cols else 0
        }
        
    return resultados
