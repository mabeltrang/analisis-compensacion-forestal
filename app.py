# -*- coding: utf-8 -*-
import streamlit as st
import os
import pandas as pd
from streamlit_folium import st_folium
from core import (
    inputs, inventario, utils, contexto,
    atc, rangos, adicionalidad, reportes, mapas
)
from config import settings

st.set_page_config(page_title="Unergy – Compensación Forestal 2026",
                   layout="wide", page_icon="🌳")
os.makedirs(settings.OUTPUTS_DIR, exist_ok=True)

st.markdown("""
<style>
.stButton>button {
    width:100%; border-radius:5px; height:3em;
    background-color:#2e7d32; color:white;
}
.metric-box {
    background:#f0f2f6; border-radius:8px;
    padding:12px 16px; margin-bottom:8px;
}
</style>""", unsafe_allow_html=True)

st.title("🌳 Sistema de Análisis de Compensación Forestal")
st.subheader("Unergy Energía Digital – Manual de Compensaciones 2026")
st.markdown("---")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://unergy.io/wp-content/uploads/2021/05/Logo-Unergy-01.png", width=200)
    st.header("⚙️ Configuración")
    gee_json = st.file_uploader("Service Account GEE (JSON)", type=['json'])
    if gee_json:
        utils.save_gee_credentials(gee_json)
        st.success("✅ Credenciales actualizadas")
    ok, msg = utils.init_gee_session()
    (st.sidebar.success if ok else st.sidebar.warning)(f"{'🌐' if ok else '⚠️'} {msg}")
    st.markdown("---")
    st.info("Procesa automáticamente los 6 rangos jerárquicos del Manual 2026.")

# ── Entradas ─────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    st.markdown("### 📝 Información Base")
    nombre_proyecto = st.text_input("Nombre del Proyecto", placeholder="Ej: P.S. Valledupar")
    codigo_proyecto = st.text_input("Código del Proyecto", placeholder="Ej: COLCES193")
    anos_proyecto   = st.number_input("Años de vida útil del proyecto (para cálculo de adicionalidad)", min_value=1, value=20, step=1)
with c2:
    st.markdown("### 📂 Carga de Archivos")
    file_impacto = st.file_uploader("Polígono de Impacto (KMZ, KML o ZIP)", type=['kmz','kml','zip'])
    file_inv     = st.file_uploader("Inventario Forestal (Excel Unergy)", type=['xlsx'])

st.markdown("---")

# ── Botón de análisis ────────────────────────────────────────────────────────
if st.button("🚀 INICIAR ANÁLISIS TÉCNICO"):
    if not (file_impacto and file_inv and nombre_proyecto and codigo_proyecto):
        st.error("❌ Complete todos los campos antes de continuar.")
    else:
        try:
            with st.spinner("⏳ Cargando polígono e inventario..."):
                gdf_impacto     = inputs.cargar_poligono_impacto(file_impacto, file_impacto.name)
                valido, msg_val = inputs.validar_geometria(gdf_impacto)
                if not valido:
                    st.error(msg_val); st.stop()
                ctx         = contexto.obtener_contexto_impacto(gdf_impacto)
                inv_results = inventario.procesar_inventario(file_inv)
                atc_results = atc.calcular_atc_por_rangos(inv_results, ctx)

            with st.spinner("🌍 Calculando áreas candidatas en Google Earth Engine..."):
                cand_results = rangos.construir_areas_candidatas(gdf_impacto, ctx)
                bau_results  = adicionalidad.calcular_tasa_bau(ctx['bioma_principal'])

            with st.spinner("🗺️ Generando Mapas Interactivos (Folium)..."):
                mapas_interactivos = mapas.obtener_mapas_por_rango(gdf_impacto, cand_results)

            st.session_state['analisis_finalizado'] = True
            st.session_state['final_data'] = {
                'proyecto':        nombre_proyecto,
                'codigo':          codigo_proyecto,
                'anos':            anos_proyecto,
                'contexto':        ctx,
                'inventario_full': inv_results,
                'atc':             atc_results,
                'candidatas':      cand_results,
                'bau':             bau_results,
                'gdf_impacto':     gdf_impacto,
                'mapas':           mapas_interactivos
            }
            st.rerun()

        except Exception as e:
            st.error(f"Error en el procesamiento: {e}")
            st.exception(e)


# ═════════════════════════════════════════════════════════════════════════════
# RESULTADOS
# ═════════════════════════════════════════════════════════════════════════════
if st.session_state.get('analisis_finalizado'):
    fd            = st.session_state['final_data']
    ctx           = fd['contexto']
    atc_results   = fd['atc']
    cand_results  = fd['candidatas']
    bau_results   = fd['bau']
    inv_results   = fd['inventario_full']
    mapas_dict    = fd.get('mapas', {})
    anos          = fd.get('anos', 20)
    tasa_bau      = bau_results.get('tasa_bau_anual', 0.001)

    st.success("✅ Análisis Finalizado")

    m1, m2, m3 = st.columns(3)
    m1.metric("Bioma Impactado",      ctx['bioma_principal'])
    m2.metric("ATC Rango 1",          f"{atc_results['Rango 1']['atc_total']:.2f} ha")
    m3.metric("Tasa BAU Anual",       f"{tasa_bau:.4%}")

    tab_rangos, tab_mapas, tab_fcafu = st.tabs([
        "📊 Comparativa de Rangos y Adicionalidad",
        "🗺️ Mapas Interactivos",
        "🌲 Detalle FCAFU"
    ])

    # ── Tab 1: Adicionalidad ─────────────────────────────────────────────────
    with tab_rangos:
        st.markdown("#### Suficiencia de Hectáreas y Adicionalidad por Rango")
        rows = []
        for r, rd in atc_results.items():
            cd          = cand_results.get(r, {})
            total_disp  = cd.get('total', 0)
            atc_req     = rd['atc_total']
            
            # Adicionalidad = Ha a compensar (ATC) * tasa_BAU * años * factor_efectividad
            adic_cons = atc_req * tasa_bau * anos * 0.85
            adic_rest = atc_req * tasa_bau * anos * 0.75

            rows.append({
                "Rango":                r,
                "ATC Req. (ha)":        round(atc_req, 2),
                "Há Conservar":         round(cd.get('ha_conservar', 0), 2),
                "Há Restaurar":         round(cd.get('ha_restaurar', 0), 2),
                "Total Disp. (ha)":     round(total_disp, 2),
                "Cubre Req.":           "✅ SÍ" if total_disp >= atc_req else "❌ NO",
                "Adic. Conservar":      round(adic_cons, 3),
                "Adic. Restaurar":      round(adic_rest, 3),
            })
        df_comp = pd.DataFrame(rows)

        def col_fila(row):
            c = "background-color:#fff3cd" if row["Cubre Req."] == "❌ NO" else ""
            return [c] * len(row)

        st.dataframe(df_comp.style.apply(col_fila, axis=1),
                     use_container_width=True, hide_index=True)
        st.info("💡 **Fórmula Adicionalidad**: `ATC Requerido (ha) × Tasa BAU Anual × Años del Proyecto × Factor de Efectividad`")

        # Bloque de efectividad fijo
        st.markdown("---")
        st.markdown("### Factores de Efectividad y Referencias")
        st.markdown("""
<div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 5px solid #2e7d32; margin-bottom: 10px;">
    <h4>🌳 CONSERVAR (cerramiento) &nbsp;&nbsp;&nbsp;&nbsp; <b>Factor: 0.85</b></h4>
    <hr style="margin: 5px 0;">
    <a href="https://doi.org/10.1073/pnas.0800437105" target="_blank" style="text-decoration: none;">🔗 Andam et al. (2008) — PNAS</a><br>
    <a href="https://doi.org/10.1016/j.worlddev.2013.01.011" target="_blank" style="text-decoration: none;">🔗 Pfaff et al. (2014) — World Dev.</a>
</div>

<div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 5px solid #FF8C00;">
    <h4>🌱 RESTAURAR (siembra activa) &nbsp;&nbsp;&nbsp;&nbsp; <b>Factor: 0.75</b></h4>
    <hr style="margin: 5px 0;">
    <a href="https://doi.org/10.1126/sciadv.1701345" target="_blank" style="text-decoration: none;">🔗 Crouzeilles et al. (2017) — Sci.Adv.</a><br>
    <a href="https://repository.humboldt.org.co" target="_blank" style="text-decoration: none;">🔗 González-M. et al. (2018) — IAvH</a>
</div>
        """, unsafe_allow_html=True)


    # ── Tab 2: Mapas Interactivos ────────────────────────────────────────────
    with tab_mapas:
        st.markdown("#### Zonificación en las 6 Jerarquías")
        
        st.markdown("""
        **Leyenda:** 
        - 🟦 Borde azul: Límite del rango
        - 🟨 Amarillo: Polígono del impacto
        - 🟩 Verde oscuro: Candidatas a Conservar (Natural)
        - 🟧 Naranja: Candidatas a Restaurar (Transformado)
        - 🟥 Rojo semitransparente: Excluidas por RUNAP
        - ⬜ Borde blanco punteado: Polígonos seleccionados para el Plan (simulado en Conservar/Restaurar)
        """)

        for r_name in ["Rango 1", "Rango 2", "Rango 3", "Rango 4", "Rango 5", "Rango 6"]:
            with st.expander(f"🗺️ Mapa Interactivo: {r_name}", expanded=(r_name=="Rango 1")):
                m_folium = mapas_dict.get(r_name)
                if m_folium is not None:
                    st_folium(m_folium, width=1000, height=500, returned_objects=[])
                else:
                    st.warning(f"No se pudo generar el mapa para {r_name}")

    # ── Tab 3: FCAFU ─────────────────────────────────────────────────────────
    with tab_fcafu:
        st.markdown("#### Cálculo del Factor por Cobertura (FCAFU)")
        rows_f = [
            {"Cobertura": cob, "N": d['N'],
             "Criterio A": d['A'], "Criterio B": round(d['B'],3),
             "Criterio C": d['C'], "FCAFU": round(d['FCAFU'],3)}
            for cob, d in inv_results.items()
        ]
        st.table(pd.DataFrame(rows_f))


    # ── Descargas ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 Descargar Reportes Finales")
    d1, d2 = st.columns(2)

    excel_name = f"ATC_{fd['codigo']}.xlsx"
    excel_path = os.path.join(settings.OUTPUTS_DIR, excel_name)
    
    # Adaptar los reportes en el futuro para que coincidan con la nueva tabla
    # Por ahora simplemente permitimos descarga de lo que ya genera reportes.generar_reporte_excel
    try:
        reportes.generar_reporte_excel(fd, excel_path)
        with d1:
            with open(excel_path, "rb") as f:
                st.download_button("📊 Descargar Matriz Excel", f, file_name=excel_name)
    except Exception as e:
        st.warning(f"No se pudo generar Excel: {e}")

    word_name = f"Informe_{fd['codigo']}.docx"
    word_path = os.path.join(settings.OUTPUTS_DIR, word_name)
    try:
        reportes.generar_reporte_word(fd, word_path)
        with d2:
            with open(word_path, "rb") as f:
                st.download_button("📄 Descargar Informe Word (GF-PN-01)", f, file_name=word_name)
    except Exception as e:
        st.warning(f"No se pudo generar Word: {e}")
