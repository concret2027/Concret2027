// Compteur et classement du quiz de Concret (concret2027.fr), déployé sur Cloudflare Workers avec une base D1 liée sous le nom DB.
// Il ne garde rien qui identifie la personne : ni adresse IP, ni e-mail ; un total par option, et pour le classement un identifiant
// tiré au hasard par le navigateur, le score de chaque jour et, si la personne en choisit un, un pseudo.
// Tables (console D1) :
//   CREATE TABLE compte (cle TEXT NOT NULL, choix INTEGER NOT NULL, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (cle, choix));
//   CREATE TABLE joueur (id TEXT PRIMARY KEY, pseudo TEXT, pseudo_norm TEXT UNIQUE, cree TEXT NOT NULL);
//   CREATE TABLE partie (id TEXT NOT NULL, jour TEXT NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL, PRIMARY KEY (id, jour));
//   CREATE INDEX partie_jour ON partie (jour);
// POST /hit?k=<clé>&n=<nombre d'options>&i=<option choisie> : ajoute 1 à l'option, renvoie { v: [total de chaque option] }.
// GET  /get?k=<clé>&n=<nombre d'options> : renvoie { v: [...] } sans rien ajouter.
// POST /partie?id=&jour=AAAA-MM-JJ&c=<page:choix,...>&g=<points des questions sur les notes> : enregistre le premier essai du jour ;
//      le score des questions des pages est recalculé ici à partir de data.json (même tirage que le site).
// GET  /classement?id=&jour= : semaine (du lundi au dimanche), mois et depuis le début : les 20 premiers et la place de la personne.
// POST /pseudo?id=&pseudo= : choisit, change ou retire (pseudo vide) le pseudo affiché dans le classement.
// POST /oubli?id= : efface le pseudo et tous les scores de cet identifiant.
const ORIGINES = ['https://concret2027.fr', 'https://www.concret2027.fr'];
const CLE = /^(quiz|score)-[a-z0-9-]{1,80}$/;
const ID = /^[A-Za-z0-9_-]{16,40}$/;
const JOUR = /^\d{4}-\d{2}-\d{2}$/;
const PAGES = ['vie', 'finances', 'sante', 'education', 'securite', 'defense'];
// Pseudos refusés : insultes, et noms de personnalités politiques (le classement reste non partisan).
const INTERDITS_MOTS = ['con', 'cons', 'conne', 'pd', 'fdp', 'ntm', 'tg', 'nazi', 'nazis', 'ss', 'kkk', 'pute', 'putes', 'bite', 'nique', 'niquer'];
const INTERDITS = ['connard', 'connasse', 'salope', 'salaud', 'putain', 'encule', 'merde', 'batard', 'couille', 'tamere', 'pedophile', 'hitler', 'nazisme', 'negre', 'bougnoul', 'youpin', 'gouine', 'tapette', 'pedale', 'enfoire', 'abruti', 'debile', 'cretin', 'admin', 'moderateur', 'concret',
  'lepen', 'bardella', 'melenchon', 'edouardphilippe', 'macron', 'glucksmann', 'attal', 'retailleau', 'lisnard', 'zemmour', 'knafo', 'hollande', 'ruffin', 'fabienroussel', 'tondelier', 'darmanin', 'villepin', 'lecornu', 'brunolemaire', 'dupontaignan', 'nathaliearthaud', 'olivierfaure', 'segolene', 'guedj', 'emmanuelmaurel', 'sarkozy', 'chirac', 'mitterrand', 'bayrou', 'barnier', 'elisabethborne', 'castex', 'valls', 'ciotti', 'marionmarechal', 'jadot', 'benoithamon', 'fillon', 'poutou', 'asselineau', 'philippot', 'wauquiez', 'pecresse', 'hidalgo', 'quatennens', 'bompard', 'panot', 'louisboyard', 'bellamy', 'olivierveran'];
const norm = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

let feed = null, feedT = 0;
async function donnees() {
  if (feed && Date.now() - feedT < 600e3) return feed;
  const r = await fetch('https://concret2027.fr/data.json', { cf: { cacheTtl: 300 } });
  if (!r.ok) throw new Error('data.json ' + r.status);
  feed = await r.json(); feedT = Date.now(); return feed;
}
const jourUTC = (j) => Date.UTC(+j.slice(0, 4), +j.slice(5, 7) - 1, +j.slice(8, 10));
const isoUTC = (t) => new Date(t).toISOString().slice(0, 10);

async function classement(env, id, jour) {
  const t = jourUTC(jour), lundi = isoUTC(t - ((new Date(t).getUTCDay() + 6) % 7) * 864e5);
  const periodes = { semaine: [lundi, isoUTC(jourUTC(lundi) + 6 * 864e5)], mois: [jour.slice(0, 8) + '01', jour.slice(0, 8) + '31'], total: ['2026-01-01', '2999-12-31'] };
  const out = {};
  for (const [nom, [de, a]] of Object.entries(periodes)) {
    const { results } = await env.DB.prepare('SELECT p.id, SUM(p.score) AS pts, COUNT(*) AS n, j.pseudo FROM partie p LEFT JOIN joueur j ON j.id = p.id WHERE p.jour BETWEEN ?1 AND ?2 GROUP BY p.id ORDER BY pts DESC, n ASC').bind(de, a).all();
    const rang = (pts) => 1 + results.filter((r) => r.pts > pts).length;
    const moi = results.find((r) => r.id === id);
    out[nom] = { de, a, joueurs: results.length, top: results.slice(0, 20).map((r) => ({ rang: rang(r.pts), pseudo: r.pseudo || null, points: r.pts, jours: r.n, moi: r.id === id })),
      moi: moi ? { rang: rang(moi.pts), points: moi.pts, jours: moi.n } : null };
  }
  const j = await env.DB.prepare('SELECT pseudo FROM joueur WHERE id = ?1').bind(id).first();
  out.pseudo = j ? j.pseudo : null;
  return out;
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url), o = req.headers.get('Origin') || '', q = (k) => url.searchParams.get(k) || '';
    const h = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'Access-Control-Allow-Origin': ORIGINES.includes(o) ? o : ORIGINES[0], 'Vary': 'Origin' };
    const rep = (x, s) => new Response(JSON.stringify(x), { status: s || 200, headers: h });
    const non = (s, m) => rep({ erreur: m || 'requête refusée' }, s);
    if (req.method === 'OPTIONS') return new Response(null, { headers: { ...h, 'Access-Control-Allow-Methods': 'GET, POST', 'Access-Control-Max-Age': '86400' } });
    const chemin = url.pathname;

    // Compteurs des réponses.
    if (chemin === '/hit' || chemin === '/get') {
      const k = q('k'), n = Number(q('n')), i = Number(q('i'));
      if (!CLE.test(k) || !Number.isInteger(n) || n < 1 || n > 12) return non(400);
      const lire = env.DB.prepare('SELECT choix, n FROM compte WHERE cle = ?1').bind(k);
      let res;
      if (chemin === '/hit') {
        if (req.method !== 'POST' || !Number.isInteger(i) || i < 0 || i >= n) return non(400);
        const ajout = env.DB.prepare('INSERT INTO compte (cle, choix, n) VALUES (?1, ?2, 1) ON CONFLICT (cle, choix) DO UPDATE SET n = n + 1').bind(k, i);
        res = (await env.DB.batch([ajout, lire]))[1];
      } else res = await lire.all();
      const v = new Array(n).fill(0);
      (res.results || []).forEach((r) => { if (r.choix < n) v[r.choix] = r.n; });
      return rep({ v });
    }

    // Classement.
    const id = q('id');
    if (!ID.test(id)) return non(400);
    if (chemin === '/classement') {
      const jour = q('jour'); if (!JOUR.test(jour)) return non(400);
      return rep(await classement(env, id, jour));
    }
    if (req.method !== 'POST') return non(405);
    if (chemin === '/partie') {
      const jour = q('jour'), auj = Date.now();
      // Le jour du quiz, à l'heure de l'appareil : il ne peut s'écarter que d'un jour de la date du serveur (fuseaux horaires).
      if (!JOUR.test(jour) || Math.abs(jourUTC(jour) - jourUTC(isoUTC(auj))) > 864e5) return non(400, 'jour');
      const S = (await donnees()).series, idx = Math.round((jourUTC(jour) - Date.UTC(2026, 0, 1)) / 864e5);
      const choix = {}; q('c').split(',').forEach((x) => { const [p, c] = x.split(':'); if (PAGES.includes(p)) choix[p] = Number(c); });
      let score = 0, total = 0;
      for (const p of PAGES) {
        const B = (S[p] || {}).QUIZ; if (!B || !B.length) continue;
        const Q = B[((idx % B.length) + B.length) % B.length]; total++;
        if (choix[p] === Q.a) score++;
      }
      // Les deux questions sur les notes sont fabriquées par le navigateur à partir des notes : leurs points sont déclarés.
      const g = Number(q('g')); if (!Number.isInteger(g) || g < 0 || g > 2) return non(400);
      score += g; total += 2;
      await env.DB.batch([
        env.DB.prepare('INSERT OR IGNORE INTO joueur (id, cree) VALUES (?1, ?2)').bind(id, isoUTC(auj)),
        env.DB.prepare('INSERT OR IGNORE INTO partie (id, jour, score, total) VALUES (?1, ?2, ?3, ?4)').bind(id, jour, score, total)
      ]);
      const p = await env.DB.prepare('SELECT score FROM partie WHERE id = ?1 AND jour = ?2').bind(id, jour).first();
      return rep({ score: p.score, total, classement: await classement(env, id, jour) });
    }
    if (chemin === '/pseudo') {
      const pseudo = q('pseudo').trim().replace(/\s+/g, ' ');
      if (!pseudo) { await env.DB.prepare('UPDATE joueur SET pseudo = NULL, pseudo_norm = NULL WHERE id = ?1').bind(id).run(); return rep({ pseudo: null }); }
      if (!/^[\p{L}\p{N} ._-]{3,20}$/u.test(pseudo)) return non(400, 'De 3 à 20 caractères : lettres, chiffres, espace, point, tiret.');
      const n = norm(pseudo), sans = n.replace(/[^a-z0-9]/g, ''), mots = n.split(/[^a-z0-9]+/);
      if (INTERDITS.some((x) => sans.includes(norm(x))) || mots.some((m) => INTERDITS_MOTS.includes(m))) return non(400, 'Ce pseudo n\'est pas accepté (pas d\'insulte ni de nom de personnalité politique).');
      const pris = await env.DB.prepare('SELECT id FROM joueur WHERE pseudo_norm = ?1').bind(sans).first();
      if (pris && pris.id !== id) return non(409, 'Ce pseudo est déjà pris.');
      await env.DB.prepare('INSERT INTO joueur (id, pseudo, pseudo_norm, cree) VALUES (?1, ?2, ?3, ?4) ON CONFLICT (id) DO UPDATE SET pseudo = ?2, pseudo_norm = ?3').bind(id, pseudo, sans, isoUTC(Date.now())).run();
      return rep({ pseudo });
    }
    if (chemin === '/oubli') {
      await env.DB.batch([env.DB.prepare('DELETE FROM partie WHERE id = ?1').bind(id), env.DB.prepare('DELETE FROM joueur WHERE id = ?1').bind(id)]);
      return rep({ efface: true });
    }
    return non(404);
  }
};
