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

os.makedirs(settings.OUTPUTS_DIR, exist_ok=True)

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

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://unergy.io/wp-content/uploads/2021/05/Logo-Unergy-01.png", width=200)
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
    file_inv     = st.file_uploader("Inventario Forestal (Excel Unergy)", type=['xlsx'])

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

                # 2. Contexto GEE
                ctx = contexto.obtener_contexto_impacto(gdf_impacto)

                # 3. Inventario FCAFU
                inv_results = inventario.procesar_inventario(file_inv)

                # 4. ATC por Rangos
                atc_results = atc.calcular_atc_por_rangos(inv_results, ctx)

                # 5. Candidatas GEE — ahora incluye geom_geojson por rango
                cand_results = rangos.construir_areas_candidatas(gdf_impacto, ctx)

                # 6. BAU Hansen
                bau_results = adicionalidad.calcular_tasa_bau(ctx['bioma_principal'])

                # 7. Biodiversidad zona de IMPACTO (GBIF, buffer 10 km)
                with st.spinner("🔍 Consultando biodiversidad zona de impacto (GBIF)..."):
                    bd_impacto = biodiversidad.consultar_biodiversidad_zona(gdf_impacto)

                # 8. Biodiversidad zonas CANDIDATAS usando geometrías de GEE
                with st.spinner("🔍 Consultando biodiversidad zonas candidatas (GBIF)..."):
                    bd_candidatas = biodiversidad.consultar_biodiversidad_candidatas(cand_results)

                # 9. Índice de adicionalidad biótica
                score_bio, razon_bio = adicionalidad.calcular_adicionalidad_biotica(bd_impacto)

                st.session_state['analisis_finalizado'] = True
                st.session_state['final_data'] = {
                    'proyecto':        nombre_proyecto,
                    'codigo':          codigo_proyecto,
                    'contexto':        ctx,
                    'inventario_full': inv_results,
                    'atc':             atc_results,
                    'candidatas':      cand_results,
                    'bau':             bau_results,
                    'gdf_impacto':     gdf_impacto,
                    'biodiv':          bd_impacto,
                    'bd_candidatas':   bd_candidatas,
                    'score_biotico':   score_bio,
                    'razon_biotica':   razon_bio,
                    'mapa_url':        mapas.obtener_url_mapa_estatico(gdf_impacto, ctx['bioma_principal'])
                }

            except Exception as e:
                st.error(f"Hubo un error en el procesamiento: {str(e)}")
                st.exception(e)

# ============================================================
# RESULTADOS
# ============================================================
if st.session_state.get('analisis_finalizado'):
    final_data    = st.session_state['final_data']
    ctx           = final_data['contexto']
    atc_results   = final_data['atc']
    cand_results  = final_data['candidatas']
    bau_results   = final_data['bau']
    inv_results   = final_data['inventario_full']
    bd_impacto    = final_data.get('biodiv', {})
    bd_candidatas = final_data.get('bd_candidatas', {})
    score_bio     = final_data.get('score_biotico', 1.0)
    tasa_bau      = bau_results.get('tasa_bau_anual', 0.001)

    st.success("✅ Análisis Finalizado")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Bioma Impactado",      ctx['bioma_principal'])
    m2.metric("ATC Rango 1",          f"{atc_results['Rango 1']['atc_total']:.2f} ha")
    m3.metric("Índice Adic. Biótica", f"x{score_bio}", help=final_data.get('razon_biotica', ''))
    m4.metric("Tasa BAU Anual",       f"{tasa_bau:.4%}")

    tab_res, tab_det, tab_biodiv = st.tabs([
        "📊 Comparativa de Rangos",
        "🌲 Detalle FCAFU",
        "🦋 Adicionalidad Biótica"
    ])

    # -------------------------------------------------------- TAB 1
    with tab_res:
        st.markdown("#### Suficiencia de Hectáreas por Rango")

        comp_list = []
        for r, r_data in atc_results.items():
            c_data      = cand_results.get(r, {})
            ha_cons     = c_data.get('ha_conservar', 0)
            ha_rest     = c_data.get('ha_restaurar', 0)
            total_disp  = c_data.get('total', 0)
            atc_req     = r_data['atc_total']
            factor      = r_data['factor_adicional']
            perdida_bau = total_disp * tasa_bau
            ha_evitadas = perdida_bau * score_bio

            comp_list.append({
                "Rango":                    r,
                "Factor Adic.":             factor,
                "ATC Req. (ha)":            round(atc_req, 2),
                "Há Conservar":             round(ha_cons, 2),
                "Há Restaurar":             round(ha_rest, 2),
                "Total Disp. (ha)":         round(total_disp, 2),
                "Cubre Req.":               "✅ SI" if total_disp >= atc_req else "❌ NO",
                "Pérdida BAU (ha/año)":     round(perdida_bau, 3),
                "Ha Evitadas (ha/año)":     round(ha_evitadas, 3),
            })

        df_comp = pd.DataFrame(comp_list)

        def colorear_fila(row):
            color = "background-color: #fff3cd" if row["Cubre Req."] == "❌ NO" else ""
            return [color] * len(row)

        st.dataframe(
            df_comp.style.apply(colorear_fila, axis=1),
            use_container_width=True,
            hide_index=True
        )

        st.info(
            "💡 **Ha Evitadas** = Total disponible × Tasa BAU × Índice biótico. "
            "Representa la pérdida de bosque que se previene al compensar en esa zona."
        )

        # Mapa debajo de la tabla
        if final_data.get('mapa_url'):
            st.markdown("#### 🗺️ Vista Preliminar GEE")
            st.image(final_data['mapa_url'], use_container_width=True)
        else:
            st.warning("No se pudo generar el mapa estático.")

    # -------------------------------------------------------- TAB 2
    with tab_det:
        st.markdown("#### Cálculo del Factor por Cobertura (FCAFU)")
        fcafu_df = []
        for cob, d in inv_results.items():
            fcafu_df.append({
                "Cobertura":  cob,
                "N":          d['N'],
                "Criterio A": d['A'],
                "Criterio B": round(d['B'], 3),
                "Criterio C": d['C'],
                "FCAFU":      round(d['FCAFU'], 3)
            })
        st.table(pd.DataFrame(fcafu_df))

    # -------------------------------------------------------- TAB 3
    with tab_biodiv:
        st.markdown("#### 🦋 Adicionalidad Biótica — Zona de Impacto vs. Zonas Candidatas")

        riqueza_impacto    = bd_impacto.get('riqueza_total', 0)
        amenazadas_impacto = bd_impacto.get('especies_amenazadas', [])

        # ---- Zona de impacto ----
        st.markdown("##### 📍 Zona de Impacto *(biodiversidad que el proyecto afecta)*")
        st.caption("Registros GBIF en radio de 10 km alrededor del polígono subido.")

        bi1, bi2, bi3 = st.columns(3)
        bi1.metric("Registros Totales",   bd_impacto.get('registros_totales', 0))
        bi2.metric("Riqueza de Especies", riqueza_impacto)
        bi3.metric("Spp. Amenazadas",     len(amenazadas_impacto))

        if amenazadas_impacto:
            st.warning("⚠️ **Amenazadas en zona de impacto:** " + ", ".join(amenazadas_impacto))

        if bd_impacto.get('taxones'):
            st.markdown("**Grupos taxonómicos — Zona de Impacto**")
            st.bar_chart(bd_impacto['taxones'])

        st.markdown("---")

        # ---- Zonas candidatas ----
        st.markdown("##### 🌿 Zonas Candidatas *(biodiversidad que la compensación protege o recupera)*")
        st.caption(
            "**Conservar** (Natural) = pérdida evitada de hábitat existente.  "
            "**Restaurar** (Transformado) = ganancia neta de hábitat.  "
            "**Δ Especies** = riqueza candidata − riqueza impacto."
        )

        bio_rows = []
        for r, bd_r in bd_candidatas.items():
            c_data       = cand_results.get(r, {})
            bd_tot       = bd_r.get('bd_total', {})
            riqueza_cand = bd_tot.get('riqueza_total', 0)
            delta        = riqueza_cand - riqueza_impacto
            amenazadas_c = len(bd_tot.get('especies_amenazadas', []))

            bio_rows.append({
                "Rango":                      r,
                "Há Conservar":               round(c_data.get('ha_conservar', 0), 2),
                "Há Restaurar":               round(c_data.get('ha_restaurar', 0), 2),
                "Riqueza Candidata":          riqueza_cand,
                "Riqueza Impacto":            riqueza_impacto,
                "Δ Especies (adicionalidad)": delta,
                "Spp Amenazadas Cand.":       amenazadas_c,
                "Valoración": (
                    "🟢 Alta ganancia"    if delta > 50 else
                    "🟡 Ganancia media"   if delta > 0  else
                    "🔴 Sin ganancia neta"
                )
            })

        df_bio = pd.DataFrame(bio_rows)

        def colorear_bio(row):
            d = row["Δ Especies (adicionalidad)"]
            if d > 50:
                c = "background-color: #d4edda"
            elif d > 0:
                c = "background-color: #fff3cd"
            else:
                c = "background-color: #f8d7da"
            return [c] * len(row)

        st.dataframe(
            df_bio.style.apply(colorear_bio, axis=1),
            use_container_width=True,
            hide_index=True
        )

        # Gráfico comparativo riqueza por rango
        st.markdown("**Comparativa de Riqueza: Zonas Candidatas vs. Zona de Impacto**")
        chart_data = pd.DataFrame({
            'Candidata': {r: bd_candidatas[r].get('bd_total', {}).get('riqueza_total', 0) for r in bd_candidatas},
            'Impacto':   {r: riqueza_impacto for r in bd_candidatas}
        })
        st.bar_chart(chart_data)

        st.info(
            "💡 Un **Δ positivo** confirma adicionalidad biótica real: la zona candidata alberga "
            "más especies que la zona afectada. Las hectáreas a **conservar** evitan la pérdida "
            "de ese hábitat; las de **restaurar** generan nueva ganancia neta."
        )

    # ---- Descargas ----
    st.markdown("---")
    st.markdown("### 📥 Descargar Reportes Finales")

    d_col1, d_col2 = st.columns(2)

    excel_name = f"ATC_{final_data['codigo']}.xlsx"
    excel_path = os.path.join(settings.OUTPUTS_DIR, excel_name)
    reportes.generar_reporte_excel(final_data, excel_path)
    with d_col1:
        with open(excel_path, "rb") as f:
            st.download_button("📊 Descargar Matriz Excel", f, file_name=excel_name)

    word_name = f"Informe_{final_data['codigo']}.docx"
    word_path = os.path.join(settings.OUTPUTS_DIR, word_name)
    reportes.generar_reporte_word(final_data, word_path)
    with d_col2:
        with open(word_path, "rb") as f:
            st.download_button("📄 Descargar Informe Word (GF-PN-01)", f, file_name=word_name)
