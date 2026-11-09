/* Verrou de Maison17 : phrase d'accès et déchiffrement des données.
   Le dépôt et le site sont publics, mais les données personnelles (mesures, historique, solaire, chauffage,
   albums photos) n'y sont publiées que chiffrées par la tâche (outils/coffre.js). Sans la phrase, elles sont illisibles.
   La phrase est demandée une fois par appareil : on garde ensuite la clé qui en découle (pas la phrase) pendant un an.
   Chiffrement : AES-256-GCM, clé = PBKDF2-SHA256(phrase, SEL, ITERATIONS) — mêmes valeurs que dans outils/coffre.js.
   Les pages lisent leurs fichiers comme avant avec fetch() : ce script déchiffre au passage ceux qui sont protégés,
   et attend que la phrase ait été saisie. window.M17 donne aussi chiffrer() / dechiffrer() (page Photos).
   La page météo seule (?vue=meteo, ?retour=meteo) n'a aucune donnée personnelle : pas de verrou.
   Écrit pour rester lisible par les navigateurs anciens des télés Samsung (ES5, pas de inset, min() doublé). */
(function(){
  if (/[?&](vue|retour)=meteo\b/.test(location.search)) return;

  var SEL = "maison17-sel-v1", ITERATIONS = 210000, PREFIXE = "M17v1:";
  var CLE_LOCALE = "maison17-cle";
  var DUREE_JOURS = 365;   // la phrase est redemandée au bout d'un an sur le même appareil
  var PROTEGES = /\/(data|solaire|chauffage)\.json$|\/historique\/[^\/]+$|\/photos\/albums\.json$/;
  var subtil = window.crypto && window.crypto.subtle;
  var fetchOrigine = window.fetch ? window.fetch.bind(window) : null;

  try { localStorage.removeItem("maison17-acces"); } catch (e) {}   // ancien verrou (simple code), plus utilisé

  /* ===== Outils ===== */
  function octets(texte){ return new TextEncoder().encode(texte); }
  function versHex(b){ return Array.prototype.map.call(new Uint8Array(b), function(x){ return ("0" + x.toString(16)).slice(-2); }).join(""); }
  function depuisHex(h){ var t = new Uint8Array(h.length / 2); for (var i = 0; i < t.length; i++) t[i] = parseInt(h.substr(i * 2, 2), 16); return t; }
  function depuisBase64(s){ var b = atob(s), t = new Uint8Array(b.length); for (var i = 0; i < b.length; i++) t[i] = b.charCodeAt(i); return t; }
  function versBase64(t){ var s = "", n = 0x8000; for (var i = 0; i < t.length; i += n) s += String.fromCharCode.apply(null, t.subarray(i, i + n)); return btoa(s); }
  function lire(){ try { return localStorage.getItem(CLE_LOCALE); } catch (e) { return null; } }
  function ecrire(v){ try { if (v) localStorage.setItem(CLE_LOCALE, v); else localStorage.removeItem(CLE_LOCALE); } catch (e) {} }

  function deriver(phrase){
    return subtil.importKey("raw", octets(phrase), { name: "PBKDF2" }, false, ["deriveBits"]).then(function(k){
      return subtil.deriveBits({ name: "PBKDF2", salt: octets(SEL), iterations: ITERATIONS, hash: { name: "SHA-256" } }, k, 256);
    });
  }
  function importer(brut){ return subtil.importKey("raw", brut, { name: "AES-GCM" }, false, ["encrypt", "decrypt"]); }
  function dechiffrerAvec(cle, texte){
    texte = String(texte).replace(/\s+$/, "");
    if (texte.indexOf(PREFIXE) !== 0) return Promise.reject(new Error("fichier non chiffré"));
    var b = depuisBase64(texte.slice(PREFIXE.length));
    return subtil.decrypt({ name: "AES-GCM", iv: b.subarray(0, 12) }, cle, b.subarray(12)).then(function(c){ return new TextDecoder().decode(c); });
  }
  /* La phrase est bonne si le fichier de contrôle publié par la tâche se déchiffre */
  function verifier(cle){
    return fetchOrigine("controle.txt?t=" + Date.now(), { cache: "no-store" }).then(function(r){
      if (!r.ok) throw { reseau: true };
      return r.text();
    }, function(){ throw { reseau: true }; }).then(function(t){ return dechiffrerAvec(cle, t); }).then(function(t){
      if (t !== "maison17") throw new Error("contrôle");
      return cle;
    });
  }

  /* ===== Clé disponible pour toute la page ===== */
  var donnerCle;
  var pret = new Promise(function(ok){ donnerCle = ok; });
  window.M17 = {
    pret: pret,
    dechiffrer: function(texte){ return pret.then(function(c){ return dechiffrerAvec(c, texte); }); },
    chiffrer: function(texte){
      return pret.then(function(c){
        var iv = crypto.getRandomValues(new Uint8Array(12));
        return subtil.encrypt({ name: "AES-GCM", iv: iv }, c, octets(texte)).then(function(x){
          var t = new Uint8Array(12 + x.byteLength); t.set(iv, 0); t.set(new Uint8Array(x), 12);
          return PREFIXE + versBase64(t);
        });
      });
    }
  };

  /* Les fichiers protégés sont déchiffrés au passage : les pages n'ont rien à changer à leurs fetch() */
  if (fetchOrigine) window.fetch = function(entree, options){
    var url = typeof entree === "string" ? entree : (entree && entree.url) || "";
    var chemin;
    try { chemin = new URL(url, location.href).pathname; } catch (e) { chemin = url.split("?")[0]; }
    if (!PROTEGES.test(chemin)) return fetchOrigine(entree, options);
    return pret.then(function(cle){
      return fetchOrigine(entree, options).then(function(r){
        if (!r.ok) return r;
        return r.text().then(function(t){ return dechiffrerAvec(cle, t); }).then(function(clair){
          return new Response(clair, { status: 200, headers: { "Content-Type": /\.json$/.test(chemin) ? "application/json; charset=utf-8" : "text/plain; charset=utf-8" } });
        });
      });
    });
  };

  /* ===== Démarrage : clé déjà gardée sur l'appareil ? ===== */
  if (!subtil) { montrer("Ce navigateur ne sait pas déchiffrer les données (il faut une adresse https)."); return; }
  var memo = lire(), p = memo ? memo.split("|") : [];
  if (p.length === 2 && /^[0-9a-f]{64}$/.test(p[0]) && Date.now() - (+p[1] || 0) < DUREE_JOURS * 864e5) {
    importer(depuisHex(p[0])).then(function(cle){
      return verifier(cle)["catch"](function(e){
        if (e && e.reseau) return cle;   // hors ligne : on fait confiance à la clé gardée
        throw e;
      });
    }).then(donnerCle, function(){ ecrire(null); montrer("La phrase d'accès a changé : saisis la nouvelle."); });
  } else {
    montrer("");
  }

  /* ===== Écran de saisie ===== */
  function montrer(message){
    document.documentElement.classList.add("verrouille");
    var style = document.createElement("style");
    style.textContent =
      "html.verrouille body>*:not(#verrou){visibility:hidden}" +
      "#verrou{position:fixed;top:0;right:0;bottom:0;left:0;z-index:99;display:flex;align-items:center;justify-content:center;background:#0f1418;color:#e8eef2;font-family:'Bricolage Grotesque',system-ui,sans-serif;padding:16px}" +
      "#verrou form{display:flex;flex-direction:column;align-items:center;width:760px;max-width:100%}" +
      "#verrou form>*{margin:1.6vh 0}" +
      "#verrou .titre{font-size:3vw;font-size:min(3vw,5.3vh);font-weight:600}" +
      "#verrou .sous{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:14px;font-size:min(1.1vw,2vh,14px);letter-spacing:.14em;text-transform:uppercase;color:#8a99a5}" +
      "#verrou input{width:100%;font:inherit;font-size:2.2vw;font-size:min(2.2vw,4vh);text-align:center;letter-spacing:.08em;padding:.4em .5em;border-radius:14px;border:2px solid #26313a;background:#182027;color:#e8eef2;outline:none}" +
      "#verrou input:focus{border-color:#7cc4e8}" +
      "#verrou button{font:inherit;font-size:1.8vw;font-size:min(1.8vw,3.2vh);font-weight:600;padding:.6em 2em;border:0;border-radius:99px;background:#7cc4e8;color:#0f1418;cursor:pointer}" +
      "#verrou button[disabled]{opacity:.6;cursor:default}" +
      "#verrou .err{min-height:1.4em;color:#f08a6a;font-size:1.4vw;font-size:min(1.4vw,2.6vh);text-align:center}" +
      "#verrou .err.info{color:#8a99a5}" +
      "@media (max-width:800px){#verrou .titre{font-size:7vw}#verrou input{font-size:5vw}#verrou button{font-size:5vw}#verrou .err{font-size:4vw}#verrou .sous{font-size:3vw}}";
    document.head.appendChild(style);

    function monter(){
      var bloc = document.createElement("div");
      bloc.id = "verrou";
      bloc.innerHTML =
        '<form autocomplete="off">' +
          '<div class="sous">Maison 17</div>' +
          '<div class="titre">🔒 Phrase d\'accès</div>' +
          '<input type="password" aria-label="Phrase d\'accès" autocapitalize="none" autocorrect="off" spellcheck="false" autofocus>' +
          '<button type="submit">Ouvrir</button>' +
          '<div class="err" role="alert"></div>' +
        '</form>';
      document.body.appendChild(bloc);
      var champ = bloc.querySelector("input"), err = bloc.querySelector(".err"), bouton = bloc.querySelector("button");
      if (message) err.textContent = message;
      champ.focus();
      function essayer(phrase){
        var brut;
        return deriver(phrase).then(function(b){ brut = b; return importer(b); }).then(verifier).then(function(cle){ return { cle: cle, brut: brut }; });
      }
      bloc.querySelector("form").addEventListener("submit", function(ev){
        ev.preventDefault();
        var phrase = champ.value.trim();
        if (!phrase) return;
        bouton.disabled = true;
        err.className = "err info"; err.textContent = "Vérification…";
        essayer(phrase)["catch"](function(e){
          if (e && e.reseau) throw e;
          if (phrase.toLowerCase() !== phrase) return essayer(phrase.toLowerCase());   // majuscule ajoutée par le clavier
          throw e;
        }).then(function(r){
          ecrire(versHex(r.brut) + "|" + Date.now());
          bloc.parentNode.removeChild(bloc);
          document.documentElement.classList.remove("verrouille");
          donnerCle(r.cle);
          window.dispatchEvent(new Event("resize"));   // les courbes se recalent une fois visibles
        }, function(e){
          bouton.disabled = false;
          err.className = "err";
          err.textContent = e && e.reseau ? "Pas de connexion : réessaie dans un instant" : "Phrase incorrecte";
          if (!(e && e.reseau)) { champ.value = ""; }
          champ.focus();
        });
      });
    }
    if (document.body) monter(); else document.addEventListener("DOMContentLoaded", monter);
  }
})();
