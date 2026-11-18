# -*- coding: utf-8 -*-
"""
components/ai_panel.py - VERSION 1.4

Cambios vs 1.3:
- SIN emojis ni iconos de sistema (causa cuadros raros)
- Analisis automatico: TAMBIEN es un chat con burbujas (misma estetica)
- Chat del asistente: tarjeta 3D flotante con sombra y perspectiva
- Botones "Regenerar" y "Preguntas sugeridas" con padding generoso
- Botones Enviar/Limpiar completamente rediseñados (neon futurista)
- Iconos del bot hechos 100% con CSS (sin caracteres especiales)
- Ambos chats tienen la misma estetica pero el del asistente flota
"""

import html
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from src.ai.assistant import (
    init_session, generate_auto_analysis, chat_response,
    get_historial, clear_historial, cuota_restante, MAX_PREGUNTA,
)
from src.ai.openrouter_client import (
    is_configured, MODELOS_DISPONIBLES, DEFAULT_MODEL
)

# -----------------------------------------------------------------------
# CSS COMPLETO - todo en un bloque, inyectado una sola vez
# -----------------------------------------------------------------------
_AI_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

/* ================================================================
   VARIABLES
   FIX (intento anterior, incompleto): se querian alimentar estas
   variables desde las variables GLOBALES del tema en vez de usar
   valores fijos. El problema es que declarar el alias UNICAMENTE en
   ":root" no basta: ":root" (el <html>) calcula --bg-zero usando el
   valor de --bg-app que existe en ESE punto del arbol, y como la
   clase ".dark-mode" se agrega al <body> (un descendiente de :root,
   no el propio :root), --bg-zero queda "congelado" con el valor
   claro para siempre, sin importar que --bg-app cambie mas abajo.
   Es un gotcha real y bastante conocido de las custom properties de
   CSS: un alias derivado solo se recalcula si se REDECLARA en el
   mismo nivel donde cambia la variable base. Por eso el encabezado
   del chat ("ImportPredic AI - DISPONIBLE") se quedaba blanco en
   modo oscuro aunque el resto de la app si cambiaba. La solucion es
   repetir el mismo alias tambien bajo ".dark-mode" / "body.dark-mode",
   que es exactamente donde --bg-app se vuelve a definir.
================================================================ */
:root {
    --c-cyan:    var(--primary, #6C63FF);
    --c-magenta: var(--accent-coral, #FF6B81);
    --c-green:   var(--accent-green, #2ECC8F);
    --c-purple:  var(--accent-violet, #8B5CF6);
    --c-orange:  var(--accent-amber, #FFB648);
    --bg-zero:   var(--bg-app, #FFFFFF);
    --bg-low:    var(--bg-card, #FAF9FE);
    --bg-mid:    var(--bg-card-alt, #F6F5FC);
    --bg-lift:   var(--bg-hover, #F3F1FD);
    --border-1:  var(--border-soft, #ECEAF6);
    --border-2:  var(--border-strong, #E3E0F7);
    --text-main: var(--text-primary, #33324D);
    --text-dim:  var(--text-secondary, #8B8FA3);
    --text-faint:var(--text-muted, #B4B7C9);
}

/* Mismo alias, recalculado en el nivel donde el modo oscuro
   realmente redefine las variables base (ver nota arriba). */
body.dark-mode, .dark-mode {
    --c-cyan:    var(--primary, #00F5FF);
    --c-magenta: var(--accent-coral, #FF00FF);
    --c-green:   var(--accent-green, #39FF14);
    --c-purple:  var(--accent-violet, #BF00FF);
    --c-orange:  var(--accent-amber, #FF6600);
    --bg-zero:   var(--bg-app, #050510);
    --bg-low:    var(--bg-card, #0A0A1E);
    --bg-mid:    var(--bg-card-alt, #0D0D2B);
    --bg-lift:   var(--bg-hover, #12123A);
    --border-1:  var(--border-soft, #1A1A3E);
    --border-2:  var(--border-strong, #1A1A3E);
    --text-main: var(--text-primary, #E0E0FF);
    --text-dim:  var(--text-secondary, #8B8FA3);
    --text-faint:var(--text-muted, #55547A);
}


/* ================================================================
   ICONO BOT - 100% CSS, sin emojis ni caracteres especiales
================================================================ */
.ai-bot-face {
    width: 32px;
    height: 32px;
    flex-shrink: 0;
    border-radius: 50%;
    background: radial-gradient(circle at 38% 38%,
        rgba(108,99,255,0.18),
        rgba(108,99,255,0.04));
    border: 1.5px solid rgba(108,99,255,0.4);
    position: relative;
    animation: faceGlow 3.5s ease-in-out infinite;
}
@keyframes faceGlow {
    0%,100% { box-shadow: 0 0 0 0 rgba(108,99,255,0); }
    50%      { box-shadow: 0 0 0 5px rgba(108,99,255,0.12); }
}
/* Ojos: dos puntos cyan */
.ai-bot-face::before {
    content: '';
    position: absolute;
    top: 9px;
    left: 50%;
    transform: translateX(-50%);
    width: 12px;
    height: 3px;
    background: transparent;
    box-shadow: -3.5px 0 0 1.5px rgba(108,99,255,0.85),
                 3.5px 0 0 1.5px rgba(108,99,255,0.85);
    border-radius: 50%;
}
/* Boca: linea curva */
.ai-bot-face::after {
    content: '';
    position: absolute;
    bottom: 8px;
    left: 50%;
    transform: translateX(-50%);
    width: 10px;
    height: 1.5px;
    background: rgba(108,99,255,0.6);
    border-radius: 2px;
}

/* Version small del icono para mensajes */
.ai-bot-face-sm {
    width: 26px;
    height: 26px;
    flex-shrink: 0;
    border-radius: 50%;
    background: radial-gradient(circle at 38% 38%,
        rgba(108,99,255,0.14), rgba(108,99,255,0.03));
    border: 1px solid rgba(108,99,255,0.3);
    position: relative;
    margin-top: 3px;
}
.ai-bot-face-sm::before {
    content: '';
    position: absolute;
    top: 7px; left: 50%;
    transform: translateX(-50%);
    width: 9px; height: 2px;
    background: transparent;
    box-shadow: -2.5px 0 0 1px rgba(108,99,255,0.75),
                 2.5px 0 0 1px rgba(108,99,255,0.75);
    border-radius: 50%;
}
.ai-bot-face-sm::after {
    content: '';
    position: absolute;
    bottom: 6px; left: 50%;
    transform: translateX(-50%);
    width: 7px; height: 1px;
    background: rgba(108,99,255,0.5);
    border-radius: 1px;
}

/* ================================================================
   CHAT DE ANALISIS AUTOMATICO
   (Misma estetica que el chat, pero sin efecto 3D)
================================================================ */
/* ================================================================
   TARJETA CONTENEDORA (analisis y chat)
   FIX: antes esta caja se dibujaba con un <div> abierto en un
   st.markdown() y cerrado en otro, lo que dejaba cajas vacias sin
   estilo (ver notas en _render_analysis / _render_chat). Ahora la
   caja real es un st.container(border=True) de Streamlit, y aqui
   se le quita el borde gris nativo para pintarle nuestro propio
   fondo/borde/sombra tematizados.
   NOTA: el testid interno que Streamlit usa para el wrapper con
   borde cambio de nombre entre versiones (stVerticalBlockBorderWrapper
   en versiones ~1.3x, stLayoutWrapper en versiones mas nuevas). Se
   cubren ambos para que el estilo no dependa de la version exacta.
================================================================ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ai-analysis-head),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ai-chat-head),
div[data-testid="stLayoutWrapper"]:has(.ai-analysis-head),
div[data-testid="stLayoutWrapper"]:has(.ai-chat-head) {
    border: 1px solid var(--border-1) !important;
    border-top: 2px solid var(--c-cyan) !important;
    border-radius: 12px !important;
    background: var(--bg-mid) !important;
    box-shadow: var(--shadow-card);
    overflow: hidden;
}

/* Efecto 3D flotante, solo en la tarjeta del chat del asistente */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ai-chat-head),
div[data-testid="stLayoutWrapper"]:has(.ai-chat-head) {
    transform: rotateX(0.8deg) rotateY(-0.4deg) translateZ(0);
    transform-style: preserve-3d;
    transition: transform 0.4s ease, box-shadow 0.4s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ai-chat-head):hover,
div[data-testid="stLayoutWrapper"]:has(.ai-chat-head):hover {
    transform: rotateX(0deg) rotateY(0deg) translateY(-3px);
    box-shadow:
        0 10px 26px rgba(108,99,255,0.14),
        0 24px 44px rgba(108,99,255,0.10) !important;
}

.ai-analysis-head {
    background: linear-gradient(90deg, var(--bg-zero) 0%, var(--bg-low) 100%);
    border-bottom: 1px solid var(--border-1);
    padding: 11px 16px;
    display: flex;
    align-items: center;
    gap: 11px;
}

/* Indicador parpadeante en vez de icono */
.ai-analysis-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--c-cyan);
    box-shadow: 0 0 8px var(--c-cyan);
    flex-shrink: 0;
    animation: dotPulse 2.5s ease-in-out infinite;
}
@keyframes dotPulse {
    0%,100% { opacity:1; transform:scale(1); }
    50%      { opacity:0.3; transform:scale(0.7); }
}

.ai-analysis-title {
    font-family: 'Poppins', sans-serif;
    font-size: 0.65rem;
    color: var(--c-cyan);
    letter-spacing: 2.5px;
    text-transform: uppercase;
}
.ai-analysis-sub {
    font-family: 'Inter', sans-serif;
    font-size: 0.56rem;
    color: var(--text-dim);
    margin-top: 1px;
    letter-spacing: 1px;
}

/* Burbuja del analisis (del bot hacia el usuario) */
.ai-analysis-bubble-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin: 6px 0 10px;
    animation: fadeUp 0.3s ease-out;
}
@keyframes fadeUp {
    from { opacity:0; transform:translateY(6px); }
    to   { opacity:1; transform:translateY(0); }
}
.ai-analysis-bubble {
    flex: 1;
    background: linear-gradient(145deg, var(--bg-low), var(--bg-mid));
    border: 1px solid var(--border-1);
    border-left: 2px solid rgba(108,99,255,0.35);
    border-radius: 3px 14px 14px 14px;
    padding: 14px 18px;
    font-family: 'Inter', sans-serif;
    font-size: 0.86rem;
    color: var(--text-main);
    line-height: 1.85;
}
.ai-analysis-meta {
    font-family: 'Inter', sans-serif;
    font-size: 0.54rem;
    color: rgba(108,99,255,0.3);
    margin-top: 5px;
    padding-left: 2px;
}

.ai-analysis-empty {
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    color: var(--text-faint);
    font-style: italic;
    text-align: center;
    padding: 22px 0;
}

/* ================================================================
   CONTROLES DEL ANALISIS / INPUT DEL CHAT
   FIX: reemplaza las antiguas ".ai-controls-row" / ".ai-input-zone",
   que eran <div> vacios (sin contenido en el mismo fragmento HTML)
   y se veian como una barra solida sin motivo. Una linea divisoria
   autocontenida cumple el mismo papel visual sin dejar cajas huecas.
================================================================ */
.ai-controls-divider {
    border-top: 1px solid var(--border-1);
    margin: 6px 14px 10px;
}

/* ================================================================
   BOTONES DE STREAMLIT - Override general con padding correcto
   El texto NO toca el borde del boton
================================================================ */

/* Botones normales (Regenerar, sugeridas)
   FIX: se agrega el selector "> p" explicito porque main.css fuerza
   TODOS los <p> dentro de botones de Streamlit a --text-on-primary
   (blanco en modo claro) con !important. Sin este selector especifico
   aqui, el texto del boton "Regenerar" quedaba blanco sobre fondo
   transparente/blanco, es decir, invisible. */
div[data-testid="stButton"] > button {
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.6rem !important;
    letter-spacing: 2px !important;
    /* padding generoso para separar texto del borde */
    padding: 10px 22px !important;
    border-radius: 7px !important;
    transition: all 0.22s ease !important;
    border: 1px solid rgba(108,99,255,0.3) !important;
    background: transparent !important;
    color: rgba(108,99,255,0.8) !important;
}
div[data-testid="stButton"] > button p {
    color: rgba(108,99,255,0.8) !important;
}
div[data-testid="stButton"] > button:hover {
    background: rgba(108,99,255,0.07) !important;
    border-color: var(--c-cyan) !important;
    color: var(--c-cyan) !important;
    /* glow no toca el texto porque hay padding suficiente */
    box-shadow:
        0 0 16px rgba(108,99,255,0.25),
        0 0 30px rgba(108,99,255,0.1),
        inset 0 0 10px rgba(108,99,255,0.04) !important;
    transform: translateY(-1px) !important;
}
div[data-testid="stButton"] > button:hover p {
    color: var(--c-cyan) !important;
}
div[data-testid="stButton"] > button:active {
    transform: translateY(0) !important;
}

/* Preguntas sugeridas: usan el mismo estilo base de boton de arriba. */

/* Selectbox modelo
   FIX: el selector anterior ("> div > div") no apuntaba al nodo real
   que BaseWeb usa para pintar el valor seleccionado, y competia con
   la regla generica de main.css sin cubrir todos los hijos de texto/
   icono. Resultado: fondo blanco fijo con texto tambien casi blanco,
   ilegible en modo claro y modo oscuro por igual. Ahora se apunta
   directo a [data-baseweb="select"] (fondo) y a todos sus
   descendientes (texto + icono de flecha), usando las variables del
   tema para que el contraste se mantenga al cambiar de modo. */
div[data-testid="stSelectbox"] label { display:none; }
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background: var(--bg-low) !important;
    border: 1px solid var(--border-1) !important;
    border-radius: 7px !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] * {
    color: var(--c-cyan) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.7rem !important;
}
div[data-testid="stSelectbox"] svg { fill: var(--c-cyan) !important; }

/* ================================================================
   DIVISOR
================================================================ */
.ai-divider {
    display:flex;
    align-items:center;
    gap:12px;
    margin: 20px 0 16px;
}
.ai-divider-line {
    flex:1;
    height:1px;
    background: linear-gradient(90deg, transparent, var(--border-2), transparent);
}
.ai-divider-text {
    font-family:'Share Tech Mono',monospace;
    font-size:0.56rem;
    color: var(--text-dim);
    letter-spacing:3px;
    white-space:nowrap;
    text-transform:uppercase;
}

/* ================================================================
   CHAT DEL ASISTENTE - TARJETA 3D FLOTANTE
================================================================ */

/* Header del chat del asistente (autocontenido, un solo fragmento) */
.ai-chat-head {
    background: linear-gradient(90deg, var(--bg-zero) 0%, var(--bg-low) 100%);
    border-bottom: 1px solid var(--border-1);
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.ai-chat-name {
    font-family: 'Poppins', sans-serif;
    font-size: 0.67rem;
    color: var(--c-cyan);
    letter-spacing: 2px;
}
.ai-chat-status {
    font-family: 'Inter', sans-serif;
    font-size: 0.56rem;
    color: var(--c-green);
    margin-top: 2px;
    display:flex;
    align-items:center;
    gap:5px;
}
.ai-status-blink {
    width:5px; height:5px;
    background: var(--c-green);
    border-radius:50%;
    animation: blinkDot 2.2s ease-in-out infinite;
}
@keyframes blinkDot {
    0%,100% { opacity:1; }
    50%      { opacity:0.15; }
}

/* Los mensajes ahora viven en un st.container(height=...) real de
   Streamlit (ver _render_chat), asi que ya no necesitan su propio
   div de scroll; el contenedor nativo ya se encarga del overflow. */

/* Mensaje bienvenida */
.ai-welcome-row {
    display:flex;
    align-items:flex-start;
    gap:10px;
    margin:4px 0 8px;
}
.ai-welcome-bubble {
    flex:1;
    background: linear-gradient(145deg, var(--bg-low), var(--bg-mid));
    border: 1px solid var(--border-1);
    border-left: 2px solid rgba(108,99,255,0.3);
    border-radius: 3px 14px 14px 14px;
    padding: 12px 16px;
    font-family: 'Inter', sans-serif;
    font-size: 0.83rem;
    color: var(--text-main);
    line-height: 1.75;
}

/* Burbuja USUARIO */
.ai-row-user {
    display:flex;
    justify-content:flex-end;
    margin: 7px 0;
    animation: slideR 0.2s ease-out;
}
@keyframes slideR {
    from { opacity:0; transform:translateX(8px); }
    to   { opacity:1; transform:translateX(0); }
}
.ai-user-inner { max-width:77%; }
.ai-bubble-user {
    background: linear-gradient(135deg, #6C63FF, #574CE0);
    border: none;
    border-radius: 16px 16px 3px 16px;
    padding: 10px 16px;
    font-family: 'Inter', sans-serif;
    font-size: 0.83rem;
    color: var(--text-on-primary, #FFFFFF);
    line-height: 1.65;
    word-break: break-word;
}
.ai-meta-user {
    font-family: 'Inter', sans-serif;
    font-size: 0.52rem;
    color: #B4AEDD;
    text-align:right;
    margin-top:4px;
    padding-right:2px;
}

/* Burbuja ASISTENTE */
.ai-row-asst {
    display:flex;
    align-items:flex-start;
    gap:9px;
    margin: 9px 0;
    animation: slideL 0.2s ease-out;
}
@keyframes slideL {
    from { opacity:0; transform:translateX(-8px); }
    to   { opacity:1; transform:translateX(0); }
}
.ai-asst-inner { flex:1; max-width:88%; }
.ai-bubble-asst {
    background: linear-gradient(145deg, var(--bg-low), var(--bg-mid));
    border: 1px solid var(--border-1);
    border-left: 2px solid rgba(108,99,255,0.3);
    border-radius: 3px 16px 16px 16px;
    padding: 12px 16px;
    font-family: 'Inter', sans-serif;
    font-size: 0.83rem;
    color: var(--text-main);
    line-height: 1.8;
    word-break: break-word;
    max-height: 340px;
    overflow-y: auto;
}
.ai-bubble-asst::-webkit-scrollbar { width:3px; }
.ai-bubble-asst::-webkit-scrollbar-thumb {
    background: rgba(108,99,255,0.15);
    border-radius:2px;
}
.ai-meta-asst {
    font-family: 'Inter', sans-serif;
    font-size: 0.52rem;
    color: rgba(108,99,255,0.28);
    margin-top:5px;
    padding-left:2px;
}

/* Etiqueta preguntas sugeridas */
.ai-sug-label {
    font-family: 'Inter', sans-serif;
    font-size: 0.58rem;
    color: var(--text-dim);
    letter-spacing: 2.5px;
    text-transform: uppercase;
    margin: 10px 0 6px;
}

/* ================================================================
   ZONA DE INPUT - Botones futuristas rediseñados
   (el fondo/borde ya lo da el contenedor tarjeta + ".ai-controls-divider")
================================================================ */

/* Textarea */
div[data-testid="stTextArea"] textarea {
    background: var(--bg-low) !important;
    border: 1px solid rgba(108,99,255,0.18) !important;
    border-radius: 8px !important;
    color: var(--text-main) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.84rem !important;
    padding: 10px 14px !important;
    line-height: 1.6 !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(108,99,255,0.5) !important;
    box-shadow: 0 0 0 1px rgba(108,99,255,0.15), 0 0 12px rgba(108,99,255,0.08) !important;
    outline: none !important;
}
div[data-testid="stTextArea"] textarea::placeholder {
    color: #DAD6F2 !important;
    font-style: italic;
}

/* BOTON ENVIAR - neon cyan */
div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #6C63FF 0%, #574CE0 100%) !important;
    border: 1px solid rgba(108,99,255,0.6) !important;
    color: var(--c-cyan) !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.6rem !important;
    letter-spacing: 2.5px !important;
    /* padding generoso - texto NO pegado al borde */
    padding: 12px 28px !important;
    border-radius: 8px !important;
    text-transform: uppercase !important;
    transition: all 0.22s ease !important;
    position: relative !important;
    overflow: hidden !important;
}
div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #574CE0 0%, #6C63FF 100%) !important;
    box-shadow:
        0 0 20px rgba(108,99,255,0.35),
        0 0 40px rgba(108,99,255,0.15),
        inset 0 1px 0 rgba(255,255,255,0.08) !important;
    transform: translateY(-2px) !important;
    border-color: var(--c-cyan) !important;
}
div[data-testid="stFormSubmitButton"] > button[kind="primary"]:active {
    transform: translateY(0px) !important;
    box-shadow: 0 0 10px rgba(108,99,255,0.25) !important;
}

/* BOTON LIMPIAR - magenta futurista */
div[data-testid="stFormSubmitButton"] > button:not([kind="primary"]) {
    background: transparent !important;
    border: 1px solid rgba(255,107,129,0.28) !important;
    color: rgba(255,107,129,0.65) !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.58rem !important;
    letter-spacing: 2px !important;
    padding: 12px 20px !important;
    border-radius: 8px !important;
    text-transform: uppercase !important;
    transition: all 0.22s ease !important;
}
div[data-testid="stFormSubmitButton"] > button:not([kind="primary"]):hover {
    background: rgba(255,107,129,0.06) !important;
    border-color: var(--c-magenta) !important;
    color: var(--c-magenta) !important;
    box-shadow:
        0 0 16px rgba(255,107,129,0.22),
        0 0 30px rgba(255,107,129,0.08) !important;
    transform: translateY(-1px) !important;
}

/* ================================================================
   INSIGHT INLINE (bajo graficas especificas)
================================================================ */
.ai-insight-outer {
    border: 1px solid rgba(139,92,246,0.15);
    border-left: 3px solid var(--c-purple);
    border-radius: 0 8px 8px 0;
    background: rgba(139,92,246,0.025);
    overflow: hidden;
    margin: 10px 0;
}
.ai-insight-head {
    padding: 8px 14px;
    border-bottom: 1px solid rgba(139,92,246,0.1);
    display:flex;
    align-items:center;
    justify-content:space-between;
}
.ai-insight-badge {
    font-family: 'Inter', sans-serif;
    font-size: 0.57rem;
    color: var(--c-purple);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    background: rgba(139,92,246,0.08);
    border: 1px solid rgba(139,92,246,0.28);
    padding: 3px 10px;
    border-radius: 20px;
}
.ai-insight-body {
    padding: 14px 18px;
    font-family: 'Inter', sans-serif;
    font-size: 0.84rem;
    color: #4C3D8F;
    line-height: 1.8;
    max-height: 360px;
    overflow-y: auto;
}

/* ================================================================
   NO CONFIGURADO
================================================================ */
.ai-not-cfg {
    background: rgba(255,182,72,0.05);
    border: 1px solid rgba(255,182,72,0.18);
    border-radius: 8px;
    padding: 14px 18px;
    font-family: 'Inter', sans-serif;
    font-size: 0.8rem;
    color: #C9761F;
    line-height: 1.65;
}

</style>
"""


# -----------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------
def _inject_css():
    """
    FIX v1.3.1: Se inyecta el CSS SIEMPRE, en cada ejecución del script.

    Antes se guardaba una bandera en session_state para inyectar el CSS
    una sola vez por sesión. El problema es que Streamlit reconstruye
    el DOM completo del navegador en cada st.rerun(), y como <style> ya
    no se volvía a insertar (la bandera seguía en True), el navegador
    perdía todos los estilos del panel IA justo después de la primera
    interaccion (enviar mensaje, regenerar analisis, cambiar de pagina, etc.).

    Inyectar el CSS en cada rerun no tiene costo real: Streamlit ya
    reconstruye todo el arbol de componentes de la pagina en cada ciclo,
    asi que evitar esta unica linea de <style> no ahorra nada.
    """
    st.markdown(_AI_CSS, unsafe_allow_html=True)


def _ts():
    return datetime.now().strftime("%H:%M")


def _model_selector(suffix):
    opts = list(MODELOS_DISPONIBLES.keys())
    actual = st.session_state.get("ai_model", DEFAULT_MODEL)
    nombre = next((k for k, v in MODELOS_DISPONIBLES.items() if v == actual), opts[0])
    sel = st.selectbox(
        "Modelo", options=opts, index=opts.index(nombre),
        key="ai_sel_{}".format(suffix), label_visibility="collapsed",
    )
    st.session_state["ai_model"] = MODELOS_DISPONIBLES[sel]


def _not_configured():
    # SEGURIDAD v2.0: ya no se le pide al usuario editar el codigo ni pegar
    # una key. La key la configura solo el administrador en los secretos
    # del servidor (OPENROUTER_API_KEY).
    from src.auth.session import is_admin

    if is_admin():
        msg = ('El asistente de IA no esta activo. Como administrador, define '
               '<code>OPENROUTER_API_KEY</code> en <code>.streamlit/secrets.toml</code> '
               '(o en los <i>Secrets</i> del servidor de despliegue) y reinicia la app.')
    else:
        msg = ('El asistente de IA no esta disponible en este momento. '
               'Contacta al administrador del sistema.')
    st.markdown('<div class="ai-not-cfg">{}</div>'.format(msg), unsafe_allow_html=True)


# -----------------------------------------------------------------------
# SECCION 1: ANALISIS AUTOMATICO (chat con burbujas)
# -----------------------------------------------------------------------
def _autoscroll_chat():
    """
    Hace scroll automatico de los contenedores de mensajes (analisis y
    chat) hasta el mensaje mas reciente.

    FIX: st.container(height=...) de Streamlit NO hace scroll
    automatico al fondo cuando se agrega contenido nuevo -- mantiene
    la posicion de scroll donde estaba. Por eso, cada vez que se hacia
    una pregunta nueva, la respuesta quedaba "escondida" mas abajo y
    habia que arrastrar la barra de scroll manualmente para verla (no
    se reflejaba la ultima pregunta al hacerla). Se reutiliza la misma
    tecnica que ya usa el interruptor de tema (components.html corre
    en un iframe del mismo origen que la app, asi que se puede llegar
    al DOM real de la pagina con window.parent.document en vez de
    document).

    FIX 2 (encontrado probando en vivo): el HTML/JS de este componente
    es identico en cada rerun, y Streamlit reutiliza el mismo iframe
    sin volver a cargarlo ni re-ejecutar su script cuando el contenido
    no cambia -- por eso el scroll solo funcionaba la primera vez.
    Se incluye un comentario HTML con una marca de tiempo unica en
    cada llamada para forzar que Streamlit trate cada render como un
    componente nuevo y si vuelva a ejecutar el script.
    """
    nonce = datetime.now().strftime("%H%M%S%f")
    components.html(
        """
        <!-- nonce:{nonce} -->
        <script>
        (function() {{
          function scrollToBottom() {{
            try {{
              const parentDoc = window.parent.document;
              const marcas = parentDoc.querySelectorAll(
                '.ai-welcome-row, .ai-row-user, .ai-row-asst, ' +
                '.ai-analysis-bubble-row, .ai-analysis-empty'
              );
              const vistos = [];
              marcas.forEach(function(marca) {{
                let nodo = marca;
                while (nodo && nodo !== parentDoc.body) {{
                  const win = nodo.ownerDocument.defaultView;
                  const cs = win.getComputedStyle(nodo);
                  if (cs.overflowY === 'auto' || cs.overflowY === 'scroll') {{
                    if (vistos.indexOf(nodo) === -1) {{
                      vistos.push(nodo);
                      nodo.scrollTop = nodo.scrollHeight;
                    }}
                    break;
                  }}
                  nodo = nodo.parentElement;
                }}
              }});
            }} catch (e) {{}}
          }}
          scrollToBottom();
          setTimeout(scrollToBottom, 80);
          setTimeout(scrollToBottom, 300);
          setTimeout(scrollToBottom, 700);
        }})();
        </script>
        """.format(nonce=nonce),
        height=0,
    )


def _render_analysis(pagina, ctx, auto_trigger, subtipo):
    """Chat-estilo para el analisis automatico.

    FIX ESPACIOS VACIOS: antes esta funcion abria ".ai-analysis-wrap"
    y ".ai-analysis-messages" con un st.markdown() y los cerraba en
    otro st.markdown() varias llamadas despues. Cada st.markdown()
    se renderiza como un fragmento HTML independiente, asi que el
    navegador cierra esos <div> automaticamente al final de CADA
    fragmento (no al final de la funcion) — el resultado eran cajas
    vacias con solo el borde/fondo de la tarjeta y el contenido real
    apareciendo suelto, sin encuadrar, justo despues. Ahora se usa
    st.container(border=True), que es un contenedor real de Streamlit
    y sí anida correctamente todo lo que se dibuja dentro de el.
    """
    cache_key = "ai_auto_{}_{}".format(pagina, subtipo or "main")
    cached = st.session_state.get(cache_key)
    ts = _ts()

    with st.container(border=True):
        # Header (autocontenido: abre y cierra en el mismo fragmento)
        st.markdown(
            '<div class="ai-analysis-head">'
            '<div class="ai-analysis-dot"></div>'
            '<div>'
            '<div class="ai-analysis-title">Analisis Automatico</div>'
            '<div class="ai-analysis-sub">IMPORTPREDIC // AI ANALYST</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Mensajes (contenedor real con scroll, ya no un div huerfano)
        with st.container(height=260, border=False):
            if cached:
                st.markdown(
                    '<div class="ai-analysis-bubble-row">'
                    '<div class="ai-bot-face-sm"></div>'
                    '<div style="flex:1;">'
                    '<div class="ai-analysis-bubble">',
                    unsafe_allow_html=True,
                )
                st.markdown(cached)
                st.markdown(
                    '</div>'
                    '<div class="ai-analysis-meta">ImportPredic AI &middot; {}</div>'
                    '</div></div>'.format(ts),
                    unsafe_allow_html=True,
                )
            elif not auto_trigger:
                st.markdown(
                    '<div class="ai-analysis-empty">'
                    'Presiona "Analizar" para generar el analisis de esta seccion.'
                    '</div>',
                    unsafe_allow_html=True,
                )

        # Controles en la parte inferior
        st.markdown('<div class="ai-controls-divider"></div>', unsafe_allow_html=True)
        c1, c2 = st.columns([1, 2])
        with c2:
            _model_selector("an_{}".format(pagina))
        with c1:
            lbl = "Analizar" if not cached else "Regenerar"
            if st.button(lbl, key="regen_{}".format(pagina), use_container_width=True):
                with st.spinner("Analizando con IA..."):
                    texto = generate_auto_analysis(pagina, ctx, subtipo=subtipo, force=True)
                st.rerun()
            elif auto_trigger and not cached:
                with st.spinner("Analizando..."):
                    generate_auto_analysis(pagina, ctx, subtipo=subtipo, force=False)
                st.rerun()


# -----------------------------------------------------------------------
# SECCION 2: CHAT DEL ASISTENTE (tarjeta 3D flotante)
# -----------------------------------------------------------------------
def _render_chat(pagina, ctx, sugeridas):
    """Chat interactivo con efecto 3D flotante.

    FIX ESPACIOS VACIOS: mismo problema que en _render_analysis — el
    div ".ai-chat-card"/".ai-chat-messages" se abria en un
    st.markdown() y se cerraba en otro, dos o tres llamadas despues.
    El navegador cierra ese <div> de inmediato al final de cada
    fragmento HTML aislado, dejando una caja vacia (fondo blanco en
    modo claro / oscuro en modo oscuro segun el tema) justo debajo
    del encabezado "ImportPredic AI - DISPONIBLE", con el mensaje de
    bienvenida o el historial apareciendo suelto, sin la tarjeta
    alrededor. Lo mismo pasaba con ".ai-input-zone", que se abria
    solo (sin contenido en el mismo fragmento) y quedaba como una
    barra vacia justo encima del cuadro de texto. Ahora todo el chat
    vive dentro de un unico st.container(border=True), que si anida
    de verdad tanto el HTML crudo como los widgets nativos (form,
    text_area, botones).
    """

    hist = get_historial(pagina)

    with st.container(border=True):
        # Encabezado (autocontenido en un solo fragmento)
        st.markdown(
            '<div class="ai-chat-head">'
            '<div class="ai-bot-face"></div>'
            '<div>'
            '<div class="ai-chat-name">ImportPredic AI</div>'
            '<div class="ai-chat-status">'
            '<div class="ai-status-blink"></div>'
            'DISPONIBLE'
            '</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Mensajes: contenedor real con scroll (reemplaza el div huerfano)
        with st.container(height=320, border=False):
            if not hist:
                st.markdown(
                    '<div class="ai-welcome-row">'
                    '<div class="ai-bot-face-sm"></div>'
                    '<div class="ai-welcome-bubble">'
                    'Bienvenido. Puedes consultarme sobre los datos, modelos, metricas '
                    'o cualquier resultado de esta seccion. Usa las preguntas sugeridas '
                    'o escribe directamente tu consulta.'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
            else:
                for msg in hist[-10:]:
                    ts = _ts()
                    if msg["role"] == "user":
                        st.markdown(
                            '<div class="ai-row-user">'
                            '<div class="ai-user-inner">'
                            '<div class="ai-bubble-user">{}</div>'
                            '<div class="ai-meta-user">Usted &middot; {}</div>'
                            '</div>'
                            '</div>'.format(html.escape(msg["content"]).replace("\n", "<br>"), ts),
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            '<div class="ai-row-asst">'
                            '<div class="ai-bot-face-sm"></div>'
                            '<div class="ai-asst-inner">'
                            '<div class="ai-bubble-asst">',
                            unsafe_allow_html=True,
                        )
                        st.markdown(msg["content"])
                        st.markdown(
                            '</div>'
                            '<div class="ai-meta-asst">ImportPredic AI &middot; {}</div>'
                            '</div></div>'.format(ts),
                            unsafe_allow_html=True,
                        )

        # Preguntas sugeridas (solo cuando no hay historial)
        if sugeridas and not hist:
            st.markdown(
                '<div style="padding:4px 14px 6px;">'
                '<div class="ai-sug-label">Preguntas sugeridas</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            for i, p_txt in enumerate(sugeridas[:3]):
                if st.button(p_txt, key="sug_{}_{}".format(pagina, i), use_container_width=True):
                    with st.spinner("Consultando..."):
                        chat_response(pagina, p_txt, ctx)
                    st.rerun()

        # Input
        st.markdown('<div class="ai-controls-divider"></div>', unsafe_allow_html=True)
        with st.form(key="chat_{}".format(pagina), clear_on_submit=True):
            inp = st.text_area(
                "msg",
                max_chars=MAX_PREGUNTA,
                placeholder="Escribe tu consulta aqui...",
                height=66,
                label_visibility="collapsed",
                key="chat_inp_{}".format(pagina),
            )
            c1, c2 = st.columns([5, 2])
            enviado = c1.form_submit_button("Enviar", use_container_width=True, type="primary")
            limpiar = c2.form_submit_button("Limpiar", use_container_width=True)
            st.caption("Consultas disponibles esta hora: {}".format(cuota_restante()))

    if enviado and inp.strip():
        with st.spinner("Consultando al asistente..."):
            chat_response(pagina, inp.strip(), ctx)
        st.rerun()

    if limpiar:
        clear_historial(pagina)
        st.rerun()


# -----------------------------------------------------------------------
# COMPONENTE PUBLICO 1: render_ai_insight
# Analisis IA inline compacto bajo una grafica
# -----------------------------------------------------------------------
def render_ai_insight(pagina, subtipo, contexto=None, label=None):
    """
    Bloque de analisis IA compacto bajo una grafica especifica.
    Sin chat. Se activa automaticamente al cargar.

    Uso:
        render_ai_insight(
            pagina="exploracion",
            subtipo="descomposicion",
            contexto={...},
            label="IA - Descomposicion STL",
        )
    """
    _inject_css()
    init_session(pagina)
    if not is_configured():
        return

    badge = label or "Analisis IA"
    cache_key = "ai_auto_{}_{}".format(pagina, subtipo)
    cached = st.session_state.get(cache_key)

    st.markdown(
        '<div class="ai-insight-outer">'
        '<div class="ai-insight-head">'
        '<span class="ai-insight-badge">{}</span>'
        '</div>'
        '<div class="ai-insight-body">'.format(badge),
        unsafe_allow_html=True,
    )

    if cached:
        st.markdown(cached)
    else:
        with st.spinner("Analizando..."):
            texto = generate_auto_analysis(pagina, contexto, subtipo=subtipo, force=False)
        st.markdown(texto)

    st.markdown('</div></div>', unsafe_allow_html=True)

    col_r, _ = st.columns([1, 6])
    with col_r:
        if st.button("Regenerar", key="ri_{}_{}".format(pagina, subtipo)):
            with st.spinner("Regenerando..."):
                generate_auto_analysis(pagina, contexto, subtipo=subtipo, force=True)
            st.rerun()


# -----------------------------------------------------------------------
# COMPONENTE PUBLICO 2: render_ai_panel
# Panel completo: analisis automatico (chat) + chatbot flotante 3D
# -----------------------------------------------------------------------
def render_ai_panel(
    pagina,
    contexto=None,
    auto_trigger=False,
    preguntas_sugeridas=None,
    modo="expander",
    subtipo=None,
):
    """
    Panel IA completo con dos secciones visualmente distintas:
    1. Analisis automatico: estilo chat con burbujas del bot
    2. Chat interactivo: tarjeta 3D flotante con efecto perspectiva

    Parametros:
        pagina             : "inicio","carga","exploracion","entrenamiento",
                             "prediccion","evaluacion","interpretabilidad","reporte"
        contexto           : dict con datos y metricas de la pagina
        auto_trigger       : True = activa analisis al cargar sin click
        preguntas_sugeridas: lista de hasta 3 preguntas rapidas
        modo               : "expander" (colapsable) | "inline"
        subtipo            : subtipo de prompt para el analisis
    """
    _inject_css()
    init_session(pagina)

    ctx = contexto or {}
    sugeridas = preguntas_sugeridas or []

    def _todo():
        if not is_configured():
            _not_configured()
            return

        # --- SECCION 1: Analisis automatico como chat ---
        _render_analysis(pagina, ctx, auto_trigger, subtipo)

        # --- Divisor ---
        st.markdown(
            '<div class="ai-divider">'
            '<div class="ai-divider-line"></div>'
            '<div class="ai-divider-text">Consultas al Asistente</div>'
            '<div class="ai-divider-line"></div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # --- SECCION 2: Chat flotante 3D ---
        _render_chat(pagina, ctx, sugeridas)

        # Bajar al mensaje mas reciente en ambos paneles de mensajes
        _autoscroll_chat()

    if modo == "inline":
        _todo()
    else:
        with st.expander(
            "Asistente IA — Analisis y Consultas",
            expanded=auto_trigger,
        ):
            _todo()
