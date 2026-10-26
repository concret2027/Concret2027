// Compteur du quiz de Concret (concret2027.fr), déployé sur Cloudflare Workers avec une base D1 liée sous le nom DB.
// Il compte les réponses sans rien garder de la personne : ni adresse IP, ni identifiant, seulement un total par option.
// Table (console D1) : CREATE TABLE compte (cle TEXT NOT NULL, choix INTEGER NOT NULL, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (cle, choix));
// POST /hit?k=<clé>&n=<nombre d'options>&i=<option choisie> : ajoute 1 à l'option, renvoie { v: [total de chaque option] }.
// GET  /get?k=<clé>&n=<nombre d'options> : renvoie { v: [...] } sans rien ajouter.
const ORIGINES = ['https://concret2027.fr', 'https://www.concret2027.fr'];
const CLE = /^(quiz|score)-[a-z0-9-]{1,80}$/;

export default {
  async fetch(req, env) {
    const url = new URL(req.url), o = req.headers.get('Origin') || '';
    const h = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'Access-Control-Allow-Origin': ORIGINES.includes(o) ? o : ORIGINES[0], 'Vary': 'Origin' };
    const non = (s) => new Response('{"erreur":"requête refusée"}', { status: s, headers: h });
    if (req.method === 'OPTIONS') return new Response(null, { headers: { ...h, 'Access-Control-Allow-Methods': 'GET, POST', 'Access-Control-Max-Age': '86400' } });
    const k = url.searchParams.get('k') || '', n = Number(url.searchParams.get('n')), i = Number(url.searchParams.get('i'));
    if (!CLE.test(k) || !Number.isInteger(n) || n < 1 || n > 12) return non(400);
    const lire = env.DB.prepare('SELECT choix, n FROM compte WHERE cle = ?1').bind(k);
    let res;
    if (url.pathname === '/hit') {
      if (req.method !== 'POST' || !Number.isInteger(i) || i < 0 || i >= n) return non(400);
      const ajout = env.DB.prepare('INSERT INTO compte (cle, choix, n) VALUES (?1, ?2, 1) ON CONFLICT (cle, choix) DO UPDATE SET n = n + 1').bind(k, i);
      res = (await env.DB.batch([ajout, lire]))[1];
    } else if (url.pathname === '/get') res = await lire.all();
    else return non(404);
    const v = new Array(n).fill(0);
    (res.results || []).forEach((r) => { if (r.choix < n) v[r.choix] = r.n; });
    return new Response(JSON.stringify({ v }), { headers: h });
  }
};
