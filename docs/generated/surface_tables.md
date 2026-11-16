# Tables de l'étude de surface — exécution 20261116T131850Z

Générées par `scripts/report_surface_tables.py` à partir de `study.json` ; aucun nombre n'est saisi à la main.

## Dates et lots

| Lot | Collection / CRID | Acquisitions | Utilisables | Fenêtres | Calculées | Lacunes |
|---|---|---:|---:|---:|---:|---|
| asc_T044_F018_P05023 | NISAR_L2_GCOV_PROVISIONAL_V1 / P05023 | 10 | 10 | 9 | 9 | 2026-07-23 → 2026-08-16 (24 j) |
| desc_T023_F072_P05023 | NISAR_L2_GCOV_PROVISIONAL_V1 / P05023 | 9 | 8 | 8 | 6 | 2026-07-21 → 2026-08-14 (24 j) |
| desc_T023_F072_P05036 | NISAR_L2_GCOV_V1 / P05036 | 2 | 2 | 1 | 1 | — |

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
| 2026-06-27 → 2026-07-09 | descending | 12 | 0.04 | -0.04 | 3 | 1.37 | 0.0301 | 0.0118 | 2.55 [2.02 ; 3.25] |  |
| 2026-07-09 → 2026-07-21 | descending | 12 | 0.01 | 0.02 | 3 | 1.32 | 0.0394 | 0.0119 | 3.31 [2.60 ; 4.25] |  |
| 2026-07-21 → 2026-08-14 | descending | 24 | 0.23 | 0.00 | insufficient_baseline | — | — | — | —  |  |
| 2026-08-14 → 2026-08-26 | descending | 12 | -0.09 | -0.09 | 4 | 1.24 | 0.0330 | 0.0126 | 2.62 [1.99 ; 3.48] |  |
| 2026-08-26 → 2026-09-07 (rejetée) | descending | 12 | — | — | not_applicable | — | — | — | —  |  |
| 2026-09-07 → 2026-09-19 (rejetée) | descending | 12 | — | — | not_applicable | — | — | — | —  |  |
| 2026-09-19 → 2026-10-01 | descending | 12 | 0.16 | 0.09 | 3 | 1.16 | 0.0147 | 0.0133 | 1.10 [0.69 ; 1.68] |  |
| 2026-10-01 → 2026-10-13 | descending | 12 | 0.25 | -0.13 | 3 | 1.57 | 0.0313 | 0.0112 | 2.79 [2.15 ; 3.68] |  |
| 2026-10-25 → 2026-11-06 | descending | 12 | 0.70 | 0.14 | insufficient_baseline | — | — | — | —  |  |

## Δγ⁰ HH agrégé par zone et par fenêtre (dB, puissance linéaire avant conversion)

| Fenêtre | Orbite | Durée | study | control_1_2km | control_2_4km | panels_outside | Z1 | N1 | N2 | N3 | N4 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-06-17 → 2026-06-29 | ascending | 12 | -0.11 | -0.09 | -0.08 | -0.11 | 0.96 | -2.52 | -4.34 | 0.51 | -2.09 |
| 2026-06-29 → 2026-07-11 | ascending | 12 | -0.03 | 0.00 | 0.02 | -0.02 | 0.94 | 3.65 | -1.49 | 2.22 | 5.68 |
| 2026-07-11 → 2026-07-23 | ascending | 12 | 0.04 | 0.06 | 0.04 | -0.03 | -1.65 | -0.54 | -0.60 | 0.40 | -0.66 |
| 2026-07-23 → 2026-08-16 | ascending | 24 | 0.29 | 0.31 | 0.30 | 0.40 | 3.82 | 2.05 | 9.08 | -0.53 | -2.89 |
| 2026-08-16 → 2026-08-28 | ascending | 12 | 0.02 | -0.02 | 0.01 | -0.03 | -2.01 | -5.64 | -2.26 | -0.73 | -0.10 |
| 2026-08-28 → 2026-09-09 | ascending | 12 | -0.14 | 0.08 | 0.08 | -0.11 | 0.19 | -1.36 | -5.34 | -0.22 | -0.37 |
| 2026-09-09 → 2026-09-21 | ascending | 12 | -0.08 | 0.02 | -0.03 | -0.01 | -0.44 | 0.82 | -0.19 | -1.55 | 8.26 |
| 2026-09-21 → 2026-10-03 | ascending | 12 | 0.22 | -0.05 | -0.01 | 0.10 | -2.82 | 3.84 | 1.94 | 0.55 | -6.29 |
| 2026-10-03 → 2026-10-15 | ascending | 12 | 0.18 | 0.17 | 0.17 | 0.20 | -0.51 | -1.15 | 4.74 | 11.22 | -0.11 |
| 2026-06-27 → 2026-07-09 | descending | 12 | 0.04 | 0.05 | 0.08 | 0.04 | 1.41 | 3.24 | -1.83 | -0.31 | 0.14 |
| 2026-07-09 → 2026-07-21 | descending | 12 | 0.01 | 0.01 | -0.01 | 0.03 | -2.78 | 1.38 | -0.27 | 1.73 | -5.79 |
| 2026-07-21 → 2026-08-14 | descending | 24 | 0.23 | 0.25 | 0.22 | 0.18 | 3.93 | 0.78 | 2.89 | -0.56 | -0.70 |
| 2026-08-14 → 2026-08-26 | descending | 12 | -0.09 | 0.00 | -0.00 | -0.09 | -1.68 | -5.04 | 0.93 | -4.39 | -0.16 |
| 2026-08-26 → 2026-09-07 | descending | 12 | — | — | — | — | — | — | — | — | — |
| 2026-09-07 → 2026-09-19 | descending | 12 | — | — | — | — | — | — | — | — | — |
| 2026-09-19 → 2026-10-01 | descending | 12 | 0.16 | 0.05 | 0.08 | -0.00 | -3.36 | 4.08 | 1.35 | 0.45 | -0.07 |
| 2026-10-01 → 2026-10-13 | descending | 12 | 0.25 | 0.41 | 0.37 | 0.02 | 0.59 | -1.11 | 2.55 | 1.27 | -0.83 |
| 2026-10-25 → 2026-11-06 | descending | 12 | 0.70 | 0.54 | 0.57 | 0.72 | 1.10 | -0.11 | 1.18 | -3.32 | -1.27 |

## Z1 : signe de Δγ⁰ HH sur des fenêtres des deux orbites qui se recouvrent (≥ 6 jours) — même signe : 4/5

| Ascendante | Descendante | Z1 asc. (dB) | Z1 desc. (dB) | Même signe |
|---|---|---:|---:|---|
| 2026-06-29 → 2026-07-11 | 2026-06-27 → 2026-07-09 | 0.94 | 1.41 | oui |
| 2026-07-11 → 2026-07-23 | 2026-07-09 → 2026-07-21 | -1.65 | -2.78 | oui |
| 2026-08-16 → 2026-08-28 | 2026-08-14 → 2026-08-26 | -2.01 | -1.68 | oui |
| 2026-09-21 → 2026-10-03 | 2026-09-19 → 2026-10-01 | -2.82 | -3.36 | oui |
| 2026-10-03 → 2026-10-15 | 2026-10-01 → 2026-10-13 | -0.51 | 0.59 | non |

## Appui optique par couple Sentinel-2 distinct

| Mode | Comparaisons radar | Couples optiques distincts | Couples avec IC > 1 |
|---|---:|---:|---:|
| strict | 3 | 2 | 2 |
| exploratory | 8 | 5 | 5 |

| Groupe | Avant | Après | Fenêtres radar |
|---|---|---|---|
| O1_strict | S2C_29SPR_20260614_0_L2A | S2B_29SPR_20260629_0_L2A | GCOV_044A_F018_20260617_20260629_P05023 |
| O2_strict | S2C_29SPR_20260813_0_L2A | S2B_29SPR_20260828_0_L2A | GCOV_044A_F018_20260816_20260828_P05023, GCOV_023D_F072_20260814_20260826_P05023 |
| O1_exploratory | S2C_29SPR_20260614_0_L2A | S2B_29SPR_20260629_0_L2A | GCOV_044A_F018_20260617_20260629_P05023 |
| O2_exploratory | S2A_29SPR_20260626_1_L2A | S2C_29SPR_20260714_0_L2A | GCOV_044A_F018_20260629_20260711_P05023, GCOV_023D_F072_20260627_20260709_P05023 |
| O3_exploratory | S2C_29SPR_20260704_0_L2A | S2B_29SPR_20260729_0_L2A | GCOV_044A_F018_20260711_20260723_P05023, GCOV_023D_F072_20260709_20260721_P05023 |
| O4_exploratory | S2C_29SPR_20260813_0_L2A | S2B_29SPR_20260828_0_L2A | GCOV_044A_F018_20260816_20260828_P05023, GCOV_023D_F072_20260814_20260826_P05023 |
| O5_exploratory | S2A_29SPR_20260825_1_L2A | S2C_29SPR_20260912_0_L2A | GCOV_044A_F018_20260828_20260909_P05023 |

## Conclusion par zone

| Zone | Surface (km²) | Radar | Fenêtres au-dessus du témoin | Fraction signalée médiane | Δ médian vs témoin (dB) | Optique | Couples optiques jugés / élevés | Sélection |
|---|---:|---|---:|---:|---:|---|---:|---|
| study | 39.544 | measured | 5/13 | 0.0164 | -0.02 | one_optical_pair | 1/2 | perimeter_definition |
| control_1_2km | 41.303 | measured | 0/13 | 0.0093 | -0.00 | not_elevated | 0/2 | perimeter_definition |
| control_2_4km | 105.156 | measured | 0/13 | 0.0114 | 0.00 | not_elevated | 0/2 | perimeter_definition |
| panels_outside | 2.389 | measured | 3/13 | 0.0153 | -0.03 | one_optical_pair | 1/2 | perimeter_definition |
| Z1 | 0.306 | measured | 13/13 | 0.2372 | -0.55 | corroborated_two_or_more_optical_pairs | 2/2 | v2_coherence_recurrence |
| N1 | 0.061 | measured | 13/13 | 0.6264 | -0.63 | corroborated_two_or_more_optical_pairs | 2/2 | recurrence_of_the_same_flags |
| N2 | 0.023 | measured | 12/13 | 0.4561 | -0.22 | corroborated_two_or_more_optical_pairs | 2/2 | recurrence_of_the_same_flags |
| N3 | 0.020 | measured | 13/13 | 0.5400 | 0.37 | one_optical_pair | 1/2 | recurrence_of_the_same_flags |
| N4 | 0.014 | measured | 12/13 | 0.4571 | -0.36 | one_optical_pair | 1/2 | recurrence_of_the_same_flags |

## Références indépendantes

État : **awaiting_annotations** ; annotations comptées : 0 ; unités tirées : {'flagged_study': 40, 'unflagged_study': 40, 'flagged_control': 33, 'unflagged_control': 40, 'not_observable': 35} ; manque : annotations_filled_by_an_independent_person, annotation_meta.

