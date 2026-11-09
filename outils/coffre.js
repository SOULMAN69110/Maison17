#!/usr/bin/env node
/* Coffre chiffré de Maison17 (Node, sans bibliothèque à installer).

   Le dépôt et le site sont publics : toutes les données personnelles (mesures, historique,
   solaire, chauffage, albums photos) n'y sont publiées que chiffrées. La clé vient de la phrase
   de passe (secret GitHub MAISON17_PHRASE) ; les pages la redemandent une fois par appareil
   (verrou.js) et déchiffrent dans le navigateur.

   Chiffrement : AES-256-GCM, clé = PBKDF2-SHA256(phrase, SEL, ITERATIONS) — mêmes valeurs dans verrou.js.
   Format d'un fichier chiffré : "M17v1:" + base64(iv 12 octets + données chiffrées + étiquette 16 octets).

   L'historique est rangé chiffré sur la branche « donnees » (un seul commit, remplacé à chaque passage).
   Commandes :
     node outils/coffre.js ouvrir <coffre> <dossier>   déchiffre le coffre dans le dossier (historique/, photos/albums.*)
     node outils/coffre.js fermer <dossier> <coffre>   rechiffre dans le coffre les fichiers qui ont changé
     node outils/coffre.js chiffrer <fichier>…         chiffre des fichiers sur place (pour le site)
     node outils/coffre.js controle <fichier>          écrit le fichier qui permet aux pages de vérifier la phrase
     node outils/coffre.js entrees                     déchiffre AJOUTER / RETIRER (venus de photos.html) en JSON sur la sortie
   Rien de clair n'est jamais écrit dans le journal de la tâche (public). */
"use strict";
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const SEL = "maison17-sel-v1";
const ITERATIONS = 210000;
const PREFIXE = "M17v1:";
const EMPREINTES = ".coffre-empreintes.json";

function cle() {
  const phrase = (process.env.MAISON17_PHRASE || "").trim();
  if (!phrase) { console.error("Coffre : secret MAISON17_PHRASE absent, arrêt (rien n'est publié en clair)."); process.exit(1); }
  return crypto.pbkdf2Sync(phrase, SEL, ITERATIONS, 32, "sha256");
}
let CLE = null;
function k() { return CLE || (CLE = cle()); }

function chiffrer(tampon) {
  const iv = crypto.randomBytes(12);
  const c = crypto.createCipheriv("aes-256-gcm", k(), iv);
  const corps = Buffer.concat([c.update(tampon), c.final()]);
  return PREFIXE + Buffer.concat([iv, corps, c.getAuthTag()]).toString("base64");
}
function dechiffrer(texte) {
  texte = String(texte).trim();
  if (!texte.startsWith(PREFIXE)) throw new Error("fichier non chiffré");
  const b = Buffer.from(texte.slice(PREFIXE.length), "base64");
  const d = crypto.createDecipheriv("aes-256-gcm", k(), b.subarray(0, 12));
  d.setAuthTag(b.subarray(b.length - 16));
  return Buffer.concat([d.update(b.subarray(12, b.length - 16)), d.final()]);
}
const empreinte = (t) => crypto.createHash("sha256").update(t).digest("hex");

/* Fichiers du coffre : tout historique/, plus la liste et la copie des albums photos */
function liste(racine) {
  const res = [];
  const hist = path.join(racine, "historique");
  if (fs.existsSync(hist)) for (const n of fs.readdirSync(hist).sort()) {
    if (fs.statSync(path.join(hist, n)).isFile()) res.push("historique/" + n);
  }
  for (const n of ["photos/albums.txt", "photos/albums.json"]) if (fs.existsSync(path.join(racine, n))) res.push(n);
  return res;
}

function ouvrir(coffre, dossier) {
  const vus = {};
  for (const rel of liste(coffre)) {
    const clair = dechiffrer(fs.readFileSync(path.join(coffre, rel), "utf8"));
    fs.mkdirSync(path.dirname(path.join(dossier, rel)), { recursive: true });
    fs.writeFileSync(path.join(dossier, rel), clair);
    vus[rel] = empreinte(clair);
  }
  fs.writeFileSync(path.join(dossier, EMPREINTES), JSON.stringify(vus));
  console.log("Coffre ouvert : " + Object.keys(vus).length + " fichier(s)");
}

function fermer(dossier, coffre) {
  let vus = {};
  try { vus = JSON.parse(fs.readFileSync(path.join(dossier, EMPREINTES), "utf8")); } catch (e) {}
  let n = 0;
  for (const rel of liste(dossier)) {
    const clair = fs.readFileSync(path.join(dossier, rel));
    if (vus[rel] === empreinte(clair) && fs.existsSync(path.join(coffre, rel))) continue;   // inchangé : on garde le même fichier chiffré
    fs.mkdirSync(path.dirname(path.join(coffre, rel)), { recursive: true });
    fs.writeFileSync(path.join(coffre, rel), chiffrer(clair) + "\n");
    n++;
  }
  console.log("Coffre fermé : " + n + " fichier(s) rechiffré(s)");
}

const [cmd, ...args] = process.argv.slice(2);
k();   // sans phrase, arrêt immédiat quelle que soit la commande
if (cmd === "ouvrir") ouvrir(args[0], args[1]);
else if (cmd === "fermer") fermer(args[0], args[1]);
else if (cmd === "chiffrer") {
  for (const f of args) if (fs.existsSync(f)) {
    const t = fs.readFileSync(f);
    if (!t.toString("utf8", 0, PREFIXE.length).startsWith(PREFIXE)) fs.writeFileSync(f, chiffrer(t) + "\n");
  }
  console.log("Chiffré : " + args.filter((f) => fs.existsSync(f)).length + " fichier(s)");
}
else if (cmd === "controle") fs.writeFileSync(args[0], chiffrer(Buffer.from("maison17")) + "\n");
else if (cmd === "entrees") {
  const sortie = {};
  for (const n of ["AJOUTER", "RETIRER"]) {
    const v = (process.env[n] || "").trim();
    sortie[n] = v.startsWith(PREFIXE) ? dechiffrer(v).toString("utf8") : v;
  }
  process.stdout.write(JSON.stringify(sortie));
}
else { console.error("Commande inconnue : " + cmd); process.exit(2); }
