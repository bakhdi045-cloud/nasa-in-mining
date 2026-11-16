# Tables de l'étude de surface — exécution TEST3

Générées par `scripts/report_surface_tables.py` à partir de `study.json` ; aucun nombre n'est saisi à la main.

## Dates et lots

| Lot | Collection / CRID | Acquisitions | Utilisables | Fenêtres | Calculées | Lacunes |
|---|---|---:|---:|---:|---:|---|
| asc_T044_F018_P05023 | NISAR_L2_GCOV_PROVISIONAL_V1 / P05023 | 10 | 10 | 9 | 9 | 2026-07-23 → 2026-08-16 (24 j) |
| desc_T023_F072_P05023 | NISAR_L2_GCOV_PROVISIONAL_V1 / P05023 | 6 | 5 | 5 | 4 | 2026-07-21 → 2026-08-14 (24 j) |
| desc_T023_F072_P05036 | NISAR_L2_GCOV_V1 / P05036 | 0 | 0 | 0 | 0 | — |

## Fenêtres (HH, observable principal)

| Fenêtre | Orbite | Durée | Δ périmètre (dB) | Δ périmètre − témoin (dB) | Couples de référence | σ témoin (dB) | Fraction signalée périmètre | témoin | Rapport (IC 95 %) | Dév. |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| 2026-06-17 → 2026-06-29 | ascending | 12 | -0.11 | -0.03 | 6 | 1.13 | 0.0210 | 0.0098 | 2.14 [1.56 ; 2.93] | oui |
| 2026-06-29 → 2026-07-11 | ascending | 12 | -0.03 | -0.04 | 5 | 1.14 | 0.0144 | 0.0089 | 1.62 [1.02 ; 2.39] |  |
| 2026-07-11 → 2026-07-23 | ascending | 12 | 0.04 | -0.01 | 6 | 1.07 | 0.0183 | 0.0115 | 1.60 [0.84 ; 2.65] |  |
| 2026-07-23 → 2026-08-16 | ascending | 24 | 0.29 | -0.01 | insufficient_baseline | — | — | — | —  |  |
| 2026-08-16 → 2026-08-28 | ascending | 12 | 0.02 | 0.02 | 6 | 1.05 | 0.0147 | 0.0114 | 1.29 [0.70 ; 2.10] | oui |
| 2026-08-28 → 2026-09-09 | ascending | 12 | -0.14 | -0.21 | 5 | 1.11 | 0.0142 | 0.0109 | 1.31 [0.84 ; 1.89] |  |
| 2026-09-09 → 2026-09-21 | ascending | 12 | -0.08 | -0.07 | 5 | 1.14 | 0.0124 | 0.0103 | 1.20 [0.74 ; 1.84] |  |
| 2026-09-21 → 2026-10-03 | ascending | 12 | 0.22 | 0.24 | 5 | 1.09 | 0.0164 | 0.0102 | 1.61 [1.00 ; 2.43] |  |
| 2026-10-03 → 2026-10-15 | ascending | 12 | 0.18 | 0.01 | 6 | 1.19 | 0.0130 | 0.0080 | 1.62 [0.95 ; 2.53] |  |
| 2026-06-27 → 2026-07-09 | descending | 12 | 0.04 | -0.04 | insufficient_baseline | — | — | — | —  |  |
| 2026-07-09 → 2026-07-21 | descending | 12 | 0.01 | 0.02 | insufficient_baseline | — | — | — | —  |  |
| 2026-07-21 → 2026-08-14 | descending | 24 | 0.23 | 0.00 | insufficient_baseline | — | — | — | —  |  |
| 2026-08-14 → 2026-08-26 | descending | 12 | -0.09 | -0.09 | insufficient_baseline | — | — | — | —  |  |
| 2026-08-26 → 2026-09-07 (rejetée) | descending | 12 | — | — | not_applicable | — | — | — | —  |  |

## Δγ⁰ HH agrégé par zone et par fenêtre (dB, puissance linéaire avant conversion)

| Fenêtre | Orbite | Durée | study | control_1_2km | control_2_4km | panels_outside | Z1 | N1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-06-17 → 2026-06-29 | ascending | 12 | -0.11 | -0.09 | -0.08 | -0.11 | 0.96 | -4.85 |
| 2026-06-29 → 2026-07-11 | ascending | 12 | -0.03 | 0.00 | 0.02 | -0.02 | 0.94 | 4.00 |
| 2026-07-11 → 2026-07-23 | ascending | 12 | 0.04 | 0.06 | 0.04 | -0.03 | -1.65 | 1.31 |
| 2026-07-23 → 2026-08-16 | ascending | 24 | 0.29 | 0.31 | 0.30 | 0.40 | 3.82 | 2.08 |
| 2026-08-16 → 2026-08-28 | ascending | 12 | 0.02 | -0.02 | 0.01 | -0.03 | -2.01 | -6.93 |
| 2026-08-28 → 2026-09-09 | ascending | 12 | -0.14 | 0.08 | 0.08 | -0.11 | 0.19 | -1.79 |
| 2026-09-09 → 2026-09-21 | ascending | 12 | -0.08 | 0.02 | -0.03 | -0.01 | -0.44 | 1.25 |
| 2026-09-21 → 2026-10-03 | ascending | 12 | 0.22 | -0.05 | -0.01 | 0.10 | -2.82 | 4.69 |
| 2026-10-03 → 2026-10-15 | ascending | 12 | 0.18 | 0.17 | 0.17 | 0.20 | -0.51 | -0.80 |
| 2026-06-27 → 2026-07-09 | descending | 12 | 0.04 | 0.05 | 0.08 | 0.04 | 1.41 | 4.64 |
| 2026-07-09 → 2026-07-21 | descending | 12 | 0.01 | 0.01 | -0.01 | 0.03 | -2.78 | 2.38 |
| 2026-07-21 → 2026-08-14 | descending | 24 | 0.23 | 0.25 | 0.22 | 0.18 | 3.93 | 0.61 |
| 2026-08-14 → 2026-08-26 | descending | 12 | -0.09 | 0.00 | -0.00 | -0.09 | -1.68 | -5.32 |
| 2026-08-26 → 2026-09-07 | descending | 12 | — | — | — | — | — | — |

## Appui optique par couple Sentinel-2 distinct

| Mode | Comparaisons radar | Couples optiques distincts | Couples avec IC > 1 |
|---|---:|---:|---:|
| strict | 2 | 2 | 2 |
| exploratory | 5 | 5 | 5 |

| Groupe | Avant | Après | Fenêtres radar |
|---|---|---|---|
| O1_strict | S2C_29SPR_20260614_0_L2A | S2B_29SPR_20260629_0_L2A | GCOV_044A_F018_20260617_20260629_P05023 |
| O2_strict | S2C_29SPR_20260813_0_L2A | S2B_29SPR_20260828_0_L2A | GCOV_044A_F018_20260816_20260828_P05023 |
| O1_exploratory | S2C_29SPR_20260614_0_L2A | S2B_29SPR_20260629_0_L2A | GCOV_044A_F018_20260617_20260629_P05023 |
| O2_exploratory | S2A_29SPR_20260626_1_L2A | S2C_29SPR_20260714_0_L2A | GCOV_044A_F018_20260629_20260711_P05023 |
| O3_exploratory | S2C_29SPR_20260704_0_L2A | S2B_29SPR_20260729_0_L2A | GCOV_044A_F018_20260711_20260723_P05023 |
| O4_exploratory | S2C_29SPR_20260813_0_L2A | S2B_29SPR_20260828_0_L2A | GCOV_044A_F018_20260816_20260828_P05023 |
| O5_exploratory | S2A_29SPR_20260825_1_L2A | S2C_29SPR_20260912_0_L2A | GCOV_044A_F018_20260828_20260909_P05023 |

## Conclusion par zone

| Zone | Surface (km²) | Radar | Fenêtres au-dessus du témoin | Fraction signalée médiane | Δ médian vs témoin (dB) | Optique | Couples optiques jugés / élevés | Sélection |
|---|---:|---|---:|---:|---:|---|---:|---|
| study | 39.544 | measured | 1/8 | 0.0146 | -0.03 | one_optical_pair | 1/2 | perimeter_definition |
| control_1_2km | 41.303 | measured | 0/8 | 0.0086 | 0.00 | not_elevated | 0/2 | perimeter_definition |
| control_2_4km | 105.156 | measured | 0/8 | 0.0110 | -0.00 | not_elevated | 0/2 | perimeter_definition |
| panels_outside | 2.389 | measured | 1/8 | 0.0144 | -0.03 | one_optical_pair | 1/2 | perimeter_definition |
| Z1 | 0.306 | measured | 8/8 | 0.2020 | -0.68 | corroborated_two_or_more_optical_pairs | 2/2 | v2_coherence_recurrence |
| N1 | 0.036 | measured | 8/8 | 0.7151 | 1.26 | corroborated_two_or_more_optical_pairs | 2/2 | recurrence_of_the_same_flags |

## Références indépendantes

État : **awaiting_annotations** ; annotations comptées : 0 ; unités tirées : {'flagged_study': 40, 'unflagged_study': 40, 'flagged_control': 24, 'unflagged_control': 40, 'not_observable': 25} ; manque : annotations_filled_by_an_independent_person, annotation_meta.

