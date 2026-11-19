// VILLA "CORAL" PARAMÉTRIQUE — d'après Ummahat 9-3, Coral Villa 1 ch. (Kengo Kuma & Associates, mer Rouge)
// Référence Capitude : ref-kkaa-ummahat-9-3 (plan KKAA 1-BED-CORAL 1:100, coupes AD 29, élévations AD 30-31, photos N. Maniero)
// Générateur Rayon run_typescript — modèle SIPEF PLAN MASSE, "3D canvas". Partie 1 : coque, plancher, pilotis, piscine, éventail.
// Plan de la référence mis à l'échelle s = 0.93 pour tenir la toiture (Ø 20,6 m -> 19,2 m) dans la parcelle 20 x 20 m.
const CAN = "8rE456sM0S3";
const P = {
  siteMin: { x: 21336, y: -9129 }, siteSize: 20000, cx: 31336, cy: 871,
  F: 2000, slabT: 350,                                   // plancher sur pilotis +2,00
  rCourt: 3100, rOuter: 7900,                            // mur de cour (axe) / façade facettée (axe)
  facets: [52, 73, 95, 118, 141, 165, 187, 210, 232, 250, 264], // sommets des facettes (deg) = cloisons
  deck: { rBuild: 8150, rTerr: 7300, lobe: 2400, lobeAt: 5, lobeHalf: 55 },
  pool: { a0: -14, a1: 26, mid: 6, rIn: 5400, rOut: 9100, bottom: 1450, top: 1970 },
  roof: { a0: 40, span: 310, Ro: 9600, RoEnd: 400, Ri: 2500, RiEnd: 1500, Eo: 3400, Ei: 3300, Hr: 5600, vR: 0.33,
          drop: 1300, dropInner: 500, edgeT: 250, Nu: 90, Nv: 16 },
  fan: { a0: 354, a1: 398, n: 13, r0: 1600, r1: 8000 },
  planterR: 1300, wallTop: 3000,
  entry: { x0: -4800, x1: -3200, yLand0: -7600, yLand1: -6700 },
  slats: [187, 250] as [number, number],                  // claustra bois (WD-01) devant séjour + entrée
};
type V = { x: number; y: number; z: number }; type F = { outer: V[] }; type P2 = { x: number; y: number };
const deg = Math.PI / 180, v3 = (x: number, y: number, z: number): V => ({ x, y, z });
const polar = (r: number, t: number): P2 => ({ x: P.cx + r * Math.cos(t * deg), y: P.cy + r * Math.sin(t * deg) });
const ss = (a: number, b: number, x: number) => { const t = Math.min(Math.max((x - a) / (b - a), 0), 1); return t * t * (3 - 2 * t); };
function newell(r: V[]): V { const n = v3(0, 0, 0); for (let i = 0; i < r.length; i++) { const a = r[i]!, b = r[(i + 1) % r.length]!; n.x += (a.y - b.y) * (a.z + b.z); n.y += (a.z - b.z) * (a.x + b.x); n.z += (a.x - b.x) * (a.y + b.y); } return n; }
const orient = (r: V[], h: V): F => { const n = newell(r); return { outer: n.x * h.x + n.y * h.y + n.z * h.z < 0 ? r.slice().reverse() : r }; };
function prism(poly: P2[], z0: number, z1: number): F[] {
  const f: F[] = [orient(poly.map(p => v3(p.x, p.y, z1)), v3(0, 0, 1)), orient(poly.map(p => v3(p.x, p.y, z0)), v3(0, 0, -1))];
  let A = 0; for (let i = 0; i < poly.length; i++) { const a = poly[i]!, b = poly[(i + 1) % poly.length]!; A += a.x * b.y - b.x * a.y; }
  const s = A > 0 ? 1 : -1;
  for (let i = 0; i < poly.length; i++) { const a = poly[i]!, b = poly[(i + 1) % poly.length]!; f.push(orient([v3(a.x, a.y, z0), v3(b.x, b.y, z0), v3(b.x, b.y, z1), v3(a.x, a.y, z1)], v3(s * (b.y - a.y), -s * (b.x - a.x), 0))); }
  return f;
}
const arc = (r: number, a0: number, a1: number, step = 2) => { const n = Math.max(2, Math.ceil(Math.abs(a1 - a0) / step)); return Array.from({ length: n + 1 }, (_, i) => polar(r, a0 + (a1 - a0) * i / n)); };
const line = (a: P2, b: P2, n: number) => Array.from({ length: n + 1 }, (_, i) => ({ x: a.x + (b.x - a.x) * i / n, y: a.y + (b.y - a.y) * i / n }));
// ruban épais à bas et haut variables (murs hauts, chevrons, solives, nervures)
function ribbon(pts: P2[], halfT: number, zb: (p: P2) => number, zt: (p: P2) => number): F[] {
  const n = pts.length, f: F[] = [];
  const T = pts.map((p, k) => { const a = pts[Math.max(k - 1, 0)]!, b = pts[Math.min(k + 1, n - 1)]!; const l = Math.hypot(b.x - a.x, b.y - a.y); return { x: (b.x - a.x) / l, y: (b.y - a.y) / l }; });
  const L = pts.map((p, k) => ({ x: p.x - T[k]!.y * halfT, y: p.y + T[k]!.x * halfT })), R = pts.map((p, k) => ({ x: p.x + T[k]!.y * halfT, y: p.y - T[k]!.x * halfT }));
  const B = pts.map(zb), H = pts.map(zt);
  const q = (P_: P2, z: number) => v3(P_.x, P_.y, z);
  for (let k = 0; k < n - 1; k++) {
    const nl = v3(-T[k]!.y, T[k]!.x, 0), nr = v3(T[k]!.y, -T[k]!.x, 0);
    const Lb = q(L[k]!, B[k]!), L1b = q(L[k + 1]!, B[k + 1]!), Rb = q(R[k]!, B[k]!), R1b = q(R[k + 1]!, B[k + 1]!);
    const Lt = q(L[k]!, H[k]!), L1t = q(L[k + 1]!, H[k + 1]!), Rt = q(R[k]!, H[k]!), R1t = q(R[k + 1]!, H[k + 1]!);
    f.push(orient([Lb, R1b, L1b], v3(0, 0, -1)), orient([Lb, Rb, R1b], v3(0, 0, -1)));
    f.push(orient([Lt, Rt, R1t], v3(0, 0, 1)), orient([Lt, R1t, L1t], v3(0, 0, 1)));
    f.push(orient([Lb, L1b, L1t], nl), orient([Lb, L1t, Lt], nl), orient([Rb, R1b, R1t], nr), orient([Rb, R1t, Rt], nr));
  }
  const e0 = v3(-T[0]!.x, -T[0]!.y, 0), e1 = v3(T[n - 1]!.x, T[n - 1]!.y, 0);
  f.push(orient([q(L[0]!, B[0]!), q(R[0]!, B[0]!), q(R[0]!, H[0]!), q(L[0]!, H[0]!)], e0));
  f.push(orient([q(L[n - 1]!, B[n - 1]!), q(R[n - 1]!, B[n - 1]!), q(R[n - 1]!, H[n - 1]!), q(L[n - 1]!, H[n - 1]!)], e1));
  return f;
}
// ---------- COQUE EN SPIRALE (nautile) ----------
const RF = P.roof;
const Ro = (u: number) => RF.Ro - RF.RoEnd * ss(0.85, 1, u);
const Ri = (u: number) => RF.Ri - (RF.Ri - RF.RiEnd) * ss(0.6, 1, u);
const bumpF = (v: number) => v >= RF.vR ? 1 - Math.pow((v - RF.vR) / (1 - RF.vR), 2.1) : 1 - Math.pow((RF.vR - v) / RF.vR, 1.6);
const flat = (u: number) => 1 - 0.45 * ss(0.7, 1, u);
const eaveV = (v: number) => RF.Ei + (RF.Eo - RF.Ei) * v;
const drop = (u: number, v: number) => RF.drop * ss(0.62, 1, u) + RF.dropInner * ss(0.75, 1, u) * (1 - v);
const topH = (u: number, v: number) => eaveV(v) + (RF.Hr - eaveV(v)) * bumpF(v) * flat(u) - drop(u, v);
const botH = (u: number, v: number) => eaveV(v) - RF.edgeT + 0.55 * (RF.Hr - eaveV(v)) * bumpF(v) * flat(u) - drop(u, v);
const thOf = (u: number) => RF.a0 + u * RF.span;
const rOf = (u: number, v: number) => Ri(u) + v * (Ro(u) - Ri(u));
function uvAt(p: P2): { u: number; v: number } | null {
  let t = Math.atan2(p.y - P.cy, p.x - P.cx) / deg; while (t < RF.a0) t += 360; while (t >= RF.a0 + 360) t -= 360;
  const u = (t - RF.a0) / RF.span; if (u > 1) return null;
  const v = (Math.hypot(p.x - P.cx, p.y - P.cy) - Ri(u)) / (Ro(u) - Ri(u)); return v < 0 || v > 1 ? null : { u, v };
}
const soffit = (p: P2) => { const w = uvAt(p); return w ? P.F + botH(w.u, w.v) : P.F + 3400; };
function roofFaces(): F[] {
  const f: F[] = [];
  const us = Array.from({ length: RF.Nu + 1 }, (_, i) => i / RF.Nu), vs = Array.from({ length: RF.Nv + 1 }, (_, j) => j / RF.Nv);
  const pt = (u: number, v: number, z: number) => { const q = polar(rOf(u, v), thOf(u)); return v3(q.x, q.y, P.F + z); };
  const T = us.map(u => vs.map(v => pt(u, v, topH(u, v)))), B = us.map(u => vs.map(v => pt(u, v, botH(u, v))));
  const up = v3(0, 0, 1), dn = v3(0, 0, -1);
  for (let i = 0; i < RF.Nu; i++) for (let j = 0; j < RF.Nv; j++) {
    f.push(orient([T[i]![j]!, T[i]![j + 1]!, T[i + 1]![j]!], up), orient([T[i]![j + 1]!, T[i + 1]![j + 1]!, T[i + 1]![j]!], up));
    f.push(orient([B[i]![j]!, B[i]![j + 1]!, B[i + 1]![j]!], dn), orient([B[i]![j + 1]!, B[i + 1]![j + 1]!, B[i + 1]![j]!], dn));
  }
  const rad = (u: number, s: number) => v3(s * Math.cos(thOf(u) * deg), s * Math.sin(thOf(u) * deg), 0);
  const tan = (u: number, s: number) => v3(-s * Math.sin(thOf(u) * deg), s * Math.cos(thOf(u) * deg), 0);
  for (let i = 0; i < RF.Nu; i++) for (const [j, s] of [[RF.Nv, 1], [0, -1]] as [number, number][]) { const a = T[i]![j]!, b = T[i + 1]![j]!, c = B[i + 1]![j]!, d = B[i]![j]!, h = rad((us[i]! + us[i + 1]!) / 2, s); f.push(orient([a, b, c], h), orient([a, c, d], h)); }
  for (let j = 0; j < RF.Nv; j++) for (const [i, s] of [[0, -1], [RF.Nu, 1]] as [number, number][]) { const a = T[i]![j]!, b = T[i]![j + 1]!, c = B[i]![j + 1]!, d = B[i]![j]!, h = tan(us[i]!, s); f.push(orient([a, b, c], h), orient([a, c, d], h)); }
  return f;
}
// ---------- PLANCHER / TERRASSE / PISCINE ----------
const inBuild = (t: number) => { const a = ((t % 360) + 360) % 360; return a >= P.facets[0]! && a <= P.facets[P.facets.length - 1]!; };
const deckR = (t: number) => { if (inBuild(t)) return P.deck.rBuild; let d = ((t - P.deck.lobeAt + 540) % 360) - 180; const b = Math.abs(d) < P.deck.lobeHalf ? Math.cos(Math.PI / 2 * d / P.deck.lobeHalf) ** 2 : 0; return P.deck.rTerr + P.deck.lobe * b; };
const deckPoly = Array.from({ length: 360 }, (_, i) => polar(deckR(i), i));
const poolPoly = [...Array.from({ length: 21 }, (_, i) => { const t = P.pool.a0 + (P.pool.a1 - P.pool.a0) * i / 20, k = ((t - P.pool.mid) / 20) ** 2; return polar(P.pool.rOut - 900 * k, t); }),
  ...Array.from({ length: 21 }, (_, i) => { const t = P.pool.a1 - (P.pool.a1 - P.pool.a0) * i / 20, k = ((t - P.pool.mid) / 20) ** 2; return polar(P.pool.rIn + 800 * k, t); })];

// ================= EXÉCUTION =================
const A = api as any;
const ex: any = await A.style.listSolidStyles({ scope: "explicit", projection: "summary" });
const byName: Record<string, string> = {}; for (const s of ex.styles) byName[s.name] = s.handle;
async function st(name: string, r: number, g: number, b: number, a = 1) { if (byName[name]) return byName[name]!; const x: any = await A.style.createSolidStyle({ canvas: CAN, name, properties: { solidFill: { kind: "color", color: { r, g, b, a } } } }); byName[name] = x.handle; return x.handle as string; }
const S = {
  roof: await st("Coral – bardeaux cèdre patinés", 0.47, 0.43, 0.39), deck: await st("Coral – platelage bois", 0.40, 0.31, 0.24),
  pile: await st("Coral – pieux", 0.62, 0.58, 0.52), timber: await st("Coral – bois clair (WD)", 0.71, 0.53, 0.35),
  glass: await st("Coral – verre", 0.70, 0.84, 0.90, 0.35), water: await st("Coral – eau", 0.30, 0.72, 0.78, 0.9),
  green: await st("Coral – jardinière végétale", 0.30, 0.45, 0.25), soffit: await st("Coral – sous-face bois", 0.78, 0.66, 0.50),
  grass: byName["Site - grass"] ?? await st("Coral – gazon", 0.45, 0.62, 0.33),
};
const parent: any = await A.layer.create({ parent: CAN, name: "Villa Coral (réf. KKAA Ummahat) – paramétrique" });
const mk = async (name: string) => ((await A.layer.create({ parent: parent.handle, name })) as any).handle as string;
const L = { site: await mk("A-Site 2 (20x20)"), pile: await mk("S-Pilotis"), deck: await mk("A-Plancher terrasse"), roof: await mk("A-Toiture coque"), wood: await mk("A-Bois (éventail, chevrons, claustra)"), glz: await mk("A-Vitrage haut (imposte)") };
const made: string[] = [];
const poly = async (layer: string, items: { name: string; style: string; faces: F[] }[]) => { for (let i = 0; i < items.length; i += 120) { const r: any = await A.solid.createPolyhedra({ layer, polyhedra: items.slice(i, i + 120) }); made.push(...r.handles); } };
const boxes = async (layer: string, b: any[]) => { const r: any = await A.solid.createBoxes({ layer, boxes: b }); made.push(...r.handles); };
const cyls = async (layer: string, c: any[]) => { const r: any = await A.solid.createCylinders({ layer, cylinders: c }); made.push(...r.handles); };
const z0 = P.F - P.slabT;
await boxes(L.site, [{ name: "Site 2 – 20 x 20 m", style: S.grass, min: v3(P.siteMin.x, P.siteMin.y, -200), max: v3(P.siteMin.x + P.siteSize, P.siteMin.y + P.siteSize, 0) }]);
const E = P.entry;
await poly(L.deck, [
  { name: "Plancher + terrasse bois", style: S.deck, faces: prism(deckPoly, z0, P.F) },
  { name: "Piscine", style: S.water, faces: prism(poolPoly, P.pool.bottom, P.pool.top) },
  { name: "Palier d'arrivée", style: S.deck, faces: prism([{ x: P.cx + E.x0, y: P.cy + E.yLand0 }, { x: P.cx + E.x1, y: P.cy + E.yLand0 }, { x: P.cx + E.x1, y: P.cy + E.yLand1 }, { x: P.cx + E.x0, y: P.cy + E.yLand1 }], z0, P.F) },
]);
const nSt = 11, rise = P.F / nSt, run = (E.yLand0 - (P.siteMin.y - P.cy) - 150) / nSt;
await boxes(L.deck, Array.from({ length: nSt }, (_, k) => ({ name: "Marche " + (k + 1), style: S.deck, min: v3(P.cx + E.x0, P.siteMin.y + 150 + k * run, k === 0 ? 0 : k * rise - 60), max: v3(P.cx + E.x1, P.siteMin.y + 150 + (k + 1) * run, (k + 1) * rise) })));
await cyls(L.wood, [{ name: "Jardinière centrale (oculus)", style: S.green, baseCenter: v3(P.cx, P.cy, P.F), radius: P.planterR, height: 450, segments: 48 }]);
// pieux : anneaux polaires sous le platelage (cf. coupe S3/S4, trame dense)
const piles: any[] = [];
for (const r of [1800, 3600, 5500, 7300, 8900]) { const n = Math.max(6, Math.round(2 * Math.PI * r / 2300)); for (let k = 0; k < n; k++) { const t = 360 * k / n + (r % 7) * 3; const inPool = r > P.pool.rIn - 200 && r < P.pool.rOut && ((t - P.pool.a0 + 360) % 360) < P.pool.a1 - P.pool.a0; if (r < deckR(t) - 350) { const c = polar(r, t); piles.push({ name: "Pieu Ø300", style: S.pile, baseCenter: v3(c.x, c.y, -100), radius: 150, height: (inPool ? P.pool.bottom : z0) + 100, segments: 16 }); } } }
for (const [x, y] of [[E.x0 + 250, E.yLand0 + 250], [E.x1 - 250, E.yLand0 + 250]] as [number, number][]) piles.push({ name: "Pieu Ø300", style: S.pile, baseCenter: v3(P.cx + x, P.cy + y, -100), radius: 150, height: z0 + 100, segments: 16 });
await cyls(L.pile, piles);
// solives rayonnantes sous plancher (soleil visible en élévation E2/E3)
const joists: any[] = [];
for (let t = 0; t < 360; t += 5) { const R = deckR(t); joists.push({ name: "Solive rayonnante", style: S.timber, faces: ribbon(line(polar(R - 2600, t), polar(R - 60, t), 2), 45, () => z0 - 280, () => z0) }); }
await poly(L.wood, joists);
// toiture
const roofH: any = await A.solid.createPolyhedra({ layer: L.roof, polyhedra: [{ name: "Toiture coque spirale – bardeaux cèdre", style: S.roof, faces: roofFaces() }] });
made.push(...roofH.handles);
await A.solid.setHiddenEdges({ handles: roofH.handles, mode: "auto", angle: Math.PI * 0.8, showCoplanar: false, smoothEdges: true });
// chevrons rayonnants en sous-face
const raf: any[] = [];
for (let u = 0.004; u < 1; u += 1 / 110) { const t = thOf(u); const a = rOf(u, 0.02), b = rOf(u, 0.985); const pts = line(polar(a, t), polar(b, t), 10); raf.push({ name: "Chevron", style: S.soffit, faces: ribbon(pts, 35, p => soffit(p) - 160, p => soffit(p) + 5) }); }
await poly(L.wood, raf);
// éventail de nervures bois au-dessus de la piscine (fente de la spirale)
const fan: any[] = [];
for (let k = 0; k < P.fan.n; k++) { const t = P.fan.a0 + (P.fan.a1 - P.fan.a0) * k / (P.fan.n - 1); const pts = line(polar(P.fan.r0, t), polar(P.fan.r1, t), 16);
  const h = (p: P2) => { const r = Math.hypot(p.x - P.cx, p.y - P.cy), s = (r - P.fan.r0) / (P.fan.r1 - P.fan.r0); return P.F + 500 + 3300 * Math.sin(Math.PI * Math.min(s * 0.85 + 0.05, 1)) * (0.75 + 0.25 * k / (P.fan.n - 1)); };
  fan.push({ name: "Nervure éventail", style: S.timber, faces: ribbon(pts, 30, p => h(p) - 220, h) }); }
await poly(L.wood, fan);
// impostes vitrées entre murs (h 3,00) et sous-face de coque
const F3 = P.F + P.wallTop;
const outerPts: P2[] = []; for (let k = 0; k < P.facets.length - 1; k++) outerPts.push(...line(polar(P.rOuter, P.facets[k]!), polar(P.rOuter, P.facets[k + 1]!), 4).slice(k ? 1 : 0));
await poly(L.glz, [
  { name: "Imposte vitrée façade", style: S.glass, faces: ribbon(outerPts, 12, () => F3, p => soffit(p) - 10) },
  { name: "Imposte vitrée cour", style: S.glass, faces: ribbon(arc(P.rCourt, P.facets[0]!, P.facets[P.facets.length - 1]!, 3), 12, () => F3, p => soffit(p) - 10) },
]);
// claustra bois vertical (WD-01) devant séjour / entrée, à 35 cm de la façade
const sl: any[] = [];
for (let k = 0; k < P.facets.length - 1; k++) { const a = P.facets[k]!, b = P.facets[k + 1]!; if (a < P.slats[0] || b > P.slats[1]) continue;
  const A_ = polar(P.rOuter + 380, a), B_ = polar(P.rOuter + 380, b); const n = Math.floor(Math.hypot(B_.x - A_.x, B_.y - A_.y) / 160);
  for (let i = 1; i < n; i++) { const c = { x: A_.x + (B_.x - A_.x) * i / n, y: A_.y + (B_.y - A_.y) * i / n }; const d = { x: (B_.x - A_.x) / n * 0.25, y: (B_.y - A_.y) / n * 0.25 };
    const o = { x: c.x - P.cx, y: c.y - P.cy }, ol = Math.hypot(o.x, o.y);
    sl.push({ name: "Lame claustra", style: S.timber, faces: ribbon([{ x: c.x - o.x / ol * 60, y: c.y - o.y / ol * 60 }, { x: c.x + o.x / ol * 60, y: c.y + o.y / ol * 60 }], 20, () => P.F, p => soffit(p) - 20) }); void d; } }
await poly(L.wood, sl);
const g: any = await A.entity.createGroups({ groups: [{ name: "Villa Coral – coque, structure, terrasse", members: made }] });
let minC = 1e9; for (const p of outerPts) minC = Math.min(minC, soffit(p) - P.F); for (const p of arc(P.rCourt, 52, 264, 2)) minC = Math.min(minC, soffit(p) - P.F);
let maxZ = 0; for (let i = 0; i <= 100; i++) for (let j = 0; j <= 20; j++) maxZ = Math.max(maxZ, topH(i / 100, j / 20));
console.log(JSON.stringify({ parent: parent.handle, layers: L, styles: S, group: g.handles, n: made.length, minSoffitAboveFloor: Math.round(minC), ridgeAboveFloor: Math.round(maxZ) }));
