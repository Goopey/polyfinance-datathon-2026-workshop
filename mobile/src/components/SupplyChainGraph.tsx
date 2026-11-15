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
import Svg, { Circle, Defs, G, Line, RadialGradient, Stop, Text as SvgText } from "react-native-svg";
import { useT } from "../i18n";
import { alpha, colors, palette, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { DependencyGraph, GraphEdge, GraphNode, Relation } from "../types/contracts";
import { ClaimTag } from "./ClaimTag";
import { EvidenceChip, openEvidence } from "./EvidenceChip";
import { Button } from "./ui";

const REL_COLOR: Record<Relation, string> = {
  FOURNISSEUR: colors.info,
  CLIENT: colors.good,
  CONCURRENT: colors.bad,
  PARTENAIRE: colors.warn,
};
const REL_ICON: Record<Relation, string> = { FOURNISSEUR: "→", CLIENT: "←", CONCURRENT: "⇄", PARTENAIRE: "∞" };
const HEIGHT = 320;
const FONT = Platform.OS === "web" ? "Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif" : undefined;
const GREY = "#5F7F6E";

function shortLabel(s: string, max = 16) {
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

export function SupplyChainGraph({ graph, runId }: { graph: DependencyGraph; runId?: string | null }) {
  const t = useT();
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
        <Text style={type.body}>{t.graph.emptyTitle}</Text>
        <Text style={type.small}>{t.graph.emptyBody}</Text>
      </View>
    );
  }

  const onEdge = (e: GraphEdge) => {
    if (e.evidence_id) openEvidence(e.evidence_id, runId);
    else setSelected(graph.nodes.find((n) => n.id === (e.source === graph.center ? e.target : e.source)) ?? null);
  };

  return (
    <View style={{ gap: space.md }}>
      <View onLayout={onLayout} style={styles.canvas} accessibilityLabel={t.graph.a11y(center?.label ?? graph.center)}>
        <Svg width={width} height={HEIGHT}>
          <Defs>
            <RadialGradient id="halo" cx="50%" cy="50%" r="50%">
              <Stop offset="0" stopColor={palette.g300} stopOpacity="0.28" />
              <Stop offset="1" stopColor={palette.g800} stopOpacity="0" />
            </RadialGradient>
          </Defs>
          {(() => {
            const c = layout.get(graph.center);
            return c ? <Circle cx={c.x} cy={c.y} r={90} fill="url(#halo)" /> : null;
          })()}
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
                  stroke={REL_COLOR[e.relation]} strokeWidth={2.5} strokeOpacity={0.9}
                  strokeDasharray={e.claim_kind === "HYPOTHESE" ? "6,5" : undefined}
                />
                <SvgText x={vertical ? mx + 7 : mx} y={vertical ? my + 4 : my - 6} fontSize={11} fill={REL_COLOR[e.relation]}
                  textAnchor={vertical ? "start" : "middle"} fontWeight="600"
                  fontFamily={FONT}>
                  {t.relation[e.relation]}
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
            const fill = isCenter ? colors.mint : n.in_universe ? colors.surfaceRaised : colors.surface;
            const stroke = isCenter ? colors.mint : n.in_universe ? colors.primary : GREY;
            return (
              <G key={n.id} onPress={() => setSelected(n)}>
                <Circle cx={p.x} cy={p.y} r={isCenter ? 32 : 18} fill={fill} stroke={stroke} strokeWidth={2}
                  strokeDasharray={n.in_universe ? undefined : "3,3"} />
                {isCenter ? (
                  <SvgText x={p.x} y={p.y + 4} fontSize={11} textAnchor="middle" fill={colors.primaryText} fontWeight="800" fontFamily={FONT}>
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
          <Text style={type.small}>{selected.in_universe ? t.graph.inUniverse : t.graph.outUniverse}</Text>
          {relationsOf(selected.id).map((e) => (
            <Text key={`${e.source}-${e.target}`} style={type.body}>
              {REL_ICON[e.relation]} {t.relation[e.relation]} {e.claim_kind === "HYPOTHESE" ? t.graph.hypothesis : ""}
            </Text>
          ))}
          {selected.in_universe && selected.id !== graph.center ? (
            <Button label={t.graph.seeIts} variant="secondary"
              onPress={() => router.push({ pathname: "/piste/[ticker]", params: runId ? { ticker: selected.id, run: runId } : { ticker: selected.id } })} />
          ) : null}
          <Button label={t.common.close} variant="ghost" onPress={() => setSelected(null)} />
        </View>
      ) : (
        <Text style={type.caption}>{t.graph.tapHint}</Text>
      )}

      <View style={{ gap: space.xs }}>
        <Text style={type.label}>{t.graph.relations(graph.edges.length)}</Text>
        {graph.edges.map((e) => {
          const other = e.source === graph.center ? e.target : e.source;
          const node = graph.nodes.find((n) => n.id === other);
          return (
            <Pressable key={`${e.source}-${e.target}-l`} onPress={() => onEdge(e)} style={({ pressed }) => [styles.relRow, pressed && { opacity: 0.75 }]} accessibilityRole="button">
              <View style={[styles.relIconWrap, { backgroundColor: alpha(REL_COLOR[e.relation], 0.14) }]}>
                <Text style={[styles.relIcon, { color: REL_COLOR[e.relation] }]}>{REL_ICON[e.relation]}</Text>
              </View>
              <View style={{ flex: 1, gap: 2 }}>
                <Text style={type.body}>
                  {t.relation[e.relation]} : {node?.label ?? other}
                </Text>
                {!node?.in_universe ? <Text style={type.caption}>{t.graph.outUniverseShort}</Text> : null}
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
  const t = useT();
  return (
    <View style={styles.legend} accessibilityLabel={t.graph.legendA11y}>
      {(Object.keys(REL_COLOR) as Relation[]).map((r) => (
        <View key={r} style={styles.legendItem}>
          <View style={[styles.swatch, { backgroundColor: REL_COLOR[r] }]} />
          <Text style={type.caption}>{REL_ICON[r]} {t.relation[r]}</Text>
        </View>
      ))}
      <View style={styles.legendItem}>
        <View style={[styles.swatch, { backgroundColor: colors.text }]} />
        <Text style={type.caption}>{t.graph.solid}</Text>
      </View>
      <View style={styles.legendItem}>
        <View style={styles.dashed} />
        <Text style={type.caption}>{t.graph.dashed}</Text>
      </View>
      <View style={styles.legendItem}>
        <View style={styles.greyNode} />
        <Text style={type.caption}>{t.graph.grey}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  canvas: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, overflow: "hidden" },
  empty: { backgroundColor: colors.surface, borderRadius: radius.md, padding: space.lg, gap: space.xs, borderWidth: 1, borderColor: colors.border },
  legend: { flexDirection: "row", flexWrap: "wrap", gap: space.md },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 6 },
  swatch: { width: 18, height: 3, borderRadius: 2 },
  dashed: { width: 18, height: 0, borderTopWidth: 2, borderStyle: "dashed", borderColor: colors.text },
  greyNode: { width: 12, height: 12, borderRadius: 6, backgroundColor: colors.surface, borderWidth: 1, borderColor: GREY },
  mini: { backgroundColor: colors.surfaceRaised, borderRadius: radius.md, padding: space.md, gap: space.sm, borderWidth: 1, borderColor: colors.borderStrong },
  relRow: {
    flexDirection: "row", alignItems: "center", gap: space.md, minHeight: 52, paddingVertical: space.sm, paddingHorizontal: space.sm,
    borderRadius: radius.md, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
  },
  relIconWrap: { width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center" },
  relIcon: { fontSize: 16, fontWeight: "700", textAlign: "center" },
});

export default SupplyChainGraph;
