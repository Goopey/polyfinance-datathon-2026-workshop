/**
 * Génère `contracts.schema.json` (schéma JSON) depuis `src/types/contracts.ts`.
 *
 * Ce fichier est la référence commune du contrat mobile ↔ backend :
 *   - mobile/tests/ vérifie que le serveur fictif le respecte ;
 *   - backend/tests/api/ vérifie que l'API réelle le respecte.
 * Un champ ajouté d'un seul côté fait donc échouer un test.
 *
 *   node scripts/contracts-schema.mjs           écrit le fichier
 *   node scripts/contracts-schema.mjs --check   échoue si le fichier n'est plus à jour
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createGenerator } from "ts-json-schema-generator";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const SCHEMA_PATH = resolve(root, "contracts.schema.json");

function sortKeys(value) {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((k) => [k, sortKeys(value[k])]));
  }
  return value;
}

export function buildSchema() {
  const schema = createGenerator({
    path: resolve(root, "src/types/contracts.ts"),
    tsconfig: resolve(root, "tsconfig.json"),
    type: "*",
    expose: "export",
    skipTypeCheck: true,
    additionalProperties: false, // un champ inconnu du contrat est une erreur
    topRef: true,
  }).createSchema("*");
  return `${JSON.stringify(sortKeys(schema), null, 2)}\n`;
}

const isMain = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const next = buildSchema();
  if (process.argv.includes("--check")) {
    let current = "";
    try {
      current = readFileSync(SCHEMA_PATH, "utf8").replace(/\r\n/g, "\n");
    } catch {
      /* fichier absent */
    }
    if (current !== next) {
      console.error("contracts.schema.json n'est plus à jour : lancer `npm run contracts`.");
      process.exit(1);
    }
    console.log("contracts.schema.json à jour.");
  } else {
    writeFileSync(SCHEMA_PATH, next);
    console.log(`Écrit : ${SCHEMA_PATH}`);
  }
}
