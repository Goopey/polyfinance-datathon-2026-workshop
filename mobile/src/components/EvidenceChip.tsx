/**
 * Composant EvidenceChip — Pastille de source : ouvre la preuve (« Pourquoi ? »).
 * `ClaimLine` : une affirmation + son étiquette + ses pastilles. Aucune affirmation sans preuve.
 */
import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { Claim } from "../types/contracts";
import { ClaimTag } from "./ClaimTag";

export function openEvidence(id: string, runId?: string | null) {
  router.push({ pathname: "/preuve/[id]", params: runId ? { id, run: runId } : { id } });
}

export function EvidenceChip({ id, runId, label }: { id: string; runId?: string | null; label?: string }) {
  return (
    <Pressable
      onPress={() => openEvidence(id, runId)}
      accessibilityRole="link"
      accessibilityLabel={`Voir la preuve ${id}`}
      hitSlop={10}
      style={({ pressed }) => [styles.chip, pressed && { opacity: 0.7 }]}
    >
      <Text style={styles.text}>ⓘ {label ?? "Source"}</Text>
    </Pressable>
  );
}

export function ClaimLine({ claim, runId }: { claim: Claim; runId?: string | null }) {
  return (
    <View style={styles.line}>
      <Text style={type.body}>{claim.text}</Text>
      <View style={styles.meta}>
        <ClaimTag kind={claim.claim_kind} />
        {claim.evidence_ids.map((id, i) => (
          <EvidenceChip key={id} id={id} runId={runId} label={claim.evidence_ids.length > 1 ? `Source ${i + 1}` : "Source"} />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    borderWidth: 1, borderColor: colors.primary, borderRadius: radius.pill,
    paddingHorizontal: space.sm, paddingVertical: 3, alignSelf: "flex-start",
  },
  text: { color: colors.primary, fontSize: 13, fontWeight: "600" },
  line: { gap: space.xs },
  meta: { flexDirection: "row", flexWrap: "wrap", gap: space.sm, alignItems: "center" },
});

export default EvidenceChip;
