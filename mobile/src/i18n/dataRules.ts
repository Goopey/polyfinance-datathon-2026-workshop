/**
 * Règles de traduction des textes du backend (voir translate.ts).
 *
 * Gabarits relevés sur l'API réelle (tests/fixtures/backend_strings.json) et dans le code du backend
 * (agents/simulated.py, agents/explanation.py, engine/*.py, orchestration/pipeline.py, api/service.py,
 * validation/*.py, data/reference/sources_registry.csv).
 *
 * Écriture d'un gabarit : `{n}` = nombre (format français, reformaté ensuite), `{t}` = symbole boursier,
 * `{s}` = texte quelconque (court), `{y}` = année. Les « % » acceptent une espace avant ou non.
 */
export type Rule = [RegExp, string | ((...m: string[]) => string)];

const NUM = "([-−+]?\\d+(?:[\\u202f\\u00a0 ]\\d{3})*(?:,\\d+)?)";
const TICK = "([A-Z0-9][A-Za-z0-9.\\-]*)";

/** Gabarit lisible → expression régulière ancrée. */
function tpl(pattern: string): RegExp {
  const esc = pattern.replace(/[.*+?^$()|[\]\\]/g, "\\$&");
  const re = esc
    .replace(/ ?%/g, "[\\u202f\\u00a0 ]?%")
    .replace(/\{n\}/g, NUM)
    .replace(/\{t\}/g, TICK)
    .replace(/\{y\}/g, "(\\d{4})")
    .replace(/\{s\}/g, "(.+?)");
  return new RegExp(`^${re}$`);
}

// ---------- Vocabulaire réutilisé dans les gabarits ----------

const LEVEL: Record<string, string> = {
  faible: "low", "faible à modérée": "low to moderate", "faible à modéré": "low to moderate",
  "modérée": "moderate", "modéré": "moderate", "élevée": "high", "élevé": "high",
};
const lvl = (s: string) => LEVEL[s] ?? s;

const MONTH: Record<string, string> = {
  janvier: "January", "février": "February", mars: "March", avril: "April", mai: "May", juin: "June",
  juillet: "July", "août": "August", septembre: "September", octobre: "October", novembre: "November", "décembre": "December",
};

const CRITERION: Record<string, string> = {
  croissance: "growth", "stabilité": "stability", diversification: "diversification", ESG: "ESG", "qualité": "quality",
  "tenue sur l'horizon": "resilience over the horizon", "préférences déclarées": "stated preferences",
};

const MISSING: Record<string, string> = {
  "signaux ESG non encore sourcés": "ESG signals not sourced yet",
  "aucune preuve ESG concluante à cette date": "no conclusive ESG evidence as of this date",
  "fondamentaux (qualité) non publiés à cette date": "fundamentals (quality) not published as of this date",
  "correspondance aux préférences déclarées non encore modélisée": "match with stated preferences not modeled yet",
  "historique de prix insuffisant": "insufficient price history",
  "apport à la diversification indisponible": "diversification contribution unavailable",
};

const THEME: Record<string, string> = {
  technologies: "technology", cryptoactifs: "crypto assets", "entreprises établies": "established companies",
  "fonds indiciels diversifiés": "diversified index funds", obligations: "bonds", or: "gold", "filtre ESG": "ESG screen",
  esg: "ESG", entreprises_etablies: "established companies", fonds_indiciels: "index funds", aucun: "none",
};
const themes = (s: string) => s.split(/,\s*/).map((x) => THEME[x] ?? x).join(", ");

const GROUP: Record<string, string> = {
  Technologies: "Technology", "Actions américaines, marché large": "U.S. stocks, broad market", Obligations: "Bonds",
};

const SECTORS_EN = [
  "Bonds (Canada aggregate)", "Bonds (Canada ultra short-term)", "Bonds (U.S. aggregate)", "Bonds (U.S. long Treasury)",
  "Broad market (Canada)", "Broad market (U.S. growth/tech-heavy)", "Broad market (U.S.)", "Broad market (U.S., ESG-screened)",
  "Communication Services", "Consumer Discretionary", "Consumer Staples", "Crypto asset", "Energy", "Financials", "Gold",
  "Health Care", "Industrials", "Information Technology", "Utilities", "Real Estate", "Materials",
];

/** Secteurs (fournis en anglais par les données) → français. */
export const SECTOR_FR: Record<string, string> = {
  "Bonds (Canada aggregate)": "Obligations (Canada, ensemble du marché)",
  "Bonds (Canada ultra short-term)": "Obligations (Canada, ultra-court terme)",
  "Bonds (U.S. aggregate)": "Obligations (É.-U., ensemble du marché)",
  "Bonds (U.S. long Treasury)": "Obligations (Trésor américain à long terme)",
  "Broad market (Canada)": "Marché large (Canada)",
  "Broad market (U.S. growth/tech-heavy)": "Marché large (É.-U., croissance et technologies)",
  "Broad market (U.S.)": "Marché large (É.-U.)",
  "Broad market (U.S., ESG-screened)": "Marché large (É.-U., filtre ESG)",
  "Communication Services": "Services de communication",
  "Consumer Discretionary": "Consommation discrétionnaire",
  "Consumer Staples": "Consommation de base",
  "Crypto asset": "Cryptoactif",
  Energy: "Énergie",
  Financials: "Finance",
  Gold: "Or",
  "Health Care": "Santé",
  Industrials: "Industrie",
  "Information Technology": "Technologies de l'information",
  Utilities: "Services publics",
  "Real Estate": "Immobilier",
  Materials: "Matériaux",
};

// ---------- Phrases fixes ----------

export const EN_EXACT: Record<string, string> = {
  ...Object.fromEntries(SECTORS_EN.map((s) => [s, s])),
  "Profil fictif": "My profile",
  "—": "—",

  // Personas (data/reference/personas.json)
  "Faire croître son capital de façon équilibrée à moyen et à long terme.": "Grow capital in a balanced way over the medium and long term.",
  "Faire croître son capital à long terme.": "Grow capital over the long term.",
  "Préserver son capital tout en maintenant un potentiel de croissance.": "Preserve capital while keeping some growth potential.",
  "Accorde de l'importance à la stabilité et à la qualité des entreprises": "Values stability and company quality",
  "Accorde une grande importance aux facteurs ESG": "Places great importance on ESG factors",
  "Intéressée par les cryptoactifs": "Interested in crypto assets",
  "Ouvert aux technologies émergentes si elles correspondent à son profil de risque": "Open to emerging technologies if they fit his risk profile",
  "Ouverte aux entreprises en forte croissance et à une volatilité importante": "Open to fast-growing companies and high volatility",
  "Peu intéressé par les cryptoactifs": "Not very interested in crypto assets",
  "Peu intéressé par les placements hautement spéculatifs": "Not very interested in highly speculative investments",
  "Peut être tenté par une entreprise très médiatisée, même si elle est plus risquée que ce qu'il recherche habituellement":
    "May be tempted by a much-hyped company, even if it is riskier than what he usually looks for",
  "Préfère les entreprises établies et les placements dont il comprend bien le modèle d'affaires":
    "Prefers established companies and investments whose business model he understands well",
  "Recherche un équilibre entre potentiel de croissance et stabilité": "Seeks a balance between growth potential and stability",
  "Souhaite maintenir une certaine diversification et éviter de miser exclusivement sur les technologies":
    "Wants to keep some diversification and avoid betting only on technology",
  "Souhaite éviter les entreprises liées à des controverses environnementales ou sociales importantes":
    "Wants to avoid companies linked to major environmental or social controversies",
  "Suit activement les marchés et s'intéresse aux nouvelles occasions d'investissement":
    "Actively follows the markets and is interested in new investment opportunities",
  "Très intéressée par l'intelligence artificielle et les technologies émergentes": "Very interested in artificial intelligence and emerging technologies",
  // Questionnaire (api/service.py)
  "Préserver son capital.": "Preserve capital.",
  "Faire croître son capital de façon équilibrée.": "Grow capital in a balanced way.",
  "Accorde une grande importance aux facteurs ESG.": "Places great importance on ESG factors.",
  "Intéressé par les technologies et l'innovation": "Interested in technology and innovation",
  "Accorde de l'importance à la stabilité et préfère les entreprises établies": "Values stability and prefers established companies",
  "Souhaite maintenir une certaine diversification et éviter de miser exclusivement sur un seul secteur":
    "Wants to keep some diversification and avoid betting on a single sector",
  "Souhaite éviter les entreprises liées à des controverses environnementales ou sociales importantes.":
    "Wants to avoid companies linked to major environmental or social controversies.",

  // Pondération du profil
  "L'objectif déclaré est d'abord de préserver le capital.": "The stated goal is first to preserve capital.",
  "L'objectif déclaré mentionne la croissance du capital.": "The stated goal mentions growing capital.",
  "Le profil accorde une grande importance aux facteurs ESG.": "The profile places great importance on ESG factors.",
  "Le profil déclare accorder de l'importance à la qualité des entreprises.": "The profile values company quality.",
  "Le profil déclare accorder de l'importance à la stabilité.": "The profile values stability.",
  "Le profil déclare peu d'intérêt pour ce type de placement.": "The profile shows little interest in this type of investment.",
  "Le profil déclare un intérêt pour les cryptoactifs, dans une part limitée.": "The profile is interested in crypto assets, in a limited share.",
  "Le profil souhaite garder une diversification et ne pas miser sur un seul secteur.": "The profile wants to stay diversified and not bet on a single sector.",
  "Le profil souhaite éviter les entreprises liées à des controverses importantes.": "The profile wants to avoid companies linked to major controversies.",
  "Poids modifiés à la main sur l'écran de résumé.": "Weights adjusted by hand on the summary screen.",
  "Poids, plafonds et repères de risque : valeurs de départ fixées par l'équipe, à calibrer.":
    "Weights, caps and risk benchmarks: starting values set by the team, to be calibrated.",

  // Explication, débat, inconnues
  "Aucune piste à présenter pour ce profil : les preuves ne suffisent pas.": "No ideas to present for this profile: the evidence is insufficient.",
  "Aucun argument étayé retenu.": "No supported argument kept.",
  "Les indicateurs décrivent le passé sur la période disponible : ils ne prévoient rien.":
    "The indicators describe the past over the available period: they predict nothing.",
  "Débat et rédaction produits par des agents simulés par des règles : aucun modèle de langage n'a été appelé.":
    "Debate and write-up produced by rule-based agents: no language model was called.",
  "Se rattache à un thème d'intérêt déclaré dans le profil.": "Matches a theme of interest stated in the profile.",
  "Se rattache à un thème d'intérêt déclaré dans votre profil.": "Matches a theme of interest stated in your profile.",
  "Secteur peu représenté dans l'univers analysé, ce qui sert de repère pour la diversification.":
    "Sector rarely represented in the analyzed universe, which serves as a diversification benchmark.",
  "Aucun document réglementaire n'a été consulté pour ce titre.": "No regulatory filing was consulted for this security.",
  "Aucune preuve ESG datée n'est disponible pour ce titre.": "No dated ESG evidence is available for this security.",
  "Signaux ESG non encore sourcés.": "ESG signals not sourced yet.",
  // Critère ESG (backend/easytrade/engine/esg.py, orchestration/pipeline.py)
  "Aucune preuve ESG concluante à cette date.": "No conclusive ESG evidence as of this date.",
  "Écarté : controverse ESG documentée, exclue par votre profil.":
    "Excluded: documented ESG controversy, excluded by your profile.",
  "Écarté : émissions directes de gaz à effet de serre documentées au-dessus du seuil d'émetteur majeur retenu par EasyTrade ; votre profil demande d'éviter les entreprises à fort impact environnemental.":
    "Excluded: documented direct greenhouse gas emissions above the major-emitter threshold chosen by EasyTrade; your profile asks to avoid companies with a heavy environmental impact.",
  "Seuil d'émetteur majeur retenu par EasyTrade (émissions directes de GES par an)":
    "Major-emitter threshold chosen by EasyTrade (direct GHG emissions per year)",
  "Ordre de grandeur fixé par l'équipe, au-dessus des écarts de méthode entre sources (AR4, AR5)":
    "Order of magnitude set by the team, above the methodological gaps between sources (AR4, AR5)",
  "Choix de l'équipe, pas une norme ; les émissions documentées sont des bornes inférieures.":
    "Team choice, not a standard; documented emissions are lower bounds.",
  "ESG (méthode EasyTrade) : émetteur majeur documenté, émissions directes déclarées au-dessus du seuil retenu":
    "ESG (EasyTrade method): documented major emitter, reported direct emissions above the chosen threshold",
  "Plus grande borne inférieure documentée parmi les preuves d'émissions du titre, comparée au seuil d'émetteur majeur ; score ESG nul (préoccupation documentée)":
    "Largest documented lower bound among the security's emissions evidence, compared with the major-emitter threshold; ESG score of zero (documented concern)",
  "ESG (méthode EasyTrade) : controverse documentée": "ESG (EasyTrade method): documented controversy",
  "Preuve de type « Controverse » publiée à la date d'analyse ; score ESG nul":
    "Evidence of the \"Controversy\" type published as of the analysis date; ESG score of zero",
  "ESG (méthode EasyTrade) : fonds à filtre ESG documenté": "ESG (EasyTrade method): documented ESG-screened fund",
  "Classification de l'univers (fonds à filtre ESG) ; score ESG maximal":
    "Universe classification (ESG-screened fund); maximum ESG score",
  "Classification sectorielle du fichier d'univers fourni par les organisateurs":
    "Sector classification from the universe file provided by the organizers",
  "Filtre et méthodologie de l'émetteur non vérifiés par l'équipe (composition non saisie) ; ne mesure pas les émissions du fonds.":
    "Issuer's screen and methodology not verified by the team (holdings not entered); does not measure the fund's emissions.",
  "Méthode de l'équipe (hypothèse) ; dimension environnementale seulement (émissions directes) ou classification d'un fonds ; ni sociale ni gouvernance.":
    "Team method (assumption); environmental dimension only (direct emissions) or a fund's classification; neither social nor governance.",
  EasyTrade: "EasyTrade",
  "Actif signalé comme hautement spéculatif par une règle de votre profil.": "Asset flagged as highly speculative by a rule of your profile.",
  "Cryptoactif écarté : votre profil n'autorise aucune part en crypto.": "Crypto asset excluded: your profile allows no share in crypto.",
  "Écarté faute d'indicateurs valides : historique de prix insuffisant à cette date.":
    "Excluded for lack of valid indicators: insufficient price history as of this date.",
  "Confiance faible sur toutes les pistes : le débat s'oppose aux candidats ou les données sont insuffisantes.":
    "Low confidence on every idea: the debate opposes the candidates or the data is insufficient.",
  "Aucun actif de l'univers ne passe les contraintes dures de votre profil.": "No asset in the universe passes your profile's hard constraints.",
  "Preuves insuffisantes : aucun candidat admissible à classer.": "Insufficient evidence: no eligible candidate to rank.",
  "Preuves insuffisantes : aucun critère exploitable sur les actifs admissibles.": "Insufficient evidence: no usable criterion on the eligible assets.",
  "Opposition du Bear appuyée sur un argument qui cite une preuve du profil (règle, repère).":
    "Bear opposition based on an argument citing profile evidence (rule, benchmark).",
  "Titre absent de l'univers analysé.": "Security not in the analyzed universe.",
  "Titre demandé absent de l'univers analysé.": "Requested security not in the analyzed universe.",
  "Simulation à des fins pédagogiques. Ceci n'est pas un conseil financier.": "For educational purposes. This is not financial advice.",
  "Décrit le passé sur la période disponible, pas une prévision. Biais du survivant.":
    "Describes the past over the available period, not a forecast. Survivorship bias.",
  "Décrit le passé sur la fenêtre indiquée, pas une prévision.": "Describes the past over the stated window, not a forecast.",
  "Approximation de l'apport de diversification (hypothèse de l'équipe), à remplacer par la corrélation au panier.":
    "Approximation of the diversification contribution (team assumption), to be replaced by correlation with the portfolio.",
  "Panier fictif : aucune transaction, aucun frais, parts fixes.": "Hypothetical portfolio: no transactions, no fees, fixed shares.",
  "Plus l'horizon de placement est court, moins il reste de temps pour traverser un tel recul.":
    "The shorter the investment horizon, the less time there is to ride out such a drop.",

  // Trace
  "Des pistes sont présentées.": "Ideas are presented.",
  "Aucune piste à rédiger : explication assemblée par le code, sans appel au modèle.":
    "No ideas to write up: explanation assembled by code, without calling the model.",
  "Dépôts réglementaires non branchés (sources sec_edgar et sedar_plus au statut « prévu »).":
    "Regulatory filings not connected (sec_edgar and sedar_plus sources are \"planned\").",
  "Aucune source de nouvelles autorisée n'est branchée.": "No authorized news source is connected.",
  "Une relance après refus du vérificateur de fidélité.": "One retry after the faithfulness checker refused.",

  // Métriques de la fiche
  "Volatilité": "Volatility",
  "Perte maximale": "Maximum drawdown",
  "Rendement annualisé observé": "Observed annualized return",
  "toute la période disponible": "the whole available period",
  neutre: "neutral", positif: "positive", "négatif": "negative",

  // Preuves : énoncés, traitements, limites
  "Médiane de la volatilité annualisée des actifs classés pour ce profil": "Median annualized volatility of the assets ranked for this profile",
  "Ne se rattache à aucun thème d'intérêt déclaré dans le profil": "Matches no theme of interest stated in the profile",
  "Part maximale en cryptoactifs dans le panier simulé (règle du profil)": "Maximum share in crypto assets in the hypothetical portfolio (profile rule)",
  "Part maximale par actif dans le panier simulé (règle du profil)": "Maximum share per asset in the hypothetical portfolio (profile rule)",
  "Part maximale par secteur dans le panier simulé (règle du profil)": "Maximum share per sector in the hypothetical portfolio (profile rule)",
  "Décompte des actifs de l'univers par secteur ; un secteur rare vaut un meilleur score":
    "Count of universe assets by sector; a rare sector earns a better score",
  "Gabarit du profil, resserré si le profil le demande": "Profile template, tightened if the profile asks for it",
  "Médiane de l'indicateur sur les actifs admissibles classés pour ce profil, hors titre testé":
    "Median of the indicator over the eligible assets ranked for this profile, excluding the tested security",
  "Recopie du profil déclaré, sans transformation": "Copy of the stated profile, unchanged",
  "Repère indicatif par niveau de tolérance au risque": "Indicative benchmark by risk tolerance level",
  "Thèmes lus dans le profil par l'agent de pondération ; rattachement de l'actif à un thème par sa classe d'actifs et son secteur (table du moteur)":
    "Themes read from the profile by the weighting agent; asset matched to a theme by its asset class and sector (engine table)",
  "Hypothèse de l'équipe, à calibrer ; ne décrit aucun fait de marché.": "Team assumption, to be calibrated; describes no market fact.",
  "Opinions d'analystes, pas une prévision ; affiché seulement, sans effet sur le score.":
    "Analyst opinions, not a forecast; shown only, with no effect on the score.",
  "Profil fictif déclaré ; aucune donnée personnelle réelle.": "Declared profile; no real personal data.",
  "Rattachement par secteur, sans analyse de l'activité réelle de l'émetteur (hypothèse de l'équipe).":
    "Matched by sector, without analyzing the issuer's actual business (team assumption).",
  "Relation décrite dans le document cité, à sa date ; elle peut avoir changé depuis.":
    "Relationship described in the cited document, as of its date; it may have changed since.",
  "Sociétés américaines seulement ; une vente d'initié a souvent une raison personnelle.":
    "U.S. companies only; an insider sale often has a personal reason.",
  "Information publiée par l'émetteur ou un tiers cité ; couverture ESG partielle.": "Information published by the issuer or a cited third party; partial ESG coverage.",
  "Méthode de l'équipe (hypothèse) ; ne compare pas les modèles d'affaires ; pas de FNB ni de crypto.":
    "Team method (assumption); does not compare business models; no ETFs or crypto.",
  "Ratio calculé par Finnhub, non audité ; décrit l'exercice indiqué, pas l'avenir.":
    "Ratio computed by Finnhub, unaudited; describes the stated fiscal year, not the future.",
  "Rentabilité des fonds propres (ROE)": "Return on equity (ROE)",
  "Dette / fonds propres": "Debt / equity",
  "Marge nette": "Net margin",

  // Écran Données : sources (data/reference/sources_registry.csv)
  "Alpaca — données de marché": "Alpaca — market data",
  "Banque du Canada — API Valet": "Bank of Canada — Valet API",
  "Banque du Canada — API Valet (FXUSDCAD)": "Bank of Canada — Valet API (FXUSDCAD)",
  "EasyTrade — questionnaire de profil fictif de l'application": "EasyTrade — the app's profile questionnaire",
  "EasyTrade — règles et hypothèses de l'équipe": "EasyTrade — team rules and assumptions",
  "FRED — Federal Reserve Bank of St. Louis": "FRED — Federal Reserve Bank of St. Louis",
  "Finnhub — offre gratuite": "Finnhub — free tier",
  "Rapports de durabilité des sociétés": "Company sustainability reports",
  "SEC EDGAR": "SEC EDGAR",
  "SEDAR+": "SEDAR+",
  "Sites des émetteurs de FNB": "ETF issuer websites",
  "Univers d'actifs (organisateurs)": "Asset universe (organizers)",
  "Yahoo Finance via yfinance": "Yahoo Finance via yfinance",
  "change USD/CAD": "USD/CAD exchange rate",
  "composition ; frais ; méthodologie ESG": "holdings; fees; ESG methodology",
  "dividendes et fractionnements": "dividends and splits",
  "dépôts réglementaires des émetteurs canadiens": "regulatory filings of Canadian issuers",
  "dépôts réglementaires et données financières des émetteurs US": "regulatory filings and financial data of U.S. issuers",
  "information ESG publiée": "published ESG information",
  "poids, plafonds, repères de risque, thèmes, panier simulé": "weights, caps, risk benchmarks, themes, hypothetical portfolio",
  prix: "prices",
  "prix quotidiens": "daily prices",
  "profils fictifs (objectif, tolérance, horizon, préférences)": "profiles (goal, tolerance, horizon, preferences)",
  "profils fictifs (objectif, tolérance, horizon, préférences, exclusions)": "profiles (goal, tolerance, horizon, preferences, exclusions)",
  "sociétés comparables (même secteur) ; fondamentaux annuels (ROE, dette / fonds propres, marge nette)":
    "comparable companies (same sector); annual fundamentals (ROE, debt / equity, net margin)",
  univers: "universe",
  "Choix de l'équipe, à calibrer ; ne décrit aucun fait de marché": "Team choices, to be calibrated; describes no market fact",
  "IPC daté au mois de référence et publié plusieurs semaines plus tard": "CPI dated to the reference month and published several weeks later",
  "Profil fictif déclaré par l'utilisateur ; aucune donnée personnelle réelle ni conservée": "Profile declared by the user; no real personal data, nothing stored",
  "Profils fictifs ; aucune donnée personnelle réelle": "Example profiles; no real personal data",
  "Secteurs simplifiés ; classification non officielle": "Simplified sectors; unofficial classification",
  "Séries mensuelles datées au mois de référence ; valeurs révisées et non telles que publiées":
    "Monthly series dated to the reference month; revised values, not as first published",
  "Un taux par jour ; aucun taux les jours fériés canadiens": "One rate per day; no rate on Canadian holidays",
  "adj_close recalculé à chaque téléchargement ; crypto en jours UTC ; données non certifiées par les bourses":
    "adj_close recomputed on every download; crypto in UTC days; data not certified by the exchanges",
  "Classification sectorielle non datée (hypothèse : identique au 2026-11-12) ; ratios calculés par Finnhub, non audités ; pas de marge nette pour les banques":
    "Undated sector classification (assumption: same as on 2026-11-12); ratios computed by Finnhub, unaudited; no net margin for banks",

  // Correctifs de l'audit : diversification mesurée, placement sans risque, tolérance au risque
  "Mesure la diversification par rapport à l'univers analysé, pas à un panier précis":
    "Measures diversification against the analyzed universe, not a specific portfolio",
  "les corrélations varient dans le temps et montent souvent pendant les crises.":
    "correlations change over time and often rise during crises.",
  "adj_close en CAD ; rendements quotidiens sur les dates communes à tous les actifs (sans remplissage) ; moyenne des corrélations de Pearson avec chacun des autres actifs ; plus elle est basse, plus l'actif diversifie":
    "adj_close in CAD; daily returns on the dates common to every asset (no filling); average Pearson correlation with each of the other assets; the lower it is, the more the asset diversifies",
  "Taux directeur moyen de la Banque du Canada sur la période (placement sans risque de référence)":
    "Average Bank of Canada policy rate over the period (risk-free reference)",
  "Approximation du rendement d'un placement sans risque ; ne tient pas compte des frais ni de l'impôt.":
    "Approximation of a risk-free investment's return; ignores fees and taxes.",
  "Dépasse un repère de risque de votre profil : adéquation plafonnée à « partielle ».":
    "Exceeds one of your profile's risk benchmarks: fit capped at \"partial\".",
  "Position non exprimée : la réponse de l'agent était invalide après une relance.":
    "Position not expressed: the agent's answer was invalid after one retry.",

  // Preuves ESG (émissions de GES, EPA et ECCC ; scripts/ingest_esg.py)
  "EPA — Greenhouse Gas Reporting Program (GHGRP), données 2023 et sociétés mères déclarées":
    "EPA — Greenhouse Gas Reporting Program (GHGRP), 2023 data and reported parent companies",
  "Environnement et Changement climatique Canada — Programme de déclaration des gaz à effet de serre (PDGES), données par installation":
    "Environment and Climate Change Canada — Greenhouse Gas Reporting Program (GHGRP), facility-level data",
  "émissions de GES par installation canadienne": "GHG emissions by Canadian facility",
  "émissions directes de GES par installation américaine ; société mère et part de détention déclarées":
    "direct GHG emissions by U.S. facility; reported parent company and ownership share",
  "GHGRP : 2023 Data Summary Spreadsheets et Reported Parent Companies (EPA)":
    "GHGRP: 2023 Data Summary Spreadsheets and Reported Parent Companies (EPA)",
  "Greenhouse Gas (GHG) Emissions Data by Facility, 2004 à aujourd'hui (ECCC, PDGES)":
    "Greenhouse Gas (GHG) Emissions Data by Facility, 2004 to present (ECCC, GHGRP)",
  ...Object.fromEntries([
    ["Installations américaines seulement : une société mondiale comme XOM n'est vue que pour sa part américaine ; émissions directes seulement (fournisseurs, injection de CO2 et CO2 biogénique exclus) ; potentiels de réchauffement AR4 alors que le Canada utilise AR5, donc non comparable directement ; valeur absolue, non rapportée au chiffre d'affaires ni à la production ; une société sans installation déclarante n'a pas de donnée (absence, pas zéro) ; année 2023, donc un décalage d'environ deux ans à la date d'analyse",
      "U.S. facilities only: a global company like XOM is seen only through its U.S. share; direct emissions only (suppliers, CO2 injection and biogenic CO2 excluded); AR4 warming potentials whereas Canada uses AR5, so not directly comparable; absolute value, not scaled to revenue or production; a company without a reporting facility has no data (absence, not zero); year 2023, so about a two-year lag at the analysis date"],
    ["Installations canadiennes seulement ; rattachement par le nom de l'exploitant, sans part de détention : une filiale sous un autre nom est omise (ex. Westcoast Energy pour Enbridge), donc borne inférieure ; coentreprises non réparties ; potentiels de réchauffement AR5 alors que l'EPA utilise AR4 ; CO2 de la biomasse publié à part ; valeur absolue, non rapportée au chiffre d'affaires ; date de publication du jeu 2024 à confirmer sur la fiche (hypothèse prudente : 2026-05-27)",
      "Canadian facilities only; matched by operator name, without ownership share: a subsidiary under another name is missed (e.g. Westcoast Energy for Enbridge), so this is a lower bound; joint ventures not allocated; AR5 warming potentials whereas the EPA uses AR4; biomass CO2 published separately; absolute value, not scaled to revenue; publication date of the 2024 dataset to be confirmed on the dataset page (cautious assumption: 2026-05-27)"],
  ].flatMap(([fr, en]) => [[fr, en], [`${fr}.`, `${en}.`]])),

  // Écran Données : contrôles qualité
  "Couverture du change sur toutes les dates utilisées": "Exchange-rate coverage on every date used",
  "Doublons (date, ticker)": "Duplicates (date, ticker)",
  "Fractionnements au ratio invraisemblable": "Splits with an implausible ratio",
  "Prix nuls, négatifs ou manquants": "Zero, negative or missing prices",
  "Volumes nuls": "Zero volumes",
  "Les jours sans taux (fériés canadiens, week-ends crypto) utilisent le dernier taux connu, jamais un taux futur.":
    "Days without a rate (Canadian holidays, crypto weekends) use the last known rate, never a future one.",
  "Si le facteur est erroné, les prix antérieurs à la date sont décalés d'au plus l'effet indiqué.":
    "If the factor is wrong, prices before the date are off by at most the stated effect.",
  "Un volume nul n'invalide pas le prix mais indique une séance peu fiable.": "A zero volume does not invalidate the price but signals an unreliable session.",
};

// ---------- Gabarits ----------

const r = (pattern: string, out: string | ((...m: string[]) => string)): Rule => [tpl(pattern), out];

export const EN_RULES: Rule[] = [
  // Correctifs de l'audit
  r("Corrélation moyenne de {n} avec les autres actifs analysés, un repère pour la diversification.",
    "Average correlation of $1 with the other analyzed assets, a diversification benchmark."),
  r("Corrélation moyenne des rendements quotidiens avec les {n} autres actifs de l'univers analysé",
    "Average correlation of daily returns with the $1 other assets in the analyzed universe"),
  r("Rendement annualisé observé de {n} %, positif mais sous le taux directeur moyen de la Banque du Canada ({n} %) sur la même période.",
    "Observed annualized return of $1%, positive but below the Bank of Canada's average policy rate ($2%) over the same period."),
  r("Rendement annualisé observé de {n} % sur toute la période disponible, au-dessus du taux directeur moyen de la Banque du Canada ({n} %) sur la période.",
    "Observed annualized return of $1% over the whole available period, above the Bank of Canada's average policy rate ($2%) over the period."),
  r("Sur la période, le rendement annualisé ({n} %) n'a pas dépassé le taux directeur moyen de la Banque du Canada ({n} %) : le risque pris n'a pas été rémunéré.",
    "Over the period, the annualized return ($1%) did not beat the Bank of Canada's average policy rate ($2%): the risk taken was not rewarded."),
  r("Série {t} ; moyenne simple des valeurs quotidiennes publiées sur la fenêtre des prix",
    "Series $1; simple average of the daily values published over the price window"),
  r("{s} : tolérance au risque retenue « {s} » au lieu de « {s} » déclarée.", (_m, why: string, applied: string, declared: string) =>
    `${CONFLICT[why] ?? why}: risk tolerance applied "${lvl(applied)}" instead of the declared "${lvl(declared)}".`),
  r("Écarté : risque au-delà de votre tolérance au risque {s} ({s}).", (_m, level: string, parts: string) =>
    `Excluded: risk beyond your ${lvl(level)} risk tolerance (${parts.split(" ; ").map(sub).join("; ")}).`),
  r("volatilité annualisée de {n} % pour un repère de {n} %", "annualized volatility of $1% against a $2% benchmark"),
  r("perte maximale observée de {n} % pour un repère de {n} %", "observed maximum drawdown of $1% against a $2% benchmark"),
  r("Pire période glissante de {n} an observée sur la période : {n} %.", "Worst rolling $1-year period observed: $2%."),
  r("Pire période glissante sur {n} an {n} %, sous la médiane {n} % des pistes retenues.",
    "Worst rolling $1-year period of $2%, below the $3% median of the selected ideas."),
  r("Médiane de la pire période glissante de {n} an des actifs classés pour ce profil",
    "Median worst rolling $1-year period of the assets ranked for this profile"),
  r("Pire période glissante de {n} an (toute la période, {s})", "Worst rolling $1-year period (whole period, $2)"),

  // Preuves ESG (émissions de GES)
  [/^Émissions directes de GES : (.+?) CO2e déclarées en (\d{4}) par (\d+) installations? américaines? \(pondérées par la part de détention de la société mère\)\.$/,
    (_m, qty: string, year: string, n: string) =>
      `Direct GHG emissions: ${qty} CO2e reported for ${year} by ${n} U.S. facilit${n === "1" ? "y" : "ies"} (weighted by the parent company's ownership share).`],
  [/^Émissions directes de GES : (.+?) CO2e déclarées en (\d{4}) par (\d+) installations? canadiennes? dont l'exploitant porte le nom de la société \(rattachement par le nom, sans part de détention\)\.$/,
    (_m, qty: string, year: string, n: string) =>
      `Direct GHG emissions: ${qty} CO2e reported for ${year} by ${n} Canadian facilit${n === "1" ? "y" : "ies"} whose operator bears the company's name (matched by name, without ownership share).`],
  r("Extraction par script ({s}) depuis « {s} » ({s}) ; extrait : {s}", (_m, script: string, title: string, url: string, excerpt: string) =>
    `Script extraction (${script}) from "${EN_EXACT[title] ?? title}" (${url}); excerpt: ${sentences(excerpt)}`),
  r("Société mère déclarée : {s}", "Reported parent company: $1"),
  r("Plus importante installation : {s} ({s} CO2e, part de détention {n} %).", "Largest facility: $1 ($2 CO2e, ownership share $3%)."),
  r("{n} installation(s) liée(s) à la société mère sans émissions directes publiées (fournisseurs, injection de CO2), non comptée(s).",
    "$1 facilit(ies) linked to the parent company with no published direct emissions (suppliers, CO2 injection), not counted."),
  r("Exploitants retenus : {s}", (_m, list: string) => `Operators included: ${list.split(" ; ").join("; ")}`),
  r("Information publiée par l'émetteur ou un tiers cité ; couverture ESG partielle. Limites de la source : {s}",
    (_m, rest: string) => `Information published by the issuer or a cited third party; partial ESG coverage. Source limits: ${sub(rest)}`),
  r("Limites de la source : {s}", (_m, rest: string) => `Source limits: ${sub(rest)}`),

  // Titres et profils
  r("{n} pistes cohérentes avec votre profil, {n} écartées", "$1 ideas consistent with your profile, $2 set aside"),
  r("{n} pistes cohérentes avec votre profil, {n} écartée", "$1 ideas consistent with your profile, $2 set aside"),
  r("{n} piste cohérente avec votre profil, {n} écartées", "$1 idea consistent with your profile, $2 set aside"),
  r("{n} piste cohérente avec votre profil, {n} écartée", "$1 idea consistent with your profile, $2 set aside"),
  r("{s} (poids modifiés)", "$1 (adjusted weights)"),
  [/^(.+?)(?:, (\d+) ans)? · risque (.+?) · horizon (.+)$/, (_m, who: string, age: string | undefined, risk: string, hz: string) =>
    `${who === "Profil fictif" ? "My profile" : who.replace(" (poids modifiés)", " (adjusted weights)")}${age ? `, ${age}` : ""} · ${lvl(risk)} risk · ${horizon(hz)} horizon`],

  // Pourquoi, débat, risques
  r("Rendement annualisé observé de {n} % sur toute la période disponible.", "Observed annualized return of $1% over the whole available period."),
  r("Rendement annualisé observé de {n} % sur la période disponible.", "Observed annualized return of $1% over the available period."),
  r("Rendement annualisé observé de {n} % pour une volatilité annualisée de {n} % sur la même période.",
    "Observed annualized return of $1% for annualized volatility of $2% over the same period."),
  r("Volatilité annualisée observée de {n} %, un repère pour le critère de stabilité de votre profil.",
    "Observed annualized volatility of $1%, a benchmark for your profile's stability criterion."),
  r("Volatilité annualisée observée de {n} % sur la période disponible.", "Observed annualized volatility of $1% over the available period."),
  r("Pire période glissante de {n} ans observée sur la période : {n} %.", "Worst rolling $1-year period observed: $2%."),
  r("Sur la période observée, la pire période glissante de {n} ans est restée positive ({n} %).",
    "Over the observed period, the worst rolling $1-year period stayed positive ($2%)."),
  r("Volatilité annualisée de {n} %, sous le repère de {n} % retenu pour ce profil.", "Annualized volatility of $1%, below the $2% benchmark set for this profile."),
  r("Volatilité annualisée de {n} %, au-dessus du repère de {n} % retenu pour ce profil.", "Annualized volatility of $1%, above the $2% benchmark set for this profile."),
  r("Perte maximale observée de {n} %, au-delà du repère de {n} % retenu pour ce profil.", "Observed maximum drawdown of $1%, beyond the $2% benchmark set for this profile."),
  r("Perte maximale observée de {n} % sur la période disponible.", "Observed maximum drawdown of $1% over the available period."),
  r("Rendement négatif sur l'année {y} : {n} %.", "Negative return in $1: $2%."),
  r("La perte maximale observée ({n} %) dépasse le repère de {n} % du profil.", "The observed maximum drawdown ($1%) exceeds the profile's $2% benchmark."),
  r("La volatilité annualisée ({n} %) dépasse le repère de {n} % du profil.", "Annualized volatility ($1%) exceeds the profile's $2% benchmark."),
  r("Se rattache au thème « {s} » déclaré dans le profil.", (_m, t: string) => `Matches the "${THEME[t] ?? t}" theme stated in the profile.`),
  r("Élargit la comparaison à un autre secteur ({s}).", "Widens the comparison to another sector ($1)."),
  [/^(Appui avec réserve|Appui|Opposition) — (.+)$/, (_m, st: string, rest: string) =>
    `${{ Appui: "Support", "Appui avec réserve": "Support with caveats", Opposition: "Opposition" }[st]} — ${sub(rest)}`],

  // Tester une idée
  r("Volatilité annualisée de {n} %, au-dessus du repère de {n} % retenu pour une tolérance au risque {s}.",
    (_m, a: string, b: string, l: string) => `Annualized volatility of ${a}%, above the ${b}% benchmark set for ${lvl(l)} risk tolerance.`),
  r("Perte maximale observée de {n} %, au-delà du repère de {n} % retenu pour une tolérance au risque {s}.",
    (_m, a: string, b: string, l: string) => `Observed maximum drawdown of ${a}%, beyond the ${b}% benchmark set for ${lvl(l)} risk tolerance.`),
  r("Volatilité annualisée {n} % contre une médiane de {n} % pour les pistes retenues de votre profil.",
    "Annualized volatility of $1% versus a median of $2% for your profile's selected ideas."),
  r("Pire période glissante sur {n} ans {n} %, sous la médiane {n} % des pistes retenues.",
    "Worst rolling $1-year period of $2%, below the $3% median of the selected ideas."),
  r("Même secteur ; volatilité annualisée observée de {n} % sur la période.", "Same sector; observed annualized volatility of $1% over the period."),
  r("Scénario fictif : un panier simulé des {n} pistes retenues, à parts égales, affiche une volatilité annualisée observée de {n} %. Avec {t} à hauteur de {n} % du panier, elle aurait été de {n} % sur la même période.",
    "Scenario: a hypothetical equal-weight portfolio of the $1 selected ideas shows observed annualized volatility of $2%. With $3 at $4% of the portfolio, it would have been $5% over the same period."),
  r("Sur la période observée, ce titre a connu une perte maximale de {n} %.", "Over the observed period, this security had a maximum drawdown of $1%."),

  // Écartées, aucune recommandation
  r("Déclassé pour cause de concentration : le plafond de {n} % par secteur est déjà atteint pour « {s} » dans le panier simulé.",
    (_m, n: string, g: string) => `Moved down for concentration: the ${n}% per-sector cap is already reached for "${GROUP[g] ?? SECTOR_LABEL(g)}" in the hypothetical portfolio.`),
  r("Déclassé pour cause de concentration : la part maximale en crypto de {n} % est déjà atteinte dans le panier simulé.",
    "Moved down for concentration: the $1% maximum crypto share is already reached in the hypothetical portfolio."),
  r("Aucune recommandation : le critère le plus important de votre profil ({s}, {n} %) n'a aucune donnée à cette date ({s}).",
    (_m, c: string, n: string, why: string) =>
      `No recommendation: your profile's most important criterion (${CRITERION[c] ?? c}, ${n}%) has no data as of this date (${MISSING[why] ?? why}).`),
  r("Le critère le plus important de votre profil ({s}, {n} %) n'a aucune donnée à cette date ({s}).",
    (_m, c: string, n: string, why: string) =>
      `Your profile's most important criterion (${CRITERION[c] ?? c}, ${n}%) has no data as of this date (${MISSING[why] ?? why}).`),
  r("Aucune recommandation : {s}", (_m, rest: string) => `No recommendation: ${sub(rest)}`),
  r("Aucun candidat à débattre : {s}", (_m, rest: string) => `No candidate to debate: ${lcFirst(sub(ucFirst(rest)))}`),
  r("Confiance trop faible pour recommander : trop de poids de votre profil porte sur des critères non encore sourcés ({s}).",
    (_m, list: string) => `Confidence too low to recommend: too much of your profile's weight rests on criteria not sourced yet (${list.split(/,\s*/).map((c) => CRITERION[c] ?? c).join(", ")}).`),
  r("Titre absent de l'univers analysé : {t}", "Security not in the analyzed universe: $1"),
  r("Profil inconnu : {s}", "Unknown profile: $1"),
  r("Analyse inconnue : {s}", "Unknown analysis: $1"),
  r("Preuve inconnue dans {s} : {s}", "Unknown evidence in $1: $2"),
  r("Aucun cours publié pour {t} au {s}", "No published price for $1 as of $2"),
  r("API injoignable ({s}). Vérifiez EXPO_PUBLIC_API_URL.", "API unreachable ($1). Check EXPO_PUBLIC_API_URL."),
  r("Erreur {n}", "Error $1"),
  r("Choix non pris en charge : {s}", "Unsupported choice: $1"),

  // Trace
  r("{n} groupes de secteurs distincts parmi les pistes retenues (minimum {n}).", "$1 distinct sector groups among the selected ideas (minimum $2)."),
  r("{n} pistes retenues ; {n} désaccord(s) conservé(s) ; {n} à examiner.", "$1 ideas selected; $2 disagreement(s) kept; $3 to review."),
  r("{n} pistes retenues, {n} déclassées pour concentration ; au plus {n} par secteur et {n} en crypto.",
    "$1 ideas selected, $2 moved down for concentration; at most $3 per sector and $4 in crypto."),
  r("panier incomplet ({n} pistes pour {n} visées) : {s}", "incomplete portfolio ($1 ideas for $2 targeted): $3"),
  r("{n}/{n} affirmations rédigées fidèles au premier passage ; {n} retirées ; {n} affirmations de la sortie recontrôlées, {n} écart restant ; {n} formulation refusée.",
    "$1/$2 written claims faithful on the first pass; $3 removed; $4 output claims rechecked, $5 discrepancy left; $6 wording refused."),
  r("{n} candidats ; {n} arguments gardés, {n} supprimés (preuve absente ou nombre non étayé).",
    "$1 candidates; $2 arguments kept, $3 removed (missing evidence or unsupported number)."),
  r("{n} candidats classés ; {n} dossiers de preuves.", "$1 candidates ranked; $2 evidence packs."),
  r("{n} candidats classés ; {n} dossiers de preuves. Critère ESG — controverses documentées : {s} ; émetteurs majeurs documentés : {s} ; fonds à filtre ESG : {s} ; preuves non concluantes : {s} ; actifs sans preuve ESG : {n}.",
    (_m, ranked: string, packs: string, controversies: string, emitters: string, screened: string, inconclusive: string, none: string) => {
      const list = (s: string) => (s === "aucun" ? "none" : s);
      return `${ranked} candidates ranked; ${packs} evidence packs. ESG criterion — documented controversies: ${list(controversies)}; `
        + `documented major emitters: ${list(emitters)}; ESG-screened funds: ${list(screened)}; inconclusive evidence: `
        + `${list(inconclusive)}; assets without ESG evidence: ${none}.`;
    }),
  r("Fonds classé « {s} » dans l'univers analysé : il applique un filtre ESG",
    (_m, sector: string) => `Fund classified as "${sector}" in the analyzed universe: it applies an ESG screen`),
  r("{n} actifs examinés ; {n} écartés par une règle du profil ; {n} écartés faute d'indicateurs valides ; {n} candidats classés.",
    "$1 assets reviewed; $2 excluded by a profile rule; $3 excluded for lack of valid indicators; $4 candidates ranked."),
  r("{n} candidats.", "$1 candidates."),
  r("{n} indicateurs calculés, {n} preuves créées, aucune donnée publiée après le {s}.", "$1 indicators computed, $2 pieces of evidence created, no data published after $3."),
  r("Niveau de risque : {s} ; thèmes : {s} ; écarts au gabarit : {s}.",
    (_m, l: string, th: string, gap: string) => `Risk level: ${lvl(l)}; themes: ${themes(th)}; deviations from the template: ${THEME[gap] ?? gap}.`),
  r("Tester une idée — {t} : {s}, {n} tension(s). {s}",
    (_m, t: string, v: string, n: string, rest: string) => `Test an idea — ${t}: ${VERDICT[v] ?? v}, ${n} tension(s). ${sub(rest)}`),
  r("Tester une idée — {t} : {s}, {n} tension(s).", (_m, t: string, v: string, n: string) => `Test an idea — ${t}: ${VERDICT[v] ?? v}, ${n} tension(s).`),
  r("Affirmations retirées par le vérificateur : {s}", "Claims removed by the checker: $1"),
  r("Propositions retirées (hors univers) : {s}.", "Proposals removed (outside the universe): $1."),
  r("Explication non affichée : le vérificateur de fidélité relève encore {s}", "Explanation not shown: the faithfulness checker still finds $1"),

  // Preuves
  r("{t} — CONCURRENT — {t}", "$1 — COMPETITOR — $2"),
  r("{t} — FOURNISSEUR — {t}", "$1 — SUPPLIER — $2"),
  r("{t} — CLIENT — {t}", "$1 — CUSTOMER — $2"),
  r("{t} — PARTENAIRE — {t}", "$1 — PARTNER — $2"),
  r("Horizon de placement déclaré : {s}", (_m, h: string) => `Stated investment horizon: ${horizon(h)}`),
  r("Objectif déclaré : {s}", (_m, o: string) => `Stated goal: ${EN_EXACT[o] ?? o}`),
  r("Tolérance au risque déclarée : {s}", (_m, l: string) => `Stated risk tolerance: ${lvl(l)}`),
  r("Préférence déclarée : {s}", (_m, p: string) => `Stated preference: ${EN_EXACT[p] ?? p}`),
  r("Poids du critère « {s} » dans le profil", (_m, c: string) => `Weight of the "${CRITERION[c] ?? c}" criterion in the profile`),
  r("Indice de sentiment des initiés (MSPR, de -100 à +100), {s} {y}", (_m, m: string, y: string) => `Insider sentiment index (MSPR, from -100 to +100), ${MONTH[m] ?? m} ${y}`),
  r("Recommandations d'analystes, {s} {y} : {n} achat fort, {n} achat, {n} conserver, {n} vente, {n} vente forte",
    (_m, m: string, y: string, a: string, b: string, c: string, d: string, e: string) =>
      `Analyst recommendations, ${MONTH[m] ?? m} ${y}: ${a} strong buy, ${b} buy, ${c} hold, ${d} sell, ${e} strong sell`),
  r("Médiane de la pire période glissante de {n} ans des actifs classés pour ce profil", "Median worst rolling $1-year period of the assets ranked for this profile"),
  r("Nombre d'actifs du secteur « {s} » dans l'univers analysé (repère de diversification)",
    "Number of assets in the \"$1\" sector of the analyzed universe (diversification benchmark)"),
  r("Repère de perte maximale pour une tolérance au risque {s}", (_m, l: string) => `Maximum drawdown benchmark for ${lvl(l)} risk tolerance`),
  r("Repère de volatilité annualisée pour une tolérance au risque {s}", (_m, l: string) => `Annualized volatility benchmark for ${lvl(l)} risk tolerance`),
  r("Se rattache à un thème d'intérêt du profil ({s})", (_m, t: string) => `Matches a theme of interest in the profile (${THEME[t] ?? t})`),
  r("Se rattache à un thème que le profil préfère éviter ({s})", (_m, t: string) => `Matches a theme the profile prefers to avoid (${THEME[t] ?? t})`),
  r("Volatilité annualisée (toute la période, {s})", (_m, c: string) => `Annualized volatility (whole period, ${c})`),
  r("Perte maximale sur la fenêtre observée (toute la période, {s})", (_m, c: string) => `Maximum drawdown over the observed window (whole period, ${c})`),
  r("Pire période glissante de {n} ans (toute la période, {s})", "Worst rolling $1-year period (whole period, $2)"),
  r("Rendement annualisé (toute la période, {s})", "Annualized return (whole period, $1)"),
  r("Rendement de l'année {y} ({y}, {s})", "Return for the year $1 ($2, $3)"),
  r("Volatilité annualisée d'un panier simulé ({n} pistes retenues, parts égales)", "Annualized volatility of a hypothetical portfolio ($1 selected ideas, equal shares)"),
  r("Volatilité annualisée d'un panier simulé ({t} à {n} %, le reste à parts égales entre les {n} pistes retenues)",
    "Annualized volatility of a hypothetical portfolio ($1 at $2%, the rest split equally among the $3 selected ideas)"),
  r("{s}, exercice clos le {s}", (_m, label: string, d: string) => `${EN_EXACT[label] ?? label}, fiscal year ended ${d}`),
  r("Pire période de {n} ans", "Worst $1-year period"),
  r("Rendement sur l'année {y}", "Return in $1"),
  r("l'année {y}", "the year $1"),
  r("toute la période, fenêtres glissantes de {n} ans", "whole period, rolling $1-year windows"),

  // Traitements (evidence.processing)
  r("Finnhub ({s} ; achats et ventes des dirigeants déclarés (formulaires {n}), agrégés par mois",
    "Finnhub ($1; insider purchases and sales filed (Forms $2), aggregated by month"),
  r("Finnhub ({s} ; solde = (achats − ventes) ÷ total des recommandations ; mois connu une fois terminé",
    "Finnhub ($1; balance = (buys − sells) ÷ total recommendations; a month is known once it has ended"),
  r("adj_close ; (prix final / prix initial) ^ (périodes par an / nombre de rendements) - {n} ; {n} périodes par an ; devise : {s}",
    "adj_close; (final price / initial price) ^ (periods per year / number of returns) - $1; $2 periods per year; currency: $3"),
  r("adj_close ; maximum du recul depuis un sommet ; {n} périodes par an ; devise : {s}",
    "adj_close; largest drop from a peak; $1 periods per year; currency: $2"),
  r("adj_close ; plus faible rendement cumulé sur {n} observations consécutives ; {n} périodes par an ; devise : {s}",
    "adj_close; lowest cumulative return over $1 consecutive observations; $2 periods per year; currency: $3"),
  r("adj_close ; rendement cumulé entre le dernier prix de l'année précédente et celui de l'année ; {n} périodes par an ; devise : {s}",
    "adj_close; cumulative return between the last price of the previous year and that of the year; $1 periods per year; currency: $2"),
  r("adj_close ; écart-type (ddof={n}) des rendements quotidiens × racine des périodes par an ; {n} périodes par an ; devise : {s}",
    "adj_close; standard deviation (ddof=$1) of daily returns × square root of periods per year; $2 periods per year; currency: $3"),
  r("adj_close en {s} ; dates communes à tous les actifs du panier (sans remplissage) ; parts fixes rééquilibrées à chaque séance ; écart-type (ddof={n}) × racine de {n} ; composition : {s}",
    "adj_close in $1; dates common to every asset in the portfolio (no filling); fixed shares rebalanced each session; standard deviation (ddof=$2) × square root of $3; holdings: $4"),
  [/^finnhub_peers stock\/peers\?symbol=(\S+), section sociétés comparables \(même secteur\) \((\S+) ; extrait : Finnhub classe (\S+) parmi les sociétés comparables à (\S+) \(relevé le (\S+)\)\. Hypothèse : classification identique au (\S+)\. ; saisie : (\S+)$/,
    "finnhub_peers stock/peers?symbol=$1, comparable companies section (same sector) ($2; excerpt: Finnhub lists $3 among the companies comparable to $4 (retrieved $5). Assumption: same classification on $6.; entered by: $7"],
  r("Finnhub, série annuelle « {s} » ({s}) ; publication supposée {n} jours après la clôture de l'exercice",
    "Finnhub, annual series \"$1\" ($2); publication assumed $3 days after fiscal year end"),
  r("Saisie manuelle depuis « {s} » ({s}) ; extrait : {s}", "Entered by hand from \"$1\" ($2); excerpt: $3"),
  r("Moyenne des rangs centiles : {s}", "Average of percentile ranks: $1"),

  // Limites (evidence.limits) — morceaux de phrases (découpées par translate.ts)
  r("Biais du survivant : univers choisi en {y}.", "Survivorship bias: universe chosen in $1."),
  r("Univers choisi en {y} : biais du survivant.", "Universe chosen in $1: survivorship bias."),
  r("Approximation de l'apport de diversification (hypothèse de l'équipe), à remplacer par la corrélation au panier. Univers choisi en {y} : biais du survivant.",
    "Approximation of the diversification contribution (team assumption), to be replaced by correlation with the portfolio. Universe chosen in $1: survivorship bias."),
  r("Converti en CAD au taux USD/CAD de la Banque du Canada ; dernier taux connu les jours sans taux ({n} séances concernées dans la fenêtre).",
    "Converted to CAD at the Bank of Canada USD/CAD rate; last known rate on days without a rate ($1 sessions affected in the window)."),
  r("Jours civils UTC, sans clôture de marché ; annualisé sur {n} jours.", "UTC calendar days, no market close; annualized over $1 days."),
  r("Anomalie de données : « fractionnement » de {s} le {s}, probablement une distribution spéciale ; non appliqué, vérification auprès des relations investisseurs en attente.",
    "Data anomaly: \"split\" of $1 on $2, probably a special distribution; not applied, pending confirmation with investor relations."),

  // Écran Données
  r("Au moins {n} observations par actif", "At least $1 observations per asset"),
  r("Trous de plus de {n} séances", "Gaps of more than $1 sessions"),
  r("Variations de plus de {n} % sur une journée", "Moves of more than $1% in a single day"),
  r("Peut être incomplet pour les FNB ; anomalie {t} du {s}", "May be incomplete for ETFs; $1 anomaly on $2"),
  r("Énoncé officiel du Datathon Polyfinances {y} — personas fictifs", "Official Polyfinances Datathon $1 brief — example personas"),
  r("fonds fédéraux ; rendements {n} et {n} ans ; IPC ; chômage", "federal funds; $1- and $2-year yields; CPI; unemployment"),
  r("taux directeur ; rendements {n} et {n} ans ; IPC", "policy rate; $1- and $2-year yields; CPI"),
  r("… et {n} autre(s)", "… and $1 more"),
  // Détails des contrôles qualité : « clé : valeur · clé : valeur ».
  [/^((?:date|ticker|ex_date|ratio|treatment|status|max_relative_effect_on_prior_prices_pct|max_days_carried|rows_with_carried_rate|rows_without_rate|usd_price_rows) : .*)$/,
    (_m, all: string) => all.split(" · ").map((pair) => {
      const i = pair.indexOf(" : ");
      if (i < 0) return pair;
      const k = pair.slice(0, i);
      const v = pair.slice(i + 3);
      return `${DETAIL_KEY[k] ?? k}: ${DETAIL_VALUE[v] ?? v}`;
    }).join(" · ")],
  // Identifiants techniques (sujets de preuves, versions, fichiers) : identiques dans les deux langues.
  [/^engine@v\d+$|^validation@v\d+$|^data\/raw\/.+$|^(?:amira|mateo|robert|fictif)(?:_[0-9a-f]+)?$|^[A-Z0-9.\-]+→[A-Z0-9.\-]+$/, (m: string) => m],
];

const CONFLICT: Record<string, string> = {
  "Votre objectif est de préserver le capital": "Your goal is to preserve capital",
  "Votre horizon est de moins de 5 ans": "Your horizon is under 5 years",
};

/** Suite de phrases (« A. B. ») : chaque phrase traduite si un gabarit la couvre. */
function sentences(text: string): string {
  const parts = text.split(/\.\s+(?=[A-Z0-9À-Ý])/);
  return parts.map((p, i) => sub(i < parts.length - 1 ? `${p}.` : p)).join(" ");
}

const VERDICT: Record<string, string> = {
  "cohérent": "consistent", "cohérent avec réserve": "consistent with caveats", "incohérent avec le profil": "inconsistent with the profile",
};

const DETAIL_KEY: Record<string, string> = {
  date: "date", ticker: "ticker", ex_date: "ex-date", ratio: "ratio", treatment: "treatment", status: "status",
  max_relative_effect_on_prior_prices_pct: "max effect on earlier prices (%)", max_days_carried: "max days carried",
  rows_with_carried_rate: "rows with a carried rate", rows_without_rate: "rows without a rate", usd_price_rows: "USD price rows",
};
const DETAIL_VALUE: Record<string, string> = {
  "Non appliqué (prix déjà ajustés). Mention ajoutée aux limites de chaque preuve de ce ticker.":
    "Not applied (prices already adjusted). Note added to the limits of every piece of evidence for this ticker.",
  "à vérifier auprès des relations investisseurs": "to be checked with investor relations",
};

function horizon(h: string): string {
  const m = /^(\d+) à (\d+) ans$/.exec(h) ?? /^(\d+) ans (?:et plus|ou plus)$/.exec(h);
  if (!m) return h;
  return m[2] ? `${m[1]} to ${m[2]} years` : `${m[1]}+ years`;
}

function SECTOR_LABEL(s: string): string {
  return SECTORS_EN.includes(s) ? s : s;
}

const ucFirst = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const lcFirst = (s: string) => s.charAt(0).toLowerCase() + s.slice(1);

/** Sous-phrase (« Aucune recommandation : … ») : traduite si connue. */
function sub(s: string): string {
  if (EN_EXACT[s] !== undefined) return EN_EXACT[s];
  for (const [re, out] of EN_RULES) {
    const m = re.exec(s);
    if (m) return typeof out === "string" ? s.replace(re, out) : out(...(m as unknown as string[]));
  }
  return s;
}

// ---------- Français : données arrivées en anglais, libellés « fictif » ----------

export const FR_EXACT: Record<string, string> = {
  ...SECTOR_FR,
  "Profil fictif": "Mon profil",
};

export const FR_RULES: Rule[] = [
  [/^Profil fictif( · .+)$/, (_m, rest: string) => `Mon profil${rest}`],
  [/^(.*)« (.+?) »(.*)$/, (m: string, a: string, sector: string, b: string) => (SECTOR_FR[sector] ? `${a}« ${SECTOR_FR[sector]} »${b}` : m)],
  // Avec de vraies données, rien n'est « fictif » : on retire le mot des libellés internes.
  [/^(.*fictif.*)$/s, (_m: string, s: string) => s
    .replace(/Scénario fictif : /g, "Scénario : ")
    .replace(/Panier fictif/g, "Panier hypothétique")
    .replace(/personas fictifs/g, "personas d'exemple")
    .replace(/Profils fictifs/g, "Profils d'exemple")
    .replace(/profils fictifs/g, "profils")
    .replace(/[Pp]rofil fictif /g, (x) => (x[0] === "P" ? "Profil " : "profil "))],
];
