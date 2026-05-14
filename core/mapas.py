# -*- coding: utf-8 -*-
import ee
import folium
import geopandas as gpd
from config import settings

def obtener_mapa_contexto(gdf_impacto, bioma_principal):
    """
    Mapa interactivo general (Folium).
    Muestra polígono de impacto y bioma.
    """
    try:
        # Calcular centroide para el mapa
        centroide = gdf_impacto.geometry.unary_union.centroid
        m = folium.Map(location=[centroide.y, centroide.x], zoom_start=11, control_scale=True)
        
        # Mapa base de satélite (Esri World Imagery)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satélite',
            overlay=False,
            control=True
        ).add_to(m)

        # Polígono Impacto
        impacto_geojson = gdf_impacto.__geo_interface__
        folium.GeoJson(
            impacto_geojson,
            name='Zona de Impacto',
            style_function=lambda x: {'fillColor': '#FFFF00', 'color': '#FFFF00', 'weight': 3, 'fillOpacity': 0.4}
        ).add_to(m)

        folium.LayerControl().add_to(m)
        return m

    except Exception as e:
        print(f"[mapas] Error mapa general interactivo: {e}")
        return None

def obtener_mapas_por_rango(gdf_impacto, cand_results):
    """
    Genera un diccionario con un folium.Map para cada rango.
    Estilos:
      - Borde azul: límite del rango
      - Amarillo: polígono del impacto
      - Verde oscuro: Conservar
      - Naranja: Restaurar
      - Rojo semitransparente: RUNAP
      - Blanco punteado: seleccionadas (simulado en Conservar/Restaurar)
    """
    mapas = {}
    
    try:
        centroide = gdf_impacto.geometry.unary_union.centroid
        impacto_geojson = gdf_impacto.__geo_interface__
    except Exception as e:
        print(f"[mapas] Error preparando impacto para folium: {e}")
        return {}

    for rango, datos in cand_results.items():
        try:
            m = folium.Map(location=[centroide.y, centroide.x], zoom_start=10, control_scale=True)
            
            # Satélite
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Satélite',
                overlay=False,
                control=True
            ).add_to(m)

            # 1. Límite del Rango (Borde Azul)
            geom_tot_dict = datos.get('geom_total')
            if geom_tot_dict:
                folium.GeoJson(
                    geom_tot_dict,
                    name=f'Límite {rango}',
                    style_function=lambda x: {'fillColor': '#0000FF', 'color': '#0000FF', 'weight': 2, 'fillOpacity': 0.05}
                ).add_to(m)

            # 2. RUNAP (Rojo Semitransparente)
            geom_runap = datos.get('geom_runap_ee')
            if geom_runap:
                folium.GeoJson(
                    geom_runap,
                    name='Exclusión RUNAP',
                    style_function=lambda x: {'fillColor': '#FF0000', 'color': '#FF0000', 'weight': 1, 'fillOpacity': 0.3}
                ).add_to(m)

            # 3. Zonas a Conservar (Verde oscuro) y "Seleccionadas" (Borde blanco punteado)
            # Para demostrar el "borde blanco punteado" simulamos que todas las candidatas son las seleccionadas 
            # para el plan, ya que actualmente no hay una selección parcial implementada.
            geom_cons = datos.get('geom_conservar_ee')
            if geom_cons:
                folium.GeoJson(
                    geom_cons,
                    name='Candidatas a Conservar',
                    style_function=lambda x: {'fillColor': '#006400', 'color': '#FFFFFF', 'weight': 2, 'dashArray': '5, 5', 'fillOpacity': 0.6}
                ).add_to(m)

            # 4. Zonas a Restaurar (Naranja) y "Seleccionadas" (Borde blanco punteado)
            geom_rest = datos.get('geom_restaurar_ee')
            if geom_rest:
                folium.GeoJson(
                    geom_rest,
                    name='Candidatas a Restaurar',
                    style_function=lambda x: {'fillColor': '#FF8C00', 'color': '#FFFFFF', 'weight': 2, 'dashArray': '5, 5', 'fillOpacity': 0.6}
                ).add_to(m)

            # 5. Polígono de Impacto (Amarillo)
            folium.GeoJson(
                impacto_geojson,
                name='Zona de Impacto',
                style_function=lambda x: {'fillColor': '#FFFF00', 'color': '#FFFF00', 'weight': 3, 'fillOpacity': 0.4}
            ).add_to(m)

            folium.LayerControl().add_to(m)
            mapas[rango] = m
            
        except Exception as e:
            print(f"[mapas] Error rango {rango} folium: {e}")
            mapas[rango] = None

    return mapas
