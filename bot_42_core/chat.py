#!/usr/bin/env python3
# chat.py – 42 Console (RPG Battle Log + Console View)

import os, sys, json, traceback, shutil, random
from datetime import datetime

# NOTE: this file is intended to be run as a module:
#   python3 -m bot_42_core.chat
# so we use relative imports below.
from .features.ethics.christ_like import ChristLikeEvaluator
from .why_log import why_log

# ============== terminal styling ==============
def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()

C = type("C", (), {})()
if _supports_color():
    C.dim   = "\x1b[2m";   C.reset = "\x1b[0m"
    C.bold  = "\x1b[1m";   C.ital  = "\x1b[3m"
    C.h1    = "\x1b[38;5;81m";  C.h2   = "\x1b[38;5;45m"
    C.ok    = "\x1b[38;5;77m";  C.warn = "\x1b[33m";    C.err = "\x1b[31m"
    C.gray  = "\x1b[90m";  C.cyan  = "\x1b[36m";  C.mag = "\x1b[35m"
    C.red   = "\x1b[196m"; C.green = "\x1b[46m"; C.yellow = "\x1b[220m"
else:
    C.dim = C.reset = C.bold = C.ital = ""
    C.h1 = C.h2 = C.ok = C.warn = C.err = ""
    C.gray = C.cyan = C.mag = C.red = C.green = C.yellow = ""

def rule(char: str = "—") -> str:
    w = max(40, shutil.get_terminal_size((80, 20)).columns)
    return char * w



# ================ import resolver ====================
def _resolve_executor():
    # Try likely import locations/names and return a callable(text) -> dict/str.
    try:
        from agent import run as _fn
        return _fn
    except Exception:
        pass
    try:
        from agent import process_with_agents as _fn
        return _fn
    except Exception:
        pass
    try:
        from main import run as _fn
        return _fn
    except Exception:
        pass
    try:
        from main import process_with_agents as _fn
        return _fn
    except Exception:
        pass
    raise ImportError(
        "Could not find an executor. Expected one of: "
        "agent.run, agent.process_with_agents, main.run, main.process_with_agents"
    )

# Ensure root and bot_42_core are on sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
CANDIDATE_DIRS = [ROOT, os.path.join(ROOT, "bot_42_core")]
for d in CANDIDATE_DIRS:
    if os.path.isdir(d) and d not in sys.path:
        sys.path.insert(0, d)

# Get real executor from main.py
EXECUTE = _resolve_executor()

# ================= banners / help ====================
BANNER = f"""
{C.h1}┌──────────────────────────────────────────────────────────┐{C.reset}
{C.h1}│{C.reset}  {C.bold}42 // RPG CONSOLE{C.reset}  {C.dim}— type a goal; 'exit' to quit{C.reset}         {C.h1}│{C.reset}
{C.h1}└──────────────────────────────────────────────────────────┘{C.reset}
{C.dim}Example goals:{C.reset}
  offense: :: The Machine insists there is ONLY ONE WAY.
  infiltrate: Check this link https://example.com and email me at user@example.org
  intervene: There is ONLY ONE WAY!! never change!

"""

HELP = f"""{C.dim}Console commands:{C.reset}
  {C.bold}:mode rpg{C.reset}         switch to RPG battle log view
  {C.bold}:mode console{C.reset}     switch to structured console view
  {C.bold}:reset{C.reset}            reset HP/buffs
  {C.bold}:stats{C.reset}            show current HP and buffs
  {C.bold}:pretty on/off{C.reset}    toggle raw JSON pretty-print in console view
  {C.bold}:raw{C.reset}              show the last full JSON again
  {C.bold}:help{C.reset}             show this help
  {C.bold}exit{C.reset}              quit
"""

# ================ RPG state & helpers =================
ENEMY_NAME = "THE MACHINE"
HERO_NAME = "42"
ENEMY_MAX_HP = 100
HERO_MAX_HP = 100
_enemy_hp = ENEMY_MAX_HP
_hero_hp = HERO_MAX_HP
_scout_buff = 1.0   # from infiltrate; amps next offense
_pretty_mode = True
_mode = "rpg"       # "rpg" or "console"
_last_raw = None
# Christ-like evaluator (soft gate for the console build)
_christ = ChristLikeEvaluator()
MIN_SCORE = float(os.getenv("CHRIST_LIKE_MIN_SCORE", "0.6"))
RPG_ICONS = {
    "offense": "🗡️",
    "infiltrate": "👁️",
    "intervene": "🛡️",
    "crit": "✧",
    "heal": "✚",
    "hit": "✦",
}

def _bar(current, maximum, width=24, fill="█", empty="·"):
    current = max(0, min(current, maximum))
    filled = int(round((current/maximum) * width))
    return f"{fill*filled}{empty*(width-filled)}"

def _rng(a, b):  # tiny randomness for fun
    return random.randint(a, b)

def _flavor_hit(dmg):
    if dmg >= 25: return "A devastating strike!"
    if dmg >= 15: return "A powerful blow!"
    if dmg >= 8:  return "A solid hit."
    if dmg >= 3:  return "A glancing blow."
    return "Barely scratches..."

def _header_rpg():
    left = f"{C.bold}{HERO_NAME}{C.reset}"
    right = f"{C.bold}{ENEMY_NAME}{C.reset}"
    hbar = _bar(_hero_hp, HERO_MAX_HP)
    ebar = _bar(_enemy_hp, ENEMY_MAX_HP)
    return (
        f"{C.h1}[ BATTLEFIELD ]{C.reset}\n"
        f"{left:>10}  HP [{hbar}] {C.ok}{_hero_hp:3d}/{HERO_MAX_HP}{C.reset}\n"
        f"{right:>10}  HP [{ebar}] {C.err}{_enemy_hp:3d}/{ENEMY_MAX_HP}{C.reset}\n"
        f"{C.gray}{rule()}{C.reset}"
    )

def _mission_header(resp: dict):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = resp.get("status", "ok").upper()
    mod = resp.get("module", "agent").upper()
    icon = RPG_ICONS.get(resp.get("module", "offense"), "✦")
    return f"{icon}  [{mod}] {status}  {C.dim}{ts}{C.reset}"

def _compute_offense_damage(report: dict) -> int:
    # Basic damage from report content
    dmg = 0
    # Blade of Clarity contradictions
    for r in report.get("results", []):
        w = r.get("weapon", "")
        if w == "Blade of Clarity":
            contradictions = r.get("contradictions", [])
            dmg += 10 * len(contradictions)
        elif w == "Shieldbreaker Spear":
            dmg += 8 * len(r.get("hits", []))
        elif w == "Dragonfire Protocol":
            # purged tokens present in original
            dmg += 6 * len(r.get("purged", []))
        elif w == "Viral Echo":
            counts = r.get("counts_after", {})
            dmg += min(12, sum(counts.values()) // 2)
        elif w == "Pulse Attack":
            dmg += 5
        elif w == "Signal Scrambler":
            dmg += 3
        elif w == "Spotlight":
            dmg += 2 * len(r.get("hits", []))
        elif w == "Mirror Shield":
            dmg += 2

    # Ensure at least chip damage if something fired
    if dmg == 0 and report.get("results"):
        dmg = 2

    # Apply scout buff
    global _scout_buff
    dmg = int(round(dmg * _scout_buff))
    # small crit chance
    if _rng(1, 100) <= 12:
        dmg = int(dmg * 1.5)
        dmg = max(dmg, 3)
        return max(1, dmg) | (1<<31)  # encode crit in high bit

    return max(1, dmg)

def _apply_offense_damage(dmg_code: int):
    # handle crit marker
    crit = False
    if dmg_code & (1<<31):
        dmg = dmg_code & ((1<<31)-1)
        crit = True
    else:
        dmg = dmg_code
    global _enemy_hp, _scout_buff
    _enemy_hp = max(0, _enemy_hp - dmg)
    # buff consumed after an offense strike
    _scout_buff = 1.0
    return dmg, crit

def _apply_intervene_heal(report: dict):
    heal = 0
    hints = report.get("hints", {})
    softened = hints.get("softened_absolutes", []) if hints else []
    risky = hints.get("risky_terms", []) if hints else []
    heal += 5 * len(softened)
    heal += 2 * len(risky)
    global _hero_hp
    if heal > 0:
        _hero_hp = min(HERO_MAX_HP, _hero_hp + heal)
    return heal

def _apply_infiltrate_buff(report: dict):
    sig = report.get("signals", {}) or {}
    urls = sig.get("urls", [])
    emails = sig.get("emails", [])
    numbers = sig.get("numbers", [])
    boost = 1.0 + 0.05 * min(10, (len(urls)+len(emails)+len(numbers)))
    boost = round(boost, 2)
    global _scout_buff
    _scout_buff = max(_scout_buff, boost)
    return _scout_buff

# ================= renderers =========================
def render_console(resp):
    # “professional” console view
    print(_render_header(resp))
    if not isinstance(resp, dict):
        print(resp); return
    if resp.get("status") != "ok":
        print(f"{C.err}Error:{C.reset} {resp.get('error', 'unknown')}"); return
    report = resp.get("report")
    if not isinstance(report, dict):
        print(pretty(resp)); return
    arsenal = (report.get("arsenal") or "").lower()
    if "offense" in arsenal:
        print(_render_offense(report))
    elif "infiltrate" in arsenal:
        print(_render_infiltrate(report))
    elif "intervene" in arsenal:
        print(_render_intervene(report))
    else:
        print(f"{h2('Report')}\n{pretty(report)}")
    print(f"\n{C.gray}{rule()}{C.reset}")

def _render_header(resp: dict) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = resp.get("status", "ok")
    mod = resp.get("module", "agent")
    status_col = C.ok if status == "ok" else (C.warn if status == "warn" else C.err)
    handled = resp.get("handled", "")
    return (
        h1(f"[42//{mod.upper()}]  {status_col}{status.upper()}{C.reset}   {C.dim}{ts}{C.reset}")
        + (f"\n{C.gray}handled:{C.reset} {handled}\n" if handled else "\n")
    )

def _render_offense(report: dict) -> str:
    out = []
    ms = report.get("mission_summary", {})
    enabled = report.get("enabled", [])
    out.append(f"{h2('Arsenal')}: {', '.join(enabled)}")
    if ms:
        out.append(f"{h2('Mission Summary')}")
        if ms.get("contradictions"): out.append(f"  • Contradictions: {ms['contradictions']}")
        if ms.get("brittle_hits"):   out.append(f"  • Brittle hits: {ms['brittle_hits']}")
        if ms.get("echo_counts"):    out.append(f"  • Echo counts: {ms['echo_counts']}")
        ex = ms.get("spotlight_examples") or []
        if ex: out.append(f"  • Spotlight: {ex}")
    out.append(f"{h2('Weapons Fired')}")
    for r in report.get("results", []):
        out.append(f"  - {C.bold}{r.get('weapon','?')}{C.reset}: {r.get('summary','')}")
    previews = [r.get("preview") for r in report.get("results", []) if r.get("preview")]
    if previews:
        out.append(f"{h2('Preview')}\n{C.dim}{previews[0]}{C.reset}")
    return "\n".join(out)

def _render_infiltrate(report: dict) -> str:
    sig = report.get("signals", {})
    out = [h2("Signals")]
    urls = sig.get("urls") or []
    emails = sig.get("emails") or []
    numbers = sig.get("numbers") or []
    kws = sig.get("top_keywords") or []
    ents = sig.get("top_entities") or []
    if urls: out.append(f"  • URLs: {', '.join(urls[:5])}")
    if emails: out.append(f"  • Emails: {', '.join(emails[:5])}")
    if numbers: out.append(f"  • Numbers: {', '.join(numbers[:5])}")
    if kws:
        top = ", ".join(f"{x['text']}({x['count']})" for x in kws[:8])
        out.append(f"  • Keywords: {top}")
    if ents:
        top = ", ".join(f"{x['text']}({x['count']})" for x in ents[:8])
        out.append(f"  • Entities: {top}")
    prev = report.get("preview")
    if prev: out.append(f"{h2('Preview')}\n{C.dim}{prev}{C.reset}")
    return "\n".join(out)

def _render_intervene(report: dict) -> str:
    hints = report.get("hints", {})
    res = report.get("result", {})
    out = [h2("Intervention")]
    if hints.get("softened_absolutes"): out.append(f"  • Softened: {hints['softened_absolutes']}")
    if hints.get("risky_terms"): out.append(f"  • Risky terms: {hints['risky_terms']}")
    if res.get("rewritten_preview"): out.append(f"{h2('Rewrite')}\n{C.ok}{res['rewritten_preview']}{C.reset}")
    return "\n".join(out)

# ================= RPG renderers =====================
def render_rpg(resp):
    # Save raw
    global _last_raw
    _last_raw = resp

    print(_header_rpg())
    print(_mission_header(resp))

    if not isinstance(resp, dict) or resp.get("status") != "ok":
        print(f"{C.err}The action fizzles...{C.reset}")
        print(f"{C.gray}{rule()}{C.reset}")
        return

    report = resp.get("report") or {}
    arsenal = (report.get("arsenal") or "").lower()

    if "offense" in arsenal:
        dmg_code = _compute_offense_damage(report)
        dmg, crit = _apply_offense_damage(dmg_code)
        star = f" {RPG_ICONS['crit']}{C.yellow} CRIT!{C.reset}" if crit else ""
        print(f"{RPG_ICONS['offense']}  {C.bold}42 uses Offense!{C.reset} {C.red}-{dmg} HP{C.reset}{star}")
        print(f"{C.dim}{_flavor_hit(dmg)}{C.reset}")

    elif "infiltrate" in arsenal:
        buff = _apply_infiltrate_buff(report)
        print(f"{RPG_ICONS['infiltrate']}  {C.bold}42 scouts the field!{C.reset} Buff to next strike: {C.ok}x{buff}{C.reset}")

    elif "intervene" in arsenal:
        heal = _apply_intervene_heal(report)
        if heal > 0:
            print(f"{RPG_ICONS['intervene']}  {C.bold}42 reinforces clarity!{C.reset} {C.green}+{heal} HP{C.reset}")
        else:
            print(f"{RPG_ICONS['intervene']}  42 steadies stance. No heal.")

    else:
        print(f"{C.dim}An unusual effect ripples across the field...{C.reset}")

    # End-of-turn status
    print()
    print(_header_rpg())
    print(f"{C.gray}{rule()}{C.reset}")

# ================= main loop ========================
def main():
    global _mode, _pretty_mode, _last_raw, _enemy_hp, _hero_hp, _scout_buff
    random.seed()

    print(BANNER)
    print(HELP)

    while True:
        try:
            msg = input(f"{C.cyan}you>{C.reset} ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye."); break

        if not msg:
            continue
        if msg.lower() in {"exit", "quit", ":q"}:
            print("bye."); break

        # Console commands
        low = msg.lower()
        if low.startswith(":mode"):
            _mode = "rpg" if "rpg" in low else "console"
            print(f"{C.dim}[mode set to {_mode.upper()}]{C.reset}")
            continue
        if low == ":reset":
            _enemy_hp, _hero_hp, _scout_buff = ENEMY_MAX_HP, HERO_MAX_HP, 1.0
            print(f"{C.dim}[battle state reset]{C.reset}")
            continue
        if low == ":stats":
            print(_header_rpg()); continue
        if low.startswith(":pretty"):
            _pretty_mode = ("on" in low)
            state = "ON" if _pretty_mode else "OFF"
            print(f"{C.dim}[pretty mode {state}]{C.reset}")
            continue
        if low == ":raw":
            if _last_raw is None: print(f"{C.dim}[no previous result]{C.reset}")
            else: print(pretty(_last_raw))
            continue
        if low in {":help", "help"}:
            print(HELP); continue

        # Execute goal
        try:
            resp = EXECUTE(msg)
            _last_raw = resp

            resp = EXECUTE(msg)
            _last_raw = resp

            # --- Christ-like ethics evaluation ---
            try:
                user_text = msg  # what you typed
                if isinstance(resp, dict):
                    reply_text = (
                        (resp.get("report", {}) or {}).get("summary")
                        or (resp.get("result", {}) or {}).get("text")
                        or resp.get("text", "")
                        or ""
                    )
                else:
                    reply_text = str(resp)

                verdict = _christ.evaluate(user_text, reply_text)
                why_log(
                    "chat_reply_eval",
                    "Christ-like evaluation of reply",
                    {"score": verdict.score, "messages": verdict.messages},
                )

                if verdict.score < MIN_SCORE:
                    print(f"{C.warn}[Ethics Gate]{C.reset} Christ-like score low: {verdict.score:.2f}")
                    print(f"{C.dim}Re-centering: compassion, humility, options/consent.{C.reset}")
                    if isinstance(resp, dict):
                        resp.setdefault("ethics", {})["christ_like_score"] = verdict.score
            except Exception as e:
                print(f"{C.err}[ChristLikeEval Error]{C.reset} {e}")
            # --- end Christ-like ethics evaluation ---

            if _mode == "rpg":
                render_rpg(resp)
            else:
                # console mode
                print(_render_header(resp))
            if _mode == "rpg":
                render_rpg(resp)
            else:
                # console mode
                print(_render_header(resp))
                if _pretty_mode and isinstance(resp, dict) and resp.get("status") == "ok" and isinstance(resp.get("report"), dict):
                    arsenal = (resp["report"].get("arsenal") or "").lower()
                    if "offense" in arsenal: print(_render_offense(resp["report"]))
                    elif "infiltrate" in arsenal: print(_render_infiltrate(resp["report"]))
                    elif "intervene" in arsenal: print(_render_intervene(resp["report"]))
                    else: print(f"{h2('Report')}\n{pretty(resp['report'])}")
                    print(f"\n{C.gray}{rule()}{C.reset}")
                else:
                    print(pretty(resp))
        except Exception:
            print(f"{C.err}[chat] error while executing:{C.reset}")
            traceback.print_exc()

if __name__ == "__main__":
    main()