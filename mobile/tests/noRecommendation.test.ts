/** État « Aucune recommandation » : raison affichée sans préfixe redondant, critère bloquant reconnu. */
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { translateData } from "../src/i18n/translate";
import { blockingCriterion, stripNoRecoPrefix } from "../src/noRecommendation";

// Texte réel de l'API pour Mateo (engine/decision.py).
const MATEO = "Aucune recommandation : le critère le plus important de votre profil (ESG, 25 %) n'a aucune donnée "
  + "à cette date (signaux ESG non encore sourcés).";

describe("aucune recommandation", () => {
  it("retire le préfixe et met une majuscule", () => {
    assert.equal(stripNoRecoPrefix(MATEO).slice(0, 30), "Le critère le plus important d");
    assert.equal(stripNoRecoPrefix("Preuves insuffisantes."), "Preuves insuffisantes.");
  });

  it("reconnaît le critère bloquant", () => {
    assert.equal(blockingCriterion(MATEO), "esg");
    assert.equal(blockingCriterion(MATEO.replace("ESG, 25", "qualité, 30")), "qualite");
    assert.equal(blockingCriterion("Aucun actif de l'univers ne passe les contraintes dures de votre profil."), null);
  });

  it("note de trace « Aucun candidat à débattre » (préfixe retiré par le backend) traduite", () => {
    const note = `Aucun candidat à débattre : ${MATEO.replace("Aucune recommandation : ", "")}`;
    assert.equal(
      translateData(note, "en"),
      "No candidate to debate: your profile's most important criterion (ESG, 25%) has no data as of this date (ESG signals not sourced yet).",
    );
  });

  it("la raison sans préfixe se traduit en anglais", () => {
    assert.equal(
      translateData(stripNoRecoPrefix(MATEO), "en"),
      "Your profile's most important criterion (ESG, 25%) has no data as of this date (ESG signals not sourced yet).",
    );
  });
});
