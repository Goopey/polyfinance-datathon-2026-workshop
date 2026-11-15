/**
 * Parcours complet de bout en bout dans un navigateur, avec clics réels.
 *
 *   npm run e2e:mock   application sur les données fictives (aucun backend)
 *   npm run e2e:api    application branchée sur l'API réelle (FastAPI lancé par ce script)
 *
 * Le script : exporte la version web, la sert en local, lance l'API si besoin, puis déroule le
 * parcours. Il échoue à la première attente non satisfaite, sur toute erreur de console et sur
 * toute réponse HTTP en erreur : un écart de contrat entre le mobile et le backend (preuve
 * introuvable, champ absent) se voit donc ici.
 *
 * E2E_SHOTS=<dossier existant> enregistre une capture d'écran par étape.
 * E2E_HEIGHT=<pixels> agrandit la fenêtre (900 par défaut) pour capturer une page entière.
 *
 * Prérequis : Chrome ou Edge (variable CHROME_PATH pour un autre emplacement) ; en mode api,
 * l'environnement Python du backend (variable EASYTRADE_PYTHON, sinon backend/.venv, sinon `python`).
 */
import { spawn, spawnSync } from "node:child_process";
import { existsSync, readFileSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer-core";

const MODE = process.argv.includes("--api") ? "api" : "mock";
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const BACKEND = resolve(ROOT, "../backend");
const DIST = resolve(ROOT, "dist", `e2e-${MODE}`);
const WEB_PORT = 8766;
const API_PORT = 8765;
const WEB = `http://localhost:${WEB_PORT}`;
const API = `http://localhost:${API_PORT}`;
const isWindows = process.platform === "win32";

function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
  ].filter(Boolean);
  const found = candidates.find((p) => existsSync(p));
  if (!found) throw new Error("Chrome introuvable : définir CHROME_PATH.");
  return found;
}

function findPython() {
  if (process.env.EASYTRADE_PYTHON) return process.env.EASYTRADE_PYTHON;
  const venv = join(BACKEND, ".venv", isWindows ? "Scripts/python.exe" : "bin/python");
  return existsSync(venv) ? venv : "python";
}

async function waitFor(url, label, timeoutMs = 60000) {
  const until = Date.now() + timeoutMs;
  for (;;) {
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      /* pas encore prêt */
    }
    if (Date.now() > until) throw new Error(`${label} ne répond pas (${url})`);
    await new Promise((r) => setTimeout(r, 300));
  }
}

const MIME = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css",
  ".png": "image/png", ".ico": "image/x-icon", ".svg": "image/svg+xml", ".ttf": "font/ttf", ".map": "application/json" };

/** Serveur statique avec repli sur index.html (application à page unique). */
function serveStatic(dir, port) {
  const server = createServer((req, res) => {
    const path = decodeURIComponent(new URL(req.url, WEB).pathname);
    let file = join(dir, path);
    if (!file.startsWith(dir) || !existsSync(file) || statSync(file).isDirectory()) file = join(dir, "index.html");
    res.writeHead(200, { "Content-Type": MIME[extname(file)] ?? "application/octet-stream" });
    res.end(readFileSync(file));
  });
  return new Promise((ok) => server.listen(port, () => ok(server)));
}

// ---------------------------------------------------------------------------------------------
const children = [];
let browser;
let webServer;
async function cleanup() {
  if (browser) await browser.close().catch(() => {});
  if (webServer) webServer.close();
  for (const child of children) {
    if (isWindows) spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"]);
    else child.kill("SIGTERM");
  }
}

async function main() {
  console.log(`Parcours de bout en bout — mode ${MODE === "api" ? "API réelle" : "données fictives"}`);

  // 1. Export web de l'application, configuré pour le mode choisi.
  const env = { ...process.env, EXPO_PUBLIC_USE_MOCKS: MODE === "api" ? "false" : "true", EXPO_PUBLIC_API_URL: API, CI: "1" };
  const exported = spawnSync(`npx expo export --platform web --output-dir "${DIST}" --clear`,
    { cwd: ROOT, env, shell: true, encoding: "utf8" });
  if (exported.status !== 0) throw new Error(`Export web en échec :\n${exported.stdout}\n${exported.stderr}`);
  console.log("✓ Export web");
  webServer = await serveStatic(DIST, WEB_PORT);

  // 2. API réelle (FastAPI), sur les données du dépôt, agents simulés.
  if (MODE === "api") {
    const api = spawn(findPython(), ["-m", "uvicorn", "easytrade.api.app:app", "--port", String(API_PORT), "--log-level", "warning"],
      { cwd: BACKEND, env: { ...process.env, PYTHONIOENCODING: "utf-8" }, stdio: ["ignore", "inherit", "inherit"] });
    children.push(api);
    await waitFor(`${API}/health`, "L'API");
    console.log("✓ API démarrée");
  }

  // 3. Navigateur.
  browser = await puppeteer.launch({ executablePath: findChrome(), headless: true, args: ["--window-size=430,900"] });
  const page = await browser.newPage();
  await page.setViewport({ width: 430, height: Number(process.env.E2E_HEIGHT) || 900 });
  const problems = [];
  page.on("console", (m) => { if (m.type() === "error") problems.push(`console : ${m.text()}`); });
  page.on("pageerror", (e) => problems.push(`exception : ${e}`));
  page.on("response", (r) => { if (r.status() >= 400) problems.push(`HTTP ${r.status()} : ${r.url()}`); });
  page.on("requestfailed", (r) => problems.push(`requête échouée : ${r.url()} (${r.failure()?.errorText})`));

  const sel = (t) => `::-p-text(${t})`;
  async function visible(t, timeout = 30000) {
    const until = Date.now() + timeout;
    while (Date.now() < until) {
      for (const el of await page.$$(sel(t))) {
        const box = await el.boundingBox();
        if (box && box.width > 0 && box.height > 0) return el;
      }
      await new Promise((r) => setTimeout(r, 150));
    }
    throw new Error(`Texte attendu absent de l'écran : « ${t} »\n${problems.join("\n")}`);
  }
  const click = async (t) => (await visible(t)).click();
  const absent = async (t) => {
    for (const el of await page.$$(sel(t))) {
      const box = await el.boundingBox();
      if (box && box.width > 0) throw new Error(`Texte inattendu à l'écran : « ${t} »`);
    }
  };
  // E2E_SHOTS=<dossier> : enregistre une capture d'écran à chaque étape (revue visuelle).
  const shots = process.env.E2E_SHOTS;
  let n = 0;
  const step = async (s) => {
    console.log(`✓ ${s}`);
    if (shots) await page.screenshot({ path: join(shots, `${MODE}-${String(++n).padStart(2, "0")}.png`), fullPage: true });
  };
  const go = (path) => page.goto(`${WEB}${path}`, { waitUntil: "networkidle0" });

  const tested = MODE === "api" ? "Tesla" : "Société médiatisée fictive G";

  await go("/");
  await visible("Choisissez votre profil d'investisseur");
  await absent("Simulation — aucune transaction réelle");
  if (MODE === "api") await absent("Démo");
  else await visible("Démo");
  await click("EN");
  await visible("Choose your investor profile");
  await visible("Low to moderate risk");
  await absent("Faible à modéré");
  await step("Accueil en anglais : sélecteur de langue en haut à droite");
  await click("FR");
  await visible("Choisissez votre profil d'investisseur");
  await step("Accueil : choix du profil d'investisseur");

  await click("Robert, 59 ans");
  await visible("Voici comment nous avons compris");
  await visible("Aucun cryptoactif.");
  await step("Résumé du profil Robert : règles et poids");
  await click("Confirmer et voir les pistes");
  await visible("pistes cohérentes avec votre profil");
  await absent("Pourquoi ? Voir la fiche");
  await step("Pistes à explorer");
  await click("Écartées et pourquoi");
  await visible("Écartées par une règle de votre profil");
  await step("Écartées et pourquoi");

  await page.click('[aria-label^="Ouvrir la fiche de"]');
  await visible("Pourquoi cette piste");
  await visible("Risque observé");
  await visible("Débat Bull / Réaliste / Bear");
  await visible("Pourquoi ce classement");
  await step("Fiche : raisons, risque, débat, contributions");
  // Tout bascule en anglais, données du backend comprises.
  await click("EN");
  await visible("Why this idea");
  await visible("Observed risk");
  await visible("Why this ranking");
  if (MODE === "api") {
    for (const fr of ["Volatilité annualisée observée", "Rendement annualisé observé", "toute la période disponible", "Appui"]) await absent(fr);
  }
  await step("Fiche en anglais : interface et textes du backend traduits");
  await click("FR");
  await visible("Pourquoi cette piste");
  await click("Source");
  await visible("Traitement");
  await visible("Publiée :");
  if (MODE === "api") await visible("Yahoo Finance via yfinance");
  await step("Preuve ouverte depuis une pastille de source");
  await click("Parcours de l'analyse");
  await visible("Contrôles de gouvernance");
  await visible("Contrôle avant l'affichage");
  await visible("Moteur de décision");
  await step("Parcours de l'analyse : étapes et contrôles");

  await go("/tester");
  await visible("Un titre vous fait envie ?");
  await page.click(`[aria-label="Tester ${tested}"]`);
  await visible("Incohérent avec le profil");
  await visible("Tensions avec le profil");
  await visible("Effet sur votre panier");
  await step(`Tester une idée : Robert + ${tested} → incohérent, tensions chiffrées, effet sur le panier`);
  await click(`Voir la fiche de ${tested}`);
  await visible("Risque observé");
  await visible("Au-delà de votre seuil");
  if (MODE === "api") {
    // Données réelles : cours, sentiment Finnhub et graphe des sociétés comparables.
    await visible("Cours observés");
    await visible("Sentiment du marché");
    await visible("Écosystème de la société");
    await visible("Concurrent");
  }
  await step("Fiche du titre testé : repères du profil dépassés, cours, sentiment, graphe");

  await go("/donnees");
  await visible("Contrôles qualité");
  await visible("Aucune preuve publiée après");
  await step("Données : sources, contrôles qualité, chronologie des preuves");

  await go("/comparer");
  await visible("Règles appliquées");
  await step("Comparer deux profils");

  await go("/profil");
  await click("Avancé");
  await click("Changer de profil");
  await click("Créer mon propre profil");
  await click("Préserver le capital"); await click("Suivant");
  await click("Moins de 5 ans"); await click("Suivant");
  await click("Je serais très inquiet"); await click("Suivant");
  await click("Ne pas tout miser sur un seul secteur"); await click("Suivant");
  await click("Placements hautement spéculatifs");
  await click("Voir mon profil");
  await visible("Voici comment nous avons compris");
  await visible("Écarter les placements hautement spéculatifs.");
  await step("Questionnaire → profil, exclusion devenue une règle");
  await click("Confirmer et voir les pistes");
  await visible("pistes cohérentes avec votre profil");
  await step("Analyse du profil créé");

  if (MODE === "api") {
    await go("/profil");
    await click("Changer de profil");
    await click("Mateo, 41 ans");
    await click("Confirmer et voir les pistes");
    await visible("Aucune piste à explorer pour ce profil");
    await visible("Le critère le plus important de votre profil (ESG");
    await absent("Aucune recommandation :");
    await visible("Ajuster les poids");
    await step("Mateo : « aucune recommandation » (ESG non sourcé), raison claire, actions proposées");
    await click("Voir les pistes sans le critère ESG");
    await visible("pistes cohérentes avec votre profil", 60000);
    await step("Mateo sans le critère ESG : pistes affichées, poids réparti");
  }

  if (problems.length) throw new Error(`Erreurs relevées pendant le parcours :\n${problems.join("\n")}`);
  console.log("Aucune erreur de console ni réponse HTTP en erreur.");
}

main()
  .then(async () => {
    await cleanup();
    console.log("PARCOURS RÉUSSI");
    process.exit(0);
  })
  .catch(async (error) => {
    await cleanup();
    console.error(`PARCOURS EN ÉCHEC\n${error.message}`);
    process.exit(1);
  });
