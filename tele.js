/* Raccourcis de la télécommande (télé Samsung) et du clavier, sur toutes les pages sauf la météo partagée :
   touches de couleur   Rouge = Accueil · Vert = Énergie · Jaune = Photos · Bleu = Chauffage (Courbes sans jeton)
   chiffres             1 Accueil · 2 Courbes · 3 Énergie · 4 Bilans · 5 Photos · 6 Chauffage
   Retour               ramène à l'accueil depuis les autres pages, quand la page ne s'en sert pas déjà
                        (diaporama, panneau Réglages, plein écran… la gardent pour se fermer).
   Sur la télécommande One Remote (sans chiffres ni couleurs), les afficher avec la touche « 123 ».
   Rien pendant une saisie (champ de texte, code d'accès, liste). Mettre <script src="tele.js"></script> dans la page.
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
