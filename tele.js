/* Raccourcis de la télécommande (télé Samsung) et du clavier, sur toutes les pages sauf la météo partagée :
   touches de couleur   Rouge = Accueil · Vert = Énergie · Jaune = Photos · Bleu = Chauffage (Courbes sans jeton)
   chiffres             1 Accueil · 2 Courbes · 3 Énergie · 4 Bilans · 5 Photos · 6 Chauffage
   Retour               ramène à l'accueil depuis les autres pages, quand la page ne s'en sert pas déjà
                        (diaporama, panneau Réglages, plein écran… la gardent pour se fermer).
   Sur la télécommande One Remote (sans chiffres ni couleurs), les afficher avec la touche « 123 ».
   Rien pendant une saisie (champ de texte, code d'accès, liste).
   Aussi : sélection bien visible de loin (cadre jaune) en mode télécommande, et retour sur le dernier bouton
   utilisé quand on revient sur une page. Mettre <script src="tele.js"></script> dans la page.
   Écrit pour les navigateurs anciens des télés (ES5). */
(function(){
  if (/[?&](vue|retour)=meteo\b/.test(location.search)) return;   // pas sur la météo partagée
  var chauffageOk = false;
  try {
    chauffageOk = window.navigator.standalone === true ||
      (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) ||
      !!localStorage.getItem("maison17-jeton-chauffage");
  } catch (x) {}
  var ACCUEIL = "./", ICI = location.pathname.split("/").pop() || "index.html";
  var CHIFFRES = [ACCUEIL, "historique.html", "energie.html", "bilans.html", "photos.html", chauffageOk ? "chauffage.html" : null];
  var COULEURS = { 403: ACCUEIL, 404: "energie.html", 405: "photos.html", 406: chauffageOk ? "chauffage.html" : "historique.html" };

  /* Sur une appli Tizen, les touches de couleur doivent être demandées ; sans effet (et sans erreur) ailleurs */
  try {
    if (window.tizen && tizen.tvinputdevice) {
      var noms = ["ColorF0Red", "ColorF1Green", "ColorF2Yellow", "ColorF3Blue", "1", "2", "3", "4", "5", "6"];
      for (var i = 0; i < noms.length; i++) { try { tizen.tvinputdevice.registerKey(noms[i]); } catch (x) {} }
    }
  } catch (x) {}

  function aller(lien){
    if (!lien) return;
    var cible = lien === ACCUEIL ? "index.html" : lien;
    if (cible === ICI) return;
    location.href = lien;
  }
  function saisie(e){
    var t = e.target && e.target.tagName;
    if (t === "INPUT" || t === "TEXTAREA" || t === "SELECT") return true;
    return /verrouille/.test(document.documentElement.className);   // écran du code d'accès
  }
  /* ----- Sélection bien visible de loin (mode « télécommande ») -----
     Actif sur la télé, et sur un autre appareil dès qu'on se sert des flèches ; un toucher ou un clic l'enlève
     (pas de cadre jaune après un appui du doigt sur l'iPhone). Mémorisé pour la durée de la visite. */
  var TELE = /Tizen|SMART-TV|SmartTV/i.test(navigator.userAgent), CLE_CLAVIER = "maison17-clavier", CLE_FOCUS = "maison17-focus-";
  var st = document.createElement("style");
  st.textContent =
    "html.clavier a:focus,html.clavier button:focus,html.clavier select:focus,html.clavier input:focus,html.clavier [tabindex]:focus{" +
      "outline:.3vw solid #ffd75e!important;outline-offset:.12vw;box-shadow:0 0 0 .55vw rgba(255,215,94,.28),0 0 1.6vw rgba(255,215,94,.45)!important;" +
      "border-color:#ffd75e!important}" +
    "@media (max-width:800px){html.clavier a:focus,html.clavier button:focus{outline-width:3px}}";
  (document.head || document.documentElement).appendChild(st);
  function clavier(oui){
    var h = document.documentElement, a = /\bclavier\b/.test(h.className);
    if (oui && !a) h.className += " clavier";
    if (!oui && a) h.className = h.className.replace(/ ?\bclavier\b/g, "");
    try { if (oui) sessionStorage.setItem(CLE_CLAVIER, "1"); else sessionStorage.removeItem(CLE_CLAVIER); } catch (x) {}
  }
  var dejaClavier = TELE;
  try { dejaClavier = dejaClavier || sessionStorage.getItem(CLE_CLAVIER) === "1"; } catch (x) {}
  if (dejaClavier) clavier(true);
  document.addEventListener("keydown", function(e){ if (e.keyCode >= 37 && e.keyCode <= 40) clavier(true); }, true);
  if (!TELE) {
    document.addEventListener("touchstart", function(){ clavier(false); }, true);
    document.addEventListener("mousedown", function(){ clavier(false); }, true);
  }

  /* ----- Retour sur le dernier bouton utilisé -----
     En mode télécommande, on note le bouton sélectionné sur chaque page ; en y revenant, il est resélectionné
     (dès qu'il existe : certaines pages construisent leurs boutons après coup). */
  function decrire(el){
    if (!el || el === document.body || !el.tagName) return null;
    var t = el.tagName;
    if (t === "INPUT" || t === "SELECT" || t === "TEXTAREA") return null;
    if (el.id) return "#" + el.id;
    if (el.getAttribute("data-i") !== null && el.className) return t.toLowerCase() + "." + String(el.className).split(" ")[0] + '[data-i="' + el.getAttribute("data-i") + '"]';
    if (t === "A" && el.getAttribute("href")) return 'a[href="' + el.getAttribute("href").replace(/"/g, "") + '"]';
    return null;
  }
  function noter(el){
    if (!/\bclavier\b/.test(document.documentElement.className)) return;
    var d = decrire(el);
    if (d) try { sessionStorage.setItem(CLE_FOCUS + ICI, d); } catch (x) {}
  }
  document.addEventListener("focusin", function(e){ noter(e.target); });
  /* aussi au départ de la page (raccourci, lien) : le bouton sélectionné à ce moment-là */
  window.addEventListener("pagehide", function(){ noter(document.activeElement); });
  window.addEventListener("beforeunload", function(){ noter(document.activeElement); });
  var memo = null;
  try { memo = sessionStorage.getItem(CLE_FOCUS + ICI); } catch (x) {}
  if (memo && dejaClavier) {
    var essais = 0;
    (function restaurer(){
      var el = null;
      try { el = document.querySelector(memo); } catch (x) { return; }
      if (el && el.offsetParent !== null) { try { el.focus(); } catch (x) {} if (document.activeElement === el) return; }
      if (++essais < 12) setTimeout(restaurer, 250);             // jusqu'à 3 s, le temps que la page se construise
    })();
  }

  /* Phase de bouillonnement, sur window : les pages ont déjà traité la touche (et l'ont marquée si elles s'en servent) */
  window.addEventListener("keydown", function(e){
    if (e.defaultPrevented || e.ctrlKey || e.altKey || e.metaKey || saisie(e)) return;
    var k = e.keyCode, lien;
    if (COULEURS[k] !== undefined) lien = COULEURS[k];
    else if (k >= 49 && k <= 54) lien = CHIFFRES[k - 49];            // 1 à 6
    else if (k >= 97 && k <= 102) lien = CHIFFRES[k - 97];           // pavé numérique
    else if (k === 10009 && ICI !== "index.html") lien = ACCUEIL;    // Retour
    else return;
    if (!lien) return;
    e.preventDefault();
    aller(lien);
  });
})();
