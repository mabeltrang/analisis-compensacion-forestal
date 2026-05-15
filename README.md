# App de Planes de Compensación Biótica (Adicionalidad)

Aplicación web para automatizar la generación de Planes de Compensación del Componente Biótico para proyectos, según la **Resolución 0305/2026 del MADS (Manual 2026) - Versión 2 (vigente al 2026-05)**.

## Requisitos
- Python 3.9+
- Cuenta de Google Earth Engine con acceso al proyecto `ndvi-restauracion`

## Instalación
```bash
pip install -r requirements.txt
```

## Uso Local
```bash
streamlit run app.py
```

## Estructura
- `app.py`: UI en Streamlit.
- `core.py`: Lógica principal del backend, cálculos FCAFU e integración con GEE.
- `manual_2026/`: Configuración JSON de las tablas de la Resolución 0305/2026.
