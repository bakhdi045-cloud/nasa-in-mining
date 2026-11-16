# Prompt à transmettre à l'agent d'exécution

Tu travailles uniquement dans :
`C:\Users\Elite\Desktop\EMINES\nasa\codetw2\nasa-in-mining`.

L'utilisateur confirme **la mine OCP Benguerir uniquement**, sans Guemassa. Il veut transformer le projet en étude
de changements de surface utilisant des données SAR publiques NASA ou partenaires : périmètre vérifié, cartes à
l'intérieur et autour, dates et masque qualité, comparaison indépendante, conclusion sur changements et inconnues.
Tu es chargé de l'implémentation et de son exécution, à partir de l'audit déjà réalisé. Agis sur les parties
réalisables sans redemander des décisions déjà fixées.

Lis d'abord :

1. `docs/audit/2026-11-16/AUDIT.md`.
2. `docs/audit/2026-11-16/PLAN_EXECUTION.md` : ordre P0–P4 et critères de passage.
3. `docs/audit/2026-11-16/data_plan.json`, `catalogue_live.json`, `local_evidence.json`, `reproducibility.json`, `checks.json`.
4. Les instructions AGENTS applicables, puis les fichiers nécessaires de la méthode, du contrat et du pipeline.

**Base et protection du travail**

- La base auditée est `feature/benguerir-robustness-v2` à `22c6ed9`. `main` puis
  `feature/benguerir-mining-case` sont ses ancêtres : aucune fusion de ces branches n'est nécessaire.
- Vérifie l'état Git actuel ; conserve le dossier d'audit et les modifications de l'utilisateur. Crée une branche
  de travail telle que `feature/benguerir-surface-study`. N'écrase ni ne réinitialise les travaux présents.
- Ne touche pas au dépôt voisin `NASA_SAR`. N'effectue aucun push, envoi de message externe ou publication distante
  sans instruction correspondante. Ne lis ni n'affiche les secrets dans les journaux.
- Préserve le cas v2 publié ; prépare un nouveau cas et des sorties séparées pour la nouvelle étude.

**Constats déjà vérifiés, à ne pas réinventer**

- 71 tests Python, 14 Vitest, compilation TypeScript/Vite et 10 parcours navigateur passent. Le serveur Playwright
  a toutefois dû être arrêté manuellement après les 10 scénarios : fiabilise cette fin d'exécution sous Windows.
- 218 entrées et 102 sorties correspondent à leurs SHA-256. Un recalcul réel sans publication reproduit les
  102 sorties et le contenu scientifique du cas publié.
- Il existe 17 GUNW P05023, dont 15 utilisables. La méthode principale indique une faible cohérence relative au
  témoin ; elle ne mesure pas encore une variation temporelle du même pixel ni une surface excavée.
- La v2 a déjà corrigé la pagination, SCL 2, le taux du témoin d'évaluation, les intervalles par blocs et les
  manifestes optiques. Préserve ces corrections.
- Les 3 comparaisons optiques strictes reposent sur **2 couples Sentinel-2 distincts** : 14–29 juin et 13–28 août.
  Compte les dépendances explicitement. Ne présente pas ces trois comparaisons comme trois confirmations temporelles indépendantes.
- Le contour actuel est OSM 2020, 39,548 km². Il n'est ni un contour OCP actuel vérifié ni une concession.
- Le catalogue CMR du 16 novembre donne 19 GCOV provisoires, 3 GCOV de collection validée, aucun GUNW validé
  sur l'emprise/période de la requête et 148 granules OPERA RTC-S1. Ce sont des candidats, pas des produits tous testés.

**Implémentation prioritaire**

1. Corrige la lecture des preuves : groupes d'acquisitions indépendantes, références structurées, validation liée
   aux preuves effectives. Conserve la lecture des contrats v2 et les valeurs absentes avec leur raison.
2. Prépare le contour récent et son dossier de provenance/revue. Si une confirmation opérateur ou une revue humaine
   manque, l'état reste en attente ; poursuis les autres travaux. N'invente pas de validation humaine.
3. Ajoute l'extraction GCOV et les cartes de variation gamma-0 en dB avec masques communs et métadonnées complètes.
   Commence par le 16–28 août 2026, T044 A F018 P05023 ; les identifiants exacts figurent dans `data_plan.json`.
   Conserve GUNW comme information complémentaire. Teste un lot homogène avant d'étendre la série.
4. Traite séparément le pilote GCOV P05036 T023 D F072 du 25 octobre au 6 novembre. Vérifie les modes et anomalies
   de calibration documentés avant le 12 novembre ; ne mélange pas automatiquement CRID, orbites ou polarimétries.
5. Crée la couche qualité explicite et son export : raisons par pixel, zones non observées et dates rejetées.
   Corrige l'aperçu de cohérence qui reçoit actuellement le tableau brut sans `valid`.
6. Mets en place le protocole de références indépendantes décrit dans le plan : annotations datées et géolocalisées,
   unités hors calibration, signalées et non signalées, indéterminés, dépendance temporelle et effectifs.
   Sans référence suffisante, garde la conclusion exploratoire ; un rapport d'association n'est pas une précision.
7. Réorganise l'interface existante autour des cinq livrables. Sors la LOS non interprétée et les recettes génériques
   du parcours principal. N'entreprends pas de migration de framework. Archive les éléments superflus après contrôle
   des dépendances ; conserve les sources et l'historique.

Pour chaque zone, distingue : variation radar mesurée, changement optique visible, cause documentée, cause indéterminée.
Z1 est une zone à vérifier, pas une excavation démontrée. Pas de minerai, teneur, volume, production, danger de digue,
vitesse annuelle ou déplacement vertical inférés à partir de ces seuls résultats.

**Données et accès**

Les requêtes CMR sont publiques. L'accès aux fichiers NISAR peut utiliser l'authentification Earthdata déjà configurée,
via le code d'accès du dépôt, sans afficher ni copier le jeton. Préfère les recadrages utiles et enregistre les échecs.
Une absence de donnée devient `unavailable` ou `insufficient_baseline`, jamais zéro ou « stable ».
OPERA est un produit NASA/JPL fondé sur Sentinel-1 ESA/Copernicus : cite les deux origines, dédoublonne les versions/bursts,
et compare les bandes L et C séparément. Vérifie les catalogues au moment de l'exécution.

La page Resources du défi fournie par l'utilisateur n'était pas accessible lors de l'audit. Retente sa consultation
pour vérifier l'alignement exact, mais ne prétends pas connaître son contenu si l'accès échoue. Les pages officielles
NASA/ASF consultées sont liées dans l'audit et les produits réellement interrogés sont dans le JSON CMR.

**Validation et livraison**

Exécute les tests pertinents, le traitement réel dans un répertoire isolé, les contrôles d'intégrité et les parcours
API/navigateur FR/EN/AR, bureau et 390 px. Ne transforme pas les fixtures de tests en données d'étude.
Vérifie les nouveaux calculs sur des cas numériques connus et les erreurs de masques, grilles et versions ; ajoute
les tests de dépendance optique et de refus d'une validation sans référence. Garde les commandes reproductibles.

Livre le code fonctionnel, les couches, le rapport imprimable, le manifeste, les références et une conclusion
proportionnée. Indique ce qui est effectivement implémenté et calculé, les contrôles exécutés, les incertitudes,
les preuves externes encore manquantes et les commandes exactes. Aucun simple changement de nom ou d'étiquette
ne permet de déclarer l'étude « validée ». Termine les parties autonomes même si la validation de terrain reste en attente.
