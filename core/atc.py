from config import settings

def calcular_atc_por_rangos(analisis_inventario, contexto):
    """
    Calcula el ATC para los 5 rangos del Manual.
    analisis_inventario: dict de coberturas con FCAFU calculado.
    contexto: dict con areas_cobertura por ecosistemas.
    """
    areas_impacto = contexto['areas_cobertura']
    resultados_atc = {}
    
    # Iterar por los 6 rangos (1 a 6)
    for rango_id in range(1, 7):
        factor_adicional = settings.FACTORES_RANGO.get(rango_id, 0.0)
        atc_total_rango = 0.0
        detalles_cobertura = []
        
        # Iterar por cada cobertura presente en el impacto
        for cob_nombre, area_ha in areas_impacto.items():
            # Buscar el FCAFU correspondiente en el inventario
            # Nota: Puede haber discrepancia de nombres entre GEE y el Excel. 
            # El sistema debe manejar esto (limpieza de strings).
            f_data = analisis_inventario.get(cob_nombre)
            
            if not f_data:
                # Si no hay inventario para esta cobertura (ej. cobertura transformada sin rboles), 
                # el Manual dice que para coberturas transformadas el factor es 1.0 a 1.
                # Pero si es una cobertura natural sin inventario, se podra asumir FCAFU base?
                # El usuario dijo: "Para coberturas transformadas el factor es 1.0 a 1".
                fcafu_base = 1.0
            else:
                fcafu_base = f_data['FCAFU']
                
            atc_parcial = area_ha * (fcafu_base + factor_adicional)
            atc_total_rango += atc_parcial
            
            detalles_cobertura.append({
                'cobertura': cob_nombre,
                'area_impacto': area_ha,
                'fcafu_base': fcafu_base,
                'factor_rango': factor_adicional,
                'atc_parcial': atc_parcial
            })
            
        resultados_atc[f"Rango {rango_id}"] = {
            'atc_total': atc_total_rango,
            'detalles': detalles_cobertura,
            'factor_adicional': factor_adicional
        }
        
    return resultados_atc
