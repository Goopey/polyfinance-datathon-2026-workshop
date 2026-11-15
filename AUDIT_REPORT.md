# Independent audit: EasyTrade (AlphaForge AI Datathon 2026)

Audit date: 2026-11-15, repository at commit `7e49732` plus uncommitted working-tree changes. Application code was **not modified** for this audit. All audit material is in `audit/`:

| File | Purpose |
|---|---|
| `audit/test_independent_metrics.py` | Recomputes every financial metric from the raw CSVs with the Python standard library only, for all 31 assets, and compares with the backend. Includes analytic examples and point-in-time checks. |
| `audit/test_suitability_and_agents.py` | Behavioural tests: hard constraints, suitability, internal consistency, debate, numeric faithfulness of claims. |
| `audit/probe_suitability.py` | Runs the real pipeline for the 3 official personas plus 8 adversarial or variant profiles. Raw output goes to `audit/out/suitability.json`. |

Run everything from `backend/`:

```
PYTHONPATH=. .venv/Scripts/python.exe -m pytest ../audit -q -p no:cacheprovider
PYTHONPATH=. .venv/Scripts/python.exe ../audit/probe_suitability.py
```

**Result: 46 audit tests, 38 pass, 8 fail.** Every failure is a real defect reproduced on the actual pipeline. Existing project suites were also run today: backend `pytest` 283 passed / 1 skipped (S2 ESG), mobile `npm test` 29 passed, browser end-to-end flows on the real API and on demo data passed.

## Scope limits (read first)

- **AWS was not exercised.** There are no credentials or deployed API URL on this machine. Everything was run locally with the **rule-based simulated agents** (`agents/simulated.py`), which is what the local API uses by default. Statements about Bedrock, IAM, timeouts and cost come from code and infrastructure inspection only. The cost (≈ $0.35 per analysis) and latency (≈ 2 min on AWS) figures are the team's own (`avancement.md`); I did not verify them.
- The debate findings in section 4 describe the simulated agents. A Bedrock-backed debate may behave differently. That has **not** been tested here, and it is the main open question for the demo.
- The installed financial-services skills are report-writing workflows that rely on paid data connectors (FactSet, S&P, LSEG and others). None applies to a code audit, so none was invoked. The equity-research norms they encode (suitability, risk disclosure, catalysts) informed sections 2 and 3.

---

## 1. Executive assessment

**The financial arithmetic is correct. The suitability logic built on top of it is not yet trustworthy.**

- **Verified:** returns, volatility, drawdown, rolling windows, USD→CAD conversion and point-in-time filtering match an independent recomputation to 1e-6 for all 31 assets. Hard rules (no crypto, speculative exclusion) cannot be overridden. Every number quoted by the agents traces to a cited evidence record. Recommending nothing works.
- **Not trustworthy:**
  - The system largely ignores the investor's **objective** and **horizon**.
  - It **does not enforce risk tolerance** in its ranking.
  - Two of its own features can **contradict each other** on the same profile and stock.
  - The three official personas receive **near-identical recommendations**.
- **The Bull / Realist / Bear debate is not independent analysis** in its current (simulated) form. It is a deterministic restatement of threshold checks on the same five metrics, and by design it never changes the ranking.

None of this is visible in the existing test suite, because those tests check that things run and that numbers are internally consistent, not that the recommendations are suitable.

## 2. Severity ranking

| # | Severity | Finding | Reproduced |
|---|---|---|---|
| C1 | **Critical** | Investment objective and horizon have no effect on questionnaire profiles. The horizon criterion is identical for every investor. | Yes (tests fail) |
| C2 | **Critical** | Risk tolerance is never enforced in the ranking. A weight change makes a 51 %-volatility stock the #1 "high fit" idea for a low-to-moderate-risk retiree, while "Test an idea" calls the same stock "inconsistent with the profile". | Yes (3 tests fail) |
| H1 | High | The official personas are not differentiated: all 7 of Amira's ideas are among Robert's 10, and GLD appears for 9 out of 9 profiles. | Yes (test fails) |
| H2 | High | The debate is not independent: Bull supports 100 % of assets, the Realist never opposes, 77 % of items are flagged "disagreement", and the ranking is unaffected by construction. | Yes (2 tests fail) |
| H3 | High | "Diversification" means sector rarity inside a hand-picked list of 31 assets, not correlation. Correlation code exists but is unused, and ETF overlaps are ignored. | Inspection plus probe |
| H4 | High | The deployed API has no authentication or throttling, CORS `*`, and every new profile or analysis triggers paid Bedrock calls. | Inspection only |
| H5 | High | One invalid model answer for one agent on one stock fails the whole analysis (0 ideas). | Yes (fake client) |
| M1 | Medium | Recommendations are produced from 3.5 months of history (30-return minimum, annualized), and analysis dates in the future are accepted. | Yes |
| M2 | Medium | "Return in 2022" is year-to-date when the analysis date falls inside 2022. | Yes |
| M3 | Medium | Liquidity needs and risk capacity (age, retirement, dependants) are not modelled; risk tolerance is the only risk input. | Inspection |
| M4 | Medium | Mateo, one of the three official personas, always gets "no recommendation" (ESG not sourced; scenario S2 skipped). | Yes |
| M5 | Medium | The fit labels ("high / partial") are relative ranks within the eligible list, not absolute suitability. | Inspection |
| M6 | Medium | On AWS, `GET /profiles/{id}` calls Bedrock synchronously behind a 29 s API Gateway limit, with a 300 s read timeout and retries. | Inspection |
| L1 | Low | The price chart headline shows an *adjusted* close converted to CAD as if it were the traded price. | Inspection |
| L2 | Low | The Bedrock IAM policy allows any foundation model in any region. | Inspection |
| L3 | Low | Currency-conversion timing nuances (Bank of Canada fixing time; crypto weekends use Friday's rate). | Inspection |
| L4 | Low | The English translation of backend text relies on fixed templates; free-form Bedrock text would stay in French. | Inspection |

---

## 3. Critical financial and suitability errors

### C1. Objective and horizon are ignored; the "horizon" criterion is the same for everyone

**What is wrong**
- Questionnaire profiles take their weights and constraints from a template chosen **only by risk tolerance** (`backend/easytrade/api/service.py:75` `TEMPLATE_BY_TOLERANCE`, then `:275` and `:283`).
- The objective (`:297`) and the horizon (`:276`) are only copied into profile text. The simulated weighting agent does not shift weights for them.
- The "horizon" criterion is the worst rolling **3-year** return for every investor (`backend/easytrade/engine/signals.py:36`). A 15-year investor and a 3–5-year investor are measured the same way. Only the weight changes, and it is 0.10 for both Amira and Robert.

**Evidence** (`audit/out/suitability.json`):
- "Preserve capital, under 5 years, high tolerance" receives **exactly** the weights and the 7 ideas of "Grow capital, 12+ years, high tolerance". These include GOOGL (32 % volatility, −39.5 % drawdown) and no bonds.
- "Preserve, under 5 years, low" and "Preserve, 12+ years, low" produce identical weights and identical ideas.

**Reproduce:** `test_horizon_change_le_resultat` and `test_objectif_contradictoire_pris_en_compte` fail.

**Why it matters:** the brief is about personalised suitability. A judge who answers the questionnaire twice with different horizons will see no difference. A contradictory profile (preserve capital, short horizon, high tolerance) is not even questioned. The brief explicitly expects incoherent requests to be challenged (Robert's test).

**Correct behaviour**
- Horizon should change what risk is acceptable, for example the drawdown benchmark and the rolling window, which should be the investor's horizon rather than always 3 years.
- Objective should shift weights; "preserve" should raise stability.
- A contradiction between objective, horizon and tolerance should be flagged, and the most conservative reading applied.

**Fix:** derive weights from all three answers, with an explicit table documented in `docs/03_DECISION_ENGINE.md`. Make the horizon criterion use a window equal to the investor's horizon. Add a "conflicting answers" check in `profile_weighting`.

### C2. Risk tolerance is not a constraint, and two features contradict each other

**What is wrong:** the per-tolerance benchmarks (`backend/easytrade/engine/coherence.py:124-129`: volatility 22 %, drawdown −25 % for "low to moderate") are used only by "Test an idea" and for display on the stock sheet. Screening (`engine/constraints.py:41-85`) and scoring never use them, so they can only lower a weighted score.

**Evidence**
- **Robert, unchanged:** GOOGL (32.3 % volatility, −39.5 % drawdown) and QQQ (22.8 %, −32.1 %) are among his 10 ideas, breaching **both** of his benchmarks.
- **Robert after a weight change on the summary screen** (growth up, stability to 0), an action available in the app: NVDA is the **#1 idea with "high fit"** at 51 % volatility and −63.5 % drawdown. 7 of his 10 ideas breach a benchmark.
- **The contradiction:** for that same profile, "Test an idea" on NVDA returns **"Inconsistent with the profile"**.

**Reproduce:** `test_profil_prudent_sans_piste_hors_reperes`, `test_variante_de_poids_ne_contourne_pas_la_tolerance` and `test_classement_et_tester_une_idee_coherents` fail.

**Why it matters:**
- **Suitability:** a near-retiree with low-to-moderate tolerance must not receive a highly volatile single stock as the top suitable idea.
- **Internal consistency:** the contradiction between the two features is easy for a judge to stumble on.

**Correct behaviour:** risk tolerance is a hard bound on the ranked ideas. Either exclude anything beyond a severity multiple of the benchmark (the code already defines `SEVERE_RATIO = 1.5`), or cap the fit label at "low" and keep it out of the selected ideas. Weights should rank *within* what tolerance allows, never override it.

**Fix:** add a tolerance screen in `engine/constraints.py` using `RISK_LIMITS` and the validated volatility and drawdown metrics, with a "set aside by your risk tolerance" rejection reason. Reuse the same function in `coherence.py`, so the ranking and "Test an idea" cannot disagree. Add these audit tests to the project suite.

---

## 4. Investor suitability failures

### H1. The official personas are not differentiated

**Evidence:**
- Amira (high risk, 15+ years, interested in AI and crypto) gets ESGV, GLD, GOOGL, JNJ, QQQ, SPY, XIU.TO. **All seven** are also in the list of Robert (low-to-moderate risk, 3–5 years, near retirement). Robert's list adds only three bond ETFs.
- GLD is recommended to **9 of 9** profiles that received ideas, from "preserve capital" to "aggressive growth", with "high confidence" for the growth profiles.

**Reproduce:** `test_profils_officiels_differencies` fails. The project's own S12 test passes because it only checks that the *order* differs.

**Why it matters:** this is the main demo story ("the system adapts to the investor"), and the sets show it barely does.

**Root causes:**
1. Percentile ranking across one mixed universe of bonds, gold, stocks and crypto. The same safe, high-ranked assets score well for everyone.
2. The diversification proxy (H3) systematically boosts single-asset sectors such as Gold.
3. Amira's interest in crypto is outweighed: BTC is even labelled "inconsistent" for her, because its 50 % volatility exceeds the 45 % "high" benchmark.

**Fix:**
- Rank within each asset class and build the list with class-level targets per profile (for example, bonds for short horizons).
- Make Amira's stated themes (technology, crypto within a 15 % cap) count enough to surface them.
- Replace the diversification proxy (H3).
- Add an S12 test on set overlap, not order.

### M3. Liquidity and risk capacity are not modelled

`grep` finds no liquidity or capacity concept anywhere in `backend/easytrade`. Robert's "considering retirement in the coming years" (`data/reference/personas.json:101`) and Mateo's two children are never used. Risk **tolerance** (attitude) is the only input, so risk **capacity** (ability to absorb losses) and liquidity needs are absent. Judges from finance will ask about this. **Fix:** add capacity and liquidity fields (the questionnaire can derive them from horizon and situation) and let them tighten the risk bounds from C2.

### M4. Mateo always gets "no recommendation"

This follows the team's rule "the most important criterion has no data → no recommendation" (`engine/decision.py:105-120`). Behaviour matches the documentation, but one of the three official personas produces nothing. The app now offers "See ideas without the ESG criterion", a user-chosen workaround. ESG remains unsourced, and scenario S2 (`backend/tests/scenarios/test_s02_mateo_esg.py`) is skipped.

### What passed

- Hard rules cannot be overridden: a crypto ban survives extreme weight changes (`test_contraintes_dures_resistent_aux_poids`), and negative weights are rejected.
- The system can say no: Mateo returns no ideas, and an analysis dated 2019 (before any data) returns no ideas.
- An unknown stock or profile returns a clean "not found".

---

## 5. Agent reasoning and hallucination risks

### H2. The debate does not provide independent analysis (simulated agents)

**Evidence:**
- **Bull** stance: support whenever the past 5-year return is above 0 (`agents/simulated.py:173`). It **cannot oppose**, and every asset in this survivor-biased universe went up. Measured: 78/78 support.
- **Realist:** support 53, support with caveats 25, **opposition 0**.
- **Bear:** opposes only when a risk benchmark is exceeded. That is the same check as "Test an idea", restated.
- **Templates:** across all 105 harvested analyses there are only **11 distinct argument templates**.
- **"Disagreement":** flagged whenever the three stances aren't identical (`schemas/debate.py:73-75`). A Bear "support with caveats" therefore counts as disagreement: 60 of 78 items (77 %) show "disagreement kept", which makes the badge meaningless.
- **Ranking:** the debate cannot change the ranking by design (`engine/decision.py:177-202`, "without touching the scores"). A single-agent baseline (the decision engine alone) produces the **same ranking and the same set of ideas**. The debate only lowers confidence labels and sets the "to review" flag.

**Reproduce:** `test_le_bull_peut_s_opposer_ou_reserver` and `test_desaccord_signifie_une_opposition` fail.

**Why it matters:** judges will ask what the multi-agent architecture adds. Today, locally, the answer is "nothing a few if-statements don't already do". The UI says so honestly in "what we don't know", but the badge shown on most cards overstates the debate.

**Correct behaviour and fix:**
- Show "disagreement" only when at least one agent opposes.
- Give each agent different evidence emphasis or tools (the Bear could get drawdown episodes, correlation with the portfolio, sentiment and concentration; the Bull could get quality and momentum).
- Let a sustained Bear opposition tied to a profile rule demote an idea out of the selected set, not just flag it.
- Demonstrate the Bedrock debate on recorded runs.

### What passed: faithfulness

`test_chiffres_des_affirmations_issus_des_preuves` checked every percentage quoted in the "why" and debate claims for Amira and Robert (more than 50 numbers). Each matches a value in the evidence it cites. No fabricated citation was found. This complements the team's own scenario S6.

### Investment-research weaknesses

| Issue | Type | Detail |
|---|---|---|
| Past returns drive "growth" | Debatable assumption | The growth criterion is the percentile of the raw 5-year annualized return, with no risk adjustment (no Sharpe or Sortino; neither is implemented). Rewards what went up in 2021–2026 in a universe picked in 2026. The limits text discloses survivorship bias. |
| Cross-asset comparison | Design weakness | Bonds, gold, broad ETFs, single stocks and crypto are ranked against each other on the same percentile scales (see H1). |
| "Sector rarely represented in the universe" shown as a *reason to invest* | Misleading claim | It describes the composition of the 31-asset list, not the investor's portfolio (see H3). |
| Missing risk factors | Gap | No interest-rate sensitivity (TLT returned −26.5 % in CAD in 2022, recomputed), no valuation, no concentration through ETF holdings, no liquidity. Macro series are loaded with correct publication lags (`data/loaders.py:74`, `data/point_in_time.py:28`), but nothing in `engine/` uses them. |
| Upcoming events | Data gap | No earnings calendar, news or filings source is connected (`agents/tools.py`). The app correctly shows nothing. |

### H3. "Diversification" is sector rarity inside the universe

`engine/signals.py:64-70` scores diversification as minus the number of assets sharing the sector *in the 31-asset list*. GLD and any one-of-a-kind sector always score highest, regardless of what the investor already holds. `validation/metrics.py:309` (`correlation_metric`) and `validation/risk.py` (`correlation_matrix`) exist but are never called. Look-through overlap is ignored: Robert's ideas include SPY, QQQ, ESGV and XIU.TO. Three of these funds (SPY, QQQ, ESGV) hold GOOGL, which is also recommended separately. The team labels this a proxy, but it is shown as a reason on cards. **Fix:** score diversification as the reduction in the volatility of the equal-weight basket of selected ideas (the basket-volatility function already exists), or as average correlation to the ideas already selected.

---

## 6. Technical defects and security concerns

### H4. Public, unauthenticated, unthrottled API that triggers paid model calls (inspection)

- `infra/stacks/api_stack.py:50-55`: an HTTP API with CORS `allow_origins=["*"]`, and no authorizer, API key, usage plan or throttling anywhere in `infra/stacks`.
- `POST /profiles` with any weight variant creates a new profile. Each new profile's analysis is a new Step Functions execution with Bedrock calls; the team reports about $0.35 each. The deterministic run ID only de-duplicates identical requests.
- `GET /profiles/{id}` also invokes Bedrock (`api_stack.py:48`).
- The local API defaults CORS to `*` as well (`backend/easytrade/api/app.py:35-36`).

**Why it matters:** anyone with the URL (it ships in the app bundle) can run up the Bedrock bill or exhaust quotas during judging. **Fix:** set stage throttling on the HTTP API, add an API key or a simple shared secret for the demo, restrict CORS to the hosted web origin, and set a budget alarm.

### H5. One bad model answer fails the whole analysis (reproduced)

A fake model client that returns invalid output for the Bear on GLD only, with every other call normal, produces `status: echec`, `LLMOutputError : Étape debate.bear.round1 : sortie invalide après 2 essais`, and **0 ideas**. Cause: `orchestration/pipeline.py:645-648` re-raises any debate error, after `MAX_ATTEMPTS = 2` (`agents/llm_client.py:29`). With about 10 candidates × 3 agents × 2 rounds per analysis, a single failure is likely enough to matter on real models. **Fix:** treat a failed debate turn as "no supported argument" for that agent on that candidate, record it in the trace, lower that idea's confidence, and continue. Keep failing the run only if most turns fail.

### M6. Synchronous Bedrock call behind a 29-second gateway (inspection)

The API Lambda has `timeout=29s` (`api_stack.py:40`). The Bedrock client uses `read_timeout=300` and 3 botocore retries (`llm_client.py:212-213`), plus one application retry. A slow profile-weighting call will surface as a gateway timeout rather than a clean error. **Fix:** set the client timeout below about 20 s in the API Lambda, or precompute and cache profile weights (they are deterministic per profile).

### M1. Thin and future history accepted

- `POST /runs` accepts any `as_of` (`schemas/api.py:82`).
- With `as_of=2022-03-01` (74 observations) the system returns 10 "consistent" ideas, with fit "high" on several. The annualized returns are extrapolated from 3.5 months (XBB.TO "−2.7 % annualized"). The minimum is 30 returns (`config.py:60`).
- `as_of=2030-01-01` is accepted and served with data ending in 2026 (stale prices presented as current).

**Fix:** require at least one year for annualized metrics, and the full horizon window for the horizon criterion. Reject `as_of` later than the last available data or before the start plus one year.

### M2. "Return in 2022" mislabelled for in-year dates

`validation/metrics.py:216-218` computes from 2021-12-31 to `min(2022-12-31, as_of)`, so at `as_of=2022-03-01` the label "Rendement sur l'année 2022" is a 2-month year-to-date figure (−1.1 % for XIU.TO). **Fix:** omit the metric unless `as_of ≥ 2022-12-31`, or label it year-to-date.

### Low-severity items

- **L1:** the chart headline (`mobile/src/components/PriceChart.tsx:59`) shows the dividend-adjusted close converted to CAD as "the price". The explanatory note was removed during the recent UI clean-up. Label it "adjusted price, CAD".
- **L2:** `infra/stacks/pipeline_stack.py:39-47` grants `bedrock:InvokeModel` on `foundation-model/*` in every region. Narrow it to the two configured model IDs and region.
- **L3:** USD prices use the same-day Bank of Canada rate (published around 16:30 ET, after the U.S. close). Crypto weekend rows reuse Friday's rate, so foreign-exchange moves land on Mondays. The effect on volatility is small, and the choice is documented in the evidence limits.
- **L4:** the English translation of backend text (`mobile/src/i18n/dataRules.ts`) covers all 2,034 strings the simulated backend emits (`mobile/tests/dataTranslation.test.ts`). Free-form Bedrock wording would fall back to French.

### Security checks that passed

No secrets in tracked files or git history (patterns: AWS access keys, secret keys, Finnhub key, Anthropic key, private keys). `.env` is git-ignored. AWS access is through Lambda roles, with no keys in code. Inputs are validated: unknown ticker or profile returns 404, negative weights return 422, and questionnaire answers are closed lists. Nothing executes user-provided text.

---

## 7. Verified strengths

| Claim | How it was verified |
|---|---|
| Annualized return, volatility (sample standard deviation, √252 or √365), maximum drawdown, worst rolling 1- and 3-year returns, and 2022 return are correct for all 31 assets. | Independent standard-library recomputation, `test_indicateurs_recalcules` × 31, tolerance 1e-6. |
| Formulas are right on known analytic cases (constant growth, alternating ±10 %, known drawdowns). | `test_exemples_analytiques`. |
| USD→CAD conversion never uses a future exchange rate. | Independent backward-lookup implementation gives identical metrics. |
| No look-ahead: metrics at past dates use only data up to that date; dividend back-adjustment cancels out in returns. | `test_aucune_donnee_posterieure` (2023-06-30, 2024-12-31). |
| Hard rules cannot be overridden by weights. | `test_contraintes_dures_resistent_aux_poids`. |
| Every number in agent claims matches cited evidence. | `test_chiffres_des_affirmations_issus_des_preuves`. |
| "No recommendation" is a working output. | Mateo; analysis dated 2019. |
| Deterministic and reproducible; full traceability (evidence registry with three dates, analysis trail). | Repeated runs are identical; existing scenarios S5, S9 and S6 pass. |

## 8. Issues most likely to cost points with judges (in demo order)

1. **"Show me how Amira's and Robert's results differ."** All 7 of Amira's ideas are in Robert's list (H1).
2. **Robert adjusts his weights.** NVDA becomes his #1 "high fit" idea, then "Test an idea" says NVDA is inconsistent with his profile (C2).
3. **Changing the horizon in the questionnaire changes nothing** (C1).
4. **"What does the debate add?"** The ranking is identical without it, the Bull never disagrees, and "disagreement" shows on most cards (H2).
5. **Mateo gets no recommendation** (M4). This is defensible if presented as intentional, but ESG remains the persona's whole point.
6. **"Gold for everyone"**: GLD is in every list (H1, H3).
7. **Public API without throttling** while judges have the URL (H4).

## 9. Recommended fixes, ranked

1. **Enforce risk tolerance as a screen** and share it between the ranking and "Test an idea" (C2). This fixes three failing tests and the most visible contradiction.
2. **Make objective and horizon matter**: weights table, horizon-length window, contradiction flag (C1).
3. **Replace the diversification proxy** with the effect on portfolio volatility or correlation, using the existing functions (H3). This should also reduce the "gold for everyone" and persona-overlap effects (H1).
4. **Rank within asset classes and add per-profile class targets**, then test set overlap between personas (H1).
5. **Throttle and protect the deployed API**, restrict CORS, set a budget alarm (H4).
6. **Degrade gracefully on model failures** in the debate (H5).
7. **Redefine "disagreement"** as at least one opposition, and give the agents differentiated evidence. Demonstrate Bedrock runs (H2).
8. **Minimum history and `as_of` validation**, and the year-to-date label (M1, M2).
9. **Model liquidity and risk capacity** (M3), and source ESG for Mateo (M4).
10. **Small fixes:** price label (L1), IAM scope (L2), API Lambda timeout (M6).

## 10. Unresolved limitations of this audit

- Bedrock agents, Step Functions, DynamoDB, S3 and the deployed API were not executed (no credentials).
- Cost and latency were not measured.
- Live market data was not re-downloaded. All checks use the frozen starter dataset (2021-11-12 to 2026-11-12) and the team's Finnhub snapshots.
- Sentiment and quality data were checked for point-in-time logic by inspection only; their values were not recomputed against Finnhub.
