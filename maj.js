/* Mise à jour automatique des pages (le tableau de bord a la sienne dans index.html).
   1. Au chargement : on compare la page affichée (copie gardée par le navigateur) à celle du site ;
      si elle a changé, on la recharge en contournant la copie. Utile surtout pour l'appli de l'écran
      d'accueil de l'iPhone, qui garde les pages en mémoire et ne les relit pas d'elle-même.
   2. Ensuite, toutes les 5 min et à chaque retour sur l'appli, on relit la page, verrou.js, nav.js et
      ce fichier ; si l'un a changé, la page se recharge (le code d'accès reste retenu).
   Écrit pour les navigateurs anciens des télés (ES5). */
(function(){
  var page = location.pathname.split("/").pop() || "index.html";
  var fichiers = [page, "verrou.js", "maj.js", "nav.js"];
  var reference = null;
  function hache(txt){ var h = 0; for (var i = 0; i < txt.length; i++) h = (h * 31 + txt.charCodeAt(i)) | 0; return txt.length + ":" + h; }
  function lire(f, frais){
    return fetch(frais ? f + (f.indexOf("?") < 0 ? "?" : "&") + "v=" + Date.now() : f, frais ? { cache: "no-store" } : {})
      .then(function(r){ if (!r.ok) throw new Error(); return r.text(); });
  }
  function empreinte(){ return Promise.all(fichiers.map(function(f){ return lire(f, true); })).then(function(t){ return hache(t.join("")); }); }
  /* Recharger en contournant la copie : on ajoute ?_v=… à l'adresse (sans effet sur la page) */
  function recharger(){
    var s = location.search.replace(/[?&]_v=\d+/g, "").replace(/^&/, "?");
    location.replace(location.pathname + (s ? s + "&" : "?") + "_v=" + Date.now() + location.hash);
  }
  function verifier(){
    empreinte().then(function(v){
      if (reference === null) { reference = v; return; }
      if (v !== reference) recharger();
    }).catch(function(){});
  }
  /* 1. Page affichée périmée ? (au plus un rechargement par minute, pour ne jamais boucler) */
  var adresse = page + location.search;
  Promise.all([lire(adresse, false), lire(page, true)]).then(function(t){
    var dernier = 0;
    try { dernier = +sessionStorage.getItem("maison17-maj") || 0; } catch (x) {}
    if (hache(t[0]) !== hache(t[1]) && Date.now() - dernier > 60 * 1000) {
      try { sessionStorage.setItem("maison17-maj", String(Date.now())); } catch (x) {}
      recharger(); return;
    }
    verifier();
  }).catch(verifier);
  /* 2. Surveillance ensuite */
  setInterval(verifier, 5 * 60 * 1000);
  document.addEventListener("visibilitychange", function(){ if (!document.hidden) verifier(); });
})();
