/* Boutons vers les autres pages, communs à Courbes, Énergie, Bilans et Chauffage
   (même allure que ceux du tableau de bord : emoji au-dessus, mot en dessous, largeur égale).
   Taille réglable par la page avec .nav-pages{font-size:…} (tout est en em).
   Mettre <nav class="nav-pages"></nav> (ajouter la classe « droite » pour aligner à droite)
   puis <script src="nav.js"></script> après. La page en cours n'a pas de bouton.
   Écrit pour les navigateurs anciens des télés Samsung (ES5, pas de gap en flexbox). */
(function(){
  var PAGES = [
    { lien: "./",              emo: "🏠", texte: "Accueil",  fichier: "index.html" },
    { lien: "historique.html", emo: "📈", texte: "Courbes" },
    { lien: "energie.html",    emo: "☀️", texte: "Énergie" },
    { lien: "bilans.html",     emo: "📊", texte: "Bilans" },
    { lien: "photos.html",     emo: "🖼️", texte: "Photos" },
    { lien: "chauffage.html",  emo: "🔥", texte: "Chauffage", chauffage: true }
  ];
  /* Chauffage : seulement là où le jeton de réglage a été saisi, ou dans l'appli installée (comme sur le tableau de bord) */
  var chauffageOk = false;
  try {
    chauffageOk = window.navigator.standalone === true ||
      (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) ||
      !!localStorage.getItem("maison17-jeton-chauffage");
  } catch (x) {}
  var ici = location.pathname.split("/").pop() || "index.html";

  var style = document.createElement("style");
  style.textContent =
    ".nav-pages{display:flex;margin-top:.8em;font-size:15px}" +
    ".nav-pages.droite{justify-content:flex-end}" +
    ".nav-pages a{flex:1 1 0;min-width:0;max-width:8em;display:flex;flex-direction:column;align-items:center;justify-content:center;" +
      "text-align:center;font-family:'Bricolage Grotesque',system-ui,'Segoe UI',Roboto,sans-serif;font-size:1em;font-weight:500;line-height:1.15;" +
      "color:#e8eef2;text-decoration:none;background:#182027;border:2px solid #26313a;border-radius:.8em;padding:.47em .4em;letter-spacing:0;text-transform:none}" +
    ".nav-pages a+a{margin-left:.53em}" +
    ".nav-pages a:focus,.nav-pages a:hover{border-color:#7cc4e8;box-shadow:0 0 0 2px #7cc4e8;outline:none}" +
    ".nav-pages a i{font-style:normal;font-size:1.2em;line-height:1;margin-bottom:.2em}" +
    "@media (max-width:800px){.nav-pages{width:100%;font-size:3.4vw}.nav-pages.droite{justify-content:flex-start}.nav-pages a{max-width:none;padding:1.8vw 1vw;border-radius:2.5vw}.nav-pages a+a{margin-left:2vw}}";
  document.head.appendChild(style);

  var html = "";
  for (var i = 0; i < PAGES.length; i++) {
    var p = PAGES[i];
    if ((p.fichier || p.lien) === ici) continue;
    if (p.chauffage && !chauffageOk) continue;
    html += '<a href="' + p.lien + '"' + (p.externe ? ' target="_blank" rel="noopener"' : '') + '><i>' + p.emo + '</i>' + p.texte + '</a>';
  }
  var zones = document.querySelectorAll(".nav-pages");
  for (var j = 0; j < zones.length; j++) { zones[j].innerHTML = html; zones[j].setAttribute("aria-label", "Autres pages"); }
})();
