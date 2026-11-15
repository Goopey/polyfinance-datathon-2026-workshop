# 03 — Moteur de décision

Le profil choisi dicte la pondération du moteur. Le moteur est du Python déterministe : mêmes entrées, même sortie.

## Étapes

```
ProfileWeights + MetricsTable + DebateRecord[]
   1. Contraintes dures      → candidats admissibles / rejetés (avec motif)
   2. Scores par critère     → valeurs entre 0 et 1, issues des métriques
   3. Score d'adéquation     → somme pondérée par les poids du profil
   4. Prise en compte du débat → niveau de confiance + désaccords conservés
   5. Garde-fous de panier   → diversification, plafonds
   6. Sortie                 → classement, rejets, tensions, ou « aucune recommandation »
```

## Critères

| Critère | Ce qu'il mesure | Preuves utilisées |
|---|---|---|
| `croissance` | Profil de croissance observé (rendement annualisé sur fenêtre explicite ; croissance des revenus si disponible) | Prix ajustés, dépôts |
| `stabilite` | Volatilité, perte maximale, comportement en 2022 | Prix ajustés |
| `diversification` | Apport au panier simulé : corrélation, concentration par secteur et classe d'actifs | Prix, univers |
| `esg` | Signaux ESG documentés et controverses datées | Sources ESG citées |
| `qualite` | Solidité : rentabilité, endettement ; pour un FNB : frais, diversification interne | Dépôts, fiches d'émetteurs |
| `horizon` | Pire période glissante de durée égale à l'horizon | Prix ajustés |
| `preferences` | Correspondance avec les préférences déclarées (thèmes, types d'actifs) | Univers, profil |

Limites à afficher :

- `croissance` et `horizon` décrivent le passé sur 5 ans. Ils ne prédisent rien et ne couvrent pas un horizon de 15 ans.
- `esg` peut valoir « inconnu ». Un inconnu n'est jamais traité comme un bon score : il baisse la confiance et s'affiche comme information manquante.

## Poids de départ par persona

Hypothèses de travail à calibrer avec les scénarios de `09_SCENARIOS_TEST.md`. La somme de chaque ligne vaut 1. Source unique : `data/reference/personas.json`.

| Critère | Amira | Mateo | Robert |
|---|---:|---:|---:|
| croissance | 0,30 | 0,15 | 0,10 |
| stabilite | 0,10 | 0,20 | 0,30 |
| diversification | 0,20 | 0,15 | 0,15 |
| esg | 0,05 | 0,25 | 0,05 |
| qualite | 0,10 | 0,15 | 0,25 |
| horizon | 0,10 | 0,05 | 0,10 |
| preferences | 0,15 | 0,05 | 0,05 |

## Contraintes dures de départ

| Contrainte | Amira | Mateo | Robert |
|---|---|---|---|
| Part maximale par actif | 15 % | 10 % | 10 % |
| Part maximale par secteur | 40 % | 30 % | 30 % |
| Part maximale en crypto | 15 % | 0 % | 0 % |
| Exclusion sur controverse documentée | non | oui | non |
| Actifs « hautement spéculatifs » | permis | exclus | signalés |

Une contrainte dure **écarte** ; un poids **classe**. La différence est montrée à l'utilisateur : « écarté par une règle de votre profil » contre « moins bien classé ».

## Score d'adéquation

```
score(a) = Σ_k  w_k · s_k(a)        avec Σ w_k = 1 et s_k(a) ∈ [0, 1]
```

- `s_k` est normalisé dans l'univers à la date `as_of` (rang centile), ce qui évite de comparer des unités différentes.
- La contribution de chaque critère (`w_k · s_k`) est conservée : c'est elle qui alimente le graphique « pourquoi ce classement » dans l'application.

## Rôle du débat

Le débat ne modifie pas le score. Il produit :

- un **niveau de confiance** (élevé / moyen / faible) selon l'accord des trois positions finales ;
- des **désaccords** recopiés tels quels dans la sortie ;
- des **questions ouvertes** (preuves manquantes).

Règle : une opposition du Bear appuyée sur un fait lié à une contrainte du profil déclenche un drapeau « à examiner » sur le candidat.

## Demande explicite de l'utilisateur (« Tester une idée »)

Quand l'utilisateur soumet un titre, le moteur ne filtre pas en silence. Il produit une **analyse de cohérence** :

| Sortie | Contenu |
|---|---|
| `tensions[]` | Chaque écart entre le titre et le profil, chiffré (ex. volatilité du titre comparée à celle des pistes retenues, horizon court) |
| `verdict` | `cohérent`, `cohérent avec réserve`, `incohérent avec le profil` |
| `context` | Ce que le titre changerait dans le panier simulé (concentration, volatilité globale) |
| `alternatives` | Actifs de l'univers qui répondent au même intérêt avec moins de tension, si la preuve existe |

C'est la réponse au test Robert : relever la tension, expliquer le risque, ne pas acquiescer automatiquement.

## « Aucune recommandation »

Sortie valide et attendue dans ces cas :

- aucun candidat ne passe les contraintes dures ;
- preuves insuffisantes (métriques manquantes, fenêtre trop courte) ;
- confiance faible sur tous les candidats ;
- **le critère le plus important du profil n'a aucune donnée** (ajout du 2026-11-15) : on ne recommande pas
  sans ce que le profil juge prioritaire. Exemple : Mateo (ESG à 25 %) si aucune piste admissible n'a de
  constat ESG concluant (section « Critère ESG »).

Le résultat explique alors ce qui manque.

## Qualité (réalisation, 2026-11-15)

Source : instantané Finnhub (`scripts/fetch_finnhub.py`, `data/reference/fundamentals.csv`, voir `04_DONNEES.md`
section 10). Code : `engine/quality.py`, branché dans l'étape « dossiers de preuves ».

| Composante | Calcul |
|---|---|
| Rentabilité des fonds propres (ROE) | Rang centile parmi les actions de l'univers |
| Endettement (dette / fonds propres, plus bas = mieux) | Rang centile **dans le secteur seulement** (une banque emprunte par nature) ; omis si le secteur compte moins de deux actions |
| Marge nette | Rang centile parmi les actions qui en ont une (pas de marge pour les banques) |
| **Score** | Moyenne des composantes disponibles |

Preuves : une preuve `FAIT` par chiffre Finnhub (exercice, date de publication supposée) et une preuve `HYPOTHESE`
pour le score (méthode de l'équipe), dont l'énoncé reprend les chiffres.

**Non applicable** (distinct de « manquant ») : pour les FNB et la crypto, la qualité n'a pas de sens (pas de comptes
de société). Le critère est retiré du score de l'actif et son poids réparti sur les autres critères, sans pénalité ni
bonus ; il ne baisse pas la confiance (`engine/signals.py`, `NOT_APPLICABLE`). Un critère manquant, lui, compte 0 et
baisse la confiance.

Effets observés : Robert gagne en confiance (« élevé ») ; GOOGL (ROE 33 %, peu d'endettement) entre dans ses pistes,
jugée légitime pour un profil attaché à la qualité ; QQQ (10e piste) est suivi dans la tâche de calibrage C7.
(Depuis la règle de tolérance ci-dessous, GOOGL et QQQ sont écartés pour Robert : ils dépassent ses deux repères de risque.)

## Critère ESG (réalisation, 2026-11-15)

Code : `engine/esg.py` (constats), `orchestration/pipeline.py` (`_add_esg_evidence`), `engine/constraints.py`
(exclusions), `engine/scoring.py` (`ABSOLUTE_CRITERIA`). Tests : `tests/unit/test_esg_engine.py`, scénario S2.

**Ce que les données permettent de conclure.** Les preuves ESG du dépôt (docs/04, section 12) sont des émissions
directes de GES absolues et, pour la plupart, des **bornes inférieures** (périmètre national, rattachement par nom
au Canada). Une borne inférieure peut établir qu'une société émet beaucoup, jamais qu'elle émet peu. Le moteur
n'en tire donc que quatre constats :

| Constat | Condition | Effet sur le classement | Effet sur les contraintes |
|---|---|---|---|
| Controverse documentée | Ligne dont le type de signal commence par « Controverse » (saisie sourcée) | Score ESG 0 (connu) | Écarté si `esg_exclusion` (règle `esg_exclusion`) |
| Émetteur majeur documenté | Plus grande borne inférieure d'émissions ≥ 10 Mt CO2e (lignes du script EPA / ECCC) | Score ESG 0 (connu) | Écarté si `esg_exclusion` **ou** si le profil pèse l'ESG à 25 % ou plus (règle `esg_emissions`) |
| Titre ESG prouvé | Ligne de `esg_evidence.csv` dont le type de signal commence par « Filtre ESG » ou « Filtrage ESG », datée et sourcée (aujourd'hui : ESGV, document de Vanguard) | Score ESG 1 ; seul rattachement au thème « filtre ESG » | — |
| Non concluant | Émissions sous le seuil | Critère **manquant** (preuves visibles dans le dossier) | — |

Un actif sans aucune preuve ESG n'a pas de constat : critère manquant. **Seule une ligne du fichier prouve qu'un titre est ESG** (décision de l'équipe, 2026-11-15) : ni la classification de l'univers, ni le nom du fonds, ni la simple présence dans le fichier (qui contient surtout des émissions) ne suffisent. Les lignes saisies à la main sans constat (émissions publiées par les sociétés, périmètre ESG des FNB) sont montrées dans la fiche et le débat, mais leurs chiffres ne sont pas relus par le moteur.

**Pourquoi pas un classement par émissions.** Pour Mateo, les seuls actifs admissibles avec une donnée sont
FTS.TO, ENB.TO, PG et XOM. Un rang centile des émissions placerait un pipelinier (ENB, borne inférieure) et
une pétrolière au-dessus de tous les actifs inconnus : le profil ESG serait poussé vers l'énergie fossile parce
que seules ces sociétés déclarent des installations. Refusé.

**Score absolu.** Le critère est catégoriel : son signal est un score dans [0, 1], utilisé tel quel. Avec un rang
centile, un émetteur majeur documenté obtiendrait un score supérieur à celui d'un actif inconnu (0).

**Confiance par piste.** La confiance fondée sur les données est calculée **par piste**, avec le poids des
critères qui lui manquent (seuils inchangés : 20 % et 40 %). Une piste sans preuve ESG pour Mateo (25 %) est au
mieux « moyenne », et le dit dans « ce que nous ne savons pas ».

**Hypothèses de l'équipe**

| Sujet | Valeur | Raison |
|---|---|---|
| Seuil d'émetteur majeur | 10 Mt CO2e par an | Un ordre de grandeur au-dessus des écarts de méthode (AR4 / AR5) ; une borne inférieure au-dessus du seuil est concluante. XOM (37,88 Mt, EPA) et CNQ.TO (18,57 Mt, ECCC) le dépassent ; PG (1,66 Mt) non. |
| Lecture « fort impact environnemental » | Un émetteur majeur est écarté pour un profil qui demande d'éviter les entreprises liées à des controverses environnementales | Lecture assumée de la préférence de Mateo, affichée comme règle d'EasyTrade, distincte d'une controverse |
| Plusieurs sources pour un titre | Plus grande borne inférieure, sans addition | Périmètres et potentiels de réchauffement différents |
| Fonds à filtre ESG | Score maximal sur la foi de la classification de l'univers | Méthodologie et composition d'ESGV non saisies (`etf_issuers`, « prévu ») : limite affichée |
| Dimensions couvertes | Environnement (émissions directes) seulement | Ni sociale ni gouvernance : aucune source admise saisie |

**Critère prioritaire sans donnée : pistes et avertissement** (décision de l'équipe, 2026-11-15, remplace la
sortie « aucune recommandation » de ce cas). Quand aucun candidat n'a de donnée pour le critère le plus important du
profil, les pistes sont classées sur les autres critères. `Decision.warnings` et `Explanation.warnings` portent un
avertissement, affiché en tête de l'écran des pistes, et chaque piste qui n'a pas ce critère a une confiance
« faible ». La règle « confiance faible partout ⇒ aucune recommandation » ne s'applique pas dans ce cas, puisque
l'avertissement l'explique. Pour un profil centré sur l'ESG (≥ 25 %), un second avertissement s'ajoute si aucune
piste retenue n'est un titre ESG prouvé. Il nomme les titres prouvés de l'univers et dit pourquoi ils ne sont pas
retenus, ou qu'il n'y en a aucun.

**Questionnaire** (`api/service.py`, `_esg_emphasis`) :

| Intérêts cochés | Poids ESG |
|---|---|
| ESG seul | Critère le plus important : au moins 30 %, au-dessus de tout autre critère |
| ESG parmi d'autres | 25 % (niveau de Mateo, même phrase de profil) |
| Sans ESG | 5 % (niveau d'Amira et de Robert). Corrige le gabarit « modéré », qui héritait des 25 % de Mateo |

Les autres poids gardent leurs proportions ; la phrase qui explique le changement figure dans le résumé du profil.

**Effet sur les personas (2026-11-12, agents simulés).** Mateo reçoit 10 pistes, ESGV en tête. XOM et CNQ.TO sont
écartés sur leurs émissions documentées, et les 9 autres pistes portent « Aucune preuve ESG concluante à cette date »,
avec une confiance moyenne. Avec le poids ESG à zéro, ESGV quitte la première place (S2, point 3). Amira et Robert
n'ont pas d'exclusion ESG ; ESGV gagne au plus leur poids ESG (5 %).

## Correctifs issus de l'audit (2026-11-15)

Audit complet : `AUDIT_REPORT.md` (racine du dépôt). Tests : `backend/tests/unit/test_audit_fixes.py` et `audit/`.

### Tolérance au risque : une règle, partagée avec « Tester une idée »

Repères par niveau (`engine/constraints.py`, `RISK_LIMITS`, inchangés) : faible 18 % / -20 %, faible à modérée
22 % / -25 %, modérée 25 % / -30 %, élevée 45 % / -50 % (volatilité annualisée / perte maximale, toute la période).

| Écart de l'actif | Profil prudent ou modéré | Profil à tolérance élevée |
|---|---|---|
| Un repère dépassé de plus de 1,5 fois | Écarté (« risque au-delà de votre tolérance », chiffres cités) | Écarté |
| Les deux repères dépassés | Écarté | Admissible avec réserve |
| Un seul repère dépassé | Admissible, adéquation plafonnée à « partielle », risque signalé | Idem |

Une classe autorisée dans une poche plafonnée (crypto avec `max_weight_crypto > 0`) suit la colonne « tolérance élevée » :
le plafond encadre son risque. Le verdict « incohérent avec le profil » de « Tester une idée » est rendu **exactement**
quand le classement écarte le titre (règle du profil ou tolérance) ; les comparaisons aux médianes des pistes retenues
nuancent le verdict sans le rendre incohérent. Le titre testé n'est pas ajouté à la liste « Écartées » : l'analyse de
cohérence en rend compte.

### Objectif et horizon

- Critère `horizon` : pire **année** glissante si l'horizon minimal déclaré est de moins de 5 ans (Robert, 3 à 5 ans),
  pire période glissante de **3 ans** sinon (`engine/signals.py`, `horizon_metric`).
- Questionnaire (`api/service.py`) : l'objectif et l'horizon ajustent les poids du gabarit (préserver : stabilité +10,
  croissance -10 ; croître : croissance +10, stabilité -5, horizon -5 ; moins de 5 ans : horizon +5, stabilité +5,
  croissance -10 ; plus de 12 ans : croissance +5, horizon -5 ; points de %, puis renormalisation).
- Réponses contradictoires : « préserver le capital » plafonne la tolérance appliquée à « faible », un horizon de moins de
  5 ans à « modérée ». La lecture la plus prudente l'emporte et l'écran de résumé le dit (« Vos réponses se contredisent »).

### Diversification mesurée

Le critère `diversification` est la **corrélation moyenne** des rendements quotidiens (CAD, dates communes, sans
remplissage) de l'actif avec les 30 autres actifs de l'univers : plus elle est basse, plus l'actif diversifie
(`engine/signals.py`, `correlation_diversification`). Elle remplace le décompte des actifs du même secteur. Preuve
`FAIT` par actif, citée dans le « pourquoi ».

### Débat

- Placement sans risque de référence : taux directeur moyen de la Banque du Canada sur la fenêtre des prix (série
  V39079, valeurs publiées à la date d'analyse), preuve `FAIT` ajoutée au dossier de chaque candidat.
- Bull : appui sans réserve seulement si le rendement annualisé dépasse ce taux ; sinon appui avec réserve.
  Réaliste : réserve si le risque pris n'a pas été rémunéré (même comparaison).
- Désaccord : au moins un agent s'oppose pendant qu'un autre ne s'oppose pas (une simple réserve n'en est plus un).
- Robustesse : une sortie invalide isolée (après relance) donne une position « non exprimée » ; un candidat dont la
  majorité des tours est invalide, ou un agent invalide pour **tous** les candidats, fait échouer l'analyse.

### Dates d'analyse

L'API refuse une date postérieure aux dernières données ou disposant de moins d'un an d'historique (HTTP 422). Le
« rendement de l'année 2022 » n'est calculé qu'une fois l'année terminée à la date d'analyse.

## Sensibilité

Pour « mettre les résultats à l'épreuve » :

- **Changer un poids** : recalculer le classement avec ±0,10 sur un critère ; afficher les pistes qui changent de rang.
- **Changer de profil** : même univers, autre persona ; afficher les différences côte à côte.
- **Changer la fenêtre** : 5 ans, 3 ans, sans 2022.

Un classement qui bascule au moindre changement est signalé comme fragile.

## Garde-fous de panier

Si l'application présente un panier simulé :

- plafonds de `hard_constraints` appliqués après le classement ;
- au moins trois classes d'actifs ou secteurs distincts pour un profil qui demande de la diversification ;
- conversion en CAD pour toute agrégation (voir `04_DONNEES.md`).

## Hypothèses ajoutées à l'étape P3

Choix de l'équipe (`HYPOTHESE`), à calibrer. Valeurs dans le code indiqué ; chaque valeur montrée à l'utilisateur a sa preuve de type `profile`, étiquetée hypothèse.

| Sujet | Valeur retenue | Raison | Code |
|---|---|---|---|
| Panier simulé | Parts égales entre les pistes retenues | Le plus simple à expliquer ; aucune optimisation cachée | `engine/governance.py` |
| Nombre de pistes retenues | Plus petit nombre qui respecte la part maximale par actif : 15 % → 7, 10 % → 10 | Le plafond par actif est tenu par construction | `basket_size` |
| Plafond par secteur, en nombre de pistes | Partie entière de (plafond × nombre de pistes) : 40 % de 7 → 2 ; 30 % de 10 → 3 | Même règle pour la part crypto (15 % de 7 → 1) | `select_basket` |
| Déclassement | Le classement est parcouru dans l'ordre ; une piste qui ferait dépasser un plafond est déclassée avec le motif, la suivante est examinée | « Moins bien classé » et « écarté par une règle » restent distincts | `select_basket` |
| Groupes de concentration | Trois groupes comptés ensemble pour le plafond par secteur : Technologies (technologies de l'information, services de communication, FNB à forte composante technologique) ; Actions américaines, marché large ; Obligations | Sans cela, trois pistes technologiques sous trois libellés de secteur passeraient chacune sous le plafond. À remplacer par la corrélation au panier | `CONCENTRATION_GROUPS` |
| Thèmes du critère `preferences` | Vocabulaire fermé de 7 thèmes : technologies, cryptoactifs, entreprises établies, fonds indiciels diversifiés, obligations, or, filtre ESG | L'agent de pondération lit le profil et choisit des thèmes ; le rattachement d'un actif à un thème est fait par le code, par classe d'actifs et secteur | `engine/signals.py` (`THEMES`) |
| Signal `preferences` | Thèmes préférés touchés − thèmes évités touchés ; 0 si aucun | Le critère est couvert pour tout l'univers, il n'est plus « manquant » | `preference_signals` |
| Écart maximal d'un poids au gabarit | ± 0,10, puis renormalisation | Borne l'effet de l'agent de pondération sur le classement | `agents/profile_weighting.py` |
| Contraintes dures et agent de pondération | Le modèle peut seulement resserrer une règle | Un modèle ne doit pas pouvoir assouplir une règle du profil | `tighten_constraints` |
| Repères de risque par tolérance | Volatilité annualisée / perte maximale : faible 18 % / −20 % ; faible à modérée 22 % / −25 % ; modérée 25 % / −30 % ; élevée 45 % / −50 % | Repris de l'écran « Tester une idée » du mobile ; niveau intermédiaire ajouté pour Robert | `engine/coherence.py` (`RISK_LIMITS`) |
| Tension sévère | Dépassement d'un repère de plus de 50 % | Une tension sévère donne « incohérent avec le profil » | `SEVERE_RATIO` |
| Libellé d'adéquation | Score rapporté au poids des critères couverts : ≥ 0,65 élevée ; ≥ 0,50 partielle ; sinon faible | Un critère sans donnée baisse la confiance, pas le libellé | `engine/scoring.py` (`fit_level`) |
| Confiance tirée du débat | Trois appuis : élevée ; au moins deux oppositions : faible ; sinon moyenne. Confiance d'une piste = minimum (données, débat) | Le débat ne modifie pas le score | `engine/decision.py` (`apply_debate`) |
| Drapeau « à examiner » | Opposition du Bear dont un argument cite une preuve du profil (règle ou repère) | Traduction de la règle « fait lié à une contrainte du profil » | `bear_flags_profile` |
| Candidats débattus | Pistes pressenties, candidats déclassés pour concentration, titre demandé | Limite le nombre d'appels au modèle ; le pré-classement est déterministe | `orchestration/pipeline.py` |
| Aucune recommandation après débat | Confiance faible sur toutes les pistes retenues | Troisième cas de la section « Aucune recommandation » | `orchestration/pipeline.py` |
| Effet sur le panier simulé | Volatilité du panier à parts égales, sans puis avec le titre testé à la part maximale par actif ; rendements quotidiens en CAD sur les dates communes | Tient compte des corrélations ; preuve `SCENARIO` | `validation/metrics.py` (`basket_volatility_metric`) |

Conséquence sur les scénarios, avec les données du jeu de départ : le critère `preferences` étant couvert, la confiance fondée sur les données passe à « élevé » pour Amira (15 % du poids sur des critères non sourcés) et reste « moyen » pour Robert (30 %) ; Mateo reste à 40 % non sourcés (ESG, qualité), donc « aucune recommandation » jusqu'à la saisie des preuves ESG (P6). (Dépassé : la qualité puis l'ESG sont maintenant renseignés, voir « Qualité » et « Critère ESG ».)
