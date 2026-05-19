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
    # Si GEE da el nombre COMPLETO del inventario, es el ideal
    if a in b:
        return 90
    # Si el INVENTARIO es una especialización del GEE
    # (ej: gee="Pastos" -> inv="Pastos limpios") es bueno
    # PERO solo si la PRIMERA palabra coincide
    palabras_a = a.split()
    palabras_b = b.split()
    if palabras_a and palabras_b:
        # Primera palabra debe coincidir para considerar homologación
        if palabras_a[0] == palabras_b[0]:
            if b in a:
                # GEE simple, inventario más específico, primera palabra =
                # Ej: gee="Pastos", inv="Pastos limpios" → SÍ homologa
                return 80
            # Comparten primera palabra (pastos = pastos)
            return 60
    # Palabras significativas en común (sin la primera palabra)
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

    # Para cada cobertura del IDEAM, encontrar el mejor match del inventario
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
            # Fallback: si no hay match razonable, primera del inv
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
