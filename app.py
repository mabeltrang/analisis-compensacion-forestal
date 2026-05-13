# -*- coding: utf-8 -*-
import streamlit as st
import os
import pandas as pd
from core import (
    inputs, inventario, utils, contexto,
    atc, rangos, adicionalidad, biodiversidad, reportes, mapas
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
    st.info("Procesa automáticamente los 5 rangos jerárquicos del Manual 2026.")

# ── Entradas ─────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    st.markdown("### 📝 Información Base")
    nombre_proyecto = st.text_input("Nombre del Proyecto", placeholder="Ej: P.S. Valledupar")
    codigo_proyecto = st.text_input("Código del Proyecto", placeholder="Ej: COLCES193")
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

            with st.spinner("🔍 Consultando biodiversidad zona de impacto (GBIF)..."):
                bd_impacto = biodiversidad.consultar_biodiversidad_zona(gdf_impacto)

            score_bio, razon_bio = adicionalidad.calcular_adicionalidad_biotica(bd_impacto)

            st.info("🦋 Consultando biodiversidad zonas candidatas (~2 min)…")
            prog_bar  = st.progress(0)
            prog_text = st.empty()

            def _cb(rango, i, total):
                pct = int(i / max(total, 1) * 100)
                prog_bar.progress(pct)
                prog_text.markdown(
                    f"*Procesando **{rango}** — {i}/{total} rangos completados*"
                )

            bd_candidatas = biodiversidad.consultar_biodiversidad_candidatas(
                cand_results, bd_impacto, progress_callback=_cb
            )
            prog_bar.progress(100)
            prog_text.markdown("✅ Consulta GBIF completada.")

            try:
                mapa_url = mapas.obtener_url_mapa_estatico(gdf_impacto, ctx['bioma_principal'])
            except Exception as e:
                st.warning(f"Mapa no disponible: {e}")
                mapa_url = None

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
                'mapa_url':        mapa_url,
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
    bd_impacto    = fd.get('biodiv', {})
    bd_candidatas = fd.get('bd_candidatas', {})
    score_bio     = fd.get('score_biotico', 1.0)
    tasa_bau      = bau_results.get('tasa_bau_anual', 0.001)
    riqueza_imp   = bd_impacto.get('riqueza_total', 0)
    especies_imp  = bd_impacto.get('especies', set())

    st.success("✅ Análisis Finalizado")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Bioma Impactado",      ctx['bioma_principal'])
    m2.metric("ATC Rango 1",          f"{atc_results['Rango 1']['atc_total']:.2f} ha")
    m3.metric("Índice Adic. Biótica", f"×{score_bio}", help=fd.get('razon_biotica',''))
    m4.metric("Tasa BAU Anual",       f"{tasa_bau:.4%}")

    tab_rangos, tab_fcafu, tab_biodiv = st.tabs([
        "📊 Comparativa de Rangos",
        "🌲 Detalle FCAFU",
        "🦋 Adicionalidad Biótica",
    ])

    # ── Tab 1 ────────────────────────────────────────────────────────────────
    with tab_rangos:
        st.markdown("#### Suficiencia de Hectáreas por Rango")
        rows = []
        for r, rd in atc_results.items():
            cd          = cand_results.get(r, {})
            total_disp  = cd.get('total', 0)
            atc_req     = rd['atc_total']
            perdida_bau = total_disp * tasa_bau
            ha_evitadas = perdida_bau * score_bio
            rows.append({
                "Rango":                r,
                "Factor Adic.":         rd['factor_adicional'],
                "ATC Req. (ha)":        round(atc_req, 2),
                "Há Conservar":         round(cd.get('ha_conservar', 0), 2),
                "Há Restaurar":         round(cd.get('ha_restaurar', 0), 2),
                "Total Disp. (ha)":     round(total_disp, 2),
                "Cubre Req.":           "✅ SÍ" if total_disp >= atc_req else "❌ NO",
                "Pérdida BAU (ha/año)": round(perdida_bau, 3),
                "Ha Evitadas (ha/año)": round(ha_evitadas, 3),
            })
        df_comp = pd.DataFrame(rows)

        def col_fila(row):
            c = "background-color:#fff3cd" if row["Cubre Req."] == "❌ NO" else ""
            return [c] * len(row)

        st.dataframe(df_comp.style.apply(col_fila, axis=1),
                     use_container_width=True, hide_index=True)
        st.info("💡 **Ha Evitadas** = Total disponible × Tasa BAU × Índice biótico.")

        if fd.get('mapa_url'):
            st.markdown("#### 🗺️ Vista Preliminar GEE")
            st.image(fd['mapa_url'], use_container_width=True)

    # ── Tab 2 ────────────────────────────────────────────────────────────────
    with tab_fcafu:
        st.markdown("#### Cálculo del Factor por Cobertura (FCAFU)")
        rows_f = [
            {"Cobertura": cob, "N": d['N'],
             "Criterio A": d['A'], "Criterio B": round(d['B'],3),
             "Criterio C": d['C'], "FCAFU": round(d['FCAFU'],3)}
            for cob, d in inv_results.items()
        ]
        st.table(pd.DataFrame(rows_f))

    # ── Tab 3: Adicionalidad Biótica ─────────────────────────────────────────
    with tab_biodiv:

        # ── Encabezado conceptual ────────────────────────────────────────────
        st.markdown("#### 🦋 Adicionalidad Biótica")
        st.markdown("""
La adicionalidad biótica responde a la pregunta:
**¿la zona donde voy a compensar es ecológicamente más valiosa que lo que el proyecto destruye?**

Para demostrarlo se comparan dos cosas:
- **Zona de impacto** → lo que el proyecto afecta (polígono subido).
- **Zonas candidatas** → donde se propone compensar, divididas en:
  - *Conservar* (cobertura Natural): hábitat que ya existe y se protege.
  - *Restaurar* (cobertura Transformada): área degradada que se recupera.

Se calculan dos métricas complementarias:
        """)

        col_a, col_b = st.columns(2)
        with col_a:
            st.info("""
**Métrica B — Amenazadas por hectárea**

Compara cuántas especies amenazadas
(Res. 0126/2024) hay *por hectárea* en
cada zona candidata vs. la zona de impacto.

→ Ratio > 1 = la compensación protege más
biodiversidad amenazada de la que destruye.
            """)
        with col_b:
            st.info("""
**Métrica C — Complementariedad**

¿Qué % de las especies de la zona candidata
**no están** en la zona de impacto?
Esas son las especies adicionales reales.

→ 70 % = 7 de cada 10 especies que protege
la compensación son nuevas respecto al impacto.
            """)

        st.markdown(
            "El **Score B+C** combina ambas métricas (60% complementariedad + 40% ratio amenazadas). "
            "🟢 Alta (>0.5) · 🟡 Media (0.2–0.5) · 🔴 Baja (<0.2)"
        )
        st.markdown("---")

        # ── Zona de impacto ──────────────────────────────────────────────────
        st.markdown("##### 📍 Zona de Impacto")
        st.caption(
            "Registros GBIF en un radio de 10 km alrededor del polígono. "
            "Estos son los valores de referencia contra los que se comparan todas las zonas candidatas."
        )

        bi1, bi2, bi3 = st.columns(3)
        bi1.metric(
            "Riqueza total",
            riqueza_imp,
            help="Número de especies distintas registradas en GBIF dentro del área de influencia del proyecto."
        )
        bi2.metric(
            "Spp. amenazadas",
            len(bd_impacto.get('especies_amenazadas', [])),
            help="Especies en categoría VU, EN o CR según Resolución 0126/2024 (MADS)."
        )
        bi3.metric(
            "Grupos con registros",
            len([k for k,v in bd_impacto.get('taxones',{}).items() if v > 0]),
            help="De los 5 grupos consultados: Aves, Plantas, Mamíferos, Reptiles, Anfibios."
        )

        amen_imp = bd_impacto.get('especies_amenazadas', [])
        if amen_imp:
            st.warning(
                "⚠️ **Especies amenazadas en zona de impacto** — "
                "su presencia eleva la exigencia de equivalencia ecológica: "
                + ", ".join(amen_imp)
            )
        else:
            st.success("✅ Sin especies amenazadas registradas en la zona de impacto.")

        taxones_imp = bd_impacto.get('taxones', {})
        if taxones_imp:
            st.markdown("**Riqueza por grupo taxonómico — Zona de Impacto**")
            st.caption("Número de especies de cada grupo registradas en GBIF.")
            st.bar_chart(pd.Series(taxones_imp))

        st.markdown("---")

        # ── Zonas candidatas ─────────────────────────────────────────────────
        st.markdown("##### 🌿 Zonas Candidatas — Métricas de Adicionalidad")
        st.caption(
            "Cada rango se evalúa en su zona a **Conservar** (Natural) y a **Restaurar** (Transformado). "
            "El **Score B+C** resume si la compensación en ese rango genera adicionalidad biótica real."
        )

        if not bd_candidatas:
            st.warning(
                "No se obtuvieron datos GBIF de zonas candidatas. "
                "Verifique que las geometrías GEE se hayan calculado correctamente."
            )
        else:
            # ── Tabla resumen ────────────────────────────────────────────────
            rows_b = []
            for r, bd_r in bd_candidatas.items():
                cd   = cand_results.get(r, {})
                cons = bd_r.get('conservar', {})
                rest = bd_r.get('restaurar', {})
                tot  = bd_r.get('total',     {})

                rows_b.append({
                    "Rango":             r,
                    # Conservar
                    "Há Conservar":      round(cd.get('ha_conservar', 0), 1),
                    "Spp Conservar":     cons.get('riqueza_zona', 0),
                    "Únicas Conservar":  cons.get('n_unicas', 0),
                    "Amen. Conservar":   cons.get('n_amenazadas_zona', 0),
                    "Compl. Conservar":  f"{cons.get('complementariedad', 0):.0%}",
                    # Restaurar
                    "Há Restaurar":      round(cd.get('ha_restaurar', 0), 1),
                    "Spp Restaurar":     rest.get('riqueza_zona', 0),
                    "Únicas Restaurar":  rest.get('n_unicas', 0),
                    "Amen. Restaurar":   rest.get('n_amenazadas_zona', 0),
                    "Compl. Restaurar":  f"{rest.get('complementariedad', 0):.0%}",
                    # Score
                    "Score B+C":         tot.get('score_bc', 0),
                    "Valoración":        tot.get('valoracion', '—'),
                })

            df_bio = pd.DataFrame(rows_b)

            def col_bio(row):
                s = row["Score B+C"]
                if s > 0.5:   c = "background-color:#d4edda"
                elif s > 0.2: c = "background-color:#fff3cd"
                else:         c = "background-color:#f8d7da"
                return [c] * len(row)

            st.dataframe(df_bio.style.apply(col_bio, axis=1),
                         use_container_width=True, hide_index=True)

            # ── Guía de lectura de la tabla ──────────────────────────────────
            with st.expander("📖 Cómo leer esta tabla"):
                st.markdown("""
| Columna | Qué mide | Cómo interpretar |
|---|---|---|
| **Spp Conservar / Restaurar** | Riqueza total de especies en esa zona (GBIF) | Referencia — no es comparable directo por diferencia de área |
| **Únicas Conservar / Restaurar** | Especies de esa zona que **no están** en la zona de impacto | Cuantas más, mayor adicionalidad real |
| **Amen. Conservar / Restaurar** | Especies amenazadas (Res. 0126/2024) presentes | Su protección es prioritaria para la CAR |
| **Compl. Conservar / Restaurar** | % de especies únicas sobre el total de la unión | >50% es buena adicionalidad; >70% es muy sólida |
| **Score B+C** | Métrica combinada 0–1 | >0.5 🟢 sustenta adicionalidad ante la CAR |
                """)

            # ── Gráfico complementariedad ────────────────────────────────────
            st.markdown("**Complementariedad por rango** *(% de especies únicas vs. zona de impacto)*")
            st.caption(
                "Una barra más alta significa que más especies de esa zona candidata "
                "son distintas a las del área afectada — mayor adicionalidad real."
            )
            chart_df = pd.DataFrame({
                'Conservar': {
                    r: bd_candidatas[r].get('conservar',{}).get('complementariedad', 0)
                    for r in bd_candidatas
                },
                'Restaurar': {
                    r: bd_candidatas[r].get('restaurar',{}).get('complementariedad', 0)
                    for r in bd_candidatas
                },
            })
            st.bar_chart(chart_df)

            # ── Detalle especies únicas del mejor rango ──────────────────────
            mejor_rango = max(
                bd_candidatas,
                key=lambda r: bd_candidatas[r].get('total', {}).get('score_bc', 0)
            )
            mejor_data  = bd_candidatas[mejor_rango]
            unicas_cons = mejor_data.get('conservar', {}).get('unicas_zona', [])
            unicas_rest = mejor_data.get('restaurar', {}).get('unicas_zona', [])
            score_mejor = mejor_data.get('total', {}).get('score_bc', 0)

            st.markdown(f"---")
            st.markdown(
                f"**🏆 Mejor rango: {mejor_rango}** — Score B+C: `{score_mejor}`  \n"
                f"Estas son las especies que **solo existen en la zona de compensación**, "
                f"no en la zona de impacto. Son el argumento más sólido de adicionalidad "
                f"para presentar ante la CAR."
            )

            d1, d2 = st.columns(2)
            with d1:
                st.markdown(
                    f"**Zona a Conservar (Natural)** — {len(unicas_cons)} especies únicas"
                )
                st.caption(
                    "Especies de hábitat natural que desaparecerían si esta zona no se protege."
                )
                if unicas_cons:
                    st.dataframe(
                        pd.DataFrame({'Especie': unicas_cons}),
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.info("Sin especies únicas detectadas en GBIF para esta zona.")

            with d2:
                st.markdown(
                    f"**Zona a Restaurar (Transformado)** — {len(unicas_rest)} especies únicas"
                )
                st.caption(
                    "Especies que podrían recuperarse al restaurar esta zona degradada."
                )
                if unicas_rest:
                    st.dataframe(
                        pd.DataFrame({'Especie': unicas_rest}),
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.info("Sin especies únicas detectadas en GBIF para esta zona.")

            st.success(
                "✅ **Conclusión de adicionalidad biótica:** "
                f"El {mejor_rango} presenta el mayor potencial de compensación. "
                f"Su complementariedad ({chart_df.get('Conservar', {}).get(mejor_rango, 0):.0%} Conservar / "
                f"{chart_df.get('Restaurar', {}).get(mejor_rango, 0):.0%} Restaurar) "
                "indica que la biodiversidad que se protege es en gran parte distinta "
                "a la afectada — criterio clave de adicionalidad biótica bajo el Manual 2026."
            )

    # ── Descargas ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 Descargar Reportes Finales")
    d1, d2 = st.columns(2)

    excel_name = f"ATC_{fd['codigo']}.xlsx"
    excel_path = os.path.join(settings.OUTPUTS_DIR, excel_name)
    reportes.generar_reporte_excel(fd, excel_path)
    with d1:
        with open(excel_path, "rb") as f:
            st.download_button("📊 Descargar Matriz Excel", f, file_name=excel_name)

    word_name = f"Informe_{fd['codigo']}.docx"
    word_path = os.path.join(settings.OUTPUTS_DIR, word_name)
    reportes.generar_reporte_word(fd, word_path)
    with d2:
        with open(word_path, "rb") as f:
            st.download_button("📄 Descargar Informe Word (GF-PN-01)", f, file_name=word_name)
