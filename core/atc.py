# -*- coding: utf-8 -*-
"""
Cálculo del Área Total a Compensar (ATC) por rango — Manual 2026.

Fórmula: ATC = Σ (area_cobertura × (FCAFU_cobertura + factor_rango))

CORRECCIÓN MAYOR (v2):
  - Antes: iteraba por coberturas de GEE y buscaba FCAFU del inventario
    por nombre exacto. Si los nombres no coincidían (GEE='Pastos' vs
    inventario='Pastos limpios'), aplicaba FCAFU=1 por default. BUG.
  - Ahora: iteraba por coberturas del INVENTARIO (donde está el FCAFU
    real calculado) y resuelve el área de cada una con matching flexible
    contra GEE. Si no hay match, reparte el área total proporcional al
    número de árboles de esa cobertura en el inventario.
"""
from config import settings
import unicodedata


def _normalizar(s):
    """Normaliza una cadena para comparación: sin tildes, minúsculas, sin espacios extra."""
    if not s:
        return ""
    s = str(s)
    s = "".join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    return s.lower().strip()


def _coincidencia(nombre_inv, nombre_gee):
    """
    Devuelve True si los nombres se refieren al mismo tipo de cobertura.
    Usa matching parcial: 'Pastos limpios' coincide con 'Pastos' y viceversa.
    """
    a = _normalizar(nombre_inv)
    b = _normalizar(nombre_gee)
    if not a or not b:
        return False
    # Coincidencia exacta
    if a == b:
        return True
    # Uno contiene al otro
    if a in b or b in a:
        return True
    # Palabras clave compartidas
    palabras_a = set(a.split())
    palabras_b = set(b.split())
    interseccion = palabras_a & palabras_b
    # Si comparten al menos 1 palabra significativa (>3 caracteres), match
    if any(len(w) > 3 for w in interseccion):
        return True
    return False


def calcular_atc_por_rangos(analisis_inventario, contexto):
    """
    Calcula el ATC para los 6 rangos del Manual 2026.

    Parámetros:
        analisis_inventario: dict {cobertura_inventario: {FCAFU, N, S, ...}}
        contexto: dict con 'areas_cobertura' = {cobertura_gee: ha}

    Retorna:
        dict {Rango N: {atc_total, detalles, factor_adicional}}
    """
    areas_gee = contexto.get('areas_cobertura', {}) or {}
    area_total_gee = sum(areas_gee.values()) if areas_gee else 0.0

    # ─────────────────────────────────────────────────────────────
    # PASO 1: asignar área a cada cobertura del INVENTARIO
    # ─────────────────────────────────────────────────────────────
    # Para cada cobertura del inventario, buscar a qué cobertura(s) de GEE
    # corresponde por matching de nombre. Si encuentra match, suma esas áreas.
    # Si no encuentra, reparte el área total GEE proporcional al N de árboles.

    coberturas_inv = list(analisis_inventario.keys())

    # Cuentas de árboles para reparto proporcional cuando no hay match
    n_total_arboles = sum(
        analisis_inventario[c].get('N', 0) for c in coberturas_inv
    )

    areas_por_cobertura_inv = {}
    gee_ya_usadas = set()

    for cob_inv in coberturas_inv:
        area_asignada = 0.0
        # Buscar coberturas de GEE que coincidan con esta del inventario
        for cob_gee, area_ha in areas_gee.items():
            if cob_gee in gee_ya_usadas:
                continue
            if _coincidencia(cob_inv, cob_gee):
                area_asignada += area_ha
                gee_ya_usadas.add(cob_gee)

        # Si NO se encontró match en GEE, repartir proporcional al N
        if area_asignada == 0.0 and area_total_gee > 0 and n_total_arboles > 0:
            n_cob = analisis_inventario[cob_inv].get('N', 0)
            area_asignada = area_total_gee * (n_cob / n_total_arboles)

        areas_por_cobertura_inv[cob_inv] = area_asignada

    # ─────────────────────────────────────────────────────────────
    # PASO 2: para cada rango, calcular ATC sumando por cobertura
    # ─────────────────────────────────────────────────────────────
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
