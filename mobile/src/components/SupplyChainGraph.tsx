/**
 * Composant SupplyChainGraph — Graphe de dépendances, version radiale fixe (repli prévu par docs/07_UX_UI.md).
 *
 * - Nœud central : la société de la fiche ; voisins à 1 niveau, répartis sur un cercle.
 * - Trait plein = fait sourcé ; pointillé = hypothèse. Couleur ET style de trait par relation, et légende toujours visible.
 * - Toucher une arête : ouvre la preuve. Toucher un nœud : mini-fiche (accès à la fiche si l'actif est dans l'univers).
 * - Nœuds hors univers grisés, sans indicateurs.
 * - La liste des relations sous le graphe donne le même contenu sans dépendre du dessin (accessibilité).
 * Version animée (d3-force) : extra n° 7 de docs/10_PLAN.md.
 */
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View, type LayoutChangeEvent } from "react-native";
import Svg, { Circle, G, Line, Text as SvgText } from "react-native-svg";
import { fr } from "../i18n/fr";
import { colors, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { DependencyGraph, GraphEdge, GraphNode, Relation } from "../types/contracts";
import { ClaimTag } from "./ClaimTag";
import { EvidenceChip, openEvidence } from "./EvidenceChip";
import { Button } from "./ui";

const REL_COLOR: Record<Relation, string> = {
  FOURNISSEUR: "#1F4FD1",
  CLIENT: "#13703F",
  CONCURRENT: "#A12626",
  PARTENAIRE: "#8A5A00",
};
const REL_ICON: Record<Relation, string> = { FOURNISSEUR: "→", CLIENT: "←", CONCURRENT: "⇄", PARTENAIRE: "∞" };
const HEIGHT = 320;
const FONT = Platform.OS === "web" ? "system-ui, -apple-system, Segoe UI, Roboto, sans-serif" : undefined;

function shortLabel(s: string, max = 16) {
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

export function SupplyChainGraph({ graph, runId }: { graph: DependencyGraph; runId?: string | null }) {
  const [width, setWidth] = useState(320);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const onLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);

  const layout = useMemo(() => {
    const cx = width / 2;
    const cy = HEIGHT / 2;
    const r = Math.min(width, HEIGHT) / 2 - 48;
    const neighbours = graph.nodes.filter((n) => n.id !== graph.center);
    const pos = new Map<string, { x: number; y: number }>([[graph.center, { x: cx, y: cy }]]);
    neighbours.forEach((n, i) => {
      const a = -Math.PI / 2 + (2 * Math.PI * i) / Math.max(1, neighbours.length);
      pos.set(n.id, { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) });
    });
    return pos;
  }, [graph, width]);

  const center = graph.nodes.find((n) => n.id === graph.center);
  const relationsOf = (id: string) => graph.edges.filter((e) => e.source === id || e.target === id);

  if (graph.edges.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={type.body}>Aucune relation sourcée n'a encore été saisie pour cet actif.</Text>
        <Text style={type.small}>Une arête n'apparaît que si un document daté la justifie, ou si elle est étiquetée « Hypothèse ».</Text>
      </View>
    );
  }

  const onEdge = (e: GraphEdge) => {
    if (e.evidence_id) openEvidence(e.evidence_id, runId);
    else setSelected(graph.nodes.find((n) => n.id === (e.source === graph.center ? e.target : e.source)) ?? null);
  };

  return (
    <View style={{ gap: space.md }}>
      <View onLayout={onLayout} style={styles.canvas} accessibilityLabel={`Graphe de dépendances de ${center?.label ?? graph.center}`}>
        <Svg width={width} height={HEIGHT}>
          {graph.edges.map((e) => {
            const a = layout.get(e.source);
            const b = layout.get(e.target);
            if (!a || !b) return null;
            const key = `${e.source}-${e.target}-${e.relation}`;
            // Libellé au milieu de l'arête ; décalé sur le côté si l'arête est presque verticale.
            const mx = (a.x + b.x) / 2;
            const my = (a.y + b.y) / 2;
            const vertical = Math.abs(a.x - b.x) < 24;
            return (
              <G key={key}>
                <Line
                  x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  stroke={REL_COLOR[e.relation]} strokeWidth={2.5}
                  strokeDasharray={e.claim_kind === "HYPOTHESE" ? "6,5" : undefined}
                />
                <SvgText x={vertical ? mx + 7 : mx} y={vertical ? my + 4 : my - 6} fontSize={11} fill={REL_COLOR[e.relation]}
                  textAnchor={vertical ? "start" : "middle"} fontWeight="600"
                  fontFamily={FONT}>
                  {fr.relation[e.relation]}
                </SvgText>
                {/* Zone tactile large, invisible */}
                <Line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="transparent" strokeWidth={22} onPress={() => onEdge(e)} />
              </G>
            );
          })}
          {graph.nodes.map((n) => {
            const p = layout.get(n.id);
            if (!p) return null;
            const isCenter = n.id === graph.center;
            const fill = isCenter ? colors.primary : n.in_universe ? colors.surface : colors.surfaceMuted;
            const stroke = isCenter ? colors.primary : n.in_universe ? colors.text : "#9AA5B4";
            return (
              <G key={n.id} onPress={() => setSelected(n)}>
                <Circle cx={p.x} cy={p.y} r={isCenter ? 32 : 18} fill={fill} stroke={stroke} strokeWidth={2}
                  strokeDasharray={n.in_universe ? undefined : "3,3"} />
                {isCenter ? (
                  <SvgText x={p.x} y={p.y + 4} fontSize={11} textAnchor="middle" fill={colors.primaryText} fontWeight="700" fontFamily={FONT}>
                    {shortLabel(n.id, 9)}
                  </SvgText>
                ) : (
                  <SvgText x={p.x} y={p.y + 32} fontSize={12} textAnchor="middle" fontFamily={FONT}
                    fill={n.in_universe ? colors.text : colors.textMuted}>
                    {shortLabel(n.label)}
                  </SvgText>
                )}
              </G>
            );
          })}
        </Svg>
      </View>

      <Legend />

      {selected ? (
        <View style={styles.mini}>
          <Text style={type.h3}>{selected.label}</Text>
          <Text style={type.small}>
            {selected.in_universe
              ? "Dans l'univers d'actifs analysé."
              : "Hors univers : affiché pour le contexte, sans indicateurs."}
          </Text>
          {relationsOf(selected.id).map((e) => (
            <Text key={`${e.source}-${e.target}`} style={type.body}>
              {REL_ICON[e.relation]} {fr.relation[e.relation]} {e.claim_kind === "HYPOTHESE" ? "(hypothèse)" : ""}
            </Text>
          ))}
          {selected.in_universe && selected.id !== graph.center ? (
            <Button label="Voir sa fiche" variant="secondary"
              onPress={() => router.push({ pathname: "/piste/[ticker]", params: runId ? { ticker: selected.id, run: runId } : { ticker: selected.id } })} />
          ) : null}
          <Button label="Fermer" variant="ghost" onPress={() => setSelected(null)} />
        </View>
      ) : (
        <Text style={type.caption}>Touchez un lien pour voir sa preuve, ou une société pour sa mini-fiche.</Text>
      )}

      <View style={{ gap: space.sm }}>
        <Text style={type.label}>Relations ({graph.edges.length})</Text>
        {graph.edges.map((e) => {
          const other = e.source === graph.center ? e.target : e.source;
          const node = graph.nodes.find((n) => n.id === other);
          return (
            <Pressable key={`${e.source}-${e.target}-l`} onPress={() => onEdge(e)} style={styles.relRow} accessibilityRole="button">
              <Text style={[styles.relIcon, { color: REL_COLOR[e.relation] }]}>{REL_ICON[e.relation]}</Text>
              <View style={{ flex: 1, gap: 2 }}>
                <Text style={type.body}>
                  {fr.relation[e.relation]} : {node?.label ?? other}
                </Text>
                {!node?.in_universe ? <Text style={type.caption}>Hors univers</Text> : null}
              </View>
              {e.claim_kind === "HYPOTHESE" ? <ClaimTag kind="HYPOTHESE" /> : null}
              {e.evidence_id ? <EvidenceChip id={e.evidence_id} runId={runId} /> : null}
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

function Legend() {
  return (
    <View style={styles.legend} accessibilityLabel="Légende du graphe">
      {(Object.keys(REL_COLOR) as Relation[]).map((r) => (
        <View key={r} style={styles.legendItem}>
          <View style={[styles.swatch, { backgroundColor: REL_COLOR[r] }]} />
          <Text style={type.caption}>{REL_ICON[r]} {fr.relation[r]}</Text>
        </View>
      ))}
      <View style={styles.legendItem}>
        <View style={[styles.swatch, { backgroundColor: colors.text }]} />
        <Text style={type.caption}>Trait plein : fait sourcé</Text>
      </View>
      <View style={styles.legendItem}>
        <View style={styles.dashed} />
        <Text style={type.caption}>Pointillé : hypothèse</Text>
      </View>
      <View style={styles.legendItem}>
        <View style={styles.greyNode} />
        <Text style={type.caption}>Gris : hors univers</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  canvas: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, overflow: "hidden" },
  empty: { backgroundColor: colors.surfaceMuted, borderRadius: radius.md, padding: space.lg, gap: space.xs },
  legend: { flexDirection: "row", flexWrap: "wrap", gap: space.md },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 6 },
  swatch: { width: 18, height: 3, borderRadius: 2 },
  dashed: { width: 18, height: 0, borderTopWidth: 2, borderStyle: "dashed", borderColor: colors.text },
  greyNode: { width: 12, height: 12, borderRadius: 6, backgroundColor: colors.surfaceMuted, borderWidth: 1, borderColor: "#9AA5B4" },
  mini: { backgroundColor: colors.surfaceMuted, borderRadius: radius.md, padding: space.md, gap: space.sm },
  relRow: { flexDirection: "row", alignItems: "center", gap: space.md, minHeight: 44, paddingVertical: space.xs },
  relIcon: { fontSize: 20, fontWeight: "700", width: 24, textAlign: "center" },
});

export default SupplyChainGraph;
