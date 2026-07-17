# -*- coding: utf-8 -*-
"""
Script de una sola vez: cruza Municipios_por_CAR (excel de Miguel) contra
municipios_colombia.fgb (fuente ya usada por core/contexto.py) para asignar
el departamento correcto a cada fila y resolver colisiones de nombre
(ej. "Barbosa" existe en Santander Y en Antioquia).

Genera: config/municipios_car.csv  con columnas departamento,municipio,car
(nombres tal cual aparecen en municipios_colombia.fgb, para que el cruce
por (departamento, municipio) sea directo en tiempo de ejecución).
"""
import os
import unicodedata
import pandas as pd
import geopandas as gpd

EXCEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Municipios_por_CAR.xlsx')
FGB_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'municipios_colombia.fgb')
OUT_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'municipios_car.csv')

# Departamentos candidatos por cada hoja del excel (jurisdicción conocida
# de cada CAR). Cuando una hoja cubre más de un departamento, se prueban
# todos y se toma el que sí tenga esa combinación (municipio, departamento)
# en el listado oficial de municipios_colombia.fgb.
CANDIDATOS_DEPTO = {
    "CARSUCRE":      ["Sucre"],
    "CORPOMOJANA":   ["Sucre"],
    "CORPOBOYACÁ":   ["Boyacá"],
    "CORPOCHIVOR":   ["Boyacá"],
    "CAR":           ["Cundinamarca", "Boyacá"],   # + Bogotá D.C. (caso especial)
    "CORPOGUAVIO":   ["Cundinamarca"],
    "CAS":           ["Santander"],
    "CDMB":          ["Santander"],
    "CORANTIOQUIA":  ["Antioquia"],
    "CORNARE":       ["Antioquia"],
    "CORPORINOQUIA": ["Arauca", "Casanare", "Vichada", "Meta", "Boyacá"],
}

# Filas del excel que corresponden a municipios de Cundinamarca (Sumapaz/
# Oriente) duplicados por error de copia dentro de la hoja CORPORINOQUIA
# (ya están correctamente asignados a Cundinamarca en la hoja "CAR" del
# mismo excel). Se excluyen aquí para no asignarlos de nuevo, mal, a
# CORPORINOQUIA.
FILAS_DUPLICADAS_IGNORAR = {
    ("CORPORINOQUIA", "cundinamarca (duplicado hoja CAR)"): [
        "caqueza", "chipaque", "choachi", "fosca", "guayabetal",
        "gutierrez", "paratebueno", "quetame", "ubaque", "une",
    ],
}

# Alias manuales para nombres que no matchean directo contra
# municipios_colombia.fgb (variantes de escritura o sedes/corregimientos).
ALIAS = {
    "villa de leyva":        "villa de leiva",
    "carmen de chucuri":     "el carmen",
    "armenia mantequilla":   "armenia",
    "el hato":               "hato",
    "guican":                "guican de la sierra",
    "palmas":                "palmas del socorro",
    "el carmen de viboral":  "carmen de viboral",
    "el santuario":          "santuario",
    "san vicente ferrer":    "san vicente",
    "el penol":              "penol",
}


def _norm(s):
    s = str(s)
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    s = s.lower().strip()
    s = s.split(" - ")[0]          # quita sufijos tipo "Sabanalarga - CASANARE"
    s = s.split(" (")[0]          # quita "(sede principal)", "(área rural)"
    s = s.rstrip(".").strip()      # quita puntos finales ("Sincelejo.")
    return s


def main():
    muns = gpd.read_file(FGB_PATH)[["municipio", "departamento"]].copy()
    muns["mun_norm"] = muns["municipio"].apply(_norm)

    xls = pd.ExcelFile(EXCEL_PATH)
    filas_out = []
    sin_match = []

    for hoja in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=hoja)
        deptos_candidatos = CANDIDATOS_DEPTO.get(hoja, [])

        for _, row in df.iterrows():
            raw = str(row["Municipio"])

            # Caso especial: Bogotá D.C. (zona rural, jurisdicción CAR)
            if "bogot" in _norm(raw):
                filas_out.append({
                    "departamento": "Bogotá D.C.",
                    "municipio": "Bogotá D.C. (área rural)",
                    "car": hoja,
                })
                continue

            mun_norm = _norm(raw)
            if mun_norm in FILAS_DUPLICADAS_IGNORAR.get(
                ("CORPORINOQUIA", "cundinamarca (duplicado hoja CAR)"), []
            ) and hoja == "CORPORINOQUIA":
                continue  # duplicado de la hoja CAR, ya cubierto ahí

            mun_norm = ALIAS.get(mun_norm, mun_norm)
            candidatos = muns[
                (muns["mun_norm"] == mun_norm)
                & (muns["departamento"].isin(deptos_candidatos))
            ]

            if len(candidatos) == 1:
                filas_out.append({
                    "departamento": candidatos.iloc[0]["departamento"],
                    "municipio":    candidatos.iloc[0]["municipio"],
                    "car":          hoja,
                })
            elif len(candidatos) > 1:
                # Ambiguo incluso restringiendo por departamento candidato
                # (no debería pasar, pero se deja registro por seguridad)
                sin_match.append((hoja, raw, "ambiguo", candidatos["departamento"].tolist()))
            else:
                sin_match.append((hoja, raw, "sin_match_en_fgb", deptos_candidatos))

    out = pd.DataFrame(filas_out).drop_duplicates()
    out = out.sort_values(["departamento", "municipio"]).reset_index(drop=True)
    out.to_csv(OUT_PATH, index=False, encoding="utf-8")

    print(f"OK: {len(out)} filas escritas en {OUT_PATH}")
    if sin_match:
        print(f"\n⚠️  {len(sin_match)} filas SIN match automático (revisar a mano):")
        for hoja, raw, motivo, info in sin_match:
            print(f"  [{hoja}] '{raw}' -> {motivo} (candidatos dpto: {info})")


if __name__ == "__main__":
    main()
