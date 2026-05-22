# -*- coding: utf-8 -*-
"""
App de Planes de Compensación Biótica - Unergy
Manual 2026 (Resolución 0305/2026 MADS) - Versión 6

NUEVO en esta versión:
  - Adicionalidad con fórmulas científicamente correctas:
      Conservar: acumulada exponencial (Hansen + Andam 2008 / Pfaff 2014)
      Restaurar: curva Chapman-Richards (Poorter 2016 + Crouzeilles 2017)
  - Restaurar muestra proyección por horizonte (no factor fijo).
  - Comparación Conservar vs Restaurar por ha compensada con ratio.
  - Nota metodológica expandible con citas y DOIs.
"""
import streamlit as st
import pandas as pd
import os
import tempfile
import io

from core import inputs, contexto, inventario, atc, utils
from core.atc import (
    adicionalidad_conservar,
    adicionalidad_conservar_anual,
    adicionalidad_restaurar,
    tabla_adicionalidad,
)
from config import settings


st.set_page_config(
    page_title="Compensación Biótica - Unergy",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 App de Planes de Compensación Biótica")
st.markdown("**Metodología:** Manual 2026 (Resolución 0305/2026 MADS) - Versión 6")
st.caption("Tasa BAU calculada con Hansen GFC por municipio. Adicionalidad con curvas científicas.")


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

    # ─── CONTEXTO ───────────────────────────────────────────────────────────
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

    # ─── TASA BAU ───────────────────────────────────────────────────────────
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

    # ─── COBERTURAS ─────────────────────────────────────────────────────────
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

    # ─── FCAFU ──────────────────────────────────────────────────────────────
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

    # ─── ATC ────────────────────────────────────────────────────────────────
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

    # ════════════════════════════════════════════════════════════════════════
    # ADICIONALIDAD POR HORIZONTE
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("🌱 Adicionalidad Esperada")

    TASA_BAU    = tasa_bau
    K_RESTAURAR = 0.076   # Chapman-Richards bs-T, Poorter 2016
    F_CONSERVAR = 0.85    # Andam 2008 / Pfaff 2014
    F_RESTAURAR = 0.75    # Crouzeilles 2017 / González-M 2018
    HORIZONTES  = [3, 5, 10, 15]

    st.markdown(
        f"**Tasa BAU usada:** `{TASA_BAU*100:.3f}%` anual "
        f"(Hansen GFC sobre {ctx.get('municipio', 'municipio')})"
    )

    # ─── NOTA METODOLÓGICA ──────────────────────────────────────────────────
    with st.expander("📖 Metodología y fuentes de las fórmulas"):
        st.markdown("""
**CONSERVAR — fórmula acumulada exponencial**

```
ha_adicional(n) = ha × [1 - (1 - tasa_BAU)ⁿ] × 0.85
```

- `[1 - (1 - tasa_BAU)ⁿ]` — probabilidad acumulada de deforestación en *n* años.
  Modelo de eventos independientes anuales. La tasa BAU se calcula con
  **Hansen et al. (2013)** sobre el municipio del impacto.
  DOI: [10.1126/science.1244693](https://doi.org/10.1126/science.1244693)

- `0.85` — fracción de la deforestación evitada que es realmente adicional.
  El 15% restante no se hubiera deforestado de todas formas (sesgo de selección).
  **Andam et al. (2008)** DOI: [10.1073/pnas.0800437105](https://doi.org/10.1073/pnas.0800437105) |
  **Pfaff et al. (2014)** DOI: [10.1016/j.worlddev.2013.01.011](https://doi.org/10.1016/j.worlddev.2013.01.011)

> *Nota: esta fórmula combina el modelo estocástico de Hansen con el factor de
efectividad de Andam/Pfaff. Es una construcción metodológica defendible, no
una ecuación de una sola fuente.*

---

**RESTAURAR — curva de Chapman-Richards (Poorter 2016)**

```
ha_adicional(n) = ha × [1 - e^(-0.076 × n)] × 0.75
```

- `[1 - e^(-k×n)]` — modelo de recuperación de biomasa en bosques tropicales
  secundarios. Curva asintótica: crece rápido al inicio y se estabiliza.
  k = 0.076 para bosques secos tropicales neotropicales.
  **Poorter et al. (2016)** Nature 530: 211-214.
  DOI: [10.1038/nature16469](https://doi.org/10.1038/nature16469)

- `0.75` — fracción de restauraciones activas que logran establecimiento exitoso.
  Para Bosque Seco Tropical colombiano.
  **Crouzeilles et al. (2017)** DOI: [10.1126/sciadv.1701345](https://doi.org/10.1126/sciadv.1701345) |
  **González-M. et al. (2018)** IAvH BST Colombia.
""")

    if atc_resultados:

        # ─── CONSERVAR ──────────────────────────────────────────────────────
        st.subheader("🌳 Escenario CONSERVAR (cerramiento)")
        st.caption(
            "Hectáreas que NO se pierden. "
            "Fórmula: `ha × [1 - (1 - tasa_BAU)ⁿ] × 0.85`"
        )
        filas_c = []
        for rango_id, data in atc_resultados.items():
            atc_total = data['atc_total']
            fila = {
                "Rango": rango_id,
                "ATC (ha)": round(atc_total, 2),
                "Adic/año (ha)": round(
                    adicionalidad_conservar_anual(atc_total, TASA_BAU, F_CONSERVAR), 4
                ),
            }
            for n in HORIZONTES:
                fila[f"A {n} años (ha)"] = round(
                    adicionalidad_conservar(atc_total, n, TASA_BAU, F_CONSERVAR), 4
                )
            filas_c.append(fila)
        st.dataframe(pd.DataFrame(filas_c), use_container_width=True, hide_index=True)

        # ─── RESTAURAR ──────────────────────────────────────────────────────
        st.subheader("🌱 Escenario RESTAURAR (siembra activa)")
        st.caption(
            "Hectáreas que SE ganan. "
            "Fórmula: `ha × [1 - e^(-0.076×n)] × 0.75` — curva Chapman-Richards"
        )
        filas_r = []
        for rango_id, data in atc_resultados.items():
            atc_total = data['atc_total']
            fila = {
                "Rango": rango_id,
                "ATC (ha)": round(atc_total, 2),
            }
            for n in HORIZONTES:
                fila[f"A {n} años (ha)"] = round(
                    adicionalidad_restaurar(atc_total, n, K_RESTAURAR, F_RESTAURAR), 4
                )
            filas_r.append(fila)
        st.dataframe(pd.DataFrame(filas_r), use_container_width=True, hide_index=True)
        st.caption(
            "💡 La ganancia no es lineal: crece rápido los primeros años "
            "y se estabiliza conforme el ecosistema madura."
        )

        # ─── COMPARACIÓN ────────────────────────────────────────────────────
        st.subheader("⚖️ Comparación Conservar vs Restaurar")
        st.caption("Por ha compensada — independiente del rango")
        filas_comp = []
        for n in HORIZONTES:
            cons_por_ha = adicionalidad_conservar(1.0, n, TASA_BAU, F_CONSERVAR)
            rest_por_ha = adicionalidad_restaurar(1.0, n, K_RESTAURAR, F_RESTAURAR)
            filas_comp.append({
                "Horizonte": f"{n} años",
                "Conservar (ha/ha)": round(cons_por_ha, 4),
                "Restaurar (ha/ha)": round(rest_por_ha, 4),
                "Ratio Rest/Cons": round(rest_por_ha / cons_por_ha, 1)
                    if cons_por_ha > 0 else "—"
            })
        st.dataframe(
            pd.DataFrame(filas_comp), use_container_width=True, hide_index=True
        )
        st.caption(
            "**Ratio:** cuántas veces más adicionalidad genera Restaurar vs Conservar "
            "por ha compensada. Restaurar siempre gana en número, pero Conservar "
            "protege bosque que ya existe con menor riesgo de falla."
        )

        # ─── MIX 50/50 ──────────────────────────────────────────────────────
        st.subheader("⚖️ Escenario MIX 50/50")
        st.caption("50% Conservar + 50% Restaurar del ATC total")
        filas_m = []
        for rango_id, data in atc_resultados.items():
            atc_total = data['atc_total']
            mitad = atc_total * 0.5
            fila = {"Rango": rango_id, "ATC (ha)": round(atc_total, 2)}
            for n in HORIZONTES:
                cons = adicionalidad_conservar(mitad, n, TASA_BAU, F_CONSERVAR)
                rest = adicionalidad_restaurar(mitad, n, K_RESTAURAR, F_RESTAURAR)
                fila[f"Mix {n} años (ha)"] = round(cons + rest, 4)
            filas_m.append(fila)
        st.dataframe(pd.DataFrame(filas_m), use_container_width=True, hide_index=True)

        st.info(
            "**¿Qué horizonte usar?**\n\n"
            "- Compra/Usufructo del predio (≥30 años) → columna de 15 años\n"
            "- Acuerdo de conservación a 15 años → columna de 15 años\n"
            "- Acuerdo a 3–5 años → columna correspondiente\n\n"
            "**Restaurar** genera más adicionalidad numérica. **Conservar** "
            "protege bosque existente con menor riesgo de falla."
        )

    # ─── DESCARGA EXCEL ─────────────────────────────────────────────────────
    st.markdown("---")
    st.header("📥 Descargar Resultados")

    def _build_excel(ctx, fcafu_por_cobertura, atc_resultados,
                     TASA_BAU, F_CONSERVAR, F_RESTAURAR, K_RESTAURAR,
                     HORIZONTES, area_impacto_ha):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:

            # Hoja 1 – Resumen del proyecto
            resumen = pd.DataFrame({
                "Variable": [
                    "Municipio", "Departamento", "BIOMA-IAvH",
                    "Zona Hidrográfica", "Subzona Hidrográfica",
                    "Área de impacto (ha)", "Tasa BAU anual (%)"
                ],
                "Valor": [
                    ctx.get("municipio", "n/d"),
                    ctx.get("departamento", "n/d"),
                    ctx.get("bioma_principal", "n/d"),
                    ctx.get("zh", "n/d"),
                    ctx.get("szh", "n/d"),
                    round(area_impacto_ha, 4),
                    round(TASA_BAU * 100, 4),
                ]
            })
            resumen.to_excel(writer, sheet_name="Resumen", index=False)

            # Hoja 2 – FCAFU por cobertura
            fcafu_rows = []
            for cob, d in fcafu_por_cobertura.items():
                fcafu_rows.append({
                    "Cobertura": cob,
                    "Individuos (N)": d["N"],
                    "Especies (S)": d["S"],
                    "S/N": round(d["SN"], 4),
                    "A (Ecosistema)": d["A"],
                    "B (Amenaza)": round(d["B"], 4),
                    "C (Composición)": d["C"],
                    "FCAFU": round(d["FCAFU"], 4),
                    "Área Basal total (m²)": round(d.get("area_basal_total", 0), 4),
                })
            pd.DataFrame(fcafu_rows).to_excel(writer, sheet_name="FCAFU", index=False)

            # Hoja 3 – ATC por rango
            atc_rows = []
            for rango_id, data in atc_resultados.items():
                atc_rows.append({
                    "Rango": rango_id,
                    "Factor Adicional": data.get("factor_adicional", ""),
                    "ATC total (ha)": round(data["atc_total"], 4),
                })
            pd.DataFrame(atc_rows).to_excel(writer, sheet_name="ATC_por_Rango", index=False)

            # Hoja 4 – Adicionalidad Conservar
            cons_rows = []
            for rango_id, data in atc_resultados.items():
                atc_total = data["atc_total"]
                fila = {
                    "Rango": rango_id,
                    "ATC (ha)": round(atc_total, 4),
                    "Adic/año (ha)": round(
                        adicionalidad_conservar_anual(atc_total, TASA_BAU, F_CONSERVAR), 6
                    ),
                }
                for n in HORIZONTES:
                    fila[f"A {n} años (ha)"] = round(
                        adicionalidad_conservar(atc_total, n, TASA_BAU, F_CONSERVAR), 6
                    )
                cons_rows.append(fila)
            pd.DataFrame(cons_rows).to_excel(writer, sheet_name="Adicionalidad_Conservar", index=False)

            # Hoja 5 – Adicionalidad Restaurar
            rest_rows = []
            for rango_id, data in atc_resultados.items():
                atc_total = data["atc_total"]
                fila = {
                    "Rango": rango_id,
                    "ATC (ha)": round(atc_total, 4),
                }
                for n in HORIZONTES:
                    fila[f"A {n} años (ha)"] = round(
                        adicionalidad_restaurar(atc_total, n, K_RESTAURAR, F_RESTAURAR), 6
                    )
                rest_rows.append(fila)
            pd.DataFrame(rest_rows).to_excel(writer, sheet_name="Adicionalidad_Restaurar", index=False)

            # Hoja 6 – Comparación por ha compensada
            comp_rows = []
            for n in HORIZONTES:
                cons_ha = adicionalidad_conservar(1.0, n, TASA_BAU, F_CONSERVAR)
                rest_ha = adicionalidad_restaurar(1.0, n, K_RESTAURAR, F_RESTAURAR)
                comp_rows.append({
                    "Horizonte (años)": n,
                    "Conservar (ha/ha)": round(cons_ha, 6),
                    "Restaurar (ha/ha)": round(rest_ha, 6),
                    "Ratio Rest/Cons": round(rest_ha / cons_ha, 2) if cons_ha > 0 else None,
                })
            pd.DataFrame(comp_rows).to_excel(writer, sheet_name="Comparacion_por_ha", index=False)

            # Hoja 7 – Especies amenazadas
            sp_rows = []
            for cob, d in fcafu_por_cobertura.items():
                for sp in d.get("amenazadas", []):
                    sp_rows.append({
                        "Cobertura": cob,
                        "Nombre científico": sp.get("Nombre cientifico", ""),
                        "Categoría": sp.get("categoria_amenaza", ""),
                    })
            if sp_rows:
                pd.DataFrame(sp_rows).to_excel(
                    writer, sheet_name="Especies_Amenazadas", index=False
                )

        buf.seek(0)
        return buf.getvalue()

    if atc_resultados and fcafu_por_cobertura:
        nombre_mun = ctx.get("municipio", "proyecto").replace(" ", "_")
        excel_bytes = _build_excel(
            ctx, fcafu_por_cobertura, atc_resultados,
            TASA_BAU, F_CONSERVAR, F_RESTAURAR, K_RESTAURAR,
            HORIZONTES, area_impacto_ha
        )
        st.download_button(
            label="⬇️ Descargar Excel de resultados",
            data=excel_bytes,
            file_name=f"compensacion_{nombre_mun}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.caption("Incluye: Resumen, FCAFU, ATC por rango, Adicionalidad Conservar/Restaurar, Comparación por ha, Especies amenazadas.")
    else:
        st.warning("⚠️ No hay resultados calculados aún. Carga el KMZ y el inventario primero.")

    # ─── MAPAS ──────────────────────────────────────────────────────────────
    st.markdown("---")
    st.header("🗺️ Mapas y Análisis Espacial")
    st.info(
        "**Mapas de áreas candidatas (R1-R6) en Google Earth Engine.**\n\n"
        "1. `code.earthengine.google.com`\n"
        "2. Pegar el script del rango correspondiente\n"
        "3. Reemplazar el asset del impacto\n"
        "4. Run → Tasks → Run exportaciones\n"
        "5. Shapefiles a Drive → abrir en QGIS/ArcMap"
    )

    # ─── BIBLIOGRAFÍA ───────────────────────────────────────────────────────
    st.markdown("---")
    st.header("📚 Fuentes y Factores de Efectividad")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🌳 CONSERVAR — Factor efectividad: 0.85**")
        st.markdown(
            "- Andam et al. (2008) PNAS — "
            "[10.1073/pnas.0800437105](https://doi.org/10.1073/pnas.0800437105)"
        )
        st.markdown(
            "- Pfaff et al. (2014) World Dev — "
            "[10.1016/j.worlddev.2013.01.011](https://doi.org/10.1016/j.worlddev.2013.01.011)"
        )
    with c2:
        st.markdown("**🌱 RESTAURAR — Factor efectividad: 0.75 | k = 0.076**")
        st.markdown(
            "- Poorter et al. (2016) Nature — "
            "[10.1038/nature16469](https://doi.org/10.1038/nature16469)"
        )
        st.markdown(
            "- Crouzeilles et al. (2017) Sci Adv — "
            "[10.1126/sciadv.1701345](https://doi.org/10.1126/sciadv.1701345)"
        )
        st.markdown(
            "- González-M. et al. (2018) IAvH BST — "
            "[Ver](http://repository.humboldt.org.co/handle/20.500.11761/35442)"
        )
    st.caption(
        "**Tasa BAU**: Hansen et al. (2013). High-Resolution Global Maps of "
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
        "4. **Adicionalidad** por escenario y horizonte temporal:\n"
        "   - Conservar: curva exponencial acumulada (Andam 2008 / Pfaff 2014)\n"
        "   - Restaurar: curva Chapman-Richards (Poorter 2016 / Crouzeilles 2017)\n\n"
        "El KMZ debe contener los folders **Proyecto** (impacto) y "
        "**Coberturas vegetales** (polígonos por tipo)."
    )
