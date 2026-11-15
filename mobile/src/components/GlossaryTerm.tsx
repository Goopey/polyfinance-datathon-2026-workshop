/**
 * Composant GlossaryTerm — Terme expliqué au toucher (définition en une phrase, dans la langue de l'interface).
 */
import { useState } from "react";
import { Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { useGlossary, useT } from "../i18n";
import { colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import { Icon } from "./Icon";
import { Button } from "./ui";

export function GlossaryTerm({ id, label }: { id: string; label?: string }) {
  const t = useT();
  const glossary = useGlossary();
  const [open, setOpen] = useState(false);
  const entry = glossary[id];
  const text = label ?? entry?.terme ?? id;
  if (!entry) return <Text style={type.label}>{text}</Text>;
  return (
    <>
      <Pressable onPress={() => setOpen(true)} accessibilityRole="button" accessibilityHint={t.common.showDefinition} hitSlop={8} style={styles.trigger}>
        <Text style={[type.label, styles.term]}>{text}</Text>
        <Icon name="info" size={14} color={colors.textMuted} />
      </Pressable>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <View style={styles.sheet}>
            <Text style={type.h2}>{entry.terme}</Text>
            <Text style={type.body}>{entry.definition}</Text>
            <Button label={t.common.understood} variant="secondary" onPress={() => setOpen(false)} />
          </View>
        </Pressable>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  trigger: { flexDirection: "row", alignItems: "center", gap: 6 },
  term: { textDecorationLine: "underline", textDecorationStyle: "dotted", textDecorationColor: colors.textMuted },
  backdrop: { flex: 1, backgroundColor: colors.overlay, justifyContent: "center", padding: space.xl },
  sheet: {
    backgroundColor: colors.surfaceRaised, borderRadius: radius.xl, padding: space.xl, gap: space.md,
    maxWidth: 480, width: "100%", alignSelf: "center", borderWidth: 1, borderColor: colors.borderStrong,
  },
});

export default GlossaryTerm;
