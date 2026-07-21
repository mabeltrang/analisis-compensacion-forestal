# -*- coding: utf-8 -*-
"""
App de Planes de Compensación Biótica — Unergy Energía Digital S.A.S. E.S.P.
Manual 2026 (Resolución 0305/2026 MADS) — Versión 7

Cambios v7:
- Criterio B corregido: VU=0.4 / EN=0.6 / CR=1.0 (Tabla 4 Manual 2026). NT=0.
- Criterio B usa un único valor por individuo: máximo entre MADS/CITES/IUCN
  (ya no se presentan escenarios separados oficial/CITES/UICN).
- Rediseño UI: colores corporativos Unergy, tabs, cards de métricas.
"""

import streamlit as st
import pandas as pd
import os, tempfile, io

from core import inputs, contexto, inventario, atc, utils, iniciativas
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

  /* ── Fix contraste: cualquier encabezado (###, ####...) sin clase propia ──
     hereda color oscuro por defecto. Las reglas más específicas de abajo
     (.unergy-header h1, .section-header h3, sidebar h3, etc.) tienen la
     MISMA especificidad pero se declaran después, así que siguen ganando
     y mantienen su color (blanco / morado) sin que esta regla las pise. ── */
  .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
    color: #1A1A2E !important;
  }}

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

  /* ── Tarjetas consulta especies ── */
  .sp-card {{
    border: 1.5px solid #B8A9E0;
    border-radius: 10px;
    padding: 12px 18px;
    margin-bottom: 10px;
    background: #FAFAFE;
  }}
  .sp-card-name {{
    font-size: 1.05rem;
    font-weight: 800;
    color: {PURPLE_DARK};
    font-style: italic;
    margin-bottom: 2px;
  }}
  .sp-card-common {{
    font-size: 0.82rem;
    color: #5A5A72;
    font-style: normal;
    margin-bottom: 4px;
  }}
  .sp-badges {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }}
  .sp-source-label {{
    font-size: 0.72rem;
    font-weight: 700;
    color: #5A5A72;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .badge-CR  {{ background:#B71C1C; color:#fff; padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.78rem; }}
  .badge-EN  {{ background:#E65100; color:#fff; padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.78rem; }}
  .badge-VU  {{ background:#F9A825; color:#1A1A2E; padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.78rem; }}
  .badge-NT  {{ background:#1565C0; color:#fff; padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.78rem; }}
  .badge-LC  {{ background:#2E7D32; color:#fff; padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.78rem; }}
  .badge-CITES {{ background:{PURPLE}; color:#fff; padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.78rem; }}
  .badge-NL  {{ background:#9E9E9E; color:#fff; padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.78rem; }}
  .sp-divider {{ border: none; border-top: 1px solid #E0D9F5; margin: 2px 0 6px 0; }}
  .sp-veda-line {{
    margin-top: 8px;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 0.82rem;
  }}
  .sp-veda-hit {{
    background: #FDECEA;
    color: #B71C1C;
    border: 1px solid #F5C6C2;
  }}
  .sp-veda-none {{
    background: #EAF6EC;
    color: #2E7D32;
    border: 1px solid #C8E6C9;
  }}

  /* ── Tabla de consulta de especies (reemplaza las tarjetas apiladas) ── */
  .sp-table-wrap {{
    background: #FFFFFF;
    border: 1.5px solid #B8A9E0;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 14px;
  }}
  .sp-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }}
  .sp-table thead th {{
    background: {PURPLE_LIGHT};
    color: {PURPLE_DARK} !important;
    font-weight: 800;
    text-align: center;
    padding: 10px 14px;
    white-space: nowrap;
  }}
  .sp-table tbody td {{
    padding: 9px 14px;
    color: #1A1A2E;
    border-top: 1px solid #E0D9F5;
    vertical-align: middle;
    text-align: center;
  }}
  .sp-table tbody tr:nth-child(even) {{
    background: #FAFAFE;
  }}
  .sp-table-sci {{
    font-style: italic;
    font-weight: 700;
    color: {PURPLE_DARK};
  }}
  .sp-table-common {{
    color: #5A5A72;
    font-size: 0.8rem;
  }}
  .badge-veda-hit {{
    display: inline-block;
    background: #FDECEA;
    color: #B71C1C;
    border: 1px solid #F5C6C2;
    padding: 3px 10px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.76rem;
  }}
  .veda-ok-text {{
    color: #2E7D32;
    font-weight: 700;
    font-size: 0.8rem;
  }}
  .veda-detalle {{
    display: block;
    font-size: 0.68rem;
    font-weight: 600;
    color: #B71C1C;
    margin-top: 2px;
  }}

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
    from config.vedas import VEDAS_REGIONALES as _VEDAS_REGIONALES_SIDEBAR
    car_proyecto = st.selectbox(
        "CAR competente",
        options=[""] + sorted(_VEDAS_REGIONALES_SIDEBAR.keys()),
        help="Opcional: si la dejas vacía, se detecta automáticamente por "
             "municipio/departamento del polígono de impacto al procesar. "
             "Selecciónala aquí solo para forzar una CAR distinta a la "
             "detección automática. Lista completa de las 31 CAR de "
             "Colombia — ver pestaña 'Consulta y Vedas' para el detalle "
             "de cada una.",
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

# ════════════════════════════════════════════════════════════════════════
# FUNCIÓN REUTILIZABLE — CONSULTA ESTADO DE AMENAZA
# ════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def _cargar_indices_amenaza():
    """Carga y preprocesa los tres CSV de amenaza para búsqueda rápida."""
    BASE = os.path.join(os.path.dirname(__file__), "config")

    df_mads = pd.read_csv(os.path.join(BASE, "especies_amenazadas_co.csv"))
    df_mads["_key"] = df_mads["nombre cientifico"].str.strip().str.lower()
    mads_idx = df_mads.set_index("_key")

    df_cites = pd.read_csv(os.path.join(BASE, "Listado_CITES.csv"), on_bad_lines="skip")
    df_cites["_sci"] = (
        df_cites["Genus"].fillna("").str.strip() + " " +
        df_cites["Species"].fillna("").str.strip()
    ).str.strip().str.lower()
    cites_idx = df_cites[df_cites["Species"].notna()].set_index("_sci")

    df_iucn = pd.read_csv(os.path.join(BASE, "Listado_UICN.csv"))
    df_iucn["_key"] = df_iucn["scientificName"].str.strip().str.lower()
    iucn_idx = df_iucn.set_index("_key")

    return mads_idx, cites_idx, iucn_idx


_IUCN_ABBR = {
    "Critically Endangered": "CR",
    "Endangered": "EN",
    "Vulnerable": "VU",
    "Near Threatened": "NT",
    "Least Concern": "LC",
    "Data Deficient": "DD",
    "Extinct": "EX",
    "Extinct in the Wild": "EW",
}


def _consultar_veda_todas_cars(nombre_cientifico, nombre_comun=""):
    """Cruza una especie contra la veda nacional y contra las 31 CAR de Colombia.

    Se usa cuando el usuario NO filtra por una CAR específica en la consulta
    (comportamiento histórico de la pestaña).

    Devuelve dict con:
      _modo: "todas"
      en_veda_nacional (bool), nacional_info (dict|None)
      regionales (list[dict]): una entrada por cada CAR en la que la especie
        está vedada (incluye las que solo heredan la veda nacional, marcadas
        con "solo_nacional": True)
    """
    from config.vedas import VEDAS_REGIONALES, consultar_veda

    r_nac = consultar_veda(nombre_cientifico, nombre_comun)
    regionales = []
    for car_key, datos in sorted(VEDAS_REGIONALES.items()):
        r = consultar_veda(nombre_cientifico, nombre_comun, car=car_key)
        if r["en_veda_regional"] and r.get("veda_regional_info"):
            regionales.append({
                "car": car_key,
                "solo_nacional": bool(datos.get("solo_nacional")),
                "norma": r["veda_regional_info"]["norma"],
            })
    return {
        "_modo": "todas",
        "en_veda_nacional": r_nac["en_veda_nacional"],
        "nacional_info": r_nac["veda_nacional_info"],
        "regionales": regionales,
    }


def _consultar_veda_car_unica(nombre_cientifico, nombre_comun, car):
    """Cruza una especie SOLO contra la veda nacional + la CAR seleccionada.

    Se usa cuando el usuario filtra la consulta por una CAR específica.
    """
    from config.vedas import consultar_veda

    r = consultar_veda(nombre_cientifico, nombre_comun, car=car)
    r["_modo"] = "car_unica"
    r["_car"] = car
    return r


def _veda_hit(veda):
    """True si la especie está en veda, sin importar el modo de consulta."""
    if veda.get("_modo") == "car_unica":
        return veda["nivel"] != "sin_veda"
    return bool(veda["en_veda_nacional"]) or bool(veda["regionales"])


def _consultar_amenaza_sp(nombre, mads_idx, cites_idx, iucn_idx, car_filtro=""):
    key = nombre.strip().lower()
    mads_cat, mads_nombre_comun, mads_familia = "No aplica (NA)", "", ""
    if key in mads_idx.index:
        row = mads_idx.loc[key]
        if isinstance(row, pd.DataFrame): row = row.iloc[0]
        mads_cat = str(row.get("Categoría de amenaza", "")).strip() or "No aplica (NA)"
        mads_nombre_comun = str(row.get("Nombre común", "")).strip()
        mads_familia = str(row.get("Familia", "")).strip()

    cites_apendice = "No aplica (NA)"
    if key in cites_idx.index:
        row = cites_idx.loc[key]
        if isinstance(row, pd.DataFrame): row = row.iloc[0]
        ap = str(row.get("CurrentListing", "")).strip()
        cites_apendice = f"Apéndice {ap}" if ap else "No aplica (NA)"

    iucn_cat = "No aplica (NA)"
    if key in iucn_idx.index:
        row = iucn_idx.loc[key]
        if isinstance(row, pd.DataFrame): row = row.iloc[0]
        cat_full = str(row.get("redlistCategory", "")).strip()
        iucn_cat = _IUCN_ABBR.get(cat_full, cat_full) or "No aplica (NA)"

    if car_filtro:
        veda = _consultar_veda_car_unica(nombre.strip(), mads_nombre_comun, car_filtro)
    else:
        veda = _consultar_veda_todas_cars(nombre.strip(), mads_nombre_comun)

    return {
        "nombre": nombre.strip(),
        "mads": mads_cat,
        "cites": cites_apendice,
        "iucn": iucn_cat,
        "nombre_comun": mads_nombre_comun,
        "familia": mads_familia,
        "veda": veda,
    }


def _badge_html(texto, fuente=None):
    t = str(texto).strip()
    _cls_map = {"CR":"badge-CR","EN":"badge-EN","VU":"badge-VU","NT":"badge-NT","LC":"badge-LC"}
    if t in _cls_map: cls = _cls_map[t]
    elif "Apéndice" in t: cls = "badge-CITES"
    else: cls = "badge-NL"
    label = f"<span class='sp-source-label'>{fuente}: </span>" if fuente else ""
    return f"{label}<span class='{cls}'>{t}</span>"


def _veda_linea_html(veda):
    """Línea HTML resumen de vedas para una especie.

    Soporta dos modos:
      - "todas": cruce contra nacional + las 31 CAR (comportamiento histórico,
        sin filtro de CAR).
      - "car_unica": cruce contra nacional + UNA CAR específica elegida por
        el usuario en la consulta.
    """
    if veda.get("_modo") == "car_unica":
        car = veda["_car"]
        if veda["nivel"] == "sin_veda":
            return (
                f"<div class='sp-veda-line sp-veda-none'>✅ Sin veda nacional "
                f"ni regional identificada para {car}</div>"
            )
        if veda["nivel"] == "nacional+regional":
            texto = (
                f"NACIONAL (todo el país) + regional propia: {car} "
                f"({veda['veda_regional_info']['norma']})"
            )
        elif veda["nivel"] == "nacional":
            texto = "NACIONAL (todo el país)"
        else:  # regional
            texto = f"regional propia: {car}"
        return f"<div class='sp-veda-line sp-veda-hit'>🚫 <b>En veda</b> — {texto}</div>"

    # modo "todas" (sin filtro de CAR) — comportamiento histórico
    if not veda["en_veda_nacional"] and not veda["regionales"]:
        return "<div class='sp-veda-line sp-veda-none'>✅ Sin veda nacional ni regional identificada</div>"
    partes = []
    if veda["en_veda_nacional"]:
        partes.append("NACIONAL (todo el país)")
    propias = [r["car"] for r in veda["regionales"] if not r["solo_nacional"]]
    if propias:
        partes.append("regional propia: " + ", ".join(propias))
    return (
        "<div class='sp-veda-line sp-veda-hit'>🚫 <b>En veda</b> — " + " · ".join(partes) + "</div>"
    )


def _veda_celda_html(veda):
    """Versión compacta de _veda_linea_html pensada para una celda de tabla
    (badge corto + detalle en una segunda línea pequeña), en vez del bloque
    de línea completa usado antes en las tarjetas."""
    if veda.get("_modo") == "car_unica":
        car = veda["_car"]
        if veda["nivel"] == "sin_veda":
            return "<span class='veda-ok-text'>✅ Sin veda</span>"
        if veda["nivel"] == "nacional+regional":
            detalle = f"NACIONAL + regional: {car}"
        elif veda["nivel"] == "nacional":
            detalle = "NACIONAL (todo el país)"
        else:  # regional
            detalle = f"regional: {car}"
        return (
            "<span class='badge-veda-hit'>🚫 En veda</span>"
            f"<span class='veda-detalle'>{detalle}</span>"
        )

    # modo "todas" (sin filtro de CAR)
    if not veda["en_veda_nacional"] and not veda["regionales"]:
        return "<span class='veda-ok-text'>✅ Sin veda</span>"
    partes = []
    if veda["en_veda_nacional"]:
        partes.append("NACIONAL")
    propias = [r["car"] for r in veda["regionales"] if not r["solo_nacional"]]
    if propias:
        partes.append("regional: " + ", ".join(propias))
    detalle = " · ".join(partes)
    return (
        "<span class='badge-veda-hit'>🚫 En veda</span>"
        f"<span class='veda-detalle'>{detalle}</span>"
    )


_CAT_NOMBRE_COMPLETO = {
    "CR": "En Peligro Crítico",
    "EN": "En Peligro",
    "VU": "Vulnerable",
    "NT": "Casi Amenazada",
    "LC": "Preocupación Menor",
    "DD": "Datos Insuficientes",
    "EX": "Extinta",
    "EW": "Extinta en Estado Silvestre",
}


def _estado_con_abrev_excel(codigo):
    """SOLO para el Excel exportable: agrega el nombre completo del estado
    con su abreviatura entre paréntesis, ej. 'En Peligro (EN)'.
    Los 'No aplica (NA)' se dejan igual."""
    t = str(codigo).strip()
    if t in ("No aplica (NA)", "No listado", "No evaluado", "", "nan"):
        return "No aplica (NA)"
    if t in _CAT_NOMBRE_COMPLETO:
        return f"{_CAT_NOMBRE_COMPLETO[t]} ({t})"
    return t  # ej. "Apéndice II" queda igual, ya es texto completo


def _tabla_consulta_html(resultados, mostrar_mads, mostrar_cites, mostrar_iucn,
                          mostrar_veda, car_filtro=""):
    """Construye la tabla HTML de resultados de consulta de especies
    (reemplaza el listado de tarjetas apiladas por una tabla visible de una
    sola vez, con colores consistentes con el resto de la app)."""
    headers = ["Nombre científico"]
    if mostrar_mads:  headers.append("MADS")
    if mostrar_cites: headers.append("CITES")
    if mostrar_iucn:  headers.append("IUCN")
    if mostrar_veda:
        headers.append(f"Veda ({car_filtro})" if car_filtro else "Veda (nacional + CAR)")

    thead = "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"

    rows_html = []
    for r in resultados:
        cells = [
            f"<td class='sp-table-sci'>{r['nombre']}</td>",
        ]
        if mostrar_mads:  cells.append(f"<td>{_badge_html(r['mads'])}</td>")
        if mostrar_cites: cells.append(f"<td>{_badge_html(r['cites'])}</td>")
        if mostrar_iucn:  cells.append(f"<td>{_badge_html(r['iucn'])}</td>")
        if mostrar_veda:  cells.append(f"<td>{_veda_celda_html(r['veda'])}</td>")

        rows_html.append("<tr>" + "".join(cells) + "</tr>")

    return (
        "<div class='sp-table-wrap'><table class='sp-table'>"
        f"<thead>{thead}</thead><tbody>{''.join(rows_html)}</tbody>"
        "</table></div>"
    )


def _render_tab_consulta_vedas(key_suffix="", todas_vedas=None, car_proyecto=""):
    """Tab único: Consulta de amenaza + cruce de vedas (nacional y las 31 CAR),
    más el cruce con el inventario (si hay uno cargado) y el navegador de
    vedas por CAR. key_suffix evita colisión de keys entre instancias."""
    from config.vedas import VEDAS_NACIONALES, VEDAS_REGIONALES

    _section("Consulta de Estado de Amenaza y Vedas por Especie", "🔍")
    st.markdown(
        "Ingresa una lista de especies (una por línea) para consultar, en un solo resultado, "
        "su categoría de amenaza según **MADS** (Res. 0126/2024), **CITES** (Apéndices) e "
        "**IUCN** (Lista Roja global), y si está **en veda** — nacional o en alguna de las "
        "**31 CAR de Colombia**. No se requiere inventario cargado."
    )
    st.info(
        "Las vedas **no modifican el FCAFU** ni el área de compensación, pero generan "
        "**obligaciones procedimentales** adicionales ante la CAR (concepto técnico, rescate, "
        "reubicación, censo 100%). Verifica siempre la norma vigente al momento de radicación."
    )

    col_input, col_opts = st.columns([3, 1])
    with col_input:
        lista_raw = st.text_area(
            "Nombres científicos (uno por línea)",
            placeholder="Cedrela odorata\nSwietenia macrophylla\nCattleya trianae\nQuercus humboldtii",
            height=180,
            key=f"consulta_especies_input{key_suffix}",
        )
        car_default_idx = 0
        _car_opciones = [""] + sorted(VEDAS_REGIONALES.keys())
        if car_proyecto and car_proyecto in _car_opciones:
            car_default_idx = _car_opciones.index(car_proyecto)
        car_filtro_sel = st.selectbox(
            "Filtrar por CAR (opcional)",
            options=_car_opciones,
            index=car_default_idx,
            key=f"car_filtro_consulta{key_suffix}",
            help="Si eliges una CAR, la veda regional se evalúa solo contra esa CAR. "
                 "Si la dejas vacía, se consulta contra la veda nacional y las 31 CAR "
                 "de Colombia (comportamiento por defecto).",
        )
    with col_opts:
        st.markdown("#### Fuentes")
        mostrar_mads  = st.checkbox("MADS (Col)", value=True, key=f"ch_mads{key_suffix}")
        mostrar_cites = st.checkbox("CITES",      value=True, key=f"ch_cites{key_suffix}")
        mostrar_iucn  = st.checkbox("IUCN",       value=True, key=f"ch_iucn{key_suffix}")
        mostrar_veda  = st.checkbox("Vedas (nacional + CAR)", value=True, key=f"ch_veda{key_suffix}")
        solo_amenazadas = st.checkbox(
            "Solo amenazadas o en veda", value=False, key=f"ch_solo_am{key_suffix}",
            help="Oculta especies sin categoría en ninguna fuente y sin veda"
        )

    if st.button("🔍 Consultar", key=f"btn_consulta_sp{key_suffix}", type="primary"):
        nombres = [n.strip() for n in lista_raw.splitlines() if n.strip()]
        if not nombres:
            st.warning("Ingresa al menos un nombre de especie.")
        else:
            spinner_txt = (
                f"Consultando {len(nombres)} especies en fuentes de amenaza y en {car_filtro_sel}..."
                if car_filtro_sel else
                f"Consultando {len(nombres)} especies en fuentes de amenaza y en las 31 CAR..."
            )
            with st.spinner(spinner_txt):
                mads_idx, cites_idx, iucn_idx = _cargar_indices_amenaza()
                resultados = [
                    _consultar_amenaza_sp(n, mads_idx, cites_idx, iucn_idx, car_filtro=car_filtro_sel)
                    for n in nombres
                ]
                resultados.sort(key=lambda r: r["nombre"].lower())

            if solo_amenazadas:
                resultados = [
                    r for r in resultados
                    if r["mads"] in {"CR","EN","VU","NT"}
                    or "Apéndice" in r["cites"]
                    or r["iucn"] in {"CR","EN","VU","NT"}
                    or _veda_hit(r["veda"])
                ]

            if not resultados:
                st.info("Ninguna especie figura con categoría de amenaza ni en veda en las fuentes consultadas.")
            else:
                n_cr   = sum(1 for r in resultados if r["mads"]=="CR"  or r["iucn"]=="CR")
                n_en   = sum(1 for r in resultados if r["mads"]=="EN"  or r["iucn"]=="EN")
                n_vu   = sum(1 for r in resultados if r["mads"]=="VU"  or r["iucn"]=="VU")
                n_cit  = sum(1 for r in resultados if "Apéndice" in r["cites"])
                n_veda = sum(1 for r in resultados if _veda_hit(r["veda"]))

                mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
                mc1.metric("Consultadas", len(resultados))
                mc2.metric("🔴 CR", n_cr)
                mc3.metric("🟠 EN", n_en)
                mc4.metric("🟡 VU", n_vu)
                mc5.metric("🟣 CITES", n_cit)
                mc6.metric(
                    "🚫 En veda" + (f" ({car_filtro_sel})" if car_filtro_sel else ""),
                    n_veda,
                )

                st.markdown("---")

                tabla_html = _tabla_consulta_html(
                    resultados,
                    mostrar_mads=mostrar_mads,
                    mostrar_cites=mostrar_cites,
                    mostrar_iucn=mostrar_iucn,
                    mostrar_veda=mostrar_veda,
                    car_filtro=car_filtro_sel,
                )
                st.markdown(tabla_html, unsafe_allow_html=True)

                st.markdown("---")
                with st.expander("📋 Ver tabla completa / exportar"):
                    filas_export = []
                    for r in resultados:
                        v = r["veda"]
                        if v.get("_modo") == "car_unica":
                            veda_nac_str = "Sí" if v["en_veda_nacional"] else "No"
                            veda_reg_str = v["_car"] if v["nivel"] in ("regional", "nacional+regional") else "—"
                            col_car_reg = f"CAR consultada ({v['_car']})"
                        else:
                            veda_nac_str = "Sí" if v["en_veda_nacional"] else "No"
                            veda_reg_str = ", ".join(
                                [x["car"] for x in v["regionales"] if not x["solo_nacional"]]
                            ) or "—"
                            col_car_reg = "CAR con veda regional propia"
                        filas_export.append({
                            "Nombre científico": r["nombre"],
                            "Nombre común":      r["nombre_comun"],
                            "Familia":           r["familia"],
                            "MADS (Res. 0126/2024)": _estado_con_abrev_excel(r["mads"]),
                            "CITES":             _estado_con_abrev_excel(r["cites"]),
                            "IUCN":              _estado_con_abrev_excel(r["iucn"]),
                            "Veda nacional":     veda_nac_str,
                            col_car_reg:         veda_reg_str,
                        })
                    df_res = pd.DataFrame(filas_export)
                    st.dataframe(df_res, use_container_width=True, hide_index=True)

                    # ── Excel: SOLO estas 4 columnas, en este orden ──────────
                    df_excel = pd.DataFrame([
                        {
                            "Especie": r["nombre"],
                            "CITES":   _estado_con_abrev_excel(r["cites"]),
                            "IUCN":    _estado_con_abrev_excel(r["iucn"]),
                            "MADS":    _estado_con_abrev_excel(r["mads"]),
                        }
                        for r in resultados
                    ])
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
                        df_excel.to_excel(xw, index=False, sheet_name="Consulta amenaza y vedas")
                    st.download_button(
                        "⬇️ Descargar Excel",
                        data=buf.getvalue(),
                        file_name="consulta_amenaza_vedas.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_consulta_sp{key_suffix}",
                    )

    # ── Cruce con inventario cargado (si aplica) ──────────────────────────────
    st.markdown("---")
    _section("Especies en Veda Detectadas en el Inventario Cargado", "📋")
    if todas_vedas is not None:
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
    else:
        st.caption(
            "💡 Carga el KMZ y el inventario forestal para ver el cruce automático "
            "con las especies inventariadas."
        )

    # ── Navegador de vedas por CAR (las 31 CAR de Colombia) ──────────────────
    st.markdown("---")
    _section("Vedas Nacionales y por CAR — Mapa Completo (31 CAR)", "🏛️")
    cars_disponibles = ["NACIONAL"] + sorted(VEDAS_REGIONALES.keys())
    default_cars = [car_proyecto] if car_proyecto and car_proyecto in VEDAS_REGIONALES else []
    cars_sel = st.multiselect(
        "Selecciona 'NACIONAL' y/o una o varias CAR para ver su listado de especies vedadas",
        options=cars_disponibles,
        default=default_cars,
        help="Si seleccionaste una CAR en el sidebar, aparece preseleccionada. "
             "Elige 'NACIONAL' para ver las vedas que aplican en todo el país.",
        key=f"vedas_cars_sel{key_suffix}"
    )
    if not cars_sel:
        st.caption("Selecciona al menos una opción para ver sus vedas.")
    else:
        for car_key in cars_sel:
            if car_key == "NACIONAL":
                st.markdown("### 🇨🇴 NACIONAL — 🔴 Veda indefinida (todo el territorio)")
                st.caption(
                    "Fuentes: Res. 0316/1974 INDERENA · Ley 61/1985 · "
                    "Res. 1602/1995 + Res. 020/1996 MADS"
                )
                rows_nac = [
                    {
                        "Nombre común": sp["nombre_comun"],
                        "Nombre científico (fragmentos)": "; ".join(
                            n.capitalize() for n in sp["sci_fragmentos"]
                        ),
                        "Norma": sp["norma"],
                        "Nota": sp["nota"],
                    }
                    for sp in VEDAS_NACIONALES
                ]
                st.dataframe(pd.DataFrame(rows_nac), use_container_width=True, hide_index=True)
                st.markdown("---")
                continue

            datos = VEDAS_REGIONALES[car_key]
            tipo_badge = (
                "🔴 Veda indefinida" if datos.get("tipo") == "indefinida"
                else "🟡 Veda temporal" if datos.get("tipo") == "temporal"
                else "⚪ Sin veda regional propia"
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
            elif datos.get("solo_nacional"):
                st.caption("👉 Sin especies propias — consulta la fila 'NACIONAL' de arriba.")
            st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA DE BIENVENIDA
# ══════════════════════════════════════════════════════════════════════════════
if not impacto_file or not excel_file:
    _tab_welcome = st.tabs(["🔍 Consulta y Vedas", "ℹ️ Cómo usar"])
    with _tab_welcome[0]:
        _render_tab_consulta_vedas(key_suffix="_bienvenida", todas_vedas=None, car_proyecto=car_proyecto)
    with _tab_welcome[1]:
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
        <li><b>FCAFU</b> por cobertura — criterios A, B (máximo entre MADS/CITES/IUCN) y C del Manual 2026</li>
        <li><b>ATC</b> por rango geográfico R1–R6</li>
        <li><b>Tasa BAU</b> dinámica por municipio, SZH y ZH (Hansen GFC)</li>
        <li><b>Adicionalidad</b> a 3, 5, 10 y 15 años — Conservar y Restaurar</li>
        <li><b>Consulta y Vedas</b>: amenaza (MADS/CITES/IUCN) y vedas nacional + 31 CAR, cruzadas con el inventario</li>
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

# ─── CAR competente: automática por municipio/departamento, con override manual ───
_car_detectada = ctx.get('car')
if not car_proyecto and _car_detectada:
    car_proyecto = _car_detectada
    st.info(
        f"📍 CAR detectada automáticamente para **{ctx['municipio']} "
        f"({ctx['departamento']})** → **{car_proyecto}**. "
        f"{ctx.get('car_mensaje', '')}"
    )
elif not car_proyecto and not _car_detectada:
    st.warning(
        f"⚠️ No se pudo determinar la CAR automáticamente para "
        f"{ctx['municipio']} ({ctx['departamento']}). {ctx.get('car_mensaje', '')}"
    )
elif car_proyecto and _car_detectada and car_proyecto != _car_detectada:
    st.warning(
        f"⚠️ Seleccionaste manualmente **{car_proyecto}** en la barra lateral, "
        f"pero la detección automática por municipio/departamento sugiere "
        f"**{_car_detectada}** ({ctx.get('car_mensaje', '')}). Verifica cuál "
        f"es la CAR competente antes de continuar — se usará la que "
        f"seleccionaste manualmente ({car_proyecto})."
    )

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

with st.spinner("Calculando ATC por rango..."):
    try:
        atc_resultados = atc.calcular_atc_por_rangos(fcafu_por_cobertura, ctx)
    except Exception as e:
        st.error(f"❌ Error calculando ATC: {e}"); st.stop()

st.success("✅ Procesamiento completo")

# Tasas BAU
tasa_bau     = ctx.get('tasa_bau', 0.005)
tasa_bau_szh = ctx.get('tasa_bau_szh', tasa_bau)
tasa_bau_zh  = ctx.get('tasa_bau_zh',  tasa_bau)
fuente_bau     = ctx.get('tasa_bau_fuente',     'Hansen GFC')
fuente_bau_szh = ctx.get('tasa_bau_szh_fuente', 'Hansen GFC')
fuente_bau_zh  = ctx.get('tasa_bau_zh_fuente',  'Hansen GFC')

TASA_POR_NIVEL = {
    "Rango 1": tasa_bau,
    "Rango 2": tasa_bau_szh,
    "Rango 3": tasa_bau_zh,
    "Rango 4": tasa_bau,
    "Rango 5": tasa_bau_szh,
    "Rango 6": tasa_bau_zh,
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
    "🔍 Consulta y Vedas",
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

    _section("Iniciativas de Conservación en la Zona", "🌿")
    st.caption(
        "RUNAP, REAA, OMEC, Bosque Seco Tropical (IAvH), Reservas Forestales Ley 2a "
        "y Portafolio CAR (si aplica) — a nivel de Municipio y SZH."
    )

    _cache_key = f"iniciativas_{ctx.get('municipio','')}_{ctx.get('szh','')}"

    if st.button("🌿 Consultar iniciativas de conservación (GEE)", key="btn_iniciativas"):
        with st.spinner("Consultando RUNAP / REAA / OMEC / BST / Reservas en GEE..."):
            try:
                filas_iniciativas = iniciativas.obtener_iniciativas(ctx)
                st.session_state[_cache_key] = filas_iniciativas
            except Exception as e:
                st.error(f"❌ Error consultando iniciativas: {e}")

    if _cache_key in st.session_state:
        df_ini = iniciativas.deduplicar_iniciativas(st.session_state[_cache_key])
        if df_ini.empty:
            st.info("No se encontraron iniciativas de conservación en el municipio ni la SZH.")
        else:
            st.dataframe(df_ini, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Descargar iniciativas (CSV)",
                # sep=';' — Excel en español usa ',' como separador decimal, así
                # que interpreta ';' como separador de columnas. Como nuestros
                # valores (ej. columna 'niveles', tags de OMEC/REAA) ya tienen
                # comas adentro, usar ',' como separador partía esas celdas.
                # encode('utf-8-sig') agrega el BOM que Excel necesita para
                # detectar UTF-8 y no romper tildes/ñ (CaÃ±o -> Caño).
                data=df_ini.to_csv(index=False, sep=';').encode("utf-8-sig"),
                file_name=f"{ctx.get('municipio','proyecto')}_iniciativas_conservacion.csv",
                mime="text/csv",
            )


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
            filas_fcafu.append({
                "Cobertura":          cob,
                "N":                  d.get('N', 0),
                "S":                  d.get('S', 0),
                "A":                  round(d.get('A', 0), 3),
                "B":                  round(d.get('B', 0), 4),
                "C":                  round(d.get('C', 0), 3),
                "FCAFU":              round(d.get('FCAFU', 0), 3),
            })
        df_fcafu = pd.DataFrame(filas_fcafu)
        st.dataframe(df_fcafu, use_container_width=True, hide_index=True)

        st.info(
            "**Criterio B** toma en cuenta las tres fuentes de amenaza "
            "(MADS Res. 0126/2024, CITES e IUCN) y usa el **valor máximo** "
            "por individuo — un solo valor, sin escenarios separados. "
            "`[MARCA_VERSION: max-B-v2]`"
        )

        # ── Resumen de TODAS las especies y su estado de amenaza ──────────
        # A diferencia del "Desglose Criterio B" (que solo aparece si hay
        # especies amenazadas/vedadas), este resumen se muestra siempre,
        # aunque ninguna especie esté en peligro — mismo estilo de tabla
        # que la pestaña "Consulta y Vedas".
        todas_especies_proyecto = sorted({
            sp for d in fcafu_por_cobertura.values()
            for sp in d.get('todas_especies', [])
        })
        if todas_especies_proyecto:
            with st.expander(
                f"📋 Resumen de especies y estado de amenaza ({len(todas_especies_proyecto)} spp.)",
                expanded=True
            ):
                mads_idx, cites_idx, iucn_idx = _cargar_indices_amenaza()
                resultados_resumen = [
                    _consultar_amenaza_sp(sp, mads_idx, cites_idx, iucn_idx, car_filtro=car_proyecto)
                    for sp in todas_especies_proyecto
                ]
                st.markdown(
                    _tabla_consulta_html(
                        resultados_resumen,
                        mostrar_mads=True, mostrar_cites=True, mostrar_iucn=True,
                        mostrar_veda=True, car_filtro=car_proyecto,
                    ),
                    unsafe_allow_html=True
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
                    B  = round(d.get('B', 0), 4)

                    st.markdown(
                        f"**{cob}** — N={N} ind. &nbsp; B=`{B}`",
                        unsafe_allow_html=True
                    )
                    rows_b = []
                    for sp in spp_cob:
                        n_sp = sp.get('n_individuos', 1)
                        v    = sp.get('valor_b', 0.0)
                        ap     = sp.get('cites_apendice',  '—')
                        cat    = sp.get('categoria_amenaza','—')
                        cat_ui = sp.get('cat_uicn',        '—')
                        rows_b.append({
                            'Nombre científico': sp.get('nombre_cientifico',''),
                            'Cat. Res.0126':     cat,
                            'CITES':             ap,
                            'Cat. UICN':         cat_ui,
                            'Valor B (máximo)':  v,
                            'N ind.':            n_sp,
                            'Aporte a B':        sp.get('aporte_b', round(v*n_sp/N,4) if N else 0),
                        })
                    st.dataframe(
                        pd.DataFrame(rows_b),
                        use_container_width=True, hide_index=True
                    )
                    st.markdown("---")

        # ── Desglose criterio A ──────────────────────────────────────────
        with st.expander("🌿 Desglose Criterio A — Grado de transformación por cobertura", expanded=False):
            st.markdown(
                r"**Fórmula:** valor A fijo por tipo de cobertura según Tabla 3, Res. 0305/2026.  "
                "Coberturas transformadas → A=0; coberturas naturales → A>0 (hasta 1.0 para bosque denso)."
            )
            filas_a = []
            for cob, d in fcafu_por_cobertura.items():
                filas_a.append({
                    "Cobertura":    cob,
                    "N ind.":       d.get('N', 0),
                    "Valor A":      round(d.get('A', 0), 3),
                    "Grado transf.": "Natural" if d.get('A', 0) > 0 else "Transformado",
                    "Aporte a FCAFU": f"+{round(d.get('A',0),3)}"
                })
            st.dataframe(pd.DataFrame(filas_a), use_container_width=True, hide_index=True)
            st.caption(
                "Fuente: Tabla 3 (Resolución 0305/2026 MADS). "
                "Para coberturas transformadas (pastos, cultivos, urbano) A=0 — "
                "el factor de ajuste viene exclusivamente de B y C."
            )

        # ── Desglose criterio C ──────────────────────────────────────────
        with st.expander("🔢 Desglose Criterio C — Diversidad (S/N) por cobertura", expanded=False):
            st.markdown(
                r"**Fórmula:** $C = f\!\left(\dfrac{S}{N}\right)$  "
                "donde **S** = riqueza de especies y **N** = total de individuos inventariados."
            )
            filas_c = []
            for cob, d in fcafu_por_cobertura.items():
                n  = d.get('N', 0)
                s  = d.get('S', 0)
                sn = round(d.get('SN', s/n if n else 0), 4)
                c  = round(d.get('C', 0), 3)
                filas_c.append({
                    "Cobertura":   cob,
                    "N ind.":      n,
                    "S spp.":      s,
                    "S/N":         sn,
                    "Rango S/N":   f"[{round((sn//0.1)*0.1,1):.1f} – {round((sn//0.1)*0.1+0.1,1):.1f})",
                    "Valor C":     c,
                    "Aporte a FCAFU": f"+{c}",
                })
            st.dataframe(pd.DataFrame(filas_c), use_container_width=True, hide_index=True)
            st.caption(
                "Fuente: Tabla de rangos S/N (Resolución 0305/2026 MADS). "
                "Mayor diversidad relativa → mayor C → mayor FCAFU. "
                "S/N=1 (todos distintos) fuerza C=1.0."
            )

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
        "El criterio B usa el valor máximo entre MADS, CITES e IUCN por individuo."
    )

    if atc_resultados:
        filas_atc = []
        for rango_id, data in atc_resultados.items():
            filas_atc.append({
                "Rango":               rango_id,
                "Factor adicional":    data['factor_adicional'],
                "ATC (ha)":            round(data['atc_total'], 3),
            })
        st.dataframe(
            pd.DataFrame(filas_atc),
            use_container_width=True, hide_index=True
        )

        st.markdown("---")
        st.caption("Criterio B: max(MADS, CITES, UICN) por individuo")
        for rango_id, data in atc_resultados.items():
            with st.expander(
                f"{rango_id} — ATC = {round(data['atc_total'],3)} ha  "
                f"(factor +{data['factor_adicional']})"
            ):
                if data.get('detalles'):
                    st.dataframe(pd.DataFrame(data['detalles']), use_container_width=True, hide_index=True)


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
                     atc_resultados,
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
                    "Cobertura":        cob,
                    "N":                d["N"], "S": d["S"],
                    "S/N":              round(d["SN"], 4),
                    "A":                d["A"],
                    "B":                round(d.get("B", 0), 4),
                    "C":                d["C"],
                    "FCAFU":            round(d["FCAFU"], 4),
                    "AB total (m²)":    round(d.get("area_basal_total",0), 4),
                })
            pd.DataFrame(rows_f).to_excel(writer, sheet_name="FCAFU", index=False)

            # Hoja 3 – ATC
            rows_a = []
            for rid, data in atc_resultados.items():
                rows_a.append({
                    "Rango": rid,
                    "Factor adicional": data.get("factor_adicional",""),
                    "ATC (ha)": round(data["atc_total"], 4),
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
                        "Cat. UICN":        sp.get("cat_uicn","—"),
                        "Valor B (máximo)": sp.get("valor_b", 0),
                        "N individuos":     sp.get("n_individuos", 0),
                        "Aporte a B":       sp.get("aporte_b", 0),
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
            atc_resultados,
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
            "Hojas incluidas: Resumen · FCAFU · ATC por Rango · "
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
# TAB 6 — CONSULTA DE ESTADO DE AMENAZA Y VEDAS (nacional + 31 CAR)
# ════════════════════════════════════════════════════════════════════════
with tab6:
    _render_tab_consulta_vedas(key_suffix="_tab6", todas_vedas=todas_vedas, car_proyecto=car_proyecto)
