# -*- coding: utf-8 -*-
"""
Exportación a Excel del Plan de Compensación Biótica.

Arma un solo libro con las tablas del formato de informe (Tablas 3, 4, 9, 10,
11, 14, 17, 18 y 19), más vedas, estado de amenaza de las especies, curvas de
adicionalidad con gráficos nativos de Excel y fuentes.

Los cálculos de FCAFU, ATC y adicionalidad se escriben como FÓRMULAS de Excel
que apuntan a sus insumos (A, B, C, áreas, tasas y parámetros), así el libro
se puede auditar y recalcula solo si alguien corrige un valor.

La app solo prepara los datos (dict `datos`, ver build_excel) y este módulo
se encarga del formato.
"""
import io
from datetime import date

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ── Paleta Unergy ────────────────────────────────────────────────────────────
MORADO_OSCURO = "2D1B4E"
MORADO = "7B4CC9"
MORADO_CLARO = "D9CEEF"
LAVANDA = "F6F3FC"
BORDE = "CFC4EA"
TEXTO = "1A1A2E"
GRIS = "6B6B80"

FUENTE = "Arial"
_lado = Side(style="thin", color=BORDE)
BORDE_CELDA = Border(left=_lado, right=_lado, top=_lado, bottom=_lado)

# Colores por categoría de amenaza / veda (relleno, texto)
COLOR_CATEGORIA = {
    "CR": ("F8D7DA", "9B1C1C"),
    "EN": ("FDE2C8", "A04A00"),
    "VU": ("FFF1BF", "7A5C00"),
    "NT": ("E6F0D5", "4A6B1E"),
    "LC": ("D7F0DD", "1E7B34"),
    "I": ("F8D7DA", "9B1C1C"),     # Apéndice I CITES
    "II": ("FDE2C8", "A04A00"),
    "III": ("FFF1BF", "7A5C00"),
}
COLOR_VEDA = ("FDECEA", "B71C1C")
COLOR_SIN = ("F1F1F4", GRIS)

# Tabla 9 del formato de informe (Manual 2026)
RANGOS_DESCRIPCION = {
    1: "BIOMA-IAvH dentro del Área de Influencia del POA (componentes físico, biótico y socioeconómico)",
    2: "BIOMA-IAvH dentro de la subzona hidrográfica del POA",
    3: "BIOMA-IAvH dentro de la zona hidrográfica del POA",
    4: "Otro BIOMA-IAvH dentro del Área de Influencia del POA",
    5: "Otro BIOMA-IAvH dentro de la subzona hidrográfica con mayor factor que el impactado",
    6: "Áreas protegidas del SINAP (únicamente por fuerza mayor, debidamente justificada)",
}

FMT_HA = "#,##0.000"
FMT_HA4 = "#,##0.0000"
FMT_FACTOR = "0.000"
FMT_PCT = "0.000%"
FMT_ENTERO = "#,##0"


def _font(**kw):
    base = {"name": FUENTE, "size": 10, "color": TEXTO}
    base.update(kw)
    return Font(**base)


def _clave_categoria(texto):
    """'VU' → 'VU'; 'Apéndice II' → 'II'; 'No aplica (NA)' → None."""
    t = str(texto or "").strip()
    if t.startswith("Apéndice"):
        return t.replace("Apéndice", "").strip()
    return t if t in COLOR_CATEGORIA else None


class Hoja:
    """Escribe bloques (título, tablas, notas) uno debajo del otro."""

    def __init__(self, wb, nombre, titulo, subtitulo="", anchos=None):
        self.ws = wb.create_sheet(nombre)
        self.ws.sheet_view.showGridLines = False
        self.ws.sheet_view.zoomScale = 90
        self.fila = 1
        self.ncols = len(anchos) if anchos else 6
        for i, w in enumerate(anchos or [], start=1):
            self.ws.column_dimensions[get_column_letter(i)].width = w
        self._banda(titulo, subtitulo)

    # ── bloques ──────────────────────────────────────────────────────────
    def _banda(self, titulo, subtitulo):
        ws = self.ws
        fin = get_column_letter(self.ncols)
        ws.merge_cells(f"A1:{fin}1")
        c = ws["A1"]
        c.value = titulo
        c.font = _font(size=15, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=MORADO_OSCURO)
        c.alignment = Alignment(vertical="center", indent=1)
        ws.row_dimensions[1].height = 34
        ws.merge_cells(f"A2:{fin}2")
        c = ws["A2"]
        c.value = subtitulo
        c.font = _font(size=9, color="E8E0FA")
        c.fill = PatternFill("solid", fgColor=MORADO_OSCURO)
        c.alignment = Alignment(vertical="center", indent=1)
        ws.row_dimensions[2].height = 20
        self.fila = 4

    def subtitulo(self, texto):
        c = self.ws.cell(row=self.fila, column=1, value=texto)
        c.font = _font(size=12, bold=True, color=MORADO_OSCURO)
        self.fila += 1

    def nota(self, texto, color=GRIS, italica=True, alto=None):
        fin = get_column_letter(self.ncols)
        self.ws.merge_cells(f"A{self.fila}:{fin}{self.fila}")
        c = self.ws.cell(row=self.fila, column=1, value=texto)
        c.font = _font(size=9, italic=italica, color=color)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if alto:
            self.ws.row_dimensions[self.fila].height = alto
        self.fila += 1

    def espacio(self, n=1):
        self.fila += n

    def tabla(self, titulo, encabezados, filas, formatos=None, total=None,
              colorear=None, ajustar=None, alto_encabezado=32):
        """
        filas: lista de listas (valores o fórmulas '=...').
        formatos: {índice_col: number_format}.
        total: lista para la fila de total (valores o fórmulas), opcional.
        colorear: índices de columnas con categorías de amenaza/veda.
        ajustar: índices de columnas de texto largo (wrap).
        Devuelve (fila_primera_dato, fila_última_dato).
        """
        ws = self.ws
        formatos = formatos or {}
        colorear = set(colorear or [])
        ajustar = set(ajustar or [])
        if titulo:
            c = ws.cell(row=self.fila, column=1, value=titulo)
            c.font = _font(size=10, bold=True, color=MORADO)
            self.fila += 1

        for j, h in enumerate(encabezados, start=1):
            c = ws.cell(row=self.fila, column=j, value=h)
            c.font = _font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor=MORADO)
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = BORDE_CELDA
        ws.row_dimensions[self.fila].height = alto_encabezado
        self.fila += 1

        primera = self.fila
        for i, fila in enumerate(filas):
            relleno = PatternFill("solid", fgColor=LAVANDA) if i % 2 else None
            for j, v in enumerate(fila, start=1):
                c = ws.cell(row=self.fila, column=j, value=v)
                c.font = _font()
                c.border = BORDE_CELDA
                es_num = isinstance(v, (int, float)) or (isinstance(v, str) and v.startswith("="))
                c.alignment = Alignment(
                    horizontal="right" if es_num else ("left" if (j - 1) in ajustar or j == 1 else "center"),
                    vertical="center", wrap_text=(j - 1) in ajustar,
                )
                if (j - 1) in formatos:
                    c.number_format = formatos[j - 1]
                if relleno:
                    c.fill = relleno
                if (j - 1) in colorear:
                    self._colorear(c, v)
            self.fila += 1
        ultima = self.fila - 1

        if total:
            for j, v in enumerate(total, start=1):
                c = ws.cell(row=self.fila, column=j, value=v)
                c.font = _font(bold=True, color=MORADO_OSCURO)
                c.fill = PatternFill("solid", fgColor=MORADO_CLARO)
                c.border = BORDE_CELDA
                c.alignment = Alignment(horizontal="right" if j > 1 else "left", vertical="center")
                if (j - 1) in formatos:
                    c.number_format = formatos[j - 1]
            self.fila += 1
        self.fila += 1
        return primera, ultima

    @staticmethod
    def _colorear(c, v):
        texto = str(v or "")
        if texto.lower().startswith("veda") or texto.lower().startswith("sí"):
            fondo, letra = COLOR_VEDA
        else:
            k = _clave_categoria(texto)
            fondo, letra = COLOR_CATEGORIA.get(k, COLOR_SIN) if k else COLOR_SIN
        c.fill = PatternFill("solid", fgColor=fondo)
        c.font = _font(bold=True, color=letra, size=9)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _estilo_grafico(ch, titulo, eje_x, eje_y):
    ch.title = titulo
    ch.x_axis.title = eje_x
    ch.y_axis.title = eje_y
    ch.roundedCorners = False
    ch.legend.position = "b"
    ch.legend.overlay = False
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ch.height = 9
    ch.width = 18


# ═════════════════════════════════════════════════════════════════════════════
def build_excel(datos):
    """
    datos: dict con
      proyecto: {municipio, departamento, car, bioma, zh, szh, ecosistema,
                 area_impacto_ha}
      coberturas: [{cobertura, area_ha, N, S, A, B, C, n_amenazadas, n_veda}]
      rangos: [{rango, factor, descripcion, tasa_bau}]
      tasas: {municipio, szh, zh}     (fracciones, p. ej. 0.00492)
      params: {f_conservar, f_restaurar, k, horizontes, max_anios}
      especies: [{nombre, nombre_comun, familia, mads, cites, iucn, veda}]
      amenazadas: [{cobertura, nombre, mads, cites, iucn, v, n, aporte}]
      vedas: [{cobertura, nombre, n, nivel, norma, alerta}]
      obligaciones: [(titulo, [items])]
      iniciativas: [{figura, categoria, nombre, entidad, niveles}] o None
      especies_zona_vida: (titulo_zona, [{zona, nombre, comun, familia, grupo, amenaza}])
      fuentes: [str]
    """
    p = datos["proyecto"]
    prm = datos["params"]
    wb = Workbook()
    wb.remove(wb.active)
    sub = f"Unergy Energía Digital S.A.S. E.S.P.  |  Manual 2026 (Res. 0305/2026 MADS)  |  Generado {date.today():%d/%m/%Y}"
    municipio = p.get("municipio", "n/d")

    # ── 1. Resumen ───────────────────────────────────────────────────────────
    h = Hoja(wb, "Resumen", f"Plan de compensación biótica — {municipio}", sub, [42, 48, 14, 14, 14, 14])
    resumen = h

    # ── 2. Coberturas y FCAFU (Tablas 4 y 10) ────────────────────────────────
    hc = Hoja(wb, "Coberturas y FCAFU", "Coberturas afectadas y FCAFU", sub, [26, 14, 12, 12, 12, 13, 14])
    cobs = datos["coberturas"]
    f4 = hc.fila + 2                      # primera fila de datos (título + encabezado)
    u4_ = f4 + len(cobs) - 1
    hc.tabla(
        "Tabla 4. Resumen de coberturas afectadas",
        ["Tipo de cobertura", "Área a aprovechar AT(i) (ha)", "N° de individuos inventariados",
         "N° de especies amenazadas", "N° de especies en veda"],
        [[c["cobertura"], c["area_ha"], c["N"], c["n_amenazadas"], c["n_veda"]] for c in cobs],
        formatos={1: FMT_HA, 2: FMT_ENTERO, 3: FMT_ENTERO, 4: FMT_ENTERO},
        total=["Total", f"=SUM(B{f4}:B{u4_})", f"=SUM(C{f4}:C{u4_})", None, None],
        alto_encabezado=44,
    )

    filas10 = []
    fila_dato = hc.fila + 2  # título + encabezado
    for i, c in enumerate(cobs):
        r = fila_dato + i
        filas10.append([c["cobertura"], c["area_ha"], c["A"], c["B"], c["C"],
                        f"=1+C{r}+D{r}+E{r}", f"=B{r}*F{r}"])
    p10, u10 = hc.tabla(
        "Tabla 10. Resultado del cálculo del FCAFU por cobertura y del área a compensar",
        ["Cobertura", "AT(i) (ha)", "a", "b", "c", "FCAFU(i)", "AC(i) (ha)"],
        filas10,
        formatos={1: FMT_HA, 2: FMT_FACTOR, 3: FMT_FACTOR, 4: FMT_FACTOR, 5: FMT_FACTOR, 6: FMT_HA},
        total=["Área total a compensar", None, None, None, None, None, f"=SUM(G{fila_dato}:G{fila_dato + len(cobs) - 1})"],
    )
    hc.nota("FCAFU(i) = 1 + a + b + c.  a: grado de transformación (Tabla 3, Res. 0305/2026); "
            "b: amenaza, promedio por individuo del valor máximo entre MADS, CITES e IUCN "
            "(CR = 1,0; EN = 0,6; VU = 0,4); c: diversidad según S/N.  AC(i) = AT(i) × FCAFU(i).")
    hc.ws.freeze_panes = "B4"
    rango_at = f"'Coberturas y FCAFU'!$B${p10}:$B${u10}"
    rango_fc = f"'Coberturas y FCAFU'!$F${p10}:$F${u10}"

    # ── 3. ATC por rango (Tablas 9 y 11) + gráfico ───────────────────────────
    ha = Hoja(wb, "ATC por rango", "Área total a compensar por jerarquía de zonificación", sub, [14, 70, 18, 16])
    rangos = datos["rangos"]
    ha.tabla(
        "Tabla 9. Rangos geográficos para la delimitación de la zonificación potencial",
        ["N°", "Rango geográfico", "Factor adicional al FCAFU"],
        [[i + 1, r["descripcion"], "FCAFU" if not r["factor"] else f"FCAFU + {r['factor']:g}".replace(".", ",")]
         for i, r in enumerate(rangos)],
        ajustar={1},
    )
    fila_dato = ha.fila + 2
    filas11 = []
    for i, r in enumerate(rangos):
        fr = fila_dato + i
        filas11.append([f"Jerarquía {i + 1}", r["factor"],
                        f"=SUMPRODUCT({rango_at},{rango_fc}+B{fr})"])
    p11, u11 = ha.tabla(
        "Tabla 11. Área total a compensar por jerarquía de zonificación",
        ["Rango", "Factor adicional", "ATC total (ha)"],
        filas11, formatos={1: "0.0", 2: FMT_HA},
    )
    ha.nota("ATC = Σ AT(i) × (FCAFU(i) + factor del rango). Las fórmulas toman AT(i) y FCAFU(i) "
            "de la hoja «Coberturas y FCAFU».")
    ch = BarChart()
    ch.type = "col"
    ch.add_data(Reference(ha.ws, min_col=3, min_row=p11 - 1, max_row=u11), titles_from_data=True)
    ch.set_categories(Reference(ha.ws, min_col=1, min_row=p11, max_row=u11))
    _estilo_grafico(ch, "ATC por jerarquía", "Jerarquía", "ha")
    ch.legend = None
    ch.series[0].graphicalProperties.solidFill = MORADO
    ch.series[0].graphicalProperties.line.solidFill = MORADO
    ha.ws.add_chart(ch, f"A{ha.fila + 1}")
    rango_atc = f"'ATC por rango'!$C${p11}:$C${u11}"

    # ── 4. Adicionalidad (Tablas 17 y 19) ────────────────────────────────────
    hd = Hoja(wb, "Adicionalidad", "Adicionalidad esperada", sub, [24, 26, 30, 18, 18, 18, 18])
    hd.subtitulo("Parámetros")
    pp, _ = hd.tabla(None, ["Parámetro", "Valor", "Fuente"], [
        ["Efectividad conservar", prm["f_conservar"], "Andam et al. 2008; Pfaff et al. 2014"],
        ["Efectividad restaurar", prm["f_restaurar"], "Crouzeilles et al. 2017"],
        ["k restauración (año⁻¹)", prm["k"], f"Poorter et al. 2021 — {p.get('ecosistema', '')}"],
    ], formatos={1: "0.000"}, ajustar={2})
    C_FC, C_FR, C_K = f"$B${pp}", f"$B${pp + 1}", f"$B${pp + 2}"

    tasas = datos["tasas"]
    hd.tabla(
        "Tabla 17. Tasa de pérdida anual de cobertura boscosa (TPACB)",
        ["Escala", "Nombre", "TPACB (%)"],
        [["Municipio", municipio, tasas["municipio"]],
         ["Subzona hidrográfica", p.get("szh", "n/d"), tasas["szh"]],
         ["Zona hidrográfica", p.get("zh", "n/d"), tasas["zh"]]],
        formatos={2: FMT_PCT},
    )
    hd.nota("Fuente: Hansen et al. (2013), Global Forest Change.")

    fila_dato = hd.fila + 2
    filas19 = []
    for i, r in enumerate(rangos):
        fr = fila_dato + i
        filas19.append([
            f"Jerarquía {i + 1}", f"=INDEX({rango_atc},{i + 1})", r["tasa_bau"],
            f"=B{fr}*C{fr}*{C_FC}",
            f"=B{fr}*(1-(1-C{fr})^3)*{C_FC}",
            f"=B{fr}*(1-EXP(-{C_K}*3))*{C_FR}",
        ])
    p19, u19 = hd.tabla(
        "Tabla 19. Proyección de adicionalidad para preservación y restauración a 3 años",
        ["Rango", "ATC (ha)", "TPACB (%)", "Adicionalidad por preservar (ha/año)",
         "Adicionalidad por preservar a 3 años (ha)", "Adicionalidad por restaurar a 3 años (ha)"],
        filas19, formatos={1: FMT_HA, 2: FMT_PCT, 3: FMT_HA, 4: FMT_HA, 5: FMT_HA}, alto_encabezado=44,
    )

    hz = prm["horizontes"]
    for nombre_esc in ("Conservar", "Restaurar", "Mix 50/50"):
        fila_dato = hd.fila + 2
        filas = []
        for i, r in enumerate(rangos):
            fr = fila_dato + i
            fila = [f"Jerarquía {i + 1}", f"=B{p19 + i}", f"=C{p19 + i}"]
            for j, n in enumerate(hz):
                if nombre_esc == "Conservar":
                    fila.append(f"=B{fr}*(1-(1-C{fr})^{n})*{C_FC}")
                elif nombre_esc == "Restaurar":
                    fila.append(f"=B{fr}*(1-EXP(-{C_K}*{n}))*{C_FR}")
                else:
                    fila.append(f"=0.5*B{fr}*(1-(1-C{fr})^{n})*{C_FC}+0.5*B{fr}*(1-EXP(-{C_K}*{n}))*{C_FR}")
            filas.append(fila)
        hd.tabla(
            f"{nombre_esc}: hectáreas adicionales por horizonte",
            ["Rango", "ATC (ha)", "TPACB (%)"] + [f"{n} años (ha)" for n in hz],
            filas, formatos={1: FMT_HA, 2: FMT_PCT, **{3 + j: FMT_HA4 for j in range(len(hz))}},
        )
    hd.nota("Conservar: ha × [1 − (1 − TPACB)ⁿ] × efectividad.  Restaurar: ha × [1 − e^(−k·n)] × efectividad "
            "(Chapman-Richards, recuperación de cobertura).  Mix: mitad del ATC en cada estrategia.")

    # ── 5. Curvas (datos con fórmulas + gráficos nativos) ────────────────────
    hv = Hoja(wb, "Curvas", "Ganancia de cobertura por hectárea compensada", sub, [10, 18, 18, 4, 10, 18, 18])
    ref_fc = f"Adicionalidad!{C_FC}"
    ref_fr = f"Adicionalidad!{C_FR}"
    ref_k = f"Adicionalidad!{C_K}"
    tasa_mun = "Adicionalidad!$C$" + str(_fila_tasa_municipio(hd.ws))
    inicio = hv.fila
    max_anios = prm["max_anios"]

    def _filas_curva(n_anios, fila0):
        out = []
        for a in range(n_anios + 1):
            out.append([a, f"=(1-(1-{tasa_mun})^A{fila0 + a})*{ref_fc}",
                        f"=(1-EXP(-{ref_k}*A{fila0 + a}))*{ref_fr}"])
        return out

    p15, u15 = hv.tabla("Curva a 15 años", ["Año", "Conservar (ha/ha)", "Restaurar (ha/ha)"],
                        _filas_curva(15, hv.fila + 2), formatos={1: FMT_HA4, 2: FMT_HA4})
    lc = LineChart()
    lc.add_data(Reference(hv.ws, min_col=2, max_col=3, min_row=p15 - 1, max_row=u15), titles_from_data=True)
    lc.set_categories(Reference(hv.ws, min_col=1, min_row=p15, max_row=u15))
    _estilo_grafico(lc, f"Ganancia de cobertura — 15 años ({p.get('ecosistema', '')})",
                    "Años", "ha adicionales / ha compensada")
    _colores_series(lc)

    # Curva completa en columnas E:G (al lado), con su gráfico debajo del primero
    fila_full0 = inicio + 2
    hv.ws.cell(row=inicio, column=5, value=f"Curva hasta estabilización ({max_anios} años)").font = _font(bold=True, color=MORADO)
    for j, hdr in enumerate(["Año", "Conservar (ha/ha)", "Restaurar (ha/ha)"], start=5):
        c = hv.ws.cell(row=inicio + 1, column=j, value=hdr)
        c.font = _font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=MORADO)
        c.alignment = Alignment(horizontal="center", wrap_text=True)
        c.border = BORDE_CELDA
    for a in range(max_anios + 1):
        fr = fila_full0 + a
        vals = [a, f"=(1-(1-{tasa_mun})^E{fr})*{ref_fc}", f"=(1-EXP(-{ref_k}*E{fr}))*{ref_fr}"]
        for j, v in enumerate(vals, start=5):
            c = hv.ws.cell(row=fr, column=j, value=v)
            c.font = _font()
            c.border = BORDE_CELDA
            if j > 5:
                c.number_format = FMT_HA4
            if a % 2:
                c.fill = PatternFill("solid", fgColor=LAVANDA)
    lc2 = LineChart()
    lc2.add_data(Reference(hv.ws, min_col=6, max_col=7, min_row=inicio + 1, max_row=fila_full0 + max_anios),
                 titles_from_data=True)
    lc2.set_categories(Reference(hv.ws, min_col=5, min_row=fila_full0, max_row=fila_full0 + max_anios))
    _estilo_grafico(lc2, "Ganancia de cobertura — hasta estabilización", "Años", "ha adicionales / ha compensada")
    _colores_series(lc2)
    # Los datos de la curva completa ocupan E:G; los gráficos van a la derecha
    hv.ws.add_chart(lc, "I4")
    hv.ws.add_chart(lc2, "I24")
    hv.ws.column_dimensions["H"].width = 3

    # ── 6. Especies y amenaza ────────────────────────────────────────────────
    he = Hoja(wb, "Especies y amenaza", "Estado de amenaza y veda de las especies inventariadas", sub,
              [30, 22, 18, 14, 14, 14, 26, 12])
    he.tabla(
        f"Especies del inventario ({len(datos['especies'])} spp.)",
        ["Nombre científico", "Nombre común", "Familia", "MADS (Res. 0126/2024)", "CITES", "IUCN",
         f"Veda ({p.get('car') or 'nacional + CAR'})"],
        [[s["nombre"], s["nombre_comun"], s["familia"], s["mads"], s["cites"], s["iucn"], s["veda"]]
         for s in datos["especies"]],
        colorear={3, 4, 5, 6}, alto_encabezado=36,
    )
    he.ws.freeze_panes = "B4"
    if datos["amenazadas"]:
        he.tabla(
            "Desglose del criterio b — individuos con categoría de amenaza",
            ["Cobertura", "Nombre científico", "MADS", "CITES", "IUCN", "Valor v (máximo)", "N ind.", "Aporte a b"],
            [[a["cobertura"], a["nombre"], a["mads"], a["cites"], a["iucn"], a["v"], a["n"], a["aporte"]]
             for a in datos["amenazadas"]],
            formatos={5: "0.0", 6: FMT_ENTERO, 7: "0.0000"}, colorear={2, 3, 4},
        )
    else:
        he.nota("Ninguna especie del inventario tiene categoría de amenaza: b = 0 en todas las coberturas.",
                color="1E7B34", italica=False)
    he.nota("Leyenda de colores: rojo = CR / Apéndice I / veda; naranja = EN / Apéndice II; "
            "amarillo = VU / Apéndice III; verde = NT y LC; gris = no aplica.")

    # ── 7. Vedas ─────────────────────────────────────────────────────────────
    hve = Hoja(wb, "Vedas", "Especies en veda y obligaciones", sub, [22, 28, 10, 18, 28, 60])
    if datos["vedas"]:
        hve.tabla(
            None, ["Cobertura", "Nombre científico", "N ind.", "Nivel de veda", "Norma", "Alerta"],
            [[v["cobertura"], v["nombre"], v["n"], v["nivel"], v["norma"], v["alerta"]] for v in datos["vedas"]],
            formatos={2: FMT_ENTERO}, colorear={3}, ajustar={4, 5},
        )
        for titulo, items in datos["obligaciones"]:
            hve.subtitulo(titulo)
            for k, it in enumerate(items, start=1):
                hve.nota(f"{k}. {it}", color=TEXTO, italica=False)
            hve.espacio()
    else:
        hve.nota("No se detectaron especies en veda (nacional ni regional) en el inventario.",
                 color="1E7B34", italica=False)
    hve.nota("Las vedas no modifican el FCAFU ni el área de compensación, pero generan obligaciones "
             "procedimentales ante la CAR. Verifica la norma vigente al momento de radicar.")

    # ── 8. Iniciativas de conservación (Tabla 18) ────────────────────────────
    hi = Hoja(wb, "Iniciativas", "Iniciativas de conservación existentes", sub, [26, 30, 40, 26, 18])
    if datos["iniciativas"]:
        hi.tabla(
            "Tabla 18. Iniciativas de conservación existentes en el municipio, zona y subzona hidrográfica",
            ["Figura", "Categoría", "Nombre", "Entidad", "Niveles"],
            [[i["figura"], i["categoria"], i["nombre"], i["entidad"], i["niveles"]] for i in datos["iniciativas"]],
            ajustar={0, 1, 2, 3},
        )
        hi.nota("Fuentes: RUNAP, REAA, OMEC, Bosque Seco Tropical (IAvH), Reservas Forestales Ley 2.ª "
                "y portafolio de la CAR, consultados en Google Earth Engine.")
    elif datos["iniciativas"] == []:
        hi.nota("No se encontraron iniciativas de conservación en el municipio ni en la subzona hidrográfica.",
                color="1E7B34", italica=False)
    else:
        hi.nota("No se pudieron obtener las iniciativas desde Google Earth Engine al generar este archivo. "
                "En la pestaña Contexto usa «Reintentar consulta» y vuelve a descargar el Excel.",
                color="A04A00", italica=False, alto=30)

    # ── 9. Especies para compensación (Tabla 14) ─────────────────────────────
    titulo_zv, filas_zv = datos["especies_zona_vida"]
    hz_ = Hoja(wb, "Especies compensación", "Especies nativas para la compensación", sub, [30, 30, 22, 18, 20, 16])
    if filas_zv:
        hz_.tabla(
            f"Tabla 14. Especies seleccionadas para compensación — {titulo_zv}",
            ["Zona de vida", "Nombre científico", "Nombre común", "Familia", "Grupo sucesional",
             "Amenaza (IUCN / Nacional)"],
            [[e["zona"], e["nombre"], e["comun"], e["familia"], e["grupo"], e["amenaza"]] for e in filas_zv],
            colorear={5},
        )
        hz_.ws.freeze_panes = "C4"
    else:
        hz_.nota("No hay especies para la zona de vida seleccionada.")

    # ── 10. Fuentes ──────────────────────────────────────────────────────────
    hf = Hoja(wb, "Fuentes", "Metodología y fuentes", sub, [120])
    for f in datos["fuentes"]:
        hf.nota(f, color=TEXTO, italica=False)

    # ── Resumen (se llena al final para poder enlazar a las otras hojas) ─────
    h = resumen
    h.tabla(
        "Tabla 3. Información del titular y del proyecto",
        ["Campo", "Valor"],
        [["Titular de la solicitud", "Unergy Energía Digital S.A.S. E.S.P."],
         ["Autoridad ambiental competente", p.get("car") or "n/d"],
         ["Municipio", municipio],
         ["Departamento", p.get("departamento", "n/d")],
         ["Bioma (IAvH)", p.get("bioma", "n/d")],
         ["Zona hidrográfica", p.get("zh", "n/d")],
         ["Subzona hidrográfica", p.get("szh", "n/d")],
         ["Tipo de cobertura a aprovechar", ", ".join(c["cobertura"] for c in cobs)],
         ["Área de impacto (ha)", p.get("area_impacto_ha", 0)]],
        formatos={1: FMT_HA}, ajustar={1},
    )
    h.tabla(
        "Resultados principales",
        ["Indicador", "Valor"],
        [["Área total a compensar AC (ha)", f"='Coberturas y FCAFU'!G{u10 + 1}"],
         ["ATC mínimo (ha)", f"=MIN({rango_atc})"],
         ["ATC máximo (ha)", f"=MAX({rango_atc})"],
         ["Especies con categoría de amenaza", len({a['nombre'] for a in datos['amenazadas']})],
         ["Registros de especies en veda", len(datos["vedas"])]],
        formatos={1: FMT_HA},
    )
    for fila in (h.fila - 3, h.fila - 2):          # las dos últimas son conteos
        h.ws.cell(row=fila, column=2).number_format = FMT_ENTERO
    h.subtitulo("Contenido del libro")
    for ws in wb.worksheets[1:]:
        c = h.ws.cell(row=h.fila, column=1, value=ws.title)
        c.hyperlink = f"#'{ws.title}'!A1"
        c.font = _font(color=MORADO, underline="single")
        h.fila += 1
    h.ws.freeze_panes = "A4"

    for ws in wb.worksheets:
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.tabColor = MORADO

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── utilidades internas ──────────────────────────────────────────────────────
def _fila_tasa_municipio(ws):
    for row in ws.iter_rows(min_col=1, max_col=1):
        if row[0].value == "Municipio":
            return row[0].row
    return 1


def _colores_series(ch):
    for s, color in zip(ch.series, (MORADO_OSCURO, "9B6FE8")):
        s.graphicalProperties.line.solidFill = color
        s.graphicalProperties.line.width = 28000
        s.smooth = False
