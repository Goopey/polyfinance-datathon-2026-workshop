/** Mise en forme française des nombres et des dates. */

export function fmtNum(v: number, digits = 1): string {
  return v.toLocaleString("fr-CA", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** Valeur en points de pourcentage (12,3 pour 12,3 %), convention de schemas/metrics.py. */
export function fmtPct(v: number, digits = 1): string {
  return `${fmtNum(v, digits)} %`;
}

export function fmtValue(v: number | null, unit: string | null): string {
  if (v === null) return "—";
  if (unit === "%") return fmtPct(v);
  const digits = Number.isInteger(v) ? 0 : 2; // un décompte (« 3 actif(s) ») s'affiche sans décimales
  return unit ? `${fmtNum(v, digits)} ${unit}` : fmtNum(v, digits);
}

/** Poids 0–1 affiché en pourcentage entier. */
export function fmtWeight(w: number): string {
  return `${Math.round(w * 100)} %`;
}

export function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(`${iso.slice(0, 10)}T12:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("fr-CA", { year: "numeric", month: "long", day: "numeric" });
}

export function durationMs(start: string, end: string): number {
  return Math.max(0, new Date(end).getTime() - new Date(start).getTime());
}
