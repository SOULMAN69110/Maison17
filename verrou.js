/* Verrou à code pour le tableau de bord et les courbes.
   C'est un simple écran d'accès, pas une vraie sécurité : le dépôt reste public.
   Le code n'est pas écrit ici en clair, seulement son empreinte SHA-256 (préfixe "maison17:").
   Pour changer le code : calculer sha256("maison17:" + nouveau_code) et remplacer EMPREINTE. */
(function(){
  var EMPREINTE = "d9f45b76d54f573dd3192137bc1334db02598ca6ec459332d5845cb6923ba294";
  var CLE = "maison17-acces";
  var DUREE_JOURS = 365;   // le code est redemandé au bout d'un an sur le même appareil

  function lire(){ try { return localStorage.getItem(CLE); } catch (e) { return null; } }
  function ecrire(v){ try { localStorage.setItem(CLE, v); } catch (e) {} }

  var memo = lire();
  if (memo) {
    var p = memo.split("|");
    if (p[0] === EMPREINTE && Date.now() - (+p[1] || 0) < DUREE_JOURS * 864e5) return;   // déjà déverrouillé
  }

  document.documentElement.classList.add("verrouille");
  var style = document.createElement("style");
  style.textContent =
    "html.verrouille body>*:not(#verrou){visibility:hidden}" +
    "#verrou{position:fixed;inset:0;z-index:99;display:flex;align-items:center;justify-content:center;background:#0f1418;color:#e8eef2;font-family:'Bricolage Grotesque',system-ui,sans-serif;padding:16px}" +
    "#verrou form{display:flex;flex-direction:column;align-items:center;gap:min(2vw,3.6vh);width:min(100%,520px)}" +
    "#verrou .titre{font-size:min(3vw,5.3vh);font-weight:600}" +
    "#verrou .sous{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:min(1.1vw,2vh,14px);letter-spacing:.14em;text-transform:uppercase;color:#8a99a5}" +
    "#verrou input{width:100%;font:inherit;font-size:min(4vw,7vh);text-align:center;letter-spacing:.35em;padding:.3em .4em;border-radius:14px;border:2px solid #26313a;background:#182027;color:#e8eef2;outline:none}" +
    "#verrou input:focus{border-color:#7cc4e8}" +
    "#verrou button{font:inherit;font-size:min(1.8vw,3.2vh);font-weight:600;padding:.6em 2em;border:0;border-radius:99px;background:#7cc4e8;color:#0f1418;cursor:pointer}" +
    "#verrou .err{min-height:1.4em;color:#f08a6a;font-size:min(1.4vw,2.6vh)}" +
    "@media (max-width:800px){#verrou .titre{font-size:7vw}#verrou input{font-size:10vw}#verrou button{font-size:5vw}#verrou .err{font-size:4vw}#verrou .sous{font-size:3vw}}";
  document.head.appendChild(style);

  function sha256(texte){
    return crypto.subtle.digest("SHA-256", new TextEncoder().encode(texte)).then(function(b){
      return Array.prototype.map.call(new Uint8Array(b), function(x){ return ("0" + x.toString(16)).slice(-2); }).join("");
    });
  }

  function monter(){
    var bloc = document.createElement("div");
    bloc.id = "verrou";
    bloc.innerHTML =
      '<form autocomplete="off">' +
        '<div class="sous">Maison 17</div>' +
        '<div class="titre">🔒 Code d\'accès</div>' +
        '<input type="password" inputmode="numeric" aria-label="Code d\'accès" autofocus>' +
        '<button type="submit">Ouvrir</button>' +
        '<div class="err" role="alert"></div>' +
      '</form>';
    document.body.appendChild(bloc);
    var champ = bloc.querySelector("input"), err = bloc.querySelector(".err");
    champ.focus();
    bloc.querySelector("form").addEventListener("submit", function(ev){
      ev.preventDefault();
      sha256("maison17:" + champ.value.trim()).then(function(h){
        if (h === EMPREINTE) {
          ecrire(EMPREINTE + "|" + Date.now());
          bloc.remove();
          document.documentElement.classList.remove("verrouille");
          window.dispatchEvent(new Event("resize"));   // les courbes se recalent une fois visibles
        } else {
          err.textContent = "Code incorrect";
          champ.value = ""; champ.focus();
        }
      }).catch(function(){ err.textContent = "Navigateur trop ancien pour vérifier le code"; });
    });
  }
  if (document.body) monter(); else document.addEventListener("DOMContentLoaded", monter);
})();
