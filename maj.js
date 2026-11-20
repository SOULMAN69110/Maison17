/* Mise à jour automatique des pages (toutes, tableau de bord et météo partagée compris).
   À chaque publication, la tâche (pages.yml) inscrit le numéro de version du site dans chaque page
   (<meta name="m17-version">) et dans version.txt. La page compare SON numéro (celui de la page
   réellement affichée, même ressortie de la mémoire de l'appli iPhone) à celui du site :
   au chargement, à chaque retour sur l'appli ou l'onglet, et toutes les 2 min ; s'ils diffèrent,
   elle se recharge en contournant la copie gardée par le navigateur (le code d'accès reste retenu).
   Pas de rechargement pendant une saisie (champ ou liste ouverts) : il attend la vérification suivante.
   Sans numéro (page ouverte en local, hors du site), rien ne se passe.
   Écrit pour les navigateurs anciens des télés (ES5). */
(function(){
  var m = document.querySelector('meta[name="m17-version"]'), ici = m ? m.getAttribute("content") : "";
  if (!ici) return;
  var CLE = "maison17-maj", enCours = false;
  function recharger(v){
    /* au plus un rechargement par minute vers la même version, pour ne jamais boucler si le site tarde */
    var d = null;
    try { d = JSON.parse(sessionStorage.getItem(CLE)); } catch (x) {}
    if (d && d.v === v && Date.now() - d.t < 60 * 1000) return;
    try { sessionStorage.setItem(CLE, JSON.stringify({ v: v, t: Date.now() })); } catch (x) {}
    var s = location.search.replace(/[?&]_v=\d+/g, "").replace(/^&/, "?");
    location.replace(location.pathname + (s ? s + "&" : "?") + "_v=" + Date.now() + location.hash);
  }
  function saisie(){
    var a = document.activeElement, t = a && a.tagName;
    return t === "INPUT" || t === "TEXTAREA" || t === "SELECT";
  }
  function verifier(){
    if (enCours || document.hidden) return;
    enCours = true;
    fetch("version.txt?v=" + Date.now(), { cache: "no-store" })
      .then(function(r){ return r.ok ? r.text() : ""; })
      .then(function(v){
        enCours = false;
        v = (v || "").replace(/\s+/g, "");
        if (/^[0-9a-f]{6,64}$/.test(v) && v !== ici && !saisie()) recharger(v);
      })["catch"](function(){ enCours = false; });
  }
  verifier();
  setInterval(verifier, 2 * 60 * 1000);
  document.addEventListener("visibilitychange", function(){ if (!document.hidden) verifier(); });
  window.addEventListener("pageshow", verifier);        // page ressortie de la mémoire (retour arrière, appli iPhone)
  window.addEventListener("focus", verifier);
})();
