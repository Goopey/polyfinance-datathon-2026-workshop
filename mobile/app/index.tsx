/**
 * Écran : Entrée : redirige vers le profil au premier lancement, sinon vers les pistes.
 */
import { Redirect } from "expo-router";
import { Loading } from "../src/components/ui";
import { useProfileHydrated, useProfileStore } from "../src/store/profile";

export default function Entree() {
  const hydrated = useProfileHydrated();
  const profileId = useProfileStore((s) => s.profileId);
  if (!hydrated) return <Loading />;
  return <Redirect href={profileId ? "/(tabs)" : "/onboarding"} />;
}
