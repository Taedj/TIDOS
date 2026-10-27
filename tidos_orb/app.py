"""The TIDOS orb: a floating bubble you can drag anywhere; click it for a flat panel of TIDOS's growth.

Read-only by design: it shows the brain (level, stats, evolution, solutions, next moves) without a login.
Everything that changes TIDOS opens the Control Center, where the owner login applies.
"""
import json
import math
import os
import queue
import socket
import threading
import tkinter as tk
from datetime import datetime, timezone

from tidos_brain import db
from tidos_session import detect

from . import data, launch

BG, SURFACE, SURFACE_2 = "#04060d", "#0a142c", "#0e1b3a"
LINE, LINE_STRONG = "#16305a", "#4fb0ff"
TEXT, MUTED, FAINT = "#dbe8ff", "#7d92b8", "#4a5b7c"
ACCENT, VIOLET, OK, WARN, BAD = "#6cc4ff", "#9b7bff", "#3ee6a0", "#ffc857", "#ff5d73"
MOOD = {"calm": ACCENT, "act": WARN, "bad": BAD}
SANS, MONO = "Segoe UI", "Consolas"
KEY = "#010203"  # transparent key: the orb's square corners vanish on Windows

ORB = 78
PANEL_W, PANEL_H = 860, 580
REFRESH_MS = 60_000
TABS = (("journey", "Journey"), ("evolution", "Evolution"), ("solutions", "Solutions"), ("next", "Next moves"))


def _state_path():
    return os.path.join(detect.tidos_home(), "orb.json")


def _load_state():
    try:
        with open(_state_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_state(state):
    try:
        os.makedirs(os.path.dirname(_state_path()), exist_ok=True)
        with open(_state_path(), "w", encoding="utf-8") as f:
            json.dump(state, f)
    except OSError:
        pass


def _ago(iso, now=None):
    try:
        then = datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
    except ValueError:
        return ""
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    minutes = int(((now or datetime.now(timezone.utc)) - then).total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return "%d min ago" % minutes
    if minutes < 48 * 60:
        return "%d h ago" % (minutes // 60)
    return "%d days ago" % (minutes // 1440)


def _one_line(text, limit):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


class Scroll(tk.Frame):
    """A vertically scrolling column; the mouse wheel works anywhere over it."""

    def __init__(self, master):
        super().__init__(master, bg=BG)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0)
        self.body = tk.Frame(self.canvas, bg=BG)
        self.window = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.canvas.pack(fill="both", expand=True)
        self.body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=(0, 0, e.width, e.height)))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window, width=e.width))

    def wheel(self, up):
        if self.canvas.yview() != (0.0, 1.0):  # only when the content is taller than the window
            self.canvas.yview_scroll(-2 if up else 2, "units")


class Orb:
    def __init__(self, server):
        self.server = server
        self.root = tk.Tk()
        self.root.title("TIDOS")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=KEY)
        try:
            self.root.attributes("-transparentcolor", KEY)
        except tk.TclError:
            pass  # not Windows: the corners stay dark, still fine
        self.canvas = tk.Canvas(self.root, width=ORB, height=ORB, bg=KEY, highlightthickness=0, bd=0, cursor="hand2")
        self.canvas.pack()
        self.state = _load_state()
        self.snap = None
        self.panel = None
        self.tab = self.state.get("tab", "journey")
        self.inbox = queue.Queue()
        self.loading = False
        self.phase = 0.0
        self._drag = None
        self.scroll = None
        self._tipwin = None
        self.root.bind_all("<MouseWheel>", lambda e: self._wheel(e.delta > 0))
        self.root.bind_all("<Button-4>", lambda e: self._wheel(True))
        self.root.bind_all("<Button-5>", lambda e: self._wheel(False))
        self._place_orb()
        self._bind_orb()
        self._listen()
        self._draw_orb()
        self.refresh()
        self.root.after(80, self._tick)
        self.root.after(REFRESH_MS, self._auto_refresh)

    # ---- orb ------------------------------------------------------------------------------------------
    def _place_orb(self):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x, y = self.state.get("x"), self.state.get("y")
        if not isinstance(x, int) or not isinstance(y, int) or not (0 <= x <= sw - ORB and 0 <= y <= sh - ORB):
            x, y = sw - ORB - 28, sh - ORB - 90  # bottom right, above the taskbar
        self.root.geometry("%dx%d+%d+%d" % (ORB, ORB, x, y))

    def _bind_orb(self):
        c = self.canvas
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._motion)
        c.bind("<ButtonRelease-1>", self._release)
        c.bind("<Button-3>", self._menu)
        c.bind("<Button-2>", self._menu)
        c.bind("<Enter>", lambda e: self._tip(True))
        c.bind("<Leave>", lambda e: self._tip(False))

    def _press(self, event):
        self._drag = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y(), False)
        self._tip(False)

    def _motion(self, event):
        if not self._drag:
            return
        x0, y0, wx, wy, moved = self._drag
        dx, dy = event.x_root - x0, event.y_root - y0
        if moved or abs(dx) + abs(dy) > 4:
            self._drag = (x0, y0, wx, wy, True)
            self.root.geometry("+%d+%d" % (wx + dx, wy + dy))

    def _release(self, event):
        moved = self._drag and self._drag[4]
        self._drag = None
        if moved:
            self.state.update(x=self.root.winfo_x(), y=self.root.winfo_y())
            _save_state(self.state)
        else:
            self.toggle_panel()

    def _menu(self, event):
        menu = tk.Menu(self.root, tearoff=0, bg=SURFACE, fg=TEXT, activebackground=SURFACE_2,
                       activeforeground=ACCENT, bd=0)
        menu.add_command(label="Open TIDOS panel", command=self.show_panel)
        menu.add_command(label="Refresh now", command=self.refresh)
        menu.add_command(label="Control Center (login)…", command=launch.open_control_center)
        menu.add_separator()
        menu.add_command(label="Close the orb", command=self.quit)
        menu.tk_popup(event.x_root, event.y_root)

    def _tip(self, show):
        if self._tipwin:
            self._tipwin.destroy()
            self._tipwin = None
        if not show or self._drag:
            return
        text = "TIDOS - loading…"
        if self.snap:
            p = self.snap["player"]
            count, _ = data.attention(self.snap)
            text = "TIDOS  ·  Level %d  ·  Rank %s" % (p["level"], p["rank"])
            text += ("\n%d thing(s) need you - click" % count) if count else "\nAll calm - click to open"
        tip = tk.Toplevel(self.root)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        tk.Label(tip, text=text, bg=SURFACE, fg=TEXT, font=(SANS, 9), justify="left", padx=10, pady=6,
                 highlightthickness=1, highlightbackground=LINE_STRONG).pack()
        tip.update_idletasks()
        x = self.root.winfo_x() - tip.winfo_reqwidth() - 8
        if x < 0:
            x = self.root.winfo_x() + ORB + 8
        tip.geometry("+%d+%d" % (x, self.root.winfo_y() + 16))
        self._tipwin = tip

    def _draw_orb(self):
        c, s = self.canvas, ORB
        c.delete("all")
        count, mood = data.attention(self.snap) if self.snap else (0, "calm")
        color = MOOD[mood]
        # halo: breathes when something needs the user
        pulse = (math.sin(self.phase) + 1) / 2 if count else 0.35
        halo = 3 + 3 * pulse
        c.create_oval(halo, halo, s - halo, s - halo, outline=color if count else LINE, width=1)
        pad = 9
        c.create_oval(pad, pad, s - pad, s - pad, fill=SURFACE, outline=LINE, width=2)
        if self.snap:
            p = self.snap["player"]
            span = max(1, p["next_xp"] - p["floor_xp"])
            frac = min(1.0, max(0.0, (p["xp"] - p["floor_xp"]) / span))
            c.create_arc(pad, pad, s - pad, s - pad, start=90, extent=-359.9 * frac, style="arc",
                         outline=ACCENT, width=3)
            c.create_text(s / 2, s / 2 - 5, text=str(p["level"]), fill=TEXT, font=(MONO, 17, "bold"))
            c.create_text(s / 2, s / 2 + 15, text="RANK " + p["rank"], fill=VIOLET, font=(MONO, 7, "bold"))
        else:
            c.create_text(s / 2, s / 2, text="TIDOS", fill=ACCENT, font=(MONO, 9, "bold"))
        if count:
            r, cx, cy = 10, s - 15, 15
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline=BG, width=2)
            c.create_text(cx, cy, text=str(min(count, 99)), fill=BG, font=(SANS, 8, "bold"))
        if self.loading:
            c.create_arc(pad - 4, pad - 4, s - pad + 4, s - pad + 4, start=-math.degrees(self.phase) * 3,
                         extent=60, style="arc", outline=VIOLET, width=2)

    def _tick(self):
        self.phase += 0.12
        while True:
            try:
                kind, payload = self.inbox.get_nowait()
            except queue.Empty:
                break
            if kind == "snap":
                self.loading = False
                self.snap = payload
                if self.panel:
                    self._render_panel()
            elif kind == "error":
                self.loading = False
            elif kind == "msg":
                self._message(payload)
        self._draw_orb()
        self.root.after(80, self._tick)

    # ---- data -----------------------------------------------------------------------------------------
    def refresh(self):
        if self.loading:
            return
        self.loading = True

        def work():
            try:
                conn = db.connect()
                try:
                    self.inbox.put(("snap", data.snapshot(conn)))
                finally:
                    conn.close()
            except Exception as e:  # noqa: BLE001 - a broken brain must not kill the orb
                self.inbox.put(("error", str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _wheel(self, up):
        if self.panel and self.scroll:
            self.scroll.wheel(up)

    def _auto_refresh(self):
        self.refresh()
        self.root.after(REFRESH_MS, self._auto_refresh)

    def _listen(self):
        server = self.server

        def loop():
            while True:
                try:
                    client, _ = server.accept()
                except OSError:
                    return
                with client:
                    client.settimeout(1)
                    try:
                        msg = client.recv(32).strip()
                    except OSError:
                        continue
                if msg in launch.MESSAGES:
                    self.inbox.put(("msg", msg))

        threading.Thread(target=loop, daemon=True).start()

    def _message(self, msg):
        if msg == b"refresh":
            self.refresh()
        elif msg == b"show":
            self.show_panel()
        elif msg == b"quit":
            self.quit()

    def quit(self):
        try:
            self.server.close()
        except OSError:
            pass
        self.root.destroy()

    # ---- panel ----------------------------------------------------------------------------------------
    def toggle_panel(self):
        if self.panel:
            self.hide_panel()
        else:
            self.show_panel()

    def hide_panel(self):
        if self.panel:
            self.panel.destroy()
            self.panel = None

    def show_panel(self):
        if self.panel:
            self.panel.lift()
            return
        self.refresh()
        panel = tk.Toplevel(self.root)
        panel.overrideredirect(True)
        panel.attributes("-topmost", True)
        panel.configure(bg=LINE_STRONG)  # 1px frame around a flat window
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        ox, oy = self.root.winfo_x(), self.root.winfo_y()
        x = ox - PANEL_W - 12 if ox + ORB / 2 > sw / 2 else ox + ORB + 12
        y = min(max(10, oy + ORB - PANEL_H), sh - PANEL_H - 50)
        panel.geometry("%dx%d+%d+%d" % (PANEL_W, PANEL_H, max(10, min(x, sw - PANEL_W - 10)), max(10, y)))
        panel.bind("<Escape>", lambda e: self.hide_panel())
        self.panel = panel
        inner = tk.Frame(panel, bg=BG)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self._header(inner)
        body = tk.Frame(inner, bg=BG)
        body.pack(fill="both", expand=True)
        self.nav = tk.Frame(body, bg=SURFACE, width=170)
        self.nav.pack(side="left", fill="y")
        self.nav.pack_propagate(False)
        self.content = tk.Frame(body, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)
        self._footer(inner)
        self._render_panel()
        panel.focus_force()

    def _header(self, parent):
        bar = tk.Frame(parent, bg=SURFACE, height=44)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text="◈ TIDOS", bg=SURFACE, fg=ACCENT, font=(MONO, 12, "bold")).pack(side="left", padx=14)
        self.chip = tk.Label(bar, text="", bg=SURFACE, fg=MUTED, font=(MONO, 9))
        self.chip.pack(side="left", padx=6)
        close = tk.Label(bar, text="✕", bg=SURFACE, fg=MUTED, font=(SANS, 12), cursor="hand2", padx=14)
        close.pack(side="right", fill="y")
        close.bind("<Button-1>", lambda e: self.hide_panel())
        close.bind("<Enter>", lambda e: close.configure(fg=BAD))
        close.bind("<Leave>", lambda e: close.configure(fg=MUTED))

        panel, grab = parent.winfo_toplevel(), [0, 0]

        def press(e):
            grab[:] = [e.x_root - panel.winfo_x(), e.y_root - panel.winfo_y()]

        def move(e):
            panel.geometry("+%d+%d" % (e.x_root - grab[0], e.y_root - grab[1]))

        bar.bind("<ButtonPress-1>", press)
        bar.bind("<B1-Motion>", move)
        tk.Frame(parent, bg=LINE, height=1).pack(fill="x")

    def _footer(self, parent):
        tk.Frame(parent, bg=LINE, height=1).pack(fill="x")
        bar = tk.Frame(parent, bg=SURFACE, height=40)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        self.updated = tk.Label(bar, text="", bg=SURFACE, fg=FAINT, font=(MONO, 8))
        self.updated.pack(side="left", padx=14)
        self._link(bar, "Control Center  →", launch.open_control_center, ACCENT).pack(side="right", padx=14)
        self._link(bar, "⟳ Refresh", self.refresh, MUTED).pack(side="right", padx=4)
        tk.Label(bar, text="read-only view · changes need the Control Center login", bg=SURFACE, fg=FAINT,
                 font=(SANS, 8)).pack(side="right", padx=12)

    def _link(self, parent, text, command, color):
        label = tk.Label(parent, text=text, bg=parent["bg"], fg=color, font=(SANS, 9, "bold"), cursor="hand2")
        label.bind("<Button-1>", lambda e: command())
        label.bind("<Enter>", lambda e: label.configure(fg=TEXT))
        label.bind("<Leave>", lambda e: label.configure(fg=color))
        return label

    def _render_panel(self):
        if not self.panel:
            return
        for w in self.nav.winfo_children():
            w.destroy()
        tk.Label(self.nav, text="SYSTEM", bg=SURFACE, fg=FAINT, font=(MONO, 8, "bold"),
                 anchor="w").pack(fill="x", padx=16, pady=(16, 6))
        for key, title in TABS:
            self._nav_item(key, title)
        snap = self.snap
        if snap and snap.get("session"):
            s = snap["session"]
            self.chip.configure(text="%s · %s mode · %s" % (s.get("model") or "?", (s.get("mode") or "?").upper(),
                                                           s.get("project") or "?"))
        if snap:
            self.updated.configure(text="updated %s" % _ago(snap["updated_at"]))
        for w in self.content.winfo_children():
            w.destroy()
        if not snap:
            tk.Label(self.content, text="Reading the brain…", bg=BG, fg=MUTED, font=(SANS, 11)).pack(pady=60)
            return
        self.scroll = Scroll(self.content)
        self.scroll.pack(fill="both", expand=True)
        getattr(self, "_tab_" + self.tab)(self.scroll.body, snap)
        self.scroll.canvas.yview_moveto(0)

    def _nav_item(self, key, title):
        active = key == self.tab
        badge = ""
        if self.snap and key == "evolution":
            count, _ = data.attention(self.snap)
            badge = "  %d" % count if count else ""
        if self.snap and key == "next":
            mine = sum(1 for r in self.snap["next"] if not r["auto"])
            badge = "  %d" % mine if mine else ""
        row = tk.Frame(self.nav, bg=SURFACE_2 if active else SURFACE, cursor="hand2")
        row.pack(fill="x")
        tk.Frame(row, bg=ACCENT if active else SURFACE, width=3).pack(side="left", fill="y")
        label = tk.Label(row, text=title, bg=row["bg"], fg=TEXT if active else MUTED, font=(SANS, 10),
                         anchor="w", padx=13, pady=9)
        label.pack(side="left", fill="x", expand=True)
        if badge:
            tk.Label(row, text=badge.strip(), bg=WARN, fg=BG, font=(SANS, 8, "bold"), padx=6).pack(side="right",
                                                                                                    padx=10)

        def pick(e):
            self.tab = key
            self.state["tab"] = key
            _save_state(self.state)
            self._render_panel()

        for w in (row, label):
            w.bind("<Button-1>", pick)

    # ---- panel building blocks ------------------------------------------------------------------------
    def _section(self, parent, title, note=""):
        head = tk.Frame(parent, bg=BG)
        head.pack(fill="x", padx=22, pady=(18, 8))
        tk.Label(head, text=title.upper(), bg=BG, fg=ACCENT, font=(MONO, 9, "bold")).pack(side="left")
        if note:
            tk.Label(head, text=note, bg=BG, fg=FAINT, font=(SANS, 8)).pack(side="left", padx=10)
        return head

    def _card(self, parent):
        card = tk.Frame(parent, bg=SURFACE, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="x", padx=22, pady=3)
        return card

    def _chip(self, parent, text, color):
        return tk.Label(parent, text=text, bg=parent["bg"], fg=color, font=(MONO, 8, "bold"),
                        highlightthickness=1, highlightbackground=color, padx=6)

    def _bar(self, parent, value, color, width=220, height=6):
        c = tk.Canvas(parent, width=width, height=height, bg=SURFACE_2, highlightthickness=0, bd=0)
        c.create_rectangle(0, 0, width * max(0, min(100, value)) / 100, height, fill=color, width=0)
        return c

    def _empty(self, parent, text):
        tk.Label(parent, text=text, bg=BG, fg=FAINT, font=(SANS, 9), anchor="w").pack(fill="x", padx=24, pady=4)

    # ---- tabs -----------------------------------------------------------------------------------------
    def _tab_journey(self, body, snap):
        p, totals = snap["player"], snap["totals"]
        hero = tk.Frame(body, bg=BG)
        hero.pack(fill="x", padx=22, pady=(20, 4))
        ring = tk.Canvas(hero, width=128, height=128, bg=BG, highlightthickness=0)
        ring.pack(side="left")
        span = max(1, p["next_xp"] - p["floor_xp"])
        frac = min(1.0, max(0.0, (p["xp"] - p["floor_xp"]) / span))
        ring.create_oval(8, 8, 120, 120, outline=LINE, width=6)
        ring.create_arc(8, 8, 120, 120, start=90, extent=-359.9 * frac, style="arc", outline=ACCENT, width=6)
        ring.create_text(64, 56, text=str(p["level"]), fill=TEXT, font=(MONO, 30, "bold"))
        ring.create_text(64, 88, text="LEVEL", fill=MUTED, font=(MONO, 8, "bold"))
        side = tk.Frame(hero, bg=BG)
        side.pack(side="left", fill="both", expand=True, padx=(18, 0))
        top = tk.Frame(side, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="RANK %s" % p["rank"], bg=BG, fg=VIOLET, font=(MONO, 16, "bold")).pack(side="left")
        tk.Label(top, text="  %d / %d XP  ·  %d XP to level %d" % (p["xp"], p["next_xp"], p["next_xp"] - p["xp"],
                                                                     p["level"] + 1),
                 bg=BG, fg=MUTED, font=(MONO, 9)).pack(side="left", pady=(6, 0))
        for st in snap["stats"]:
            row = tk.Frame(side, bg=BG)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=st["key"], bg=BG, fg=TEXT, font=(MONO, 9, "bold"), width=4, anchor="w").pack(side="left")
            color = OK if st["value"] >= 70 else WARN if st["value"] >= 45 else BAD
            self._bar(row, st["value"], color, width=150).pack(side="left", padx=6)
            tk.Label(row, text="%3d" % st["value"], bg=BG, fg=color, font=(MONO, 9, "bold")).pack(side="left")
            tk.Label(row, text=_one_line(st["hint"], 46), bg=BG, fg=FAINT,
                     font=(SANS, 8), anchor="w").pack(side="left", padx=8)
        tk.Label(body, text="%d tasks · %d sessions · %d cleared · %d failed" % (
            totals["tasks"], totals["sessions"], totals["success"], totals["failure"]),
            bg=BG, fg=MUTED, font=(MONO, 9), anchor="w").pack(fill="x", padx=24, pady=(8, 0))

        gained = sum(d["xp"] for d in snap["growth"])
        self._section(body, "Revolution · last 14 days", "%+d XP · %d cleared   (bars = XP, green = tasks cleared)" % (
            gained, sum(d["cleared"] for d in snap["growth"])))
        self._growth_chart(body, snap["growth"])

        self._section(body, "Domains", "where TIDOS has grown")
        for d in snap["domains"]:
            row = tk.Frame(body, bg=BG)
            row.pack(fill="x", padx=24, pady=2)
            tk.Label(row, text=_one_line(d["name"], 18), bg=BG, fg=TEXT, font=(SANS, 9), width=18,
                     anchor="w").pack(side="left")
            self._chip(row, d["rank"], VIOLET).pack(side="left", padx=(0, 8))
            top_xp = max(1, snap["domains"][0]["xp"])
            self._bar(row, 100 * d["xp"] / top_xp, ACCENT, width=240).pack(side="left")
            tk.Label(row, text="  Lv %d · %d XP · %d/%d cleared" % (d["level"], d["xp"], d["success"], d["tasks"]),
                     bg=BG, fg=FAINT, font=(MONO, 8)).pack(side="left")
        tk.Frame(body, bg=BG, height=18).pack()

    def _growth_chart(self, parent, days):
        w, h, left, bottom = 610, 150, 34, 22
        c = tk.Canvas(parent, width=w, height=h, bg=SURFACE, highlightthickness=1, highlightbackground=LINE)
        c.pack(padx=22, anchor="w")
        top = max([abs(d["xp"]) for d in days] + [10])
        zero = (h - bottom) * top / (top + max([-d["xp"] for d in days] + [0])) if any(
            d["xp"] < 0 for d in days) else h - bottom
        scale = (zero - 12) / top
        c.create_line(left, zero, w - 8, zero, fill=LINE)
        c.create_text(left - 6, 12, text=str(top), fill=FAINT, font=(MONO, 7), anchor="e")
        c.create_text(left - 6, zero, text="0", fill=FAINT, font=(MONO, 7), anchor="e")
        slot = (w - left - 12) / max(1, len(days))
        for i, d in enumerate(days):
            x0 = left + i * slot + slot * 0.22
            x1 = left + (i + 1) * slot - slot * 0.22
            if d["xp"]:
                y = zero - d["xp"] * scale
                c.create_rectangle(x0, min(y, zero), x1, max(y, zero), width=0,
                                   fill=ACCENT if d["xp"] > 0 else BAD)
            if d["cleared"]:
                c.create_text((x0 + x1) / 2, min(zero - d["xp"] * scale, zero) - 7, text=str(d["cleared"]),
                              fill=OK, font=(MONO, 7, "bold"))
            if i % 2 == len(days) % 2 or i == len(days) - 1:
                c.create_text((x0 + x1) / 2, h - 9, text=d["day"][5:], fill=FAINT, font=(MONO, 7))

    def _tab_evolution(self, body, snap):
        self._section(body, "System messages", "what needs your attention")
        colors = {"bad": BAD, "ok": OK, "info": ACCENT}
        for n in snap["notifications"] or []:
            card = self._card(body)
            tk.Frame(card, bg=colors.get(n["level"], ACCENT), width=3).pack(side="left", fill="y")
            tk.Label(card, text=n["text"], bg=SURFACE, fg=TEXT, font=(SANS, 9), anchor="w", justify="left",
                     wraplength=560, padx=10, pady=7).pack(side="left", fill="x")
        if not snap["notifications"]:
            self._empty(body, "Nothing needs you right now.")

        report, drafts = snap["report"], snap["drafts"]
        self._section(body, "Daily quest", report["name"] if report else "")
        if report:
            good = "REGRESSION" not in report["result"]
            card = self._card(body)
            tk.Label(card, text="✔" if good else "✖", bg=SURFACE, fg=OK if good else BAD,
                     font=(SANS, 14, "bold"), padx=12).pack(side="left")
            tk.Label(card, text=report["result"] or "-", bg=SURFACE, fg=TEXT, font=(SANS, 10), anchor="w",
                     pady=8).pack(side="left")
        else:
            self._empty(body, "No daily quest report yet (scripts/daily_quest.py).")

        self._section(body, "Unlocked by growth", "drafts wait for you - never activated without you")
        row = tk.Frame(body, bg=BG)
        row.pack(fill="x", padx=22)
        for label, n, color in (("skills", drafts["skills"], ACCENT), ("specialists", drafts["agents"], VIOLET),
                                ("issues", drafts["issues"], WARN)):
            box = tk.Frame(row, bg=SURFACE, highlightthickness=1, highlightbackground=LINE)
            box.pack(side="left", padx=(0, 8), ipadx=18, ipady=6)
            tk.Label(box, text=str(n), bg=SURFACE, fg=color, font=(MONO, 18, "bold")).pack()
            tk.Label(box, text=label, bg=SURFACE, fg=MUTED, font=(SANS, 8)).pack()

        counts = snap["proposal_counts"]
        self._section(body, "Proposals", " · ".join("%d %s" % (n, s) for s, n in sorted(counts.items())))
        status_color = {"new": WARN, "accepted": ACCENT, "implemented": OK, "rejected": FAINT, "done": OK}
        for prop in snap["proposals"]:
            card = self._card(body)
            top = tk.Frame(card, bg=SURFACE)
            top.pack(fill="x", padx=10, pady=(7, 0))
            tk.Label(top, text="#%s" % prop["id"], bg=SURFACE, fg=FAINT, font=(MONO, 9)).pack(side="left")
            tk.Label(top, text=_one_line(prop["title"], 70), bg=SURFACE, fg=TEXT,
                     font=(SANS, 10, "bold")).pack(side="left", padx=6)
            self._chip(top, prop["status"] or "?", status_color.get(prop["status"], MUTED)).pack(side="right")
            self._chip(top, prop["priority"] or "-", MUTED).pack(side="right", padx=6)
            tk.Label(card, text=_one_line(prop["reason"], 220) + (
                ("\nbranch: " + prop["branch"]) if prop.get("branch") else ""),
                bg=SURFACE, fg=MUTED, font=(SANS, 9), anchor="w", justify="left", wraplength=580).pack(
                fill="x", padx=10, pady=(2, 8))
        if not snap["proposals"]:
            self._empty(body, "The evolution queue is empty: TIDOS has no proposal for itself right now.")
        tk.Frame(body, bg=BG, height=18).pack()

    def _tab_solutions(self, body, snap):
        self._section(body, "Cleared tasks", "verified solutions TIDOS learned from")
        for s in snap["solutions"]:
            card = self._card(body)
            top = tk.Frame(card, bg=SURFACE)
            top.pack(fill="x", padx=10, pady=(7, 0))
            self._chip(top, s["project"] or "?", VIOLET).pack(side="left")
            tk.Label(top, text=_ago(s["ts"]), bg=SURFACE, fg=FAINT, font=(MONO, 8)).pack(side="left", padx=8)
            score = s.get("score") or 0
            tk.Label(top, text="score %.2f" % score, bg=SURFACE, fg=OK if score >= 0.7 else WARN,
                     font=(MONO, 8, "bold")).pack(side="right")
            tk.Label(card, text=_one_line(s["prompt"], 200), bg=SURFACE, fg=TEXT, font=(SANS, 9), anchor="w",
                     justify="left", wraplength=580).pack(fill="x", padx=10, pady=(3, 8))
        if not snap["solutions"]:
            self._empty(body, "No cleared task yet: finish one with a passing check.")
        self._section(body, "Models at work")
        tk.Label(body, text="Every model's tasks feed the same brain; open the Control Center for the full army.",
                 bg=BG, fg=FAINT, font=(SANS, 8), anchor="w").pack(fill="x", padx=24)
        tk.Frame(body, bg=BG, height=18).pack()

    def _tab_next(self, body, snap):
        self._section(body, "Today's quests")
        for q in snap["quests"]:
            card = self._card(body)
            mark, color = ("✔", OK) if q["done"] else ("✖", BAD) if q.get("failed") else ("○", MUTED)
            tk.Label(card, text=mark, bg=SURFACE, fg=color, font=(SANS, 12, "bold"), padx=12).pack(side="left")
            tk.Label(card, text=q["title"], bg=SURFACE, fg=TEXT, font=(SANS, 10), pady=7).pack(side="left")
            tk.Label(card, text="%d / %d" % (q["progress"], q["goal"]), bg=SURFACE, fg=MUTED,
                     font=(MONO, 9)).pack(side="right", padx=12)
        self._section(body, "Next moves", "what TIDOS recommends doing next")
        for r in snap["next"]:
            card = self._card(body)
            top = tk.Frame(card, bg=SURFACE)
            top.pack(fill="x", padx=10, pady=(7, 0))
            tk.Label(top, text=r["title"], bg=SURFACE, fg=TEXT, font=(SANS, 10, "bold")).pack(side="left")
            self._chip(top, r["verdict"], OK if r["auto"] else WARN).pack(side="right")
            tk.Label(card, text=r["reason"], bg=SURFACE, fg=MUTED, font=(SANS, 9), anchor="w", justify="left",
                     wraplength=580).pack(fill="x", padx=10, pady=(2, 8))
        if not snap["next"]:
            self._empty(body, "Nothing recommended right now.")
        row = tk.Frame(body, bg=BG)
        row.pack(fill="x", padx=22, pady=14)
        self._link(row, "Decide in the Control Center  →", launch.open_control_center, ACCENT).pack(side="left")

    def run(self):
        self.root.mainloop()


def main(port=launch.PORT, show=False):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind(("127.0.0.1", port))
    except OSError:  # one orb per user: bring the running one forward instead
        server.close()
        launch.send(b"show", port)
        return 0
    server.listen(4)
    try:
        orb = Orb(server)
    except tk.TclError:
        server.close()
        return 1  # no display
    if show:
        orb.root.after(300, orb.show_panel)
    orb.run()
    return 0
