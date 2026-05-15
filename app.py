# -*- coding: utf-8 -*-
"""
App de Planes de Compensación Biótica - Unergy
Manual 2026 (Resolución 0305/2026 MADS) - Versión 2

Esta versión utiliza el módulo core/ (no el archivo core.py legacy).
"""
import streamlit as st
import pandas as pd
import io
import os
import tempfile
import folium
from streamlit_folium import st_folium

# Módulo core/ (NO core.py legacy)
from core import inputs, contexto, inventario, atc, rangos, utils
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
st.markdown("**Metodología:** Manual 2026 (Resolución 0305/2026 MADS) - Versión 2")
st.caption("Solo adicionalidad por área (ha). La adicionalidad por biodiversidad queda para v2.")


# ═══════════════════════════════════════════════════════════════════
# SIDEBAR — CARGA DE DATOS
# ═══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("1. Carga de Datos")

    impacto_file = st.file_uploader(
        "Polígono de Impacto (KMZ / KML / ZIP-SHP)",
        type=["kmz", "kml", "zip"]
    )
    excel_file = st.file_uploader(
        "Inventario Forestal (Excel)",
        type=["xlsx", "xls"]
    )

    st.markdown("---")
    st.info(
        "**Columnas esperadas en el Excel:**\n"
        "- Nombre científico\n"
        "- DAP a (m) [se convierte a cm]\n"
        "- Cobertura\n"
        "- AB t (m2) [opcional]\n\n"
        "La app auto-detecta la fila de encabezado y los nombres "
        "alternativos de columnas."
    )

    st.markdown("---")
    dap_min = st.number_input(
        "DAP mínimo (cm)",
        min_value=1.0,
        max_value=30.0,
        value=settings.DAP_MIN_DEFAULT,
        step=0.5,
        help="Árboles con DAP menor a este valor se excluyen del cálculo del FCAFU"
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
            st.info(
                "Para usar la app necesitas configurar las credenciales de GEE.\n"
                "Sube el archivo `gee_service_account.json` a la carpeta `credentials/` "
                "o configura los Secrets de Streamlit Cloud."
            )
            st.stop()
        st.success(f"✓ {msg}")

    # ─── PASO 2: KMZ → contexto geográfico ─────────────────────────
    with st.spinner("Cargando polígono de impacto..."):
        try:
            gdf_impacto = inputs.cargar_poligono_impacto(
                impacto_file, impacto_file.name
            )
            ok, msg = inputs.validar_geometria(gdf_impacto)
            if not ok:
                st.error(f"❌ {msg}")
                st.stop()

            # Calcular área de impacto
            gdf_proj = gdf_impacto.to_crs(epsg=3857)
            area_impacto_ha = gdf_proj.geometry.area.sum() / 10000
        except Exception as e:
            st.error(f"❌ Error cargando el polígono: {e}")
            st.stop()

    with st.spinner("Cruzando con capas IDEAM, ZH y municipios..."):
        try:
            ctx = contexto.obtener_contexto_impacto(gdf_impacto)
        except Exception as e:
            st.error(f"❌ Error obteniendo contexto geográfico: {e}")
            st.stop()

    # ─── PASO 3: Procesar inventario forestal ──────────────────────
    with st.spinner("Procesando inventario forestal (FCAFU = 1 + A + B + C)..."):
        try:
            # Guardar el Excel temporal para que pandas pueda leerlo por path
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

    # ─── PASO 4: ATC por rango ─────────────────────────────────────
    with st.spinner("Calculando Área Total a Compensar por rango..."):
        try:
            atc_resultados = atc.calcular_atc_por_rangos(
                fcafu_por_cobertura, ctx
            )
        except Exception as e:
            st.error(f"❌ Error calculando ATC: {e}")
            st.stop()

    st.success("✅ Procesamiento completo")

    # ═══════════════════════════════════════════════════════════════
    # UI: BLOQUE 1 — CONTEXTO DEL PROYECTO
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

    # Coberturas impactadas según GEE
    if ctx.get('areas_cobertura'):
        st.subheader("Coberturas Impactadas (según IDEAM)")
        df_cob = pd.DataFrame([
            {"Cobertura": k, "Área (ha)": round(v, 4)}
            for k, v in ctx['areas_cobertura'].items()
        ])
        st.dataframe(df_cob, use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════════════════════════
    # UI: BLOQUE 2 — FCAFU CALCULADO
    # ═══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("🌳 FCAFU por Cobertura")
    st.caption("Fórmula del Manual 2026: FCAFU = 1 + A + B + C")

    df_fcafu = pd.DataFrame([
        {
            "Cobertura": cob,
            "N (individuos)": d['N'],
            "S (especies)": d['S'],
            "A (cobertura)": round(d['A'], 3),
            "B (amenaza)": round(d['B'], 3),
            "C (mezcla)": round(d['C'], 3),
            "FCAFU": round(d['FCAFU'], 3)
        }
        for cob, d in fcafu_por_cobertura.items()
    ])
    st.dataframe(df_fcafu, use_container_width=True, hide_index=True)

    # Mostrar amenazadas detectadas (si las hay)
    amenazadas_total = []
    for cob, d in fcafu_por_cobertura.items():
        for sp in d.get('amenazadas', []):
            amenazadas_total.append({**sp, 'cobertura': cob})

    if amenazadas_total:
        with st.expander(
            f"⚠️ Especies amenazadas detectadas ({len(amenazadas_total)})"
        ):
            st.dataframe(
                pd.DataFrame(amenazadas_total),
                use_container_width=True, hide_index=True
            )

    # ═══════════════════════════════════════════════════════════════
    # UI: BLOQUE 3 — ATC POR RANGO
    # ═══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("📐 Área Total a Compensar (ATC) por Rango")
    st.caption("Fórmula: ATC = Σ (área_cobertura × (FCAFU + factor_rango))")

    df_atc = pd.DataFrame([
        {
            "Rango": rango_id,
            "Factor +": data['factor_adicional'],
            "ATC total (ha)": round(data['atc_total'], 3),
        }
        for rango_id, data in atc_resultados.items()
    ])
    st.dataframe(df_atc, use_container_width=True, hide_index=True)

    # Detalle por rango en expanders
    for rango_id, data in atc_resultados.items():
        with st.expander(f"Ver detalle de {rango_id}"):
            df_det = pd.DataFrame(data['detalles'])
            st.dataframe(df_det, use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════════════════════════
    # UI: BLOQUE 4 — ADICIONALIDAD POR ÁREA
    # ═══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("🌱 Adicionalidad Esperada (solo área)")

    st.markdown(
        "**Conservar** (cerramiento): `ha × tasa_BAU × 15 × 0.85` → "
        "*hectáreas que NO se pierden gracias al Plan*"
    )
    st.markdown(
        "**Restaurar** (siembra activa): `ha × 0.75` → "
        "*hectáreas que SE ganan gracias al Plan*"
    )

    # Parámetros (provisionales — refinables)
    TASA_BAU = 0.0062  # 0.62% anual provisional Hansen
    HORIZONTE = settings.HORIZONTE_TEMPORAL
    F_CONSERVAR = 0.85
    F_RESTAURAR = 0.75

    df_adic = pd.DataFrame([
        {
            "Rango": rango_id,
            "ATC (ha)": round(data['atc_total'], 2),
            "Si todo Conservar (ha adic)": round(
                data['atc_total'] * TASA_BAU * HORIZONTE * F_CONSERVAR, 3
            ),
            "Si todo Restaurar (ha adic)": round(
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
    # UI: BLOQUE 5 — BIBLIOGRAFÍA
    # ═══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("📚 Factores de Efectividad — Fuentes")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🌳 CONSERVAR (cerramiento) — Factor: 0.85**")
        st.markdown(
            "- Andam et al. (2008) PNAS — "
            "[10.1073/pnas.0800437105]"
            "(https://doi.org/10.1073/pnas.0800437105)"
        )
        st.markdown(
            "- Pfaff et al. (2014) World Development — "
            "[10.1016/j.worlddev.2013.01.011]"
            "(https://doi.org/10.1016/j.worlddev.2013.01.011)"
        )
    with c2:
        st.markdown("**🌱 RESTAURAR (siembra activa) — Factor: 0.75**")
        st.markdown(
            "- Crouzeilles et al. (2017) Science Advances — "
            "[10.1126/sciadv.1701345]"
            "(https://doi.org/10.1126/sciadv.1701345)"
        )
        st.markdown(
            "- González-M. et al. (2018) Catálogo BST IAvH — "
            "[Ver]"
            "(http://repository.humboldt.org.co/handle/20.500.11761/35442)"
        )

else:
    st.info("👈 Sube un polígono de impacto y un inventario forestal en el panel lateral.")
    st.markdown("---")
    st.markdown(
        "Esta aplicación calcula automáticamente:\n\n"
        "1. **FCAFU** por cobertura impactada (criterios A, B, C del Manual 2026)\n"
        "2. **Área Total a Compensar (ATC)** para los 6 rangos jerárquicos\n"
        "3. **Adicionalidad esperada** según escenario (Conservar / Restaurar / Mix)\n\n"
        "Toda la lógica geoespacial se procesa en Google Earth Engine."
    )
