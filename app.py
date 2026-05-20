# -*- coding: utf-8 -*-
"""
App de Planes de Compensación Biótica - Unergy
Manual 2026 (Resolución 0305/2026 MADS) - Versión 5

NUEVO en esta versión:
  - Adicionalidad mostrada por horizonte: anual, 3 años, 5 años, 15 años.
  - Tasa BAU calculada dinámicamente con Hansen GFC por municipio.
  - Lee áreas reales por cobertura del KMZ.
"""
import streamlit as st
import pandas as pd
import os
import tempfile

from core import inputs, contexto, inventario, atc, utils
from config import settings


st.set_page_config(
    page_title="Compensación Biótica - Unergy",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 App de Planes de Compensación Biótica")
st.markdown("**Metodología:** Manual 2026 (Resolución 0305/2026 MADS) - Versión 5")
st.caption("Tasa BAU calculada con Hansen GFC por municipio. Adicionalidad por horizonte.")


with st.sidebar:
    st.header("1. Carga de Datos")
    impacto_file = st.file_uploader(
        "KMZ del Proyecto (con folders Proyecto/Coberturas)",
        type=["kmz", "kml"]
    )
    excel_file = st.file_uploader(
        "Inventario Forestal (Excel)",
        type=["xlsx", "xls"]
    )
    st.markdown("---")
    st.info(
        "**Estructura esperada del KMZ:**\n"
        "- 📁 Proyecto → con polígono 'Minigranja'\n"
        "- 📁 Coberturas vegetales → polígonos por tipo\n"
        "- 📁 Árboles (opcional, se ignora)\n\n"
        "**Columnas del Excel:**\n"
        "- Nombre científico, DAP a (m), Cobertura, AB t (m2)"
    )
    st.markdown("---")
    dap_min = st.number_input(
        "DAP mínimo (cm)",
        min_value=1.0, max_value=30.0,
        value=float(settings.DAP_MIN_DEFAULT), step=0.5,
    )


if impacto_file and excel_file:

    with st.spinner("Conectando a Google Earth Engine..."):
        success, msg = utils.init_gee_session()
        if not success:
            st.error(f"❌ {msg}")
            st.stop()
        st.success(f"✓ {msg}")

    with st.spinner("Leyendo polígono de impacto del KMZ..."):
        try:
            gdf_impacto = inputs.cargar_poligono_impacto(
                impacto_file, impacto_file.name
            )
            ok, msg = inputs.validar_geometria(gdf_impacto)
            if not ok:
                st.error(f"❌ {msg}")
                st.stop()
            gdf_proj = gdf_impacto.to_crs(epsg=3857)
            area_impacto_ha = gdf_proj.geometry.area.sum() / 10000
        except Exception as e:
            st.error(f"❌ Error leyendo el polígono: {e}")
            st.stop()

    with st.spinner("Leyendo coberturas del KMZ..."):
        try:
            coberturas_kmz = inputs.extraer_coberturas_de_kmz(
                impacto_file, impacto_file.name
            )
        except Exception as e:
            st.warning(f"⚠️ No se pudieron leer coberturas del KMZ: {e}")
            coberturas_kmz = {}

    with st.spinner("Obteniendo contexto geográfico + tasa BAU (Hansen)..."):
        try:
            ctx = contexto.obtener_contexto_impacto(gdf_impacto)
        except Exception as e:
            st.error(f"❌ Error contexto: {e}")
            st.stop()

    if coberturas_kmz:
        ctx['areas_cobertura'] = coberturas_kmz
        fuente_coberturas = "KMZ del proyecto (áreas reales)"
    else:
        fuente_coberturas = "IDEAM 1:100K (genérico)"
        st.warning(
            "⚠️ No se encontró el folder 'Coberturas vegetales' en el KMZ. "
            "Se usarán las áreas de IDEAM 1:100K (menos preciso)."
        )

    with st.spinner("Procesando inventario (FCAFU = 1 + A + B + C)..."):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(excel_file.getbuffer())
                excel_path = tmp.name
            fcafu_por_cobertura = inventario.procesar_inventario(
                excel_path, dap_min=dap_min
            )
            os.unlink(excel_path)
        except Exception as e:
            st.error(f"❌ Error procesando inventario: {e}")
            st.stop()

    with st.spinner("Calculando ATC por rango..."):
        try:
            atc_resultados = atc.calcular_atc_por_rangos(
                fcafu_por_cobertura, ctx
            )
        except Exception as e:
            st.error(f"❌ Error calculando ATC: {e}")
            st.stop()

    st.success("✅ Procesamiento completo")

    # ─── CONTEXTO ───
    st.markdown("---")
    st.header("📍 Contexto del Proyecto")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Área de Impacto", f"{area_impacto_ha:.2f} ha")
        st.write(f"**Municipio:** {ctx.get('municipio', 'n/d')}")
        st.write(f"**Departamento:** {ctx.get('departamento', 'n/d')}")
    with c2:
        st.write(f"**BIOMA-IAvH:** {ctx.get('bioma_principal', 'n/d')}")
        st.write(f"**ZH:** {ctx.get('zh', 'n/d')}")
        st.write(f"**SZH:** {ctx.get('szh', 'n/d')}")

    # ─── TASA BAU DINÁMICA ───
    tasa_bau = ctx.get('tasa_bau', 0.005)
    fuente_bau = ctx.get('tasa_bau_fuente', 'No disponible')
    st.markdown("---")
    st.subheader("🌲 Tasa de Pérdida de Bosque (BAU)")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.metric(
            "Tasa anual",
            f"{tasa_bau*100:.3f} %",
            help="Pérdida promedio anual sobre el bosque del municipio"
        )
    with c2:
        st.caption(f"**Fuente:** {fuente_bau}")
        st.caption("Dataset: Hansen GFC v1.12 (Universidad de Maryland)")

    # ─── COBERTURAS ───
    st.subheader(f"Coberturas Impactadas ({fuente_coberturas})")
    if ctx.get('areas_cobertura'):
        df_cob = pd.DataFrame([
            {"Cobertura": k, "Área (ha)": round(v, 4)}
            for k, v in ctx['areas_cobertura'].items()
        ])
        total_cob = sum(ctx['areas_cobertura'].values())
        df_cob.loc[len(df_cob)] = ["TOTAL", round(total_cob, 4)]
        st.dataframe(df_cob, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ No se detectaron coberturas.")

    # ─── FCAFU ───
    st.markdown("---")
    st.header("🌳 FCAFU por Cobertura")
    st.caption("Fórmula del Manual 2026: FCAFU = 1 + A + B + C")
    if fcafu_por_cobertura:
        df_fcafu = pd.DataFrame([
            {
                "Cobertura": cob,
                "N (individuos)": d.get('N', 0),
                "S (especies)": d.get('S', 0),
                "A (cobertura)": round(d.get('A', 0) or 0, 3),
                "B (amenaza)": round(d.get('B', 0) or 0, 3),
                "C (mezcla)": round(d.get('C', 0) or 0, 3),
                "FCAFU": round(d.get('FCAFU', 0) or 0, 3)
            }
            for cob, d in fcafu_por_cobertura.items()
        ])
        st.dataframe(df_fcafu, use_container_width=True, hide_index=True)
        amenazadas_total = []
        for cob, d in fcafu_por_cobertura.items():
            for sp in d.get('amenazadas', []):
                amenazadas_total.append({**sp, 'cobertura': cob})
        if amenazadas_total:
            with st.expander(f"⚠️ Especies amenazadas ({len(amenazadas_total)})"):
                st.dataframe(pd.DataFrame(amenazadas_total), hide_index=True)
    else:
        st.warning(
            "⚠️ El inventario no generó cálculos FCAFU. "
            "Verifica que el Excel tenga columnas **Nombre científico**, "
            "**DAP a (m)** y **Cobertura** llenas para cada árbol."
        )

    # ─── ATC ───
    st.markdown("---")
    st.header("📐 Área Total a Compensar (ATC) por Rango")
    st.caption("Fórmula: ATC = Σ (área_cobertura × (FCAFU + factor_rango))")
    if atc_resultados:
        df_atc = pd.DataFrame([
            {
                "Rango": rango_id,
                "Factor +": data['factor_adicional'],
                "ATC total (ha)": round(data['atc_total'], 3),
            }
            for rango_id, data in atc_resultados.items()
        ])
        st.dataframe(df_atc, use_container_width=True, hide_index=True)
        for rango_id, data in atc_resultados.items():
            with st.expander(f"Ver detalle de {rango_id}"):
                if data.get('detalles'):
                    df_det = pd.DataFrame(data['detalles'])
                    st.dataframe(df_det, use_container_width=True, hide_index=True)

    # ════════════════════════════════════════════════════════════════
    # ADICIONALIDAD POR HORIZONTE (NUEVO)
    # ════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("🌱 Adicionalidad Esperada")

    F_CONSERVAR = 0.85
    F_RESTAURAR = 0.75
    HORIZONTES = [3, 5, 15]  # años a mostrar

    st.markdown(
        f"**Tasa BAU usada:** `{tasa_bau*100:.3f}%` anual "
        f"(Hansen sobre {ctx.get('municipio', 'municipio')})"
    )

    # ─── CONSERVAR ─────────────────────────────────────────────────
    st.subheader("🌳 Escenario CONSERVAR (cerramiento)")
    st.caption(
        "Hectáreas que NO se pierden por proteger el área. "
        "Fórmula: `ATC × tasa_BAU × años × 0.85`"
    )
    if atc_resultados:
        filas = []
        for rango_id, data in atc_resultados.items():
            atc_total = data['atc_total']
            por_anio = atc_total * tasa_bau * F_CONSERVAR
            filas.append({
                "Rango": rango_id,
                "ATC (ha)": round(atc_total, 2),
                "Adic/año (ha)": round(por_anio, 4),
                "A 3 años (ha)": round(por_anio * 3, 3),
                "A 5 años (ha)": round(por_anio * 5, 3),
                "A 15 años (ha)": round(por_anio * 15, 3),
            })
        df_cons = pd.DataFrame(filas)
        st.dataframe(df_cons, use_container_width=True, hide_index=True)

    # ─── RESTAURAR ─────────────────────────────────────────────────
    st.subheader("🌱 Escenario RESTAURAR (siembra)")
    st.caption(
        "Hectáreas que SE ganan por siembra activa. "
        "Fórmula: `ATC × 0.75` (independiente del horizonte temporal)"
    )
    if atc_resultados:
        filas_r = []
        for rango_id, data in atc_resultados.items():
            atc_total = data['atc_total']
            filas_r.append({
                "Rango": rango_id,
                "ATC (ha)": round(atc_total, 2),
                "Restaurar (ha)": round(atc_total * F_RESTAURAR, 3),
            })
        df_rest = pd.DataFrame(filas_r)
        st.dataframe(df_rest, use_container_width=True, hide_index=True)

    # ─── MIX 50/50 ─────────────────────────────────────────────────
    st.subheader("⚖️ Escenario MIX 50/50 (mitad cada uno)")
    st.caption(
        "Hectáreas adicionales si se reparte 50% Conservar + 50% Restaurar."
    )
    if atc_resultados:
        filas_m = []
        for rango_id, data in atc_resultados.items():
            atc_total = data['atc_total']
            mitad_atc = atc_total * 0.5
            restaurar_aporte = mitad_atc * F_RESTAURAR
            por_anio_cons = mitad_atc * tasa_bau * F_CONSERVAR
            filas_m.append({
                "Rango": rango_id,
                "ATC (ha)": round(atc_total, 2),
                "Adic Mix a 3 años": round(restaurar_aporte + por_anio_cons * 3, 3),
                "Adic Mix a 5 años": round(restaurar_aporte + por_anio_cons * 5, 3),
                "Adic Mix a 15 años": round(restaurar_aporte + por_anio_cons * 15, 3),
            })
        df_mix = pd.DataFrame(filas_m)
        st.dataframe(df_mix, use_container_width=True, hide_index=True)

    st.info(
        "**¿Qué horizonte usar?** Depende del mecanismo jurídico de Unergy:\n\n"
        "- **Compra/Usufructo del predio (30 años)** → usar la columna de 15+ años\n"
        "- **Acuerdo de conservación a 15 años** → usar la columna de 15 años\n"
        "- **Acuerdo a 3-5 años** → usar las columnas correspondientes\n\n"
        "**Restaurar no depende del horizonte** porque mide hectáreas físicamente sembradas."
    )

    # ─── MAPAS ───
    st.markdown("---")
    st.header("🗺️ Mapas y Análisis Espacial")
    st.info(
        "**Mapas de áreas candidatas (R1-R6) en Google Earth Engine.**\n\n"
        "1. `code.earthengine.google.com`\n"
        "2. Pegar `script_compensacion_v6_adicionalidad.js`\n"
        "3. Reemplazar el asset del impacto\n"
        "4. Run → Tasks → Run exportaciones\n"
        "5. Shapefiles a Drive → abrir en QGIS/ArcMap"
    )

    # ─── BIBLIOGRAFÍA ───
    st.markdown("---")
    st.header("📚 Factores de Efectividad — Fuentes")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🌳 CONSERVAR — Factor: 0.85**")
        st.markdown(
            "- Andam et al. (2008) PNAS — "
            "[10.1073/pnas.0800437105](https://doi.org/10.1073/pnas.0800437105)"
        )
        st.markdown(
            "- Pfaff et al. (2014) World Dev — "
            "[10.1016/j.worlddev.2013.01.011](https://doi.org/10.1016/j.worlddev.2013.01.011)"
        )
    with c2:
        st.markdown("**🌱 RESTAURAR — Factor: 0.75**")
        st.markdown(
            "- Crouzeilles et al. (2017) Sci Adv — "
            "[10.1126/sciadv.1701345](https://doi.org/10.1126/sciadv.1701345)"
        )
        st.markdown(
            "- González-M. et al. (2018) BST IAvH — "
            "[Ver](http://repository.humboldt.org.co/handle/20.500.11761/35442)"
        )
    st.markdown("---")
    st.caption(
        "**Tasa BAU**: Hansen et al. (2013) High-Resolution Global Maps of "
        "21st-Century Forest Cover Change. Science 342: 850-853. "
        "[10.1126/science.1244693](https://doi.org/10.1126/science.1244693)"
    )

else:
    st.info("👈 Sube un KMZ y el inventario forestal en el panel lateral.")
    st.markdown("---")
    st.markdown(
        "### Esta app calcula:\n\n"
        "1. **FCAFU** por cobertura (1 + A + B + C del Manual)\n"
        "2. **ATC** por rango usando áreas REALES del KMZ\n"
        "3. **Tasa BAU** dinámica del municipio (Hansen Global Forest Change)\n"
        "4. **Adicionalidad** por escenario (Conservar / Restaurar / Mix) "
        "y por horizonte temporal (anual, 3, 5, 15 años)\n\n"
        "El KMZ debe contener los folders **Proyecto** (impacto) y "
        "**Coberturas vegetales** (polígonos por tipo)."
    )
