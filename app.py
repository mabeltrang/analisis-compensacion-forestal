# -*- coding: utf-8 -*-
"""
App de Planes de Compensación Biótica - Unergy
Manual 2026 (Resolución 0305/2026 MADS) - Versión 3

NUEVO en esta versión:
  - El KMZ debe contener carpetas 'Proyecto' (con Minigranja) y 'Coberturas vegetales'.
  - Lee áreas reales por cobertura desde el KMZ (no usa IDEAM genérico).
  - El ATC se calcula con FCAFU específico por cobertura: ATC = Σ (área × FCAFU).

Estructura esperada del KMZ:
  📁 Proyecto
      ├─ Polígono "Minigranja" (área de impacto)
  📁 Coberturas vegetales
      ├─ Polígono "2.3.1. Pastos limpios"
      ├─ Polígono "2.4.4. Mosaico de pastos con espacios naturales"
      └─ ...
  📁 Árboles  (se ignora, el inventario viene del Excel)
"""
import streamlit as st
import pandas as pd
import os
import tempfile

from core import inputs, contexto, inventario, atc, utils
from config import settings


# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ═══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Compensación Biótica - Unergy",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 App de Planes de Compensación Biótica")
st.markdown("**Metodología:** Manual 2026 (Resolución 0305/2026 MADS) - Versión 3")
st.caption("Lee áreas de coberturas directamente del KMZ. Mapas R1-R6 → script GEE Editor.")


# ═══════════════════════════════════════════════════════════════════
# SIDEBAR — CARGA DE DATOS
# ═══════════════════════════════════════════════════════════════════

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
        min_value=1.0,
        max_value=30.0,
        value=float(settings.DAP_MIN_DEFAULT),
        step=0.5,
    )


# ═══════════════════════════════════════════════════════════════════
# FLUJO PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

if impacto_file and excel_file:

    # ─── PASO 1: GEE ──────────────────────────────────────────────
    with st.spinner("Conectando a Google Earth Engine..."):
        success, msg = utils.init_gee_session()
        if not success:
            st.error(f"❌ {msg}")
            st.stop()
        st.success(f"✓ {msg}")

    # ─── PASO 2: KMZ → polígono impacto + coberturas ────────────
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

    with st.spinner("Obteniendo contexto geográfico (BIOMA, ZH, SZH)..."):
        try:
            ctx = contexto.obtener_contexto_impacto(gdf_impacto)
        except Exception as e:
            st.error(f"❌ Error contexto: {e}")
            st.stop()

    # Si encontramos coberturas en el KMZ, REEMPLAZAR las de IDEAM
    if coberturas_kmz:
        ctx['areas_cobertura'] = coberturas_kmz
        fuente_coberturas = "KMZ del proyecto (áreas reales)"
    else:
        fuente_coberturas = "IDEAM 1:100K (genérico)"
        st.warning(
            "⚠️ No se encontró el folder 'Coberturas vegetales' en el KMZ. "
            "Se usarán las áreas de IDEAM 1:100K (menos preciso)."
        )

    # ─── PASO 3: Inventario forestal ────────────────────────────
    with st.spinner("Procesando inventario (FCAFU = 1 + A + B + C)..."):
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".xlsx"
            ) as tmp:
                tmp.write(excel_file.getbuffer())
                excel_path = tmp.name
            fcafu_por_cobertura = inventario.procesar_inventario(
                excel_path, dap_min=dap_min
            )
            os.unlink(excel_path)
        except Exception as e:
            st.error(f"❌ Error procesando inventario: {e}")
            st.stop()

    # ─── PASO 4: ATC por rango ──────────────────────────────────
    with st.spinner("Calculando ATC por rango..."):
        try:
            atc_resultados = atc.calcular_atc_por_rangos(
                fcafu_por_cobertura, ctx
            )
        except Exception as e:
            st.error(f"❌ Error calculando ATC: {e}")
            st.stop()

    st.success("✅ Procesamiento completo")

    # ═══════════════════════════════════════════════════════════════
    # UI: BLOQUE 1 — CONTEXTO
    # ═══════════════════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════════════════
    # UI: BLOQUE 2 — FCAFU
    # ═══════════════════════════════════════════════════════════════
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
            with st.expander(
                f"⚠️ Especies amenazadas ({len(amenazadas_total)})"
            ):
                st.dataframe(pd.DataFrame(amenazadas_total), hide_index=True)
    else:
        st.warning("⚠️ Inventario sin FCAFU. Revisa columnas del Excel.")

    # ═══════════════════════════════════════════════════════════════
    # UI: BLOQUE 3 — ATC POR RANGO
    # ═══════════════════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════════════════
    # UI: BLOQUE 4 — ADICIONALIDAD
    # ═══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("🌱 Adicionalidad Esperada (solo área)")

    st.markdown(
        "**Conservar** (cerramiento): `ha × tasa_BAU × 15 × 0.85` → ha que NO se pierden\n\n"
        "**Restaurar** (siembra): `ha × 0.75` → ha que SE ganan"
    )

    TASA_BAU = 0.0062
    HORIZONTE = settings.HORIZONTE_TEMPORAL
    F_CONSERVAR = 0.85
    F_RESTAURAR = 0.75

    if atc_resultados:
        df_adic = pd.DataFrame([
            {
                "Rango": rango_id,
                "ATC (ha)": round(data['atc_total'], 2),
                "Conservar (ha adic)": round(
                    data['atc_total'] * TASA_BAU * HORIZONTE * F_CONSERVAR, 3
                ),
                "Restaurar (ha adic)": round(
                    data['atc_total'] * F_RESTAURAR, 3
                ),
                "Mix 50/50 (ha adic)": round(
                    0.5 * data['atc_total'] * TASA_BAU * HORIZONTE * F_CONSERVAR
                    + 0.5 * data['atc_total'] * F_RESTAURAR, 3
                )
            }
            for rango_id, data in atc_resultados.items()
        ])
        st.dataframe(df_adic, use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════════════════════════
    # UI: BLOQUE 5 — INSTRUCCIÓN MAPAS
    # ═══════════════════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════════════════
    # UI: BLOQUE 6 — BIBLIOGRAFÍA
    # ═══════════════════════════════════════════════════════════════
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

else:
    st.info("👈 Sube un KMZ y el inventario forestal en el panel lateral.")
    st.markdown("---")
    st.markdown(
        "### Esta app calcula:\n\n"
        "1. **FCAFU** por cobertura (1 + A + B + C del Manual)\n"
        "2. **ATC** por rango usando áreas REALES del KMZ\n"
        "3. **Adicionalidad** por escenario (Conservar / Restaurar / Mix)\n\n"
        "El KMZ debe contener los folders **Proyecto** (impacto) y "
        "**Coberturas vegetales** (polígonos por tipo)."
    )
