# -*- coding: utf-8 -*-
"""
Cálculo del Área Total a Compensar (ATC) por rango — Manual 2026.

LÓGICA v6 (definitiva):
  - El área REAL viene de IDEAM (cruce KMZ × Shape_E_ECCMC).
  - El FCAFU se calcula del inventario.
  - HOMOLOGACIÓN: cada cobertura GEE se homologa con la cobertura más
    parecida del inventario, prefiriendo el match MÁS LITERAL (sin
    palabras extra que puedan confundir).
"""
from config import settings
import unicodedata
import math


def _normalizar(s):
    if not s:
        return ""
    s = str(s)
    s = "".join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    return s.lower().strip()


def _score_homologacion(nombre_inv, nombre_gee):
    """
    Score 0-100:
      100 = match exacto
      90  = gee contiene a inv (ej: inv='Pastos limpios', gee='Pastos limpios')
      80  = inv contiene a gee (ej: gee='Pastos', inv='Pastos limpios')
      60  = primera palabra coincide
      30  = comparten palabras significativas
       0  = sin relación
    """
    a = _normalizar(nombre_inv)
    b = _normalizar(nombre_gee)
    if not a or not b:
        return 0
    if a == b:
        return 100
    if a in b:
        return 90
    palabras_a = a.split()
    palabras_b = b.split()
    if palabras_a and palabras_b:
        if palabras_a[0] == palabras_b[0]:
            if b in a:
                return 80
            return 60
    palabras_a_sig = set(w for w in palabras_a[1:] if len(w) > 3)
    palabras_b_sig = set(w for w in palabras_b[1:] if len(w) > 3)
    interseccion = palabras_a_sig & palabras_b_sig
    if interseccion:
        return 30
    return 0


def calcular_atc_por_rangos(analisis_inventario, contexto):
    areas_gee = dict(contexto.get('areas_cobertura', {}) or {})
    coberturas_inv = list(analisis_inventario.keys())

    areas_por_cobertura_inv = {cob: 0.0 for cob in coberturas_inv}

    for cob_gee, area_gee in areas_gee.items():
        mejor_score = 0
        mejor_cob_inv = None
        for cob_inv in coberturas_inv:
            score = _score_homologacion(cob_inv, cob_gee)
            if score > mejor_score:
                mejor_score = score
                mejor_cob_inv = cob_inv

        if mejor_cob_inv and mejor_score >= 30:
            areas_por_cobertura_inv[mejor_cob_inv] += area_gee
        elif coberturas_inv:
            areas_por_cobertura_inv[coberturas_inv[0]] += area_gee

    resultados_atc = {}
    for rango_id in range(1, 7):
        factor_adicional = settings.FACTORES_RANGO.get(rango_id, 0.0)
        atc_total_rango = 0.0
        detalles_cobertura = []
        for cob_inv, area_ha in areas_por_cobertura_inv.items():
            f_data = analisis_inventario.get(cob_inv, {})
            fcafu_base = f_data.get('FCAFU', 1.0)
            atc_parcial = area_ha * (fcafu_base + factor_adicional)
            atc_total_rango += atc_parcial
            detalles_cobertura.append({
                'cobertura': cob_inv,
                'area_impacto_ha': round(area_ha, 4),
                'fcafu_base': round(fcafu_base, 3),
                'factor_rango': factor_adicional,
                'atc_parcial': round(atc_parcial, 4)
            })
        resultados_atc[f"Rango {rango_id}"] = {
            'atc_total': atc_total_rango,
            'detalles': detalles_cobertura,
            'factor_adicional': factor_adicional
        }
    return resultados_atc


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE ADICIONALIDAD — Manual 2026
# ══════════════════════════════════════════════════════════════════════════════
#
# Dos fórmulas independientes, una por acción. Ambas retornan hectáreas
# adicionales netas: lo que realmente cambia gracias a la intervención.


def adicionalidad_conservar(ha: float, n: int,
                             tasa_bau: float = 0.0062,
                             efectividad: float = 0.85) -> float:
    """
    Hectáreas adicionales evitadas por conservación en n años.

    Fórmula:
        ha_adicional(n) = ha × [1 - (1 - tasa_BAU)^n] × efectividad

    Componentes:
    - [1 - (1 - tasa_BAU)^n]: probabilidad acumulada de deforestación en n años.
      Modelo de eventos independientes anuales. La tasa BAU (Business As Usual)
      representa la fracción del bosque que se pierde anualmente en ausencia de
      intervención. Se calcula con Hansen GFC (lossyear 2001-2023) sobre el
      municipio del impacto.
      Fuente: Hansen et al. (2013). High-Resolution Global Maps of 21st-Century
      Forest Cover Change. Science 342: 850-853.
      DOI: 10.1126/science.1244693

    - efectividad (0.85): fracción de la deforestación evitada que es realmente
      adicional. El 15% restante no se hubiera deforestado de todas formas
      (sesgo de selección de sitio). Estimado para áreas protegidas tropicales.
      Fuente 1: Andam et al. (2008). Measuring the effectiveness of protected
      area networks in reducing deforestation. PNAS 105(42): 16089-16094.
      DOI: 10.1073/pnas.0800437105
      Fuente 2: Pfaff et al. (2014). Governance, location and avoided
      deforestation from protected areas. World Development 55: 7-20.
      DOI: 10.1016/j.worlddev.2013.01.011

    Nota metodológica: esta fórmula es una construcción que combina el modelo
    estocástico de deforestación (Hansen) con el factor de efectividad de áreas
    protegidas (Andam/Pfaff). No existe como ecuación única en una sola fuente.

    Args:
        ha: hectáreas a conservar
        n: horizonte en años
        tasa_bau: tasa anual de deforestación (fracción, default 0.0062 = 0.62%)
        efectividad: factor de efectividad del área protegida (default 0.85)

    Returns:
        hectáreas adicionales netas (ha evitadas de perderse)
    """
    prob_acumulada = 1 - (1 - tasa_bau) ** n
    return ha * prob_acumulada * efectividad


def adicionalidad_conservar_anual(ha: float,
                                   tasa_bau: float = 0.0062,
                                   efectividad: float = 0.85) -> float:
    """
    Hectáreas adicionales evitadas por conservación por año (tasa constante).

    Simplificación de adicionalidad_conservar para un solo año.
    La tasa es constante porque la probabilidad de deforestación anual
    no varía significativamente en el corto plazo.

    Returns:
        hectáreas adicionales por año
    """
    return ha * tasa_bau * efectividad


def adicionalidad_restaurar(ha: float, n: int,
                             k: float = 0.076,
                             efectividad: float = 0.75) -> float:
    """
    Hectáreas adicionales ganadas por restauración activa en n años.

    Fórmula:
        ha_adicional(n) = ha × [1 - e^(-k × n)] × efectividad

    Componentes:
    - [1 - e^(-k × n)]: modelo de Chapman-Richards para recuperación de biomasa
      en bosques tropicales secundarios. Representa la fracción del ecosistema
      de referencia que se recupera en n años. Es una curva asintótica (logística)
      que crece rápido al inicio y se estabiliza — más realista que una tasa lineal.
      k = 0.076 para bosques secos tropicales neotropicales.
      Fuente: Poorter et al. (2016). Biomass resilience of Neotropical secondary
      forests. Nature 530: 211-214.
      DOI: 10.1038/nature16469

    - efectividad (0.75): fracción de restauraciones activas que logran
      establecimiento exitoso de la vegetación (supervivencia de plántulas,
      establecimiento de coberturas). Para bosque seco tropical colombiano.
      Fuente 1: Crouzeilles et al. (2017). Ecological restoration success is
      higher for natural regeneration than for active restoration in tropical
      forests. Science Advances 3: e1701345.
      DOI: 10.1126/sciadv.1701345
      Fuente 2: González-M. et al. (2018). Patrones de diversidad y estructura
      del Bosque Seco Tropical en Colombia. IAvH, Bogotá.
      http://repository.humboldt.org.co/handle/20.500.11761/35442

    Args:
        ha: hectáreas a restaurar
        n: horizonte en años
        k: constante de recuperación de Chapman-Richards (default 0.076, bs-T)
        efectividad: factor de efectividad de restauración activa (default 0.75)

    Returns:
        hectáreas adicionales netas (ha de ecosistema recuperado)
    """
    recuperacion = 1 - math.exp(-k * n)
    return ha * recuperacion * efectividad


def adicionalidad_restaurar_anual(ha: float, n: int,
                                   k: float = 0.076,
                                   efectividad: float = 0.75) -> float:
    """
    Tasa instantánea de ganancia de adicionalidad por restauración en el año n.

    Derivada de la curva de Chapman-Richards:
        d/dn [ha × (1 - e^(-k×n)) × ef] = ha × k × e^(-k×n) × ef

    La tasa es alta al inicio (bosque joven crece rápido) y disminuye
    con el tiempo a medida que el ecosistema se estabiliza.

    Args:
        ha: hectáreas restauradas
        n: año específico (1, 2, 3...)
        k: constante de Chapman-Richards (default 0.076)
        efectividad: factor de efectividad (default 0.75)

    Returns:
        hectáreas adicionales ganadas en ese año específico
    """
    return ha * k * math.exp(-k * n) * efectividad


def tabla_adicionalidad(ha_conservar: float, ha_restaurar: float,
                         tasa_bau: float = 0.0062,
                         horizontes: list = None) -> list:
    """
    Genera tabla comparativa de adicionalidad para conservar y restaurar.

    Args:
        ha_conservar: hectáreas destinadas a conservación
        ha_restaurar: hectáreas destinadas a restauración
        tasa_bau: tasa BAU del municipio
        horizontes: lista de años a calcular (default [3, 5, 10, 15])

    Returns:
        Lista de dicts con columnas: años, conservar_ha, restaurar_ha, total_ha
    """
    if horizontes is None:
        horizontes = [3, 5, 10, 15]

    filas = []
    for n in horizontes:
        cons = adicionalidad_conservar(ha_conservar, n, tasa_bau)
        rest = adicionalidad_restaurar(ha_restaurar, n)
        filas.append({
            'Horizonte (años)': n,
            'Conservar (ha evitadas)': round(cons, 4),
            'Restaurar (ha ganadas)': round(rest, 4),
            'Total adicional (ha)': round(cons + rest, 4)
        })
    return filas
