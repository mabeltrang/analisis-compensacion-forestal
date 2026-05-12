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
    reportes
)
from config import settings

st.set_page_config(page_title="Unergy - Compensacin Forestal 2026", layout="wide", page_icon="🌳")

# Estilos CSS para mejorar la esttica
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #2e7d32; color: white; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🌳 Sistema de Anlisis de Compensacin Forestal")
st.subheader("Unergy Energía Digital - Manual de Compensaciones 2026")
st.markdown("---")

# --- SIDEBAR: Configuracin y GEE ---
with st.sidebar:
    st.image("https://unergy.io/wp-content/uploads/2021/05/Logo-Unergy-01.png", width=200) # Logo placeholder
    st.header("⚙️ Configuracin")
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
    st.info("Este sistema procesa automticamente los 5 rangos jerrquicos del Manual 2026.")

# --- ENTRADAS ---
c1, c2 = st.columns(2)
with c1:
    st.markdown("### 📝 Informacin Base")
    nombre_proyecto = st.text_input("Nombre del Proyecto", placeholder="Ej: P.S. Valledupar")
    codigo_proyecto = st.text_input("Cdigo del Proyecto", placeholder="Ej: COLCES193")

with c2:
    st.markdown("### 📂 Carga de Archivos")
    file_impacto = st.file_uploader("Polgono de Impacto (KMZ, KML o ZIP)", type=['kmz', 'kml', 'zip'])
    file_inv = st.file_uploader("Inventario Forestal (Excel Unergy)", type=['xlsx'])

st.markdown("---")

if st.button("🚀 INICIAR ANLISIS TCNICO"):
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
                
                # --- VISUALIZACIN DE RESULTADOS ---
                st.success("✅ Anlisis Finalizado")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Bioma Impactado", ctx['bioma_principal'])
                m2.metric("ATC Rango 1", f"{atc_results['Rango 1']['atc_total']:.2f} ha")
                m3.metric("Tasa BAU", f"{bau_results['tasa_bau_anual']*100:.4f}%")
                
                tab_res, tab_det, tab_biodiv = st.tabs(["📊 Comparativa de Rangos", "🌲 Detalle FCAFU", "🦋 Biodiversidad (GBIF)"])
                
                with tab_res:
                    st.markdown("#### Suficiencia de Hectreas por Rango")
                    comp_list = []
                    for r, r_data in atc_results.items():
                        c_data = cand_results.get(r, {})
                        comp_list.append({
                            "Rango": r,
                            "ATC Requerido (ha)": round(r_data['atc_total'], 2),
                            "Hectreas Candidatas": round(c_data.get('total', 0), 2),
                            "Estado": "✅ Suficiente" if c_data.get('total', 0) >= r_data['atc_total'] else "❌ Insuficiente"
                        })
                    st.dataframe(pd.DataFrame(comp_list), use_container_width=True)
                
                with tab_det:
                    st.markdown("#### Clculo del Factor por Cobertura")
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
                    st.info("Consulta a GBIF en progreso para reas candidatas...")
                    # Simular o ejecutar consulta
                    st.write("Caracterizacin por taxn disponible en los reportes descargables.")

                # --- DESCARGAS ---
                st.markdown("---")
                st.markdown("### 📥 Descargar Reportes Finales")
                
                final_data = {
                    'proyecto': nombre_proyecto, 'codigo': codigo_proyecto,
                    'contexto': ctx, 'inventario_full': inv_results,
                    'atc': atc_results, 'candidatas': cand_results, 'bau': bau_results
                }
                
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

            except Exception as e:
                st.error(f"Hubo un error en el procesamiento: {str(e)}")
                st.exception(e)
