/**
 * Composant EvidenceChip — Pastille de source : ouvre la preuve (« Pourquoi ? »).
 * `ClaimLine` : une affirmation + son étiquette + ses pastilles. Aucune affirmation sans preuve.
 */
import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useT } from "../i18n";
import { alpha, colors, radius, space } from "../theme/tokens";
import { fontFamily, type } from "../theme/typography";
import type { Claim } from "../types/contracts";
import { ClaimTag } from "./ClaimTag";
import { Icon } from "./Icon";

export function openEvidence(id: string, runId?: string | null) {
  router.push({ pathname: "/preuve/[id]", params: runId ? { id, run: runId } : { id } });
}

export function EvidenceChip({ id, runId, label }: { id: string; runId?: string | null; label?: string }) {
  const t = useT();
  return (
    <Pressable
      onPress={() => openEvidence(id, runId)}
      accessibilityRole="link"
      accessibilityLabel={t.common.seeEvidence(id)}
      hitSlop={10}
      style={({ pressed }) => [styles.chip, pressed && { opacity: 0.7 }]}
    >
      <Icon name="info" size={13} color={colors.mint} strokeWidth={2.4} />
      <Text style={styles.text}>{label ?? t.common.source}</Text>
    </Pressable>
  );
}

export function ClaimLine({ claim, runId }: { claim: Claim; runId?: string | null }) {
  const t = useT();
  return (
    <View style={styles.line}>
      <Text style={type.body}>{claim.text}</Text>
      <View style={styles.meta}>
        <ClaimTag kind={claim.claim_kind} />
        {claim.evidence_ids.map((id, i) => (
          <EvidenceChip key={id} id={id} runId={runId} label={claim.evidence_ids.length > 1 ? t.common.sourceN(i + 1) : t.common.source} />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    flexDirection: "row", alignItems: "center", gap: 5,
    borderWidth: 1, borderColor: alpha(colors.mint, 0.35), backgroundColor: alpha(colors.mint, 0.06),
    borderRadius: radius.pill, paddingHorizontal: space.sm + 2, paddingVertical: 3, alignSelf: "flex-start",
  },
  text: { fontFamily, color: colors.mint, fontSize: 13, fontWeight: "600" },
  line: { gap: space.xs + 2 },
  meta: { flexDirection: "row", flexWrap: "wrap", gap: space.sm, alignItems: "center" },
});

export default EvidenceChip;
