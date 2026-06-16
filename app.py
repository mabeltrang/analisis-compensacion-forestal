# -*- coding: utf-8 -*-
"""
App de Planes de Compensación Biótica — Unergy Energía Digital S.A.S. E.S.P.
Manual 2026 (Resolución 0305/2026 MADS) — Versión 7

Cambios v7:
- Criterio B corregido: VU=0.4 / EN=0.6 / CR=1.0 (Tabla 4 Manual 2026). NT=0.
- Doble escenario ATC: sin CITES (oficial) y con CITES (equiparación Unergy).
- Rediseño UI: colores corporativos Unergy, tabs, cards de métricas.
"""

import streamlit as st
import pandas as pd
import os, tempfile, io

from core import inputs, contexto, inventario, atc, utils
from core.atc import (
    adicionalidad_conservar,
    adicionalidad_conservar_anual,
    adicionalidad_restaurar,
)
from config import settings

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG Y ESTILOS
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Compensación Biótica · Unergy",
    page_icon="🌿",
    layout="wide",
)

PURPLE      = "#7B4CC9"
PURPLE_DARK = "#2D1B4E"
PURPLE_LIGHT= "#D9CEEF"
PURPLE_MID  = "#9B6FE8"
WHITE       = "#FFFFFF"
GRAY_TEXT   = "#3A3A52"

st.markdown(f"""
<style>
  /* ── Fondo general: blanco puro para máximo contraste ── */
  .stApp {{ background-color: #FFFFFF; }}

  /* ── Texto base oscuro — SIN tocar code/pre para no romper bloques de código ── */
  .stApp p, .stApp li {{ color: #1A1A2E; }}

  /* ── Header corporativo ── */
  .unergy-header {{
    background: {PURPLE_DARK};
    padding: 18px 32px 14px 32px;
    border-radius: 12px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 18px;
  }}
  .unergy-header h1 {{
    color: #FFFFFF !important;
    font-size: 1.55rem;
    font-weight: 700;
    margin: 0;
  }}
  .unergy-header p {{
    color: #C5B3F0 !important;
    font-size: 0.82rem;
    margin: 2px 0 0 0;
  }}
  .unergy-logo {{ font-size: 2.4rem; line-height: 1; }}

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
    background: {PURPLE_LIGHT};
    border-radius: 10px;
    padding: 4px;
    border: 1px solid #B8A9E0;
  }}
  /* Quitar línea indicadora default (la roja) */
  .stTabs [data-baseweb="tab-highlight"] {{
    display: none !important;
    background: transparent !important;
  }}
  .stTabs [data-baseweb="tab-border"] {{
    display: none !important;
  }}
  .stTabs [data-baseweb="tab"] {{
    border-radius: 8px !important;
    color: {PURPLE_DARK} !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    padding: 7px 18px !important;
    border: none !important;
    background: transparent !important;
  }}
  .stTabs [data-baseweb="tab"]:hover {{
    background: rgba(123,76,201,0.12) !important;
  }}
  .stTabs [aria-selected="true"] {{
    background: {PURPLE} !important;
    color: #FFFFFF !important;
    border-radius: 8px !important;
  }}
  /* Texto dentro del tab activo */
  .stTabs [aria-selected="true"] p,
  .stTabs [aria-selected="true"] span,
  .stTabs [aria-selected="true"] div {{
    color: #FFFFFF !important;
  }}

  /* ── Cards métricas ── */
  .metric-card {{
    background: #FFFFFF;
    border: 2px solid {PURPLE_LIGHT};
    border-left: 5px solid {PURPLE};
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(123,76,201,0.08);
  }}
  .metric-card .label {{
    font-size: 0.72rem;
    color: #5A5A72 !important;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 4px;
  }}
  .metric-card .value {{
    font-size: 1.35rem;
    font-weight: 800;
    color: {PURPLE_DARK} !important;
  }}
  .metric-card .sub {{
    font-size: 0.76rem;
    color: #5A5A72 !important;
    margin-top: 3px;
  }}

  /* ── Sección header ── */
  .section-header {{
    background: {PURPLE_LIGHT};
    border-left: 5px solid {PURPLE};
    border-radius: 0 8px 8px 0;
    padding: 9px 16px;
    margin: 20px 0 12px 0;
  }}
  .section-header h3 {{
    color: {PURPLE_DARK} !important;
    font-size: 1.05rem;
    font-weight: 800;
    margin: 0;
  }}

  /* ── Expanders: borde visible + texto oscuro ── */
  [data-testid="stExpander"] {{
    border: 1.5px solid #B8A9E0 !important;
    border-radius: 8px !important;
    background: #FAFAFA !important;
  }}
  [data-testid="stExpander"] summary {{
    color: {PURPLE_DARK} !important;
    font-weight: 700 !important;
    background: #F0EBF9 !important;
    border-radius: 6px !important;
    padding: 10px 14px !important;
  }}
  [data-testid="stExpander"] summary:hover {{
    background: {PURPLE_LIGHT} !important;
  }}
  /* Solo párrafos y listas — NO code/pre para no romper bloques de código */
  [data-testid="stExpander"] p,
  [data-testid="stExpander"] li {{
    color: #1A1A2E !important;
  }}

  /* ── Dataframes / tablas ── */
  [data-testid="stDataFrame"] {{
    border: 1.5px solid #B8A9E0;
    border-radius: 8px;
    overflow: hidden;
  }}

  /* ── Alerts / warnings / info con texto legible ── */
  [data-testid="stAlert"] {{
    border-left: 4px solid {PURPLE} !important;
  }}
  [data-testid="stAlert"] p {{
    color: #1A1A2E !important;
  }}
  div[data-baseweb="notification"] p {{ color: #1A1A2E !important; }}

  /* ── Captions ── */
  [data-testid="stCaptionContainer"] p {{ color: #4A4A62 !important; font-size: 0.8rem; }}

  /* ── Sidebar oscuro con texto blanco garantizado ── */
  [data-testid="stSidebar"] {{
    background: {PURPLE_DARK} !important;
    border-right: 3px solid {PURPLE};
  }}
  [data-testid="stSidebar"] *,
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] div {{
    color: #FFFFFF !important;
  }}
  [data-testid="stSidebar"] h3 {{ color: #C5B3F0 !important; }}
  [data-testid="stSidebar"] .stSelectbox > div > div {{
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    color: #FFFFFF !important;
  }}
  [data-testid="stSidebar"] .stFileUploader {{
    background: rgba(255,255,255,0.08) !important;
    border: 1.5px dashed rgba(255,255,255,0.4) !important;
    border-radius: 8px !important;
    padding: 8px !important;
  }}
  [data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.2) !important; }}

  /* ── Botón descarga ── */
  .stDownloadButton > button {{
    background: {PURPLE} !important;
    color: #FFFFFF !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    border: none !important;
    padding: 10px 24px !important;
    font-size: 0.95rem !important;
  }}
  .stDownloadButton > button:hover {{
    background: {PURPLE_DARK} !important;
    color: #FFFFFF !important;
  }}

  /* ── Métricas nativas de Streamlit ── */
  [data-testid="stMetric"] label {{ color: #5A5A72 !important; font-weight:600; }}
  [data-testid="stMetric"] [data-testid="stMetricValue"] {{ color: {PURPLE_DARK} !important; font-weight:800; }}

  /* ── Markdown general: párrafos oscuros, code blocks intactos ── */
  div[data-testid="stMarkdownContainer"] > p {{ color: #1A1A2E; }}
  div[data-testid="stMarkdownContainer"] > ul li {{ color: #1A1A2E; }}
  /* Bloques code/pre: fondo oscuro con texto claro (st.code) */
  /* code INLINE (backticks en markdown): fondo suave, texto morado oscuro */
  code {{
    background: #EDE7F9 !important;
    color: {PURPLE_DARK} !important;
    border-radius: 4px !important;
    padding: 1px 5px !important;
    font-size: 0.88em !important;
  }}
  /* Bloques de código completos (st.code / triple backtick): mantener tema oscuro */
  pre code {{
    background: transparent !important;
    color: inherit !important;
    padding: 0 !important;
  }}
  pre {{
    background: #1E1E2E !important;
    color: #CDD6F4 !important;
    border-radius: 8px !important;
    padding: 14px !important;
  }}
</style>
""", unsafe_allow_html=True)

# ── Header corporativo ────────────────────────────────────────────────────────
st.markdown(f"""
<div class="unergy-header">
  <div class="unergy-logo">🌿</div>
  <div>
    <h1>Planes de Compensación Biótica</h1>
    <p>Unergy Energía Digital S.A.S. E.S.P. &nbsp;·&nbsp;
       Manual 2026 (Res. 0305/2026 MADS) &nbsp;·&nbsp; v7</p>
  </div>
</div>
""", unsafe_allow_html=True)


def _metric_card(label, value, sub=""):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="metric-card">
      <div class="label">{label}</div>
      <div class="value">{value}</div>
      {sub_html}
    </div>""", unsafe_allow_html=True)


def _section(title, icon=""):
    st.markdown(
        f'<div class="section-header"><h3>{icon} {title}</h3></div>',
        unsafe_allow_html=True
    )


def _badge(cat):
    cls = f"badge-{cat}" if cat in ("CR","EN","VU","LC") else "badge-CITES"
    return f'<span class="{cls}">{cat}</span>'


def _render_tab_vedas(todas_vedas, car_proyecto):
    """Contenido completo del tab Vedas. Reutilizable con o sin inventario."""
    from config.vedas import VEDAS_NACIONALES, VEDAS_REGIONALES, consultar_veda

    _section("Vedas de Flora — Consulta y Cruce con Inventario", "🚫")

    st.info(
        "Las vedas **no modifican el FCAFU** ni el área de compensación, pero generan "
        "**obligaciones procedimentales** adicionales ante la CAR (concepto técnico, "
        "rescate, reubicación, censo 100%). Verifica siempre la norma vigente al momento "
        "de radicación."
    )

    # ── A: Cruce con inventario ───────────────────────────────────────────────
    if todas_vedas is not None:
        _section("Especies en Veda Detectadas en el Inventario", "📋")
        if todas_vedas:
            n_nac = sum(v['n_individuos'] for v in todas_vedas if 'nacional' in v.get('nivel', ''))
            n_reg = sum(v['n_individuos'] for v in todas_vedas if v.get('nivel') == 'regional')
            n_spp = len({v['nombre_cientifico'] for v in todas_vedas})
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Especies en veda", n_spp)
            col_b.metric("Ind. veda nacional", n_nac)
            col_c.metric("Ind. veda regional", n_reg)
            st.markdown("---")
            df_v = pd.DataFrame(todas_vedas)[
                ['cobertura', 'nombre_cientifico', 'n_individuos', 'nivel', 'norma', 'alerta']
            ]
            df_v.columns = ['Cobertura', 'Nombre científico', 'N ind.', 'Nivel', 'Norma', 'Alerta']
            st.dataframe(df_v, use_container_width=True, hide_index=True)
            if any('nacional' in v.get('nivel', '') for v in todas_vedas):
                st.error(
                    "**Obligaciones — veda nacional (Circular MADS 8201-2-808/2019):**\n"
                    "1. Censo al 100% de individuos fustales de la especie vedada.\n"
                    "2. Medidas in situ: rescate y reubicación de individuos.\n"
                    "3. Medidas ex situ: propagación en vivero y siembra en área de compensación.\n"
                    "4. Shapefile georreferenciado con localización de cada individuo vedado."
                )
            if any(v.get('nivel') == 'regional' for v in todas_vedas):
                car_txt = car_proyecto or "la CAR competente"
                st.warning(
                    f"**Obligaciones — veda regional ({car_txt}):**\n"
                    "1. Solicitud formal ante GIT Forestal de la CAR.\n"
                    "2. Concepto técnico favorable previo a cualquier intervención.\n"
                    "3. Justificación de interés público o condición de riesgo.\n"
                    "4. Medidas de compensación o reposición que determine la CAR."
                )
        else:
            st.success(
                "✅ Ninguna especie del inventario figura en la base de datos de vedas "
                f"(nacional ni {car_proyecto or 'regional'}). "
                "Verifica igualmente con la CAR competente antes de la radicación."
            )
        st.markdown("---")
    else:
        st.caption(
            "💡 Carga el KMZ y el inventario forestal para ver el cruce automático "
            "con las especies inventariadas."
        )
        st.markdown("---")

    # ── B: Vedas nacionales ───────────────────────────────────────────────────
    with st.expander(
        "🇨🇴 Vedas Nacionales — aplican en todo el territorio nacional",
        expanded=(todas_vedas is None)
    ):
        st.caption(
            "Fuentes: Res. 0316/1974 INDERENA · Ley 61/1985 · "
            "Res. 1602/1995 + Res. 020/1996 MADS"
        )
        st.markdown("---")
        for sp in VEDAS_NACIONALES:
            nombres_sci = " / ".join(f"*{n.capitalize()}*" for n in sp["sci_fragmentos"])
            st.markdown(
                f"**{sp['nombre_comun']}** &nbsp;({nombres_sci})  \n"
                f"<small>📋 {sp['norma']} &nbsp;|&nbsp; {sp['nota']}</small>",
                unsafe_allow_html=True,
            )
            st.markdown("---")

    # ── C: Vedas regionales ───────────────────────────────────────────────────
    _section("Vedas Regionales por CAR", "🏛️")
    cars_disponibles = sorted(VEDAS_REGIONALES.keys())
    default_cars = [car_proyecto] if car_proyecto and car_proyecto in VEDAS_REGIONALES else []
    cars_sel = st.multiselect(
        "Selecciona una o varias CARs",
        options=cars_disponibles,
        default=default_cars,
        help="Si seleccionaste una CAR en el sidebar, aparece preseleccionada.",
        key="vedas_cars_sel"
    )
    if not cars_sel:
        st.caption("Selecciona al menos una CAR para ver sus vedas regionales.")
    else:
        for car_key in cars_sel:
            datos = VEDAS_REGIONALES[car_key]
            tipo_badge = (
                "🔴 Veda indefinida" if datos.get("tipo") == "indefinida"
                else "🟡 Veda temporal"
            )
            st.markdown(f"### {car_key} — {tipo_badge}")
            st.markdown(
                f"📋 **Norma:** {datos['norma']}  \n"
                f"ℹ️ {datos['nota']}"
            )
            rows = [
                {
                    "Nombre común": sp["nombre_comun"],
                    "Nombre científico (fragmentos)": "; ".join(
                        n.capitalize() for n in sp["sci_fragmentos"]
                    ),
                }
                for sp in datos.get("spp", [])
            ]
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.markdown("---")

    # ── D: Buscador libre ─────────────────────────────────────────────────────
    _section("Buscador de Especie", "🔍")
    busqueda = st.text_input(
        "Ingresa nombre científico o común para verificar si está en veda",
        placeholder="ej. Anacardium excelsum · Samán · Ceiba pentandra",
        key="vedas_busqueda"
    )
    if busqueda.strip():
        resultado_nac = consultar_veda(busqueda.strip())
        hits_reg = []
        for ck in cars_disponibles:
            r = consultar_veda(busqueda.strip(), car=ck)
            if r["en_veda_regional"] and r.get("veda_regional_info"):
                info = r["veda_regional_info"].copy()
                info["car"] = ck
                hits_reg.append(info)
        if resultado_nac["en_veda_nacional"] or hits_reg:
            if resultado_nac["en_veda_nacional"]:
                info = resultado_nac["veda_nacional_info"]
                st.error(
                    f"🚫 **Veda NACIONAL** — {info['nombre_comun']}  \n"
                    f"📋 {info['norma']}  \n{info['nota']}"
                )
            for item in hits_reg:
                st.warning(
                    f"⚠️ **Veda REGIONAL** ({item['car']}) — "
                    f"{item.get('nombre_comun', busqueda)}  \n"
                    f"📋 {item['norma']}  \n{item['nota']}"
                )
        else:
            st.success(
                f"✅ **'{busqueda}'** no figura en la base de datos de vedas "
                "(nacional ni regional). Verifica también con la CAR competente."
            )
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    st.markdown("---")

    impacto_file = st.file_uploader(
        "KMZ del Proyecto",
        type=["kmz","kml"],
        help="Debe contener folders: Proyecto / Coberturas vegetales"
    )
    excel_file = st.file_uploader(
        "Inventario Forestal (Excel)",
        type=["xlsx","xls"],
    )

    st.markdown("---")
    dap_min = st.number_input(
        "DAP mínimo (cm)",
        min_value=1.0, max_value=30.0,
        value=float(settings.DAP_MIN_DEFAULT), step=0.5,
        help="CAP ≥ 31 cm → DAP ≈ 9.87 cm"
    )
    car_proyecto = st.selectbox(
        "CAR competente",
        options=[
            "", "CORPOCESAR", "CORPOGUAJIRA", "CRA", "CORPOBOYACA",
            "CDMB", "CAS", "CORPAMAG", "CORANTIOQUIA", "CORPOURABA",
            "CORTOLIMA", "CARDER", "CVC", "CRC", "CORPOCALDAS",
            "CAR", "CORPONOR",
        ],
        help="Para cruce con vedas regionales"
    )

    st.markdown("---")
    st.markdown("""
**Estructura KMZ:**
- 📁 Proyecto → polígono impacto
- 📁 Coberturas vegetales → por tipo

**Columnas Excel:**
- Nombre científico
- DAP a (m)
- Cobertura
- AB t (m2) *(opcional)*
    """)


# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA DE BIENVENIDA
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA DE BIENVENIDA
# ══════════════════════════════════════════════════════════════════════════════
if not impacto_file or not excel_file:
    _tab_vedas_only = st.tabs(["🚫 Vedas", "ℹ️ Cómo usar"])
    with _tab_vedas_only[0]:
        _render_tab_vedas(todas_vedas=None, car_proyecto=car_proyecto)
    with _tab_vedas_only[1]:
        st.markdown("### ¿Qué calcula esta app?")
        col1, col2, col3 = st.columns(3)
        with col1:
            _metric_card("1. Sube el KMZ", "📂", "Polígono de impacto + coberturas")
        with col2:
            _metric_card("2. Sube el Excel", "📊", "Inventario forestal Unergy")
        with col3:
            _metric_card("3. Obtén resultados", "📐", "FCAFU · ATC · Adicionalidad")
        st.markdown("---")
        st.markdown(f"""
    <div style="background:{PURPLE_LIGHT}; border-radius:10px; padding:20px 24px;">
      <ul style="color:{GRAY_TEXT}; margin:0; padding-left:18px; line-height:1.8;">
        <li><b>FCAFU</b> por cobertura — criterios A, B (oficial y con CITES) y C del Manual 2026</li>
        <li><b>ATC</b> por rango geográfico R1–R6 en dos escenarios: oficial y con CITES</li>
        <li><b>Tasa BAU</b> dinámica por municipio, SZH y ZH (Hansen GFC)</li>
        <li><b>Adicionalidad</b> a 3, 5, 10 y 15 años — Conservar y Restaurar</li>
        <li><b>Vedas</b> nacionales y regionales cruzadas con el inventario</li>
      </ul>
    </div>
        """, unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PROCESAMIENTO
# ══════════════════════════════════════════════════════════════════════════════
with st.spinner("Conectando a Google Earth Engine..."):
    success, msg = utils.init_gee_session()
    if not success:
        st.error(f"❌ {msg}")
        st.stop()

with st.spinner("Leyendo polígono de impacto..."):
    try:
        gdf_impacto = inputs.cargar_poligono_impacto(impacto_file, impacto_file.name)
        ok, msg = inputs.validar_geometria(gdf_impacto)
        if not ok:
            st.error(f"❌ {msg}"); st.stop()
        gdf_proj = gdf_impacto.to_crs(epsg=3116)
        area_impacto_ha = gdf_proj.geometry.area.sum() / 10000
    except Exception as e:
        st.error(f"❌ Error leyendo polígono: {e}"); st.stop()

with st.spinner("Leyendo coberturas del KMZ..."):
    try:
        coberturas_kmz = inputs.extraer_coberturas_de_kmz(impacto_file, impacto_file.name)
    except Exception as e:
        st.warning(f"⚠️ No se pudieron leer coberturas del KMZ: {e}")
        coberturas_kmz = {}

with st.spinner("Obteniendo contexto geográfico + tasas BAU (Hansen GFC)..."):
    try:
        ctx = contexto.obtener_contexto_impacto(gdf_impacto)
    except Exception as e:
        st.error(f"❌ Error contexto GEE: {e}"); st.stop()

if coberturas_kmz:
    ctx['areas_cobertura'] = coberturas_kmz
    fuente_coberturas = "KMZ del proyecto (áreas reales)"
else:
    fuente_coberturas = "IDEAM 1:100K (genérico)"
    st.warning("⚠️ No se encontró folder 'Coberturas vegetales' en el KMZ. Usando IDEAM 1:100K.")

with st.spinner("Procesando inventario forestal (criterios A, B, C)..."):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(excel_file.getbuffer())
            excel_path = tmp.name
        fcafu_por_cobertura = inventario.procesar_inventario(
            excel_path, dap_min=dap_min, car=car_proyecto
        )
        os.unlink(excel_path)
    except Exception as e:
        st.error(f"❌ Error procesando inventario: {e}"); st.stop()

with st.spinner("Calculando ATC por rango (escenario oficial)..."):
    try:
        atc_resultados = atc.calcular_atc_por_rangos(fcafu_por_cobertura, ctx)
    except Exception as e:
        st.error(f"❌ Error calculando ATC: {e}"); st.stop()

# ATC escenario CITES: mismo cálculo pero con FCAFU_cites
with st.spinner("Calculando ATC por rango (escenario con CITES)..."):
    try:
        # Crear copia temporal de fcafu con FCAFU_cites como FCAFU
        fcafu_cites_tmp = {}
        for cob, d in fcafu_por_cobertura.items():
            fcafu_cites_tmp[cob] = {**d, 'FCAFU': d.get('FCAFU_cites', d['FCAFU'])}
        atc_resultados_cites = atc.calcular_atc_por_rangos(fcafu_cites_tmp, ctx)
    except Exception as e:
        st.warning(f"⚠️ No se pudo calcular ATC con CITES: {e}")
        atc_resultados_cites = atc_resultados

st.success("✅ Procesamiento completo")

# Tasas BAU
tasa_bau     = ctx.get('tasa_bau', 0.005)
tasa_bau_szh = ctx.get('tasa_bau_szh', tasa_bau)
tasa_bau_zh  = ctx.get('tasa_bau_zh',  tasa_bau)
fuente_bau     = ctx.get('tasa_bau_fuente',     'Hansen GFC')
fuente_bau_szh = ctx.get('tasa_bau_szh_fuente', 'Hansen GFC')
fuente_bau_zh  = ctx.get('tasa_bau_zh_fuente',  'Hansen GFC')

TASA_POR_NIVEL = {
    "Rango 1": tasa_bau,     "Rango 2": tasa_bau_szh,
    "Rango 3": tasa_bau_zh,  "Rango 4": tasa_bau,
    "Rango 5": tasa_bau_szh, "Rango 6": tasa_bau_zh,
}
K_RESTAURAR = 0.076
F_CONSERVAR = 0.85
F_RESTAURAR = 0.75
HORIZONTES  = [3, 5, 10, 15]
TASA_BAU    = tasa_bau


# ══════════════════════════════════════════════════════════════════════════════
# TABS PRINCIPALES
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📍 Contexto",
    "🌳 FCAFU",
    "📐 ATC",
    "🌱 Adicionalidad",
    "📥 Exportar",
    "🚫 Vedas",
])


# ════════════════════════════════════════════════════════════════════════
# TAB 1 — CONTEXTO
# ════════════════════════════════════════════════════════════════════════
with tab1:
    _section("Contexto Geográfico del Proyecto", "📍")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _metric_card("Área de Impacto", f"{area_impacto_ha:.4f} ha")
    with c2:
        _metric_card("Municipio", ctx.get('municipio','n/d'))
    with c3:
        _metric_card("Departamento", ctx.get('departamento','n/d'))
    with c4:
        _metric_card("BIOMA-IAvH", ctx.get('bioma_principal','n/d'))

    c5, c6 = st.columns(2)
    with c5:
        _metric_card("Zona Hidrográfica (ZH)", ctx.get('zh','n/d'))
    with c6:
        _metric_card("Subzona Hidrográfica (SZH)", ctx.get('szh','n/d'))

    _section("Tasa de Pérdida de Bosque BAU (Hansen GFC)", "🌲")
    st.caption("Calculada con Hansen GFC 2001–2023 sobre cada unidad espacial. "
               "Cada nivel jerárquico usa la tasa de su unidad.")

    c7, c8, c9 = st.columns(3)
    with c7:
        _metric_card(
            f"Municipio · {ctx.get('municipio','n/d')}",
            f"{tasa_bau*100:.3f} %",
            f"Usada en R1 y R4 · {fuente_bau}"
        )
    with c8:
        _metric_card(
            f"SZH · {ctx.get('szh','n/d')}",
            f"{tasa_bau_szh*100:.3f} %",
            f"Usada en R2 y R5 · {fuente_bau_szh}"
        )
    with c9:
        _metric_card(
            f"ZH · {ctx.get('zh','n/d')}",
            f"{tasa_bau_zh*100:.3f} %",
            f"Usada en R3 y R6 · {fuente_bau_zh}"
        )

    _section(f"Coberturas Impactadas · {fuente_coberturas}", "🗺️")
    if ctx.get('areas_cobertura'):
        df_cob = pd.DataFrame([
            {"Cobertura": k, "Área (ha)": round(v, 4)}
            for k, v in ctx['areas_cobertura'].items()
        ])
        total_cob = sum(ctx['areas_cobertura'].values())
        df_cob.loc[len(df_cob)] = ["**TOTAL**", round(total_cob, 4)]
        st.dataframe(df_cob, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ No se detectaron coberturas.")


# ── Cálculo global de vedas detectadas (disponible para tab2 y tab6) ──
todas_vedas = []
for cob, d in fcafu_por_cobertura.items():
    for v in d.get('vedas_detectadas', []):
        todas_vedas.append({**v, 'cobertura': cob})

# ════════════════════════════════════════════════════════════════════════
# TAB 2 — FCAFU
# ════════════════════════════════════════════════════════════════════════
with tab2:

    if todas_vedas:
        n_nac = sum(v['n_individuos'] for v in todas_vedas if 'nacional' in v['nivel'])
        n_reg = sum(v['n_individuos'] for v in todas_vedas if v['nivel'] == 'regional')
        st.error(
            f"🚫 **Especies en veda detectadas** — "
            f"{n_nac} ind. en veda nacional · {n_reg} ind. en veda regional"
        )
        with st.expander(f"📋 Detalle especies en veda ({len(todas_vedas)} registros)", expanded=True):
            df_v = pd.DataFrame(todas_vedas)[
                ['cobertura','nombre_cientifico','n_individuos','nivel','norma','alerta']
            ]
            df_v.columns = ['Cobertura','Nombre científico','N ind.','Nivel','Norma','Alerta']
            st.dataframe(df_v, use_container_width=True, hide_index=True)
            if any('nacional' in v['nivel'] for v in todas_vedas):
                st.warning(
                    "**Obligaciones — veda nacional (Circular MADS 8201-2-808/2019):**\n"
                    "1. Censo al 100% de individuos fustales de especies vedadas.\n"
                    "2. Medidas de manejo in situ: rescate y reubicación.\n"
                    "3. Medidas ex situ: propagación en vivero y siembra en área de compensación.\n"
                    "4. Shapefile con localización de cada individuo vedado."
                )
            if any(v['nivel'] == 'regional' for v in todas_vedas):
                car_txt = car_proyecto or "la CAR competente"
                st.warning(
                    f"**Obligaciones — veda regional {car_txt}:**\n"
                    "1. Solicitud formal ante GIT Forestal de la CAR.\n"
                    "2. Concepto técnico favorable.\n"
                    "3. Justificación de interés público o riesgo.\n"
                    "4. Medidas de compensación/reposición que determine la CAR."
                )

    # ── Tabla FCAFU resumen ──────────────────────────────────────────────
    _section("Resumen FCAFU por Cobertura", "🌳")
    st.markdown(
        f"**Fórmula Manual 2026:** `FCAFU = 1 + A + B + C`  "
        f"&nbsp;&nbsp;Criterio B: `CR=1.0 · EN=0.6 · VU=0.4 · NT=0` (Tabla 4, Res. 0305/2026)",
        unsafe_allow_html=True
    )

    if fcafu_por_cobertura:
        filas_fcafu = []
        for cob, d in fcafu_por_cobertura.items():
            b_of   = round(d.get('B_oficial', d.get('B', 0)), 4)
            b_ci   = round(d.get('B_cites', b_of), 4)
            f_of   = round(d.get('FCAFU', 0), 3)
            f_ci   = round(d.get('FCAFU_cites', f_of), 3)
            delta  = round(f_ci - f_of, 3)
            filas_fcafu.append({
                "Cobertura":          cob,
                "N":                  d.get('N', 0),
                "S":                  d.get('S', 0),
                "A":                  round(d.get('A', 0), 3),
                "B oficial":          b_of,
                "B con CITES":        b_ci,
                "C":                  round(d.get('C', 0), 3),
                "FCAFU oficial":      f_of,
                "FCAFU con CITES":    f_ci,
                "Δ FCAFU":            f"+{delta}" if delta > 0 else str(delta),
            })
        df_fcafu = pd.DataFrame(filas_fcafu)
        st.dataframe(df_fcafu, use_container_width=True, hide_index=True)

        st.info(
            "**FCAFU oficial** usa solo Res. 0126/2024 (CR/EN/VU).  "
            "**FCAFU con CITES** suma equivalencia interna Unergy: "
            "Apéndice I = 0.6 (≈ EN) · Apéndice II = 0.4 (≈ VU). "
            "Sin respaldo normativo directo — presentar como escenario conservador."
        )

        # ── Desglose criterio B ──────────────────────────────────────────
        amenazadas_total = []
        for cob, d in fcafu_por_cobertura.items():
            for sp in d.get('amenazadas', []):
                amenazadas_total.append({**sp, 'cobertura': cob, 'N_cob': d.get('N', 0)})

        if amenazadas_total:
            n_sp_amen = len({sp['nombre_cientifico'] for sp in amenazadas_total})
            n_ind_amen = sum(sp['n_individuos'] for sp in amenazadas_total)
            with st.expander(
                f"🔍 Desglose Criterio B — {n_ind_amen} individuos en {n_sp_amen} spp.",
                expanded=False
            ):
                st.markdown(
                    r"**Fórmula:** $B = \dfrac{\sum_{i=1}^{N} v_i}{N}$  "
                    "donde **vᵢ** = valor de amenaza del individuo *i*"
                )

                for cob, d in fcafu_por_cobertura.items():
                    spp_cob = d.get('amenazadas', [])
                    if not spp_cob:
                        continue
                    N  = d.get('N', 0)
                    B_of = round(d.get('B_oficial', d.get('B', 0)), 4)
                    B_ci = round(d.get('B_cites', B_of), 4)

                    st.markdown(
                        f"**{cob}** — N={N} ind. &nbsp; B oficial=`{B_of}` &nbsp; "
                        f"B con CITES=`{B_ci}`",
                        unsafe_allow_html=True
                    )
                    rows_b = []
                    for sp in spp_cob:
                        n_sp   = sp.get('n_individuos', 1)
                        v_of   = sp.get('valor_b_oficial', 0.0)
                        v_ci   = sp.get('valor_b_cites',   v_of)
                        ap     = sp.get('cites_apendice',  '—')
                        cat    = sp.get('categoria_amenaza','—')
                        rows_b.append({
                            'Nombre científico': sp.get('nombre_cientifico',''),
                            'Cat. Res.0126':     cat,
                            'CITES':             ap,
                            'v oficial':         v_of,
                            'v con CITES':       v_ci,
                            'N ind.':            n_sp,
                            'Aporte B oficial':  sp.get('aporte_b_oficial', round(v_of*n_sp/N,4) if N else 0),
                            'Aporte B CITES':    sp.get('aporte_b_cites',   round(v_ci*n_sp/N,4) if N else 0),
                        })
                    st.dataframe(
                        pd.DataFrame(rows_b),
                        use_container_width=True, hide_index=True
                    )
                    st.markdown("---")
    else:
        st.warning(
            "⚠️ El inventario no generó cálculos FCAFU. "
            "Verifica columnas **Nombre científico**, **DAP a (m)** y **Cobertura**."
        )


# ════════════════════════════════════════════════════════════════════════
# TAB 3 — ATC
# ════════════════════════════════════════════════════════════════════════
with tab3:
    _section("Área Total a Compensar (ATC) por Rango", "📐")
    st.markdown(
        "**Fórmula:** `ATC = Σ (área_cobertura × (FCAFU + factor_rango))`  "
        "Se presentan dos escenarios: **oficial** (solo Res. 0126/2024) "
        "y **con CITES** (equiparación interna Unergy)."
    )

    if atc_resultados:
        # Tabla comparativa
        filas_atc = []
        for rango_id, data in atc_resultados.items():
            atc_of = round(data['atc_total'], 3)
            atc_ci = round(atc_resultados_cites.get(rango_id, data)['atc_total'], 3)
            delta  = round(atc_ci - atc_of, 3)
            filas_atc.append({
                "Rango":              rango_id,
                "Factor adicional":   data['factor_adicional'],
                "ATC oficial (ha)":   atc_of,
                "ATC con CITES (ha)": atc_ci,
                "Δ ATC (ha)":         f"+{delta}" if delta > 0 else str(delta),
            })
        st.dataframe(
            pd.DataFrame(filas_atc),
            use_container_width=True, hide_index=True
        )

        st.markdown("---")
        sub_tab1, sub_tab2 = st.tabs(["📋 Escenario Oficial", "🔬 Escenario con CITES"])

        with sub_tab1:
            st.caption("Criterio B: solo Res. 0126/2024 (CR=1.0 · EN=0.6 · VU=0.4)")
            for rango_id, data in atc_resultados.items():
                with st.expander(
                    f"{rango_id} — ATC = {round(data['atc_total'],3)} ha  "
                    f"(factor +{data['factor_adicional']})"
                ):
                    if data.get('detalles'):
                        st.dataframe(
                            pd.DataFrame(data['detalles']),
                            use_container_width=True, hide_index=True
                        )

        with sub_tab2:
            st.caption(
                "Criterio B: Res. 0126/2024 + CITES (Apéndice I=0.6 · II=0.4)  "
                "⚠️ Equiparación interna Unergy — sin normativa directa"
            )
            for rango_id, data in atc_resultados_cites.items():
                with st.expander(
                    f"{rango_id} — ATC = {round(data['atc_total'],3)} ha  "
                    f"(factor +{data['factor_adicional']})"
                ):
                    if data.get('detalles'):
                        st.dataframe(
                            pd.DataFrame(data['detalles']),
                            use_container_width=True, hide_index=True
                        )


# ════════════════════════════════════════════════════════════════════════
# TAB 4 — ADICIONALIDAD
# ════════════════════════════════════════════════════════════════════════
with tab4:
    _section("Adicionalidad Esperada por Escenario y Horizonte", "🌱")

    st.markdown(
        f"Tasas BAU: **Municipio** `{tasa_bau*100:.3f}%` · "
        f"**SZH** `{tasa_bau_szh*100:.3f}%` · "
        f"**ZH** `{tasa_bau_zh*100:.3f}%`"
    )

    with st.expander("📖 Metodología y fuentes"):
        st.markdown("""
**CONSERVAR — Fórmula exponencial acumulada**
```
ha_adicional(n) = ha × [1 - (1 - tasa_BAU)ⁿ] × 0.85
```
- Tasa BAU: **Hansen et al. (2013)** [DOI:10.1126/science.1244693](https://doi.org/10.1126/science.1244693)
- Factor 0.85: **Andam et al. (2008)** [DOI:10.1073/pnas.0800437105](https://doi.org/10.1073/pnas.0800437105) · **Pfaff et al. (2014)** [DOI:10.1016/j.worlddev.2013.01.011](https://doi.org/10.1016/j.worlddev.2013.01.011)

---
**RESTAURAR — Curva Chapman-Richards (Poorter 2016)**
```
ha_adicional(n) = ha × [1 - e^(-0.076×n)] × 0.75
```
- k=0.076: **Poorter et al. (2016)** Nature 530:211-214. [DOI:10.1038/nature16469](https://doi.org/10.1038/nature16469)
- Factor 0.75: **Crouzeilles et al. (2017)** [DOI:10.1126/sciadv.1701345](https://doi.org/10.1126/sciadv.1701345) · **González-M. et al. (2018)** IAvH BST Colombia
        """)

    if atc_resultados:
        adic_tab1, adic_tab2, adic_tab3 = st.tabs([
            "🌳 Conservar", "🌱 Restaurar", "⚖️ Mix & Comparación"
        ])

        with adic_tab1:
            st.caption(
                "Hectáreas que NO se pierden — tasa BAU según unidad del nivel jerárquico"
            )
            filas_c = []
            for rango_id, data in atc_resultados.items():
                atc_total  = data['atc_total']
                tasa_rango = TASA_POR_NIVEL.get(rango_id, tasa_bau)
                fila = {
                    "Rango":         rango_id,
                    "ATC (ha)":      round(atc_total, 2),
                    "Tasa BAU":      f"{tasa_rango*100:.3f}%",
                    "Adic/año (ha)": round(adicionalidad_conservar_anual(atc_total, tasa_rango, F_CONSERVAR), 4),
                }
                for n in HORIZONTES:
                    fila[f"{n} años (ha)"] = round(
                        adicionalidad_conservar(atc_total, n, tasa_rango, F_CONSERVAR), 4
                    )
                filas_c.append(fila)
            st.dataframe(pd.DataFrame(filas_c), use_container_width=True, hide_index=True)

        with adic_tab2:
            st.caption(
                "Hectáreas que SE ganan — curva Chapman-Richards (k=0.076, f=0.75)"
            )
            filas_r = []
            for rango_id, data in atc_resultados.items():
                atc_total = data['atc_total']
                fila = {"Rango": rango_id, "ATC (ha)": round(atc_total, 2)}
                for n in HORIZONTES:
                    fila[f"{n} años (ha)"] = round(
                        adicionalidad_restaurar(atc_total, n, K_RESTAURAR, F_RESTAURAR), 4
                    )
                filas_r.append(fila)
            st.dataframe(pd.DataFrame(filas_r), use_container_width=True, hide_index=True)
            st.caption("💡 Crece rápido los primeros años y se estabiliza conforme el ecosistema madura.")

        with adic_tab3:
            # Mix 50/50
            _section("Escenario Mix 50/50", "⚖️")
            st.caption("50% Conservar + 50% Restaurar del ATC total — tasa BAU por nivel")
            filas_m = []
            for rango_id, data in atc_resultados.items():
                atc_total  = data['atc_total']
                mitad      = atc_total * 0.5
                tasa_rango = TASA_POR_NIVEL.get(rango_id, tasa_bau)
                fila = {"Rango": rango_id, "ATC (ha)": round(atc_total, 2)}
                for n in HORIZONTES:
                    cons = adicionalidad_conservar(mitad, n, tasa_rango, F_CONSERVAR)
                    rest = adicionalidad_restaurar(mitad, n, K_RESTAURAR, F_RESTAURAR)
                    fila[f"Mix {n} años (ha)"] = round(cons + rest, 4)
                filas_m.append(fila)
            st.dataframe(pd.DataFrame(filas_m), use_container_width=True, hide_index=True)

            # Comparación por ha
            _section("Conservar vs Restaurar (por ha compensada)", "📊")
            st.caption(f"Referencia: tasa BAU municipio `{tasa_bau*100:.3f}%`")
            filas_comp = []
            for n in HORIZONTES:
                cons_ha = adicionalidad_conservar(1.0, n, tasa_bau, F_CONSERVAR)
                rest_ha = adicionalidad_restaurar(1.0, n, K_RESTAURAR, F_RESTAURAR)
                filas_comp.append({
                    "Horizonte":        f"{n} años",
                    "Conservar (ha/ha)":round(cons_ha, 4),
                    "Restaurar (ha/ha)":round(rest_ha, 4),
                    "Ratio Rest/Cons":  round(rest_ha/cons_ha, 1) if cons_ha > 0 else "—",
                })
            st.dataframe(pd.DataFrame(filas_comp), use_container_width=True, hide_index=True)

            st.info(
                "**¿Qué horizonte usar?**\n\n"
                "- Compra / Usufructo predial (≥ 30 años) → columna de 15 años\n"
                "- Acuerdo de conservación 15 años → columna de 15 años\n"
                "- Acuerdo 3–5 años → columna correspondiente\n\n"
                "**Restaurar** genera más adicionalidad numérica. "
                "**Conservar** protege bosque existente con menor riesgo de falla."
            )


# ════════════════════════════════════════════════════════════════════════
# TAB 5 — EXPORTAR
# ════════════════════════════════════════════════════════════════════════
with tab5:
    _section("Descarga de Resultados", "📥")

    def _build_excel(ctx, fcafu_por_cobertura,
                     atc_resultados, atc_resultados_cites,
                     TASA_BAU, tasa_bau_szh, tasa_bau_zh,
                     TASA_POR_NIVEL, F_CONSERVAR, F_RESTAURAR,
                     K_RESTAURAR, HORIZONTES, area_impacto_ha):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:

            # Hoja 1 – Resumen
            pd.DataFrame({
                "Variable": [
                    "Municipio","Departamento","BIOMA-IAvH",
                    "Zona Hidrográfica","Subzona Hidrográfica",
                    "Área de impacto (ha)",
                    "Tasa BAU Municipio (%)","Tasa BAU SZH (%)","Tasa BAU ZH (%)",
                ],
                "Valor": [
                    ctx.get("municipio","n/d"), ctx.get("departamento","n/d"),
                    ctx.get("bioma_principal","n/d"),
                    ctx.get("zh","n/d"), ctx.get("szh","n/d"),
                    round(area_impacto_ha, 4),
                    round(TASA_BAU*100, 4),
                    round(tasa_bau_szh*100, 4),
                    round(tasa_bau_zh*100, 4),
                ]
            }).to_excel(writer, sheet_name="Resumen", index=False)

            # Hoja 2 – FCAFU
            rows_f = []
            for cob, d in fcafu_por_cobertura.items():
                rows_f.append({
                    "Cobertura":      cob,
                    "N":              d["N"], "S": d["S"],
                    "S/N":            round(d["SN"], 4),
                    "A":              d["A"],
                    "B oficial":      round(d.get("B_oficial", d.get("B",0)), 4),
                    "B con CITES":    round(d.get("B_cites",   d.get("B",0)), 4),
                    "C":              d["C"],
                    "FCAFU oficial":  round(d["FCAFU"], 4),
                    "FCAFU con CITES":round(d.get("FCAFU_cites", d["FCAFU"]), 4),
                    "AB total (m²)":  round(d.get("area_basal_total",0), 4),
                })
            pd.DataFrame(rows_f).to_excel(writer, sheet_name="FCAFU", index=False)

            # Hoja 3 – ATC oficial
            rows_a = []
            for rid, data in atc_resultados.items():
                rows_a.append({
                    "Rango": rid,
                    "Factor adicional": data.get("factor_adicional",""),
                    "ATC oficial (ha)": round(data["atc_total"], 4),
                    "ATC con CITES (ha)": round(
                        atc_resultados_cites.get(rid, data)["atc_total"], 4
                    ),
                })
            pd.DataFrame(rows_a).to_excel(writer, sheet_name="ATC_por_Rango", index=False)

            # Hoja 4 – Adicionalidad Conservar
            rows_c = []
            for rid, data in atc_resultados.items():
                atc_total  = data["atc_total"]
                tasa_rango = TASA_POR_NIVEL.get(rid, TASA_BAU)
                fila = {
                    "Rango": rid,
                    "ATC (ha)": round(atc_total, 4),
                    "Tasa BAU (%)": round(tasa_rango*100, 4),
                    "Adic/año (ha)": round(
                        adicionalidad_conservar_anual(atc_total, tasa_rango, F_CONSERVAR), 6
                    ),
                }
                for n in HORIZONTES:
                    fila[f"A {n} años (ha)"] = round(
                        adicionalidad_conservar(atc_total, n, tasa_rango, F_CONSERVAR), 6
                    )
                rows_c.append(fila)
            pd.DataFrame(rows_c).to_excel(writer, sheet_name="Adicionalidad_Conservar", index=False)

            # Hoja 5 – Adicionalidad Restaurar
            rows_r = []
            for rid, data in atc_resultados.items():
                atc_total = data["atc_total"]
                fila = {"Rango": rid, "ATC (ha)": round(atc_total, 4)}
                for n in HORIZONTES:
                    fila[f"A {n} años (ha)"] = round(
                        adicionalidad_restaurar(atc_total, n, K_RESTAURAR, F_RESTAURAR), 6
                    )
                rows_r.append(fila)
            pd.DataFrame(rows_r).to_excel(writer, sheet_name="Adicionalidad_Restaurar", index=False)

            # Hoja 6 – Comparación por ha
            rows_cp = []
            for n in HORIZONTES:
                cons_ha = adicionalidad_conservar(1.0, n, TASA_BAU, F_CONSERVAR)
                rest_ha = adicionalidad_restaurar(1.0, n, K_RESTAURAR, F_RESTAURAR)
                rows_cp.append({
                    "Horizonte (años)":  n,
                    "Conservar (ha/ha)": round(cons_ha, 6),
                    "Restaurar (ha/ha)": round(rest_ha, 6),
                    "Ratio Rest/Cons":   round(rest_ha/cons_ha, 2) if cons_ha > 0 else None,
                })
            pd.DataFrame(rows_cp).to_excel(writer, sheet_name="Comparacion_por_ha", index=False)

            # Hoja 7 – Especies amenazadas + CITES
            rows_sp = []
            for cob, d in fcafu_por_cobertura.items():
                for sp in d.get("amenazadas", []):
                    rows_sp.append({
                        "Cobertura":        cob,
                        "Nombre científico":sp.get("nombre_cientifico",""),
                        "Cat. Res.0126":    sp.get("categoria_amenaza",""),
                        "CITES":            sp.get("cites_apendice","—"),
                        "v oficial":        sp.get("valor_b_oficial", 0),
                        "v con CITES":      sp.get("valor_b_cites",   0),
                        "N individuos":     sp.get("n_individuos", 0),
                    })
            if rows_sp:
                pd.DataFrame(rows_sp).to_excel(
                    writer, sheet_name="Especies_Amenazadas", index=False
                )

        buf.seek(0)
        return buf.getvalue()

    if atc_resultados and fcafu_por_cobertura:
        nombre_mun  = ctx.get("municipio","proyecto").replace(" ","_")
        excel_bytes = _build_excel(
            ctx, fcafu_por_cobertura,
            atc_resultados, atc_resultados_cites,
            TASA_BAU, tasa_bau_szh, tasa_bau_zh,
            TASA_POR_NIVEL, F_CONSERVAR, F_RESTAURAR,
            K_RESTAURAR, HORIZONTES, area_impacto_ha
        )
        st.download_button(
            label="⬇️ Descargar Excel de resultados",
            data=excel_bytes,
            file_name=f"compensacion_{nombre_mun}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.caption(
            "Hojas incluidas: Resumen · FCAFU (oficial + CITES) · ATC por Rango · "
            "Adicionalidad Conservar · Adicionalidad Restaurar · Comparación por ha · "
            "Especies Amenazadas"
        )
    else:
        st.warning("⚠️ No hay resultados aún. Carga el KMZ y el inventario.")

    _section("Mapas y Análisis Espacial", "🗺️")
    st.info(
        "**Mapas de áreas candidatas (R1–R6) en Google Earth Engine**\n\n"
        "1. Abre `code.earthengine.google.com`\n"
        "2. Pega el script del rango correspondiente\n"
        "3. Reemplaza el asset del impacto\n"
        "4. Run → Tasks → Exportar shapefiles a Drive\n"
        "5. Abre en QGIS / ArcMap"
    )

    _section("Referencias", "📚")
    c_ref1, c_ref2 = st.columns(2)
    with c_ref1:
        st.markdown("**🌳 CONSERVAR — Factor efectividad: 0.85**")
        st.markdown("- Andam et al. (2008) PNAS — [10.1073/pnas.0800437105](https://doi.org/10.1073/pnas.0800437105)")
        st.markdown("- Pfaff et al. (2014) World Dev — [10.1016/j.worlddev.2013.01.011](https://doi.org/10.1016/j.worlddev.2013.01.011)")
    with c_ref2:
        st.markdown("**🌱 RESTAURAR — Factor efectividad: 0.75 · k = 0.076**")
        st.markdown("- Poorter et al. (2016) Nature — [10.1038/nature16469](https://doi.org/10.1038/nature16469)")
        st.markdown("- Crouzeilles et al. (2017) Sci Adv — [10.1126/sciadv.1701345](https://doi.org/10.1126/sciadv.1701345)")
        st.markdown("- González-M. et al. (2018) IAvH BST Colombia")
    st.caption(
        "**Tasa BAU:** Hansen et al. (2013) Science 342:850-853 — "
        "[10.1126/science.1244693](https://doi.org/10.1126/science.1244693)"
    )


# ════════════════════════════════════════════════════════════════════════
# TAB 6 — VEDAS
# ════════════════════════════════════════════════════════════════════════
with tab6:
    _render_tab_vedas(todas_vedas=todas_vedas, car_proyecto=car_proyecto)
