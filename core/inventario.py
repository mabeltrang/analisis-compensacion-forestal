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
    # Leer el excel
    df = pd.read_excel(excel_path)
    
    # Columnas obligatorias
    cols_req = ['Nombre cientifico', 'DAP A en metros', 'Cobertura']
    for col in cols_req:
        if col not in df.columns:
            raise ValueError(f"Falta la columna obligatoria: {col}")
            
    # Limpieza de datos
    df['Nombre cientifico'] = df['Nombre cientifico'].str.strip().str.capitalize()
    df['Cobertura'] = df['Cobertura'].str.strip()
    
    # Convertir DAP a cm
    df['DAP_cm'] = df['DAP A en metros'] * 100
    
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
            'area_basal_total': group['AB T en metros cuadrados'].sum() if 'AB T en metros cuadrados' in group.columns else 0
        }
        
    return resultados
