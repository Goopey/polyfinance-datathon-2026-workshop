/**
 * Composant SupplyChainGraph — Graphe de dépendances servi par l'API (GET /assets/{ticker}/graph), version radiale.
 *
 * - Nœud central : la société de la fiche ; voisins à 1 niveau, répartis sur un cercle.
 * - Trait plein = fait sourcé ; pointillé = hypothèse. Couleur par relation ; la légende ne montre que
 *   ce qui figure dans le graphe.
 * - Toucher un nœud : il est mis en avant (ses liens restent vifs, les autres s'estompent) et une mini-fiche
 *   s'ouvre (accès à la fiche si l'actif est dans l'univers, preuve du lien).
 * - Nœuds hors univers en pointillé, sans indicateurs.
 * - Graphe sans arête : rien n'est affiché (la fiche masque la section).
 */
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { Platform, StyleSheet, Text, View, type LayoutChangeEvent } from "react-native";
import Svg, { Circle, Defs, G, Line, RadialGradient, Stop, Text as SvgText } from "react-native-svg";
import { useT } from "../i18n";
import { alpha, colors, palette, radius, space } from "../theme/tokens";
import { type } from "../theme/typography";
import type { DependencyGraph, GraphEdge, GraphNode, Relation } from "../types/contracts";
import { ClaimTag } from "./ClaimTag";
import { EvidenceChip } from "./EvidenceChip";
import { Icon } from "./Icon";
import { Button, Collapsible, FadeIn, Tap } from "./ui";

const REL_COLOR: Record<Relation, string> = {
  FOURNISSEUR: colors.info,
  CLIENT: colors.good,
  CONCURRENT: colors.hypothesis,
  PARTENAIRE: colors.warn,
};
const REL_ICON: Record<Relation, string> = { FOURNISSEUR: "→", CLIENT: "←", CONCURRENT: "⇄", PARTENAIRE: "∞" };
const HEIGHT = 300;
const FONT = Platform.OS === "web" ? "Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif" : undefined;
const GREY = "#5F7F6E";

function shortLabel(s: string, max = 14) {
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

export function hasGraph(graph: DependencyGraph | undefined | null) {
  return !!graph && graph.edges.length > 0;
}

export function SupplyChainGraph({ graph, runId }: { graph: DependencyGraph; runId?: string | null }) {
  const t = useT();
  const [width, setWidth] = useState(320);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const onLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);

  const layout = useMemo(() => {
    const cx = width / 2;
    const cy = HEIGHT / 2;
    const r = Math.min(width, HEIGHT) / 2 - 44;
    const neighbours = graph.nodes.filter((n) => n.id !== graph.center);
    const pos = new Map<string, { x: number; y: number }>([[graph.center, { x: cx, y: cy }]]);
    neighbours.forEach((n, i) => {
      const a = -Math.PI / 2 + (2 * Math.PI * i) / Math.max(1, neighbours.length);
      pos.set(n.id, { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) });
    });
    return pos;
  }, [graph, width]);

  if (graph.edges.length === 0) return null;

  const center = graph.nodes.find((n) => n.id === graph.center);
  const selected = graph.nodes.find((n) => n.id === selectedId) ?? null;
  const touches = (e: GraphEdge, id: string) => e.source === id || e.target === id;
  const relations = [...new Set(graph.edges.map((e) => e.relation))];
  const hasHypothesis = graph.edges.some((e) => e.claim_kind === "HYPOTHESE");
  const hasFact = graph.edges.some((e) => e.claim_kind !== "HYPOTHESE");
  const hasOutside = graph.nodes.some((n) => !n.in_universe);
  const select = (id: string) => setSelectedId(selectedId === id || id === graph.center ? null : id);

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
            const dim = selectedId !== null && !touches(e, selectedId);
            return (
              <G key={`${e.source}-${e.target}-${e.relation}`}>
                <Line
                  x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  stroke={REL_COLOR[e.relation]} strokeWidth={dim ? 1.5 : 2.5} strokeOpacity={dim ? 0.2 : 0.9}
                  strokeDasharray={e.claim_kind === "HYPOTHESE" ? "6,5" : undefined}
                />
                <Line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="transparent" strokeWidth={22}
                  onPress={() => select(e.source === graph.center ? e.target : e.source)} />
              </G>
            );
          })}
          {graph.nodes.map((n) => {
            const p = layout.get(n.id);
            if (!p) return null;
            const isCenter = n.id === graph.center;
            const isSel = n.id === selectedId;
            const fill = isCenter ? colors.mint : isSel ? colors.primary : n.in_universe ? colors.surfaceRaised : colors.surface;
            const stroke = isCenter ? colors.mint : isSel ? colors.mint : n.in_universe ? colors.primary : GREY;
            return (
              <G key={n.id} onPress={() => select(n.id)}>
                {isSel ? <Circle cx={p.x} cy={p.y} r={28} fill={alpha(colors.mint, 0.14)} /> : null}
                <Circle cx={p.x} cy={p.y} r={isCenter ? 32 : 19} fill={fill} stroke={stroke} strokeWidth={2}
                  strokeDasharray={n.in_universe || isSel ? undefined : "3,3"} />
                {isCenter ? (
                  <SvgText x={p.x} y={p.y + 4} fontSize={11} textAnchor="middle" fill={colors.primaryText} fontWeight="800" fontFamily={FONT}>
                    {shortLabel(n.id, 9)}
                  </SvgText>
                ) : (
                  <>
                    <SvgText x={p.x} y={p.y + 4} fontSize={9.5} textAnchor="middle" fontWeight="800" fontFamily={FONT}
                      fill={isSel ? colors.primaryText : colors.mint}>
                      {shortLabel(n.id.replace(/\.TO$/, ""), 6)}
                    </SvgText>
                    {n.label !== n.id ? (
                      <SvgText x={p.x} y={p.y + 33} fontSize={11.5} textAnchor="middle" fontFamily={FONT}
                        fill={n.in_universe ? colors.text : colors.textMuted}>
                        {shortLabel(n.label)}
                      </SvgText>
                    ) : null}
                  </>
                )}
              </G>
            );
          })}
        </Svg>
      </View>

      <View style={styles.legend} accessibilityLabel={t.graph.legendA11y}>
        {relations.map((r) => (
          <View key={r} style={styles.legendItem}>
            <View style={[styles.swatch, { backgroundColor: REL_COLOR[r] }]} />
            <Text style={type.caption}>{REL_ICON[r]} {t.relation[r]}</Text>
          </View>
        ))}
        {hasFact && hasHypothesis ? (
          <View style={styles.legendItem}>
            <View style={[styles.swatch, { backgroundColor: colors.text }]} />
            <Text style={type.caption}>{t.graph.solid}</Text>
          </View>
        ) : null}
        {hasHypothesis ? (
          <View style={styles.legendItem}>
            <View style={styles.dashed} />
            <Text style={type.caption}>{t.graph.dashed}</Text>
          </View>
        ) : null}
        {hasOutside ? (
          <View style={styles.legendItem}>
            <View style={styles.greyNode} />
            <Text style={type.caption}>{t.graph.grey}</Text>
          </View>
        ) : null}
      </View>

      {selected ? (
        <FadeIn key={selected.id}>
          <View style={styles.mini}>
            <View style={styles.miniHead}>
              <Text style={[type.h3, { flex: 1 }]}>{selected.label}</Text>
              <Tap onPress={() => setSelectedId(null)} hitSlop={10} accessibilityRole="button" accessibilityLabel={t.common.close}>
                <Icon name="x" size={18} color={colors.textMuted} />
              </Tap>
            </View>
            <Text style={type.small}>{selected.in_universe ? t.graph.inUniverse : t.graph.outUniverse}</Text>
            {graph.edges.filter((e) => touches(e, selected.id)).map((e) => (
              <View key={`${e.source}-${e.target}`} style={styles.miniRel}>
                <Text style={[type.body, { color: REL_COLOR[e.relation] }]}>{REL_ICON[e.relation]} {t.relation[e.relation]}</Text>
                {e.claim_kind === "HYPOTHESE" ? <ClaimTag kind="HYPOTHESE" /> : null}
                {e.evidence_id ? <EvidenceChip id={e.evidence_id} runId={runId} /> : null}
              </View>
            ))}
            {selected.in_universe && selected.id !== graph.center ? (
              <Button label={t.graph.seeIts} variant="secondary" icon="arrowRight"
                onPress={() => router.push({ pathname: "/piste/[ticker]", params: runId ? { ticker: selected.id, run: runId } : { ticker: selected.id } })} />
            ) : null}
          </View>
        </FadeIn>
      ) : (
        <Text style={type.caption}>{t.graph.tapHint}</Text>
      )}

      <Collapsible title={t.graph.relations(graph.edges.length)} icon="network">
        {graph.edges.map((e) => {
          const other = e.source === graph.center ? e.target : e.source;
          const node = graph.nodes.find((n) => n.id === other);
          return (
            <Tap key={`${e.source}-${e.target}-l`} onPress={() => select(other)} scaleTo={0.98}
              style={({ pressed }) => [styles.relRow, (pressed || other === selectedId) && styles.relRowOn]} accessibilityRole="button">
              <View style={[styles.relIconWrap, { backgroundColor: alpha(REL_COLOR[e.relation], 0.14) }]}>
                <Text style={[styles.relIcon, { color: REL_COLOR[e.relation] }]}>{REL_ICON[e.relation]}</Text>
              </View>
              <View style={{ flex: 1, gap: 2 }}>
                <Text style={type.body}>{t.relation[e.relation]} : {node?.label ?? other}</Text>
                {!node?.in_universe ? <Text style={type.caption}>{t.graph.outUniverseShort}</Text> : null}
              </View>
              {e.evidence_id ? <EvidenceChip id={e.evidence_id} runId={runId} /> : null}
            </Tap>
          );
        })}
      </Collapsible>
    </View>
  );
}

const styles = StyleSheet.create({
  canvas: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, overflow: "hidden" },
  legend: { flexDirection: "row", flexWrap: "wrap", gap: space.md },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 6 },
  swatch: { width: 18, height: 3, borderRadius: 2 },
  dashed: { width: 18, height: 0, borderTopWidth: 2, borderStyle: "dashed", borderColor: colors.text },
  greyNode: { width: 12, height: 12, borderRadius: 6, backgroundColor: colors.surface, borderWidth: 1, borderStyle: "dashed", borderColor: GREY },
  mini: { backgroundColor: colors.surfaceRaised, borderRadius: radius.md, padding: space.md, gap: space.sm, borderWidth: 1, borderColor: colors.borderStrong },
  miniHead: { flexDirection: "row", alignItems: "center", gap: space.sm },
  miniRel: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: space.sm },
  relRow: {
    flexDirection: "row", alignItems: "center", gap: space.md, minHeight: 52, paddingVertical: space.sm, paddingHorizontal: space.sm,
    borderRadius: radius.md, backgroundColor: colors.surfaceMuted, borderWidth: 1, borderColor: colors.border,
  },
  relRowOn: { borderColor: colors.primary, backgroundColor: alpha(colors.primary, 0.1) },
  relIconWrap: { width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center" },
  relIcon: { fontSize: 16, fontWeight: "700", textAlign: "center" },
});

export default SupplyChainGraph;
