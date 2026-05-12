# -*- coding: utf-8 -*-
import streamlit as st
import os
import pandas as pd
from core import (
    inputs, 
    inventario, 
    utils, 
    contexto, 
    atc, 
    rangos, 
    adicionalidad, 
    biodiversidad, 
    reportes,
    mapas
)
from config import settings

st.set_page_config(page_title="Unergy - Compensación Forestal 2026", layout="wide", page_icon="🌳")

# Asegurar que la carpeta de salidas exista
os.makedirs(settings.OUTPUTS_DIR, exist_ok=True)

# Estilos CSS para mejorar la esttica
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #2e7d32; color: white; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🌳 Sistema de Análisis de Compensación Forestal")
st.subheader("Unergy Energía Digital - Manual de Compensaciones 2026")
st.markdown("---")

# --- SIDEBAR: Configuracin y GEE ---
with st.sidebar:
    st.image("https://unergy.io/wp-content/uploads/2021/05/Logo-Unergy-01.png", width=200) # Logo placeholder
    st.header("⚙️ Configuración")
    gee_json = st.file_uploader("Cargar Service Account GEE (JSON)", type=['json'])
    
    if gee_json:
        creds_path = utils.save_gee_credentials(gee_json)
        st.success("✅ Credenciales actualizadas")
    
    success, msg = utils.init_gee_session()
    if success:
        st.sidebar.success(f"🌐 {msg}")
    else:
        st.sidebar.warning(f"⚠️ {msg}")
    
    st.markdown("---")
    st.info("Este sistema procesa automáticamente los 5 rangos jerárquicos del Manual 2026.")

# --- ENTRADAS ---
c1, c2 = st.columns(2)
with c1:
    st.markdown("### 📝 Información Base")
    nombre_proyecto = st.text_input("Nombre del Proyecto", placeholder="Ej: P.S. Valledupar")
    codigo_proyecto = st.text_input("Código del Proyecto", placeholder="Ej: COLCES193")

with c2:
    st.markdown("### 📂 Carga de Archivos")
    file_impacto = st.file_uploader("Polígono de Impacto (KMZ, KML o ZIP)", type=['kmz', 'kml', 'zip'])
    file_inv = st.file_uploader("Inventario Forestal (Excel Unergy)", type=['xlsx'])

st.markdown("---")

if st.button("🚀 INICIAR ANÁLISIS TÉCNICO"):
    if not (file_impacto and file_inv and nombre_proyecto and codigo_proyecto):
        st.error("❌ Por favor complete todos los datos antes de continuar.")
    else:
        with st.spinner("⏳ Procesando datos espaciales y bióticos..."):
            try:
                # 1. Cargar Impacto
                gdf_impacto = inputs.cargar_poligono_impacto(file_impacto, file_impacto.name)
                valido, msg_val = inputs.validar_geometria(gdf_impacto)
                if not valido:
                    st.error(msg_val)
                    st.stop()
                
                # 2. Contexto (GEE)
                ctx = contexto.obtener_contexto_impacto(gdf_impacto)
                
                # 3. Inventario (FCAFU)
                inv_results = inventario.procesar_inventario(file_inv)
                
                # 4. ATC por Rangos
                atc_results = atc.calcular_atc_por_rangos(inv_results, ctx)
                
                # 5. Candidatas (GEE)
                cand_results = rangos.construir_areas_candidatas(gdf_impacto, ctx)
                
                # 6. Adicionalidad (Hansen)
                bau_results = adicionalidad.calcular_tasa_bau(ctx['bioma_principal'])
                
                # Guardar en sesión para evitar reinicios al descargar
                st.session_state['analisis_finalizado'] = True
                st.session_state['final_data'] = {
                    'proyecto': nombre_proyecto, 'codigo': codigo_proyecto,
                    'contexto': ctx, 'inventario_full': inv_results,
                    'atc': atc_results, 'candidatas': cand_results, 'bau': bau_results,
                    'gdf_impacto': gdf_impacto,
                    'biodiv': biodiversidad.consultar_biodiversidad_zona(gdf_impacto),
                    'mapa_url': mapas.obtener_url_mapa_estatico(gdf_impacto, ctx['bioma_principal'])
                }
                # Calcular Adicionalidad Biótica
                final_data = st.session_state['final_data']
                score_bio, razon_bio = adicionalidad.calcular_adicionalidad_biotica(final_data['biodiv'])
                final_data['score_biotico'] = score_bio
                final_data['razon_biotica'] = razon_bio
            except Exception as e:
                st.error(f"Hubo un error en el procesamiento: {str(e)}")
                st.exception(e)

if st.session_state.get('analisis_finalizado'):
    final_data = st.session_state['final_data']
    ctx = final_data['contexto']
    atc_results = final_data['atc']
    cand_results = final_data['candidatas']
    bau_results = final_data['bau']
    inv_results = final_data['inventario_full']
    codigo_proyecto = final_data['codigo']
    nombre_proyecto = final_data['proyecto']

    # --- VISUALIZACIÓN DE RESULTADOS ---
    st.success("✅ Análisis Finalizado")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Bioma Impactado", ctx['bioma_principal'])
    m2.metric("ATC Rango 1", f"{atc_results['Rango 1']['atc_total']:.2f} ha")
    m3.metric("Índice Adic. Biótica", f"x{final_data.get('score_biotico', 1.0)}", help=final_data.get('razon_biotica', ''))
    
    tab_res, tab_det, tab_biodiv = st.tabs(["📊 Comparativa de Rangos", "🌲 Detalle FCAFU", "🦋 Biodiversidad (GBIF)"])
    
    with tab_res:
        st.markdown("#### Suficiencia de Hectáreas por Rango")
        
        # Layout Columnas: Tabla (2/3) y Mapa (1/3)
        col_tab, col_map = st.columns([2, 1])
        
        with col_tab:
            comp_list = []
            for r, r_data in atc_results.items():
                c_data = cand_results.get(r, {})
                balance = adicionalidad.analizar_balance_biodiversidad(c_data, final_data.get('biodiv', {}))
                
                comp_list.append({
                    "Rango": r,
                    "ATC Req. (ha)": round(r_data['atc_total'], 2),
                    "Candidatas": round(c_data.get('total', 0), 2),
                    "Potencial Biodiv.": balance['analisis'],
                    "Adic. (ha/año)": round(c_data.get('total', 0) * bau_results['tasa_bau_anual'] * final_data.get('score_biotico', 1.0), 4),
                    "Estado": "✅ OK" if c_data.get('total', 0) >= r_data['atc_total'] else "❌ Insuf"
                })
            st.dataframe(pd.DataFrame(comp_list), use_container_width=True)
        
        with col_map:
            if final_data.get('mapa_url'):
                st.markdown("**Vista Preliminar GEE**")
                st.image(final_data['mapa_url'], use_container_width=True)
                with st.expander("🔍 Ver mapa ampliado"):
                    st.image(final_data['mapa_url'], use_container_width=True)
            else:
                st.warning("No se pudo generar el mapa estático.")
        
        st.info("💡 **Adicionalidad**: Estimación del beneficio ambiental directo al proteger/restaurar estas hectáreas frente a la tasa de pérdida del bioma.")
    
    with tab_det:
        st.markdown("#### Cálculo del Factor por Cobertura")
        fcafu_df = []
        for cob, d in inv_results.items():
            fcafu_df.append({
                "Cobertura": cob,
                "N": d['N'],
                "Criterio A": d['A'],
                "Criterio B": round(d['B'], 3),
                "Criterio C": d['C'],
                "FCAFU": round(d['FCAFU'], 3)
            })
        st.table(pd.DataFrame(fcafu_df))
    
    with tab_biodiv:
        bd = final_data.get('biodiv', {})
        st.markdown("#### Caracterización Biótica en Zona de Impacto (GBIF)")
        
        b1, b2, b3 = st.columns(3)
        b1.metric("Registros Totales", bd.get('registros_totales', 0))
        b2.metric("Riqueza Especies", bd.get('riqueza_total', 0))
        b3.metric("Especies Amenazadas", len(bd.get('especies_amenazadas', [])))
        
        st.markdown("---")
        st.markdown("**Distribución por Taxón**")
        st.bar_chart(bd.get('taxones', {}))
        
        if bd.get('especies_amenazadas'):
            st.warning("⚠️ **Especies Amenazadas detectadas en la zona:**")
            st.write(", ".join(bd['especies_amenazadas']))
        
        st.info("La adicionalidad en biodiversidad se garantiza priorizando la restauración en áreas con baja conectividad pero alto potencial biótico según GBIF.")

    # --- DESCARGAS ---
    st.markdown("---")
    st.markdown("### 📥 Descargar Reportes Finales")
    
    d_col1, d_col2 = st.columns(2)
    
    # Excel
    excel_name = f"ATC_{codigo_proyecto}.xlsx"
    excel_path = os.path.join(settings.OUTPUTS_DIR, excel_name)
    reportes.generar_reporte_excel(final_data, excel_path)
    with d_col1:
        with open(excel_path, "rb") as f:
            st.download_button("📊 Descargar Matriz Excel", f, file_name=excel_name)
    
    # Word
    word_name = f"Informe_{codigo_proyecto}.docx"
    word_path = os.path.join(settings.OUTPUTS_DIR, word_name)
    reportes.generar_reporte_word(final_data, word_path)
    with d_col2:
        with open(word_path, "rb") as f:
            st.download_button("📄 Descargar Informe Word (GF-PN-01)", f, file_name=word_name)
