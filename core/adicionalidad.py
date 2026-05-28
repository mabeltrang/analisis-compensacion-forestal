# ════════════════════════════════════════════════════════════════
    # ADICIONALIDAD POR HORIZONTE
    # Reemplaza el bloque anterior desde "st.header("🌱 Adicionalidad")"
    # hasta el st.info() de bibliografía
    # ════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("🌱 Adicionalidad Esperada")

    from core.atc import (
        adicionalidad_conservar,
        adicionalidad_conservar_anual,
        adicionalidad_restaurar,
        adicionalidad_restaurar_anual,
        tabla_adicionalidad,
    )

    # ─── Tasas BAU por unidad hidrográfica ────────────────────────
    # Cada nivel jerárquico (R1-R6) usa la tasa de su unidad espacial:
    #   R1/R4 → municipio · R2/R5 → SZH · R3/R6 → ZH
    TASA_BAU_MUN = tasa_bau                           # viene de ctx
    TASA_BAU_SZH = ctx.get('tasa_bau_szh', tasa_bau) # SZH — fallback a municipio
    TASA_BAU_ZH  = ctx.get('tasa_bau_zh',  tasa_bau) # ZH  — fallback a municipio

    K_RESTAURAR = 0.076   # Chapman-Richards bs-T, Poorter 2016
    F_CONSERVAR = 0.85    # Andam 2008 / Pfaff 2014
    F_RESTAURAR = 0.75    # Crouzeilles 2017 / González-M 2018
    HORIZONTES  = [3, 5, 10, 15]

    # Mapa nivel jerárquico → tasa BAU aplicable para CONSERVAR
    TASA_POR_NIVEL = {
        "Rango 1": TASA_BAU_MUN,   # mismo BIOMA-IAvH ∩ Municipio
        "Rango 2": TASA_BAU_SZH,   # mismo BIOMA-IAvH ∩ SZH
        "Rango 3": TASA_BAU_ZH,    # mismo BIOMA-IAvH ∩ ZH
        "Rango 4": TASA_BAU_MUN,   # otro  BIOMA-IAvH ∩ Municipio
        "Rango 5": TASA_BAU_SZH,   # otro  BIOMA-IAvH ∩ SZH
        "Rango 6": TASA_BAU_ZH,    # otro  BIOMA-IAvH ∩ ZH / país
    }

    st.markdown(
        f"**Tasas BAU (Hansen GFC):** "
        f"Municipio `{TASA_BAU_MUN*100:.3f}%` · "
        f"SZH `{TASA_BAU_SZH*100:.3f}%` · "
        f"ZH `{TASA_BAU_ZH*100:.3f}%` anual"
    )

    # ─── NOTA METODOLÓGICA ─────────────────────────────────────────
    with st.expander("📖 Metodología y fuentes de las fórmulas"):
        st.markdown("""
**CONSERVAR — fórmula acumulada exponencial**

```
ha_adicional(n) = ha × [1 - (1 - tasa_BAU)ⁿ] × 0.85
```

- `[1 - (1 - tasa_BAU)ⁿ]` — probabilidad acumulada de deforestación en *n* años.
  Modelo de eventos independientes anuales. La tasa BAU se calcula con
  **Hansen et al. (2013)** sobre la unidad espacial del nivel jerárquico:
  municipio (R1/R4), SZH (R2/R5) o ZH (R3/R6).
  DOI: [10.1126/science.1244693](https://doi.org/10.1126/science.1244693)

- `0.85` — fracción de la deforestación evitada que es realmente adicional.
  El 15% restante no se hubiera deforestado de todas formas (sesgo de selección).
  **Andam et al. (2008)** DOI: [10.1073/pnas.0800437105](https://doi.org/10.1073/pnas.0800437105) |
  **Pfaff et al. (2014)** DOI: [10.1016/j.worlddev.2013.01.011](https://doi.org/10.1016/j.worlddev.2013.01.011)

> *Nota: esta fórmula combina el modelo estocástico de Hansen con el factor de
efectividad de Andam/Pfaff. Es una construcción metodológica defendible, no
una ecuación de una sola fuente.*

---

**RESTAURAR — curva de Chapman-Richards (Poorter 2016)**

```
ha_adicional(n) = ha × [1 - e^(-0.076 × n)] × 0.75
```

- `[1 - e^(-k×n)]` — modelo de recuperación de biomasa en bosques tropicales
  secundarios. Curva asintótica: crece rápido al inicio y se estabiliza.
  k = 0.076 para bosques secos tropicales neotropicales.
  **Poorter et al. (2016)** Nature 530: 211-214.
  DOI: [10.1038/nature16469](https://doi.org/10.1038/nature16469)

- `0.75` — fracción de restauraciones activas que logran establecimiento exitoso.
  Para Bosque Seco Tropical colombiano.
  **Crouzeilles et al. (2017)** DOI: [10.1126/sciadv.1701345](https://doi.org/10.1126/sciadv.1701345) |
  **González-M. et al. (2018)** IAvH BST Colombia.
""")

    if atc_resultados:

        # ─── CONSERVAR ─────────────────────────────────────────────
        st.subheader("🌳 Escenario CONSERVAR (cerramiento)")
        st.caption(
            "Hectáreas que NO se pierden. "
            "Fórmula: `ha × [1 - (1 - tasa_BAU)ⁿ] × 0.85` — "
            "tasa BAU según unidad espacial del nivel jerárquico."
        )

        filas_c = []
        for rango_id, data in atc_resultados.items():
            atc_total  = data['atc_total']
            tasa_rango = TASA_POR_NIVEL.get(rango_id, TASA_BAU_MUN)
            fila = {
                "Rango":        rango_id,
                "ATC (ha)":     round(atc_total, 2),
                "Tasa BAU":     f"{tasa_rango*100:.3f}%",
                "Adic/año (ha)": round(
                    adicionalidad_conservar_anual(atc_total, tasa_rango, F_CONSERVAR), 4
                ),
            }
            for n in HORIZONTES:
                fila[f"A {n} años (ha)"] = round(
                    adicionalidad_conservar(atc_total, n, tasa_rango, F_CONSERVAR), 4
                )
            filas_c.append(fila)
        st.dataframe(pd.DataFrame(filas_c), use_container_width=True, hide_index=True)

        # ─── RESTAURAR ─────────────────────────────────────────────
        st.subheader("🌱 Escenario RESTAURAR (siembra activa)")
        st.caption(
            "Hectáreas que SE ganan. "
            "Fórmula: `ha × [1 - e^(-0.076×n)] × 0.75` — curva Chapman-Richards"
        )

        filas_r = []
        for rango_id, data in atc_resultados.items():
            atc_total = data['atc_total']
            fila = {
                "Rango":    rango_id,
                "ATC (ha)": round(atc_total, 2),
            }
            for n in HORIZONTES:
                fila[f"A {n} años (ha)"] = round(
                    adicionalidad_restaurar(atc_total, n, K_RESTAURAR, F_RESTAURAR), 4
                )
            filas_r.append(fila)
        st.dataframe(pd.DataFrame(filas_r), use_container_width=True, hide_index=True)

        st.caption(
            "💡 La ganancia de Restaurar no es lineal: crece rápido los primeros "
            "años y se estabiliza conforme el ecosistema madura (curva logística)."
        )

        # ─── COMPARACIÓN ───────────────────────────────────────────
        st.subheader("⚖️ Comparación Conservar vs Restaurar")
        st.caption(
            "Por ha compensada — referencia: tasa BAU del municipio "
            f"(`{TASA_BAU_MUN*100:.3f}%`)"
        )

        import pandas as pd
        filas_comp = []
        for n in HORIZONTES:
            # Comparación ilustrativa: usa municipio como referencia fija
            cons_por_ha = adicionalidad_conservar(1.0, n, TASA_BAU_MUN, F_CONSERVAR)
            rest_por_ha = adicionalidad_restaurar(1.0, n, K_RESTAURAR, F_RESTAURAR)
            filas_comp.append({
                "Horizonte":                     f"{n} años",
                "Conservar (ha adic/ha comp)":   round(cons_por_ha, 4),
                "Restaurar (ha adic/ha comp)":   round(rest_por_ha, 4),
                "Ratio Rest/Cons":               round(rest_por_ha / cons_por_ha, 1)
                                                 if cons_por_ha > 0 else "—"
            })
        st.dataframe(
            pd.DataFrame(filas_comp),
            use_container_width=True, hide_index=True
        )
        st.caption(
            "**Ratio Rest/Cons:** cuántas veces más adicionalidad genera Restaurar "
            "vs Conservar por cada hectárea compensada. Restaurar siempre gana en "
            "adicionalidad numérica, pero Conservar protege bosque que ya existe."
        )

        # ─── MIX 50/50 ─────────────────────────────────────────────
        st.subheader("⚖️ Escenario MIX 50/50")
        st.caption("50% Conservar + 50% Restaurar del ATC total — tasa BAU por nivel")

        filas_m = []
        for rango_id, data in atc_resultados.items():
            atc_total  = data['atc_total']
            mitad      = atc_total * 0.5
            tasa_rango = TASA_POR_NIVEL.get(rango_id, TASA_BAU_MUN)
            fila = {"Rango": rango_id, "ATC (ha)": round(atc_total, 2)}
            for n in HORIZONTES:
                cons = adicionalidad_conservar(mitad, n, tasa_rango, F_CONSERVAR)
                rest = adicionalidad_restaurar(mitad, n, K_RESTAURAR, F_RESTAURAR)
                fila[f"Mix {n} años (ha)"] = round(cons + rest, 4)
            filas_m.append(fila)
        st.dataframe(pd.DataFrame(filas_m), use_container_width=True, hide_index=True)

        st.info(
            "**¿Qué horizonte usar?**\n\n"
            "- Compra/Usufructo del predio (≥30 años) → columna de 15 años\n"
            "- Acuerdo de conservación a 15 años → columna de 15 años\n"
            "- Acuerdo a 3-5 años → columna correspondiente\n\n"
            "**Restaurar** genera más adicionalidad numérica, pero **Conservar** "
            "protege bosque existente con menor riesgo de falla. La mezcla óptima "
            "depende del presupuesto y del mecanismo jurídico."
        )

    # ─── BIBLIOGRAFÍA ──────────────────────────────────────────────
    st.markdown("---")
    st.header("📚 Fuentes y Factores de Efectividad")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🌳 CONSERVAR — Factor efectividad: 0.85**")
        st.markdown(
            "- Andam et al. (2008) PNAS — "
            "[10.1073/pnas.0800437105](https://doi.org/10.1073/pnas.0800437105)"
        )
        st.markdown(
            "- Pfaff et al. (2014) World Dev — "
            "[10.1016/j.worlddev.2013.01.011](https://doi.org/10.1016/j.worlddev.2013.01.011)"
        )
    with c2:
        st.markdown("**🌱 RESTAURAR — Factor efectividad: 0.75 | k = 0.076**")
        st.markdown(
            "- Poorter et al. (2016) Nature — "
            "[10.1038/nature16469](https://doi.org/10.1038/nature16469)"
        )
        st.markdown(
            "- Crouzeilles et al. (2017) Sci Adv — "
            "[10.1126/sciadv.1701345](https://doi.org/10.1126/sciadv.1701345)"
        )
        st.markdown(
            "- González-M. et al. (2018) IAvH BST — "
            "[Ver](http://repository.humboldt.org.co/handle/20.500.11761/35442)"
        )
    st.caption(
        "**Tasa BAU**: Hansen et al. (2013). High-Resolution Global Maps of "
        "21st-Century Forest Cover Change. Science 342: 850-853. "
        "[10.1126/science.1244693](https://doi.org/10.1126/science.1244693) — "
        "calculada sobre municipio (R1/R4), SZH (R2/R5) y ZH (R3/R6)."
    )
