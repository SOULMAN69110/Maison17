/* Écran de veille de Maison17 : au bout de quelques minutes sans aucune manipulation sur la page
   (télécommande, clavier, toucher, souris), on ouvre photos.html?veille=1, qui passe en plein écran
   le diaporama de l'album choisi dans ⚙️ Réglages de la page Photos ; la moindre action y ramène ici.
   Réglages « veille » et « veille_min » de photos/reglages.json (ou de l'appareil, sans jeton GitHub).
   Mettre <script src="veille.js"></script> dans la page. Écrit pour les navigateurs anciens des télés (ES5). */
(function(){
  if (/[?&](vue|retour)=meteo\b/.test(location.search)) return;   // pas sur la météo partagée
  var minuteur = null, delai = 0;

  function lireLocal(){
    try {
      if (localStorage.getItem("maison17-jeton-chauffage")) return null;   // avec jeton : réglages communs seulement
      return JSON.parse(localStorage.getItem("maison17-photos-reglages"));
    } catch (e) { return null; }
  }
  function partir(){
    var h = document.documentElement.className;
    if (/verrouille/.test(h)) { relancer(); return; }                 // écran du code d'accès : on attend
    var ici = (location.pathname.split("/").pop() || "") + location.search + location.hash;
    location.href = "photos.html?veille=1&retour=" + encodeURIComponent(ici);
  }
  function relancer(){
    clearTimeout(minuteur);
    if (delai) minuteur = setTimeout(partir, delai);
  }
  var x = new XMLHttpRequest();
  x.open("GET", "photos/reglages.json?t=" + Date.now());
  x.onload = function(){
    var r = {}, l = lireLocal(), k;
    try { if (x.status === 200) r = JSON.parse(x.responseText) || {}; } catch (e) {}
    if (l) for (k in l) r[k] = l[k];
    if (!r.veille || r.veille === "non") return;
    delai = Math.max(1, +r.veille_min || 3) * 60000;
    var evts = ["keydown", "mousedown", "mousemove", "touchstart", "wheel", "scroll"];
    for (var i = 0; i < evts.length; i++) document.addEventListener(evts[i], relancer, true);
    relancer();
  };
  x.send();
})();
