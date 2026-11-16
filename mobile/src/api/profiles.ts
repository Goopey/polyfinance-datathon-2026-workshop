/**
 * GET /personas, POST /profiles, GET /profiles/{id}.
 */
import type { Persona, ProfileDraft, ProfileWeights } from "../types/contracts";
import { registerTranslations } from "../i18n/translate";
import { mockApi } from "../mocks/server";
import { USE_MOCKS, http, mocked } from "./client";

export type ProfileRequest = ProfileDraft;

export const getPersonas = () => (USE_MOCKS ? mocked(mockApi.personas) : http.get<Persona[]>("/personas"));

/** Les motifs rédigés par un vrai modèle arrivent avec leur version anglaise : elle est enregistrée au passage. */
const withTranslations = (pw: ProfileWeights) => { registerTranslations(pw.translations); return pw; };

export const getProfile = (id: string) =>
  (USE_MOCKS ? mocked(() => mockApi.profile(id)) : http.get<ProfileWeights>(`/profiles/${encodeURIComponent(id)}`))
    .then(withTranslations);

export const createProfile = (draft: ProfileRequest) =>
  (USE_MOCKS ? mocked(() => mockApi.createProfile(draft)) : http.post<ProfileWeights>("/profiles", draft))
    .then(withTranslations);
