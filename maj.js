/* Mise à jour automatique des pages Énergie et Bilans (le tableau de bord a la sienne dans index.html).
   Toutes les 5 min, on relit la page, verrou.js et ce fichier ; si l'un a changé depuis le chargement,
   la page se recharge (le code d'accès reste retenu). Écrit pour les navigateurs anciens des télés. */
(function(){
  var fichiers = [(location.pathname.split("/").pop() || "index.html"), "verrou.js", "maj.js", "nav.js"];
  var reference = null;
  function empreinte(){
    return Promise.all(fichiers.map(function(f){
      return fetch(f + "?v=" + Date.now(), { cache: "no-store" }).then(function(r){ if (!r.ok) throw new Error(); return r.text(); });
    })).then(function(t){
      var txt = t.join(""), h = 0;
      for (var i = 0; i < txt.length; i++) h = (h * 31 + txt.charCodeAt(i)) | 0;
      return txt.length + ":" + h;
    });
  }
  empreinte().then(function(v){ reference = v; }).catch(function(){});
  setInterval(function(){
    empreinte().then(function(v){
      if (reference === null) { reference = v; return; }
      if (v !== reference) location.reload();
    }).catch(function(){});
  }, 5 * 60 * 1000);
})();
