import streamlit as st
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
import core

st.set_page_config(page_title="Compensación Biótica - Unergy", page_icon="🌿", layout="wide")

st.title("🌿 App de Planes de Compensación Biótica")
st.markdown("**Metodología:** Manual 2026 (Resolución 0305/2026 MADS) - Versión 2")

with st.sidebar:
    st.header("1. Carga de Datos")
    st.markdown("Sube los archivos necesarios para evaluar el proyecto.")
    
    kmz_file = st.file_uploader("Polígono de Impacto (KMZ)", type=["kmz"])
    excel_file = st.file_uploader("Inventario Forestal (Excel)", type=["xlsx", "xls", "csv"])
    
    st.markdown("---")
    st.info("""
    **Columnas requeridas en Excel:**
    - `id_arbol`
    - `especie`
    - `dap_cm`
    - `altura_total_m`
    - `cobertura` (Clase CLC Nivel 3)
    - `amenaza` (CR, EN, VU, NT, LC)
    """)

if kmz_file and excel_file:
    # ---------------------------------------------------------
    # PROCESAMIENTO
    # ---------------------------------------------------------
    st.header("⚙️ Procesando Datos...")
    
    with st.spinner("Leyendo Inventario Forestal..."):
        if excel_file.name.endswith('.csv'):
            df_inv = pd.read_csv(excel_file)
        else:
            df_inv = pd.read_excel(excel_file)
            
        try:
            resultados_fcafu = core.procesar_inventario(df_inv)
        except Exception as e:
            st.error(f"Error procesando inventario: {e}")
            st.stop()
            
    with st.spinner("Extrayendo Geometría KMZ..."):
        try:
            gdf_impacto, area_impacto_ha = core.parse_kmz(kmz_file)
            geom_ee = core.gdf_to_ee_poly(gdf_impacto)
        except Exception as e:
            st.error(f"Error procesando KMZ: {e}")
            st.stop()
            
    with st.spinner("Consultando Google Earth Engine (esto puede tardar unos segundos)..."):
        try:
            core.init_gee()
            contexto, rangos = core.generar_rangos(geom_ee)
        except Exception as e:
            st.error(f"Error en GEE: {e}")
            st.stop()
            
    st.success("¡Datos procesados con éxito!")
    
    # ---------------------------------------------------------
    # UI: DATOS DEL PROYECTO
    # ---------------------------------------------------------
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📍 Localización")
        st.write(f"**Municipio:** {contexto['Municipio']}")
        st.write(f"**BIOMA-IAvH:** {contexto['BIOMA_IAvH']}")
        st.write(f"**ZH:** {contexto['ZH']} | **SZH:** {contexto['SZH']}")
        st.write(f"**Área Impacto:** {area_impacto_ha:.2f} ha")
        
    with col2:
        st.subheader("📊 Resultados FCAFU")
        for cob, datos in resultados_fcafu.items():
            if datos['tipo'] == 'natural':
                st.markdown(f"**{cob}** (Natural) -> **FCAFU: {datos['fcafu']:.2f}** (A:{datos['A']}, B:{datos['B']:.2f}, C:{datos['C']:.2f})")
            else:
                st.markdown(f"**{cob}** (Transformada) -> **Compensación 1:1**")

    # ---------------------------------------------------------
    # DESCARGA DE GDFs (RANGOS)
    # ---------------------------------------------------------
    st.header("🗺️ Análisis Espacial de Jerarquías (R1 - R2)")
    
    gdfs_descargados = {}
    rangos_ac = {}
    rangos_adic = {}
    
    tab1, tab2 = st.tabs(["Rango 1 (Mismo Bioma ∩ Municipio AI)", "Rango 2 (Mismo Bioma ∩ SZH)"])
    tabs = {'R1': tab1, 'R2': tab2}
    
    # Extraer factores y procesar AC y Adicionalidad
    for r_name in ['R1', 'R2']:
        rango_dict = rangos.get(r_name)
        if not rango_dict: continue
        
        with st.spinner(f"Descargando polígonos de {r_name}..."):
            gdf_rango = core.descargar_rango_gdf(rango_dict)
            gdfs_descargados[r_name] = gdf_rango
        
        if gdf_rango is None or gdf_rango.empty:
            tabs[r_name].warning(f"No se encontraron áreas candidatas o la respuesta fue muy grande para {r_name}.")
            continue
            
        # Cálculos AC (Area a compensar)
        ac_total = 0
        for cob, datos in resultados_fcafu.items():
            ac_parcial = core.calcular_area_a_compensar(datos['fcafu'], rango_dict['factor_adicional'], area_impacto_ha) # Asume que el Ai aplica completo a cada cob, en la vida real se dividiria por ha de cobertura.
            # NOTA: Para este MVP asumimos que el Ai total aplica. Si se debe dividir, se necesita la ha por cobertura.
            ac_total += ac_parcial
            
        ha_cons_disp = gdf_rango[gdf_rango['accion'] == 'Conservar']['area_ha'].sum()
        ha_rest_disp = gdf_rango[gdf_rango['accion'] == 'Restaurar']['area_ha'].sum()
        
        rangos_ac[r_name] = {'conservar': ha_cons_disp, 'restaurar': ha_rest_disp}
        
        adic_cons = core.calcular_adicionalidad(ac_total, 'Conservar')
        adic_rest = core.calcular_adicionalidad(ac_total, 'Restaurar')
        rangos_adic[r_name] = {'ac_total': ac_total, 'adic_cons': adic_cons, 'adic_rest': adic_rest}
        
        with tabs[r_name]:
            c1, c2, c3 = st.columns(3)
            c1.metric("Área a Compensar (AC)", f"{ac_total:.2f} ha")
            c2.metric("Disponible para Conservar", f"{ha_cons_disp:,.0f} ha")
            c3.metric("Disponible para Restaurar", f"{ha_rest_disp:,.0f} ha")
            
            st.markdown(f"**Adicionalidad Esperada:** Si todo es Conservar: **{adic_cons:.2f} ha** | Si todo es Restaurar: **{adic_rest:.2f} ha**")
            
            # Mapa simple con Folium
            m = folium.Map(location=[gdf_impacto.geometry.centroid.y.mean(), gdf_impacto.geometry.centroid.x.mean()], zoom_start=11)
            
            # Añadir impacto (rojo)
            folium.GeoJson(gdf_impacto, style_function=lambda x: {'color': 'red'}).add_to(m)
            
            # Añadir candidatos
            if not gdf_rango.empty:
                def style_fn(feature):
                    if feature['properties']['accion'] == 'Conservar':
                        return {'color': '#39FF14', 'fillColor': '#39FF14', 'weight': 1}
                    else:
                        return {'color': '#FF8C00', 'fillColor': '#FF8C00', 'weight': 1}
                folium.GeoJson(gdf_rango, style_function=style_fn).add_to(m)
            
            st_folium(m, width=800, height=400, key=f"map_{r_name}")

    # ---------------------------------------------------------
    # REFERENCIAS
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("""
    ┌─────────────────────────────────────────────────────┐  
    │  **FACTORES DE EFECTIVIDAD APLICADOS**                   │  
    ├─────────────────────────────────────────────────────┤  
    │                                                      │  
    │  🌳 **CONSERVAR** (cerramiento)        Factor: 0.85      │  
    │  ────────────────────────────────────────────       │  
    │  Andam et al. (2008) — PNAS          🔗 [Ver paper](https://doi.org/10.1073/pnas.0800437105)   │  
    │  Pfaff et al. (2014) — World Dev.    🔗 [Ver paper](https://doi.org/10.1016/j.worlddev.2013.01.011)   │  
    │                                                      │  
    │  🌱 **RESTAURAR** (siembra activa)     Factor: 0.75      │  
    │  ────────────────────────────────────────────       │  
    │  Crouzeilles et al. (2017) — Sci. Adv. 🔗 [Ver paper](https://doi.org/10.1126/sciadv.1701345) │  
    │  González-M. et al. (2018) — IAvH    🔗 [Ver paper](http://repository.humboldt.org.co/handle/20.500.11761/35442)   │  
    │                                                      │  
    └─────────────────────────────────────────────────────┘
    """)

    # ---------------------------------------------------------
    # EXPORTACIÓN
    # ---------------------------------------------------------
    st.header("📥 Descargables")
    st.markdown("Obtén el paquete con la memoria de cálculo, los Shapefiles de áreas y el Plan en Word.")
    
    # Creamos un Excel dummy de memoria de cálculo
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df_inv.to_excel(writer, sheet_name='Inventario Original', index=False)
        pd.DataFrame(resultados_fcafu).T.to_excel(writer, sheet_name='Resultados FCAFU')
    excel_buffer.seek(0)
    
    zip_buffer = core.generar_zip_descargables(gdfs_descargados, excel_buffer)
    docx_buffer = core.generar_reporte_docx(contexto, resultados_fcafu, area_impacto_ha, rangos_ac, rangos_adic)
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("Descargar Anexos (ZIP con Shapefiles y Excel)", data=zip_buffer, file_name="anexos_compensacion.zip", mime="application/zip")
    with c2:
        st.download_button("Descargar Reporte Word (.docx)", data=docx_buffer, file_name="Plan_Compensacion.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
else:
    st.info("👈 Sube un archivo KMZ y un Excel en el panel lateral para comenzar.")
