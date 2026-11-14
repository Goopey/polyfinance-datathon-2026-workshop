/**
 * Composant GlossaryTerm — Terme expliqué au toucher (définition en une phrase).
 */
import { useState } from "react";
import { Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { glossaire } from "../i18n/glossaire";
import { colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import { Button } from "./ui";

export function GlossaryTerm({ id, label }: { id: keyof typeof glossaire | string; label?: string }) {
  const [open, setOpen] = useState(false);
  const entry = glossaire[id];
  const text = label ?? entry?.terme ?? id;
  if (!entry) return <Text style={type.label}>{text}</Text>;
  return (
    <>
      <Pressable onPress={() => setOpen(true)} accessibilityRole="button" accessibilityHint="Affiche la définition" hitSlop={8}>
        <Text style={[type.label, styles.term]}>{text} ⓘ</Text>
      </Pressable>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <View style={styles.sheet}>
            <Text style={type.h3}>{entry.terme}</Text>
            <Text style={type.body}>{entry.definition}</Text>
            <Button label="Compris" variant="secondary" onPress={() => setOpen(false)} />
          </View>
        </Pressable>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  term: { textDecorationLine: "underline", textDecorationStyle: "dotted" },
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.35)", justifyContent: "center", padding: space.xl },
  sheet: {
    backgroundColor: colors.surface, borderRadius: radius.lg, padding: space.xl, gap: space.md,
    maxWidth: 480, width: "100%", alignSelf: "center",
  },
});

export default GlossaryTerm;
