/* Écran de veille et mode nuit de Maison17, après quelques minutes sans aucune manipulation sur la page
   (télécommande, clavier, toucher, souris) :
   - le jour : ouverture de photos.html?veille=1, diaporama plein écran de l'album choisi dans ⚙️ Réglages
     de la page Photos (réglages « veille » et « veille_min » de photos/reglages.json, ou de l'appareil sans
     jeton GitHub) ; la moindre action y ramène ici ;
   - la nuit (mode nuit réglé sur l'appareil, dans les mêmes Réglages : clé « maison17-nuit », par défaut
     de 23 h à 7 h sur la télé, désactivé ailleurs) : écran noir avec seulement l'heure, la date et la
     température dehors (sonde Mobile Alerts), en gris très sombre, qui se promène lentement sur l'écran ; la moindre action
     le fait disparaître (sans déclencher le bouton sous le doigt).
   Mettre <script src="veille.js"></script> dans la page. Écrit pour les navigateurs anciens des télés (ES5). */
(function(){
  if (/[?&](vue|retour)=meteo\b/.test(location.search)) return;   // pas sur la météo partagée
  var TELE = /Tizen|SMART-TV|SmartTV/i.test(navigator.userAgent);
  var photosIci = true;
  try { photosIci = localStorage.getItem("maison17-veille-appareil") !== "non"; } catch (e) {}   // coupé sur cet appareil (⚙️ Réglages de Photos)
  var minuteur = null, delaiPhotos = 0, ecran = null, horloge = null, derniereTemp = null;
  var DELAI_NUIT = 2 * 60000;          // mode nuit sans diaporama : 2 min sans action
  var JOURS = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];
  var MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];

  /* ----- Heures de nuit de cet appareil ----- */
  function plageNuit(){
    var v = null;
    try { v = localStorage.getItem("maison17-nuit"); } catch (e) {}
    if (v === null) return TELE ? { debut: 23, fin: 7 } : null;
    if (v === "non") return null;
    try { var n = JSON.parse(v); return typeof n.debut === "number" && typeof n.fin === "number" ? n : null; } catch (e) { return null; }
  }
  function cestLaNuit(){
    var n = plageNuit(); if (!n) return false;
    var h = new Date().getHours();
    return n.debut < n.fin ? (h >= n.debut && h < n.fin) : (h >= n.debut || h < n.fin);
  }

  /* ----- Écran de nuit ----- */
  function deux(n){ return (n < 10 ? "0" : "") + n; }
  /* L'heure se promène : toutes les 20 s, elle glisse lentement (20 s, mouvement continu) vers un autre point
     de l'écran pris au hasard. Glissement par transform : léger pour la télé. */
  var PAS_S = 20;
  function texteNuit(){
    var d = new Date();
    ecran.firstChild.innerHTML = '<div class="nuit-h">' + d.getHours() + ":" + deux(d.getMinutes()) + '</div>' +
      '<div class="nuit-d">' + JOURS[d.getDay()] + " " + d.getDate() + " " + MOIS[d.getMonth()] + '</div>' +
      (derniereTemp !== null ? '<div class="nuit-t">dehors ' + String(derniereTemp.toFixed(1)).replace(".", ",") + ' °C</div>' : '');
  }
  function deplacer(x, y, anime){
    var b = ecran.firstChild, t = "translate(" + Math.round(x) + "px," + Math.round(y) + "px)";
    var tr = anime ? "transform " + PAS_S + "s linear" : "none";
    b.style.webkitTransition = anime ? "-webkit-transform " + PAS_S + "s linear" : "none";
    b.style.transition = tr;
    b.style.webkitTransform = t; b.style.transform = t;
  }
  function auHasard(){
    var b = ecran.firstChild;
    if (ecran.clientWidth <= b.offsetWidth) { setTimeout(function(){ if (ecran) auHasard(); }, 500); return; }   // page pas encore dessinée
    var l = Math.max(0, ecran.clientWidth - b.offsetWidth), h = Math.max(0, ecran.clientHeight - b.offsetHeight);
    deplacer(Math.random() * l, Math.random() * h, true);
  }
  function dessinerNuit(){
    if (!ecran) return;
    if (!cestLaNuit()) { cacherNuit(); return; }                     // le jour est levé
    texteNuit();
    auHasard();
  }
  /* Température dehors : sonde extérieure Mobile Alerts de la station du salon (data.json, déchiffré au passage
     par verrou.js), comme la tuile « Dehors » de l'accueil. Rien d'affiché si la mesure a plus de 3 h. */
  function lireTemperature(){
    if (!window.fetch) return;
    fetch("data.json?t=" + Date.now(), { cache: "no-store" }).then(function(r){ return r.json(); }).then(function(j){
      var a = (j.devices || []).filter(function(x){ return String(x.deviceid) === "salon"; })[0];
      var m = a && a.measurement;
      derniereTemp = m && typeof m.t2 === "number" && (!m.ts || Date.now() / 1000 - m.ts < 3 * 3600) ? m.t2 : null;
      if (ecran) texteNuit();
    })["catch"](function(){});
  }
  function montrerNuit(){
    if (ecran) return;
    if (!document.getElementById("nuit-style")) {
      var st = document.createElement("style");
      st.id = "nuit-style";
      st.textContent =
        "#nuit{position:fixed;top:0;left:0;width:100%;height:100%;z-index:2147483000;background:#000;cursor:none;overflow:hidden}" +
        "#nuit>div{position:absolute;left:0;top:0;padding:2vw 3vw;text-align:center;color:#3c444a;" +
          "font-family:'Bricolage Grotesque',system-ui,'Segoe UI',Roboto,sans-serif;white-space:nowrap;-webkit-backface-visibility:hidden;backface-visibility:hidden}" +
        "#nuit .nuit-h{font-size:10vw;font-weight:600;line-height:1;letter-spacing:-.02em}" +
        "#nuit .nuit-d{font-size:2vw;margin-top:1vw;color:#30373c}" +
        "#nuit .nuit-t{font-size:3vw;margin-top:1.4vw;color:#34505e}" +
        "@media (max-width:800px) and (orientation:portrait){#nuit .nuit-h{font-size:22vw}#nuit .nuit-d{font-size:4.5vw}#nuit .nuit-t{font-size:6.5vw}}";
      document.head.appendChild(st);
    }
    ecran = document.createElement("div");
    ecran.id = "nuit";
    ecran.setAttribute("aria-hidden", "true");
    ecran.appendChild(document.createElement("div"));
    document.body.appendChild(ecran);
    try { sessionStorage.setItem("maison17-nuit-direct", "1"); } catch (e) {}   // rechargement de la page (nouvelle version) : l'écran de nuit revient aussitôt
    lireTemperature();
    texteNuit();
    var b = ecran.firstChild;                                        // départ au centre, sans glissement
    deplacer((ecran.clientWidth - b.offsetWidth) / 2, (ecran.clientHeight - b.offsetHeight) / 2, false);
    void b.offsetWidth;
    setTimeout(function(){ if (ecran) auHasard(); }, 50);
    var tours = 0;
    horloge = setInterval(function(){
      dessinerNuit();
      if (++tours % 30 === 0) lireTemperature();                     // toutes les 10 min
    }, PAS_S * 1000);
  }
  var avalerJusqua = 0;                 // après le réveil, le clic qui suit l'appui ne doit rien déclencher
  function cacherNuit(){
    if (!ecran) return;
    clearInterval(horloge);
    ecran.parentNode.removeChild(ecran);
    ecran = null;
    avalerJusqua = Date.now() + 700;
    try { sessionStorage.removeItem("maison17-nuit-direct"); } catch (e) {}
    relancer();
  }

  /* ----- Minuteur d'inactivité ----- */
  function delai(){
    if (cestLaNuit()) return delaiPhotos ? Math.min(delaiPhotos, DELAI_NUIT) : DELAI_NUIT;
    return delaiPhotos;
  }
  function partir(){
    if (/verrouille/.test(document.documentElement.className)) { relancer(); return; }   // écran du code d'accès : on attend
    if (cestLaNuit()) { montrerNuit(); return; }
    if (!delaiPhotos) { relancer(); return; }
    var ici = (location.pathname.split("/").pop() || "") + location.search + location.hash;
    location.href = "photos.html?veille=1&retour=" + encodeURIComponent(ici);
  }
  function relancer(){
    clearTimeout(minuteur);
    if (ecran) return;
    var d = delai();
    /* sans diaporama ni nuit en ce moment : on revérifie toutes les 5 min (la nuit peut commencer) */
    minuteur = setTimeout(partir, d || 5 * 60000);
  }
  function action(e){
    if (ecran) {                                     // écran de nuit : la touche ou l'appui ne sert qu'à le réveiller
      if (e.type === "mousemove" || e.type === "scroll") return;
      if (e.type === "keydown" || e.type === "mousedown" || e.type === "touchstart") { e.preventDefault(); e.stopPropagation(); }
      cacherNuit();
      return;
    }
    relancer();
  }
  var evts = ["keydown", "mousedown", "mousemove", "touchstart", "wheel", "scroll", "click"];
  for (var i = 0; i < evts.length; i++) document.addEventListener(evts[i], function(e){
    if (e.type === "click") { if (ecran || Date.now() < avalerJusqua) { e.preventDefault(); e.stopPropagation(); } return; }
    action(e);
  }, true);

  /* Réglages du diaporama de veille */
  function lireLocal(){
    try {
      if (localStorage.getItem("maison17-jeton-chauffage")) return null;   // avec jeton : réglages communs seulement
      return JSON.parse(localStorage.getItem("maison17-photos-reglages"));
    } catch (e) { return null; }
  }
  var x = new XMLHttpRequest();
  x.open("GET", "photos/reglages.json?t=" + Date.now());
  x.onload = x.onerror = function(){
    var r = {}, l = lireLocal(), k;
    try { if (x.status === 200) r = JSON.parse(x.responseText) || {}; } catch (e) {}
    if (l) for (k in l) r[k] = l[k];
    delaiPhotos = photosIci && r.veille && r.veille !== "non" ? Math.max(1, +r.veille_min || 3) * 60000 : 0;
    relancer();
  };
  x.send();

  /* Retour du diaporama de veille à l'heure de la nuit, ou page rechargée pendant la nuit : écran de nuit tout de suite */
  var direct = false;
  try { direct = sessionStorage.getItem("maison17-nuit-direct") === "1"; } catch (e) {}
  if (direct && cestLaNuit()) {
    if (document.body) montrerNuit();
    else document.addEventListener("DOMContentLoaded", montrerNuit);
  }
})();
