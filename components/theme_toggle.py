# -*- coding: utf-8 -*-
"""
components/theme_toggle.py

Toggle visual dia/noche (sol/luna) para alternar entre el modo claro
(paleta morada pastel, default) y el modo oscuro (paleta neon original
de ImportPredic v1.0-1.3).

Funcionamiento:
- El interruptor esta inspirado en el diseno de referencia proporcionado
  por el usuario: pildora redondeada con circulo deslizante, cielo con
  nubes en modo dia y cielo estrellado con luna en modo noche.
- Al hacer clic, un script JS agrega o quita la clase "dark-mode" al
  <body> del documento PADRE de Streamlit (los componentes con
  components.html corren en un <iframe>, por eso se usa
  window.parent.document en vez de document).
- La preferencia se guarda en sessionStorage del documento padre para
  que persista mientras dure la sesion del navegador, incluso al
  cambiar de pagina (cada pagina de Streamlit recarga el iframe del
  componente, pero el <body> padre y su sessionStorage persisten).
"""

import streamlit as st
import streamlit.components.v1 as components


_TOGGLE_HTML = """
<div id="importpredic-theme-toggle-wrapper" style="display:flex; align-items:center; justify-content:flex-end; padding: 4px 8px;">
  <button id="ip-theme-switch" aria-label="Cambiar tema claro/oscuro" style="
      position: relative;
      width: 74px;
      height: 34px;
      border-radius: 34px;
      border: none;
      cursor: pointer;
      padding: 0;
      background: linear-gradient(180deg, #6EC6FF 0%, #A7DFFF 100%);
      box-shadow: inset 0 2px 6px rgba(0,0,0,0.15), 0 2px 6px rgba(0,0,0,0.08);
      transition: background 0.5s cubic-bezier(0.65,0,0.35,1);
      overflow: hidden;
  ">
    <span id="ip-clouds" style="
        position:absolute; inset:0; opacity:1;
        transition: opacity 0.5s ease;
        background-image:
          radial-gradient(circle at 70% 70%, rgba(255,255,255,0.9) 6px, transparent 7px),
          radial-gradient(circle at 55% 60%, rgba(255,255,255,0.85) 8px, transparent 9px),
          radial-gradient(circle at 40% 75%, rgba(255,255,255,0.8) 5px, transparent 6px);
    "></span>
    <span id="ip-stars" style="
        position:absolute; inset:0; opacity:0;
        transition: opacity 0.5s ease;
        background-image:
          radial-gradient(circle at 20% 30%, #fff 1px, transparent 2px),
          radial-gradient(circle at 32% 60%, #fff 1px, transparent 2px),
          radial-gradient(circle at 45% 25%, #fff 1.4px, transparent 2px),
          radial-gradient(circle at 60% 55%, #fff 1px, transparent 2px);
    "></span>
    <span id="ip-knob" style="
        position: absolute;
        top: 3px;
        left: 3px;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: radial-gradient(circle at 35% 30%, #FFE27A, #FFC93C);
        box-shadow: 0 2px 4px rgba(0,0,0,0.25);
        transition: transform 0.5s cubic-bezier(0.65,0,0.35,1), background 0.5s ease;
    "></span>
  </button>
</div>

<script>
(function() {
  const parentDoc = window.parent.document;
  const STORAGE_KEY = "importpredic_theme";

  function applyTheme(isDark) {
    parentDoc.body.classList.toggle("dark-mode", isDark);
    // Tambien aplicar al contenedor raiz de la app por si el CSS
    // apunta a .dark-mode en un nivel distinto de body.
    const appRoot = parentDoc.querySelector('.stApp');
    if (appRoot) appRoot.classList.toggle("dark-mode", isDark);
  }

  function getSavedTheme() {
    try {
      return window.parent.sessionStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function saveTheme(isDark) {
    try {
      window.parent.sessionStorage.setItem(STORAGE_KEY, isDark ? "dark" : "light");
    } catch (e) {}
  }

  const saved = getSavedTheme();
  let isDark = saved === "dark";
  applyTheme(isDark);

  function updateVisual() {
    const clouds = document.getElementById("ip-clouds");
    const stars = document.getElementById("ip-stars");
    const knob = document.getElementById("ip-knob");
    const btn = document.getElementById("ip-theme-switch");
    if (isDark) {
      clouds.style.opacity = "0";
      stars.style.opacity = "1";
      knob.style.transform = "translateX(40px)";
      knob.style.background = "radial-gradient(circle at 35% 30%, #E8E8F0, #C8C8D8)";
      btn.style.background = "linear-gradient(180deg, #0A0A2A 0%, #1A1A3E 100%)";
    } else {
      clouds.style.opacity = "1";
      stars.style.opacity = "0";
      knob.style.transform = "translateX(0)";
      knob.style.background = "radial-gradient(circle at 35% 30%, #FFE27A, #FFC93C)";
      btn.style.background = "linear-gradient(180deg, #6EC6FF 0%, #A7DFFF 100%)";
    }
  }
  updateVisual();

  document.getElementById("ip-theme-switch").addEventListener("click", function() {
    isDark = !isDark;
    applyTheme(isDark);
    saveTheme(isDark);
    updateVisual();
  });
})();
</script>
"""


def render_theme_toggle():
    """
    Renderiza el interruptor dia/noche. Debe llamarse una vez por pagina,
    idealmente cerca del inicio (despues de st.set_page_config y de
    inyectar el CSS con get_css()), para que el usuario pueda cambiar
    de tema desde cualquier modulo del sistema.
    """
    components.html(_TOGGLE_HTML, height=46, scrolling=False)
