"""Windows GUI for pytr – Trade Republic CLI tool."""

import asyncio
import io
import os
import queue
import re
import tempfile
import threading
import time
import tkinter as tk
from datetime import datetime, timedelta
from typing import Any
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .alarms import Alarms
from .api import BASE_DIR, CREDENTIALS_FILE, TradeRepublicApi
from .details import Details
from .dl import DL
from .event import Event
from .portfolio import PORTFOLIO_COLUMNS, Portfolio
from .savings_plans import SavingsPlans
from .timeline import Timeline
from .transactions import SUPPORTED_LANGUAGES, TransactionExporter
from .utils import get_logger

_ANSI = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_ISIN_RE = re.compile(r"^[A-Za-z]{2}[A-Za-z0-9]{10}$")

_ASSET_TYPES = ["stock", "etf", "fund", "crypto", "bond", "derivative"]

# ---------------------------------------------------------------------------
# Details: suppress raw JSON and replace with formatted output
# ---------------------------------------------------------------------------

_STOPPED = "__stopped__"


class _GUIDetails(Details):
    """Details subclass: two-phase fetch (exchange-agnostic first, then ticker/perf
    using the exchange reported by the instrument), with stop-event support."""

    async def details_loop(self, stop_event: threading.Event | None = None) -> None:  # type: ignore[name-defined]
        tr = self.tr
        # Clear stale subscriptions from previous operations so recv() can't stall
        # waiting for IDs that a freshly-reconnected server has never seen.
        tr.subscriptions.clear()
        tr._previous_responses.clear()

        def check_stop() -> None:
            if stop_event and stop_event.is_set():
                raise RuntimeError(_STOPPED)

        async def drain(waiting: set) -> None:
            """Keep calling recv() until all IDs in *waiting* have been answered or
            cancelled by the server. Exits early if stop is requested."""
            while waiting:
                check_stop()
                # Detect subscriptions silently cancelled by server (C frames)
                cancelled = waiting - set(tr.subscriptions.keys())
                waiting -= cancelled
                if not waiting:
                    break
                try:
                    sid, sub, response = await asyncio.wait_for(tr.recv(), timeout=2.0)
                except asyncio.TimeoutError:
                    continue  # re-check stop + cancellations
                if sid not in waiting:
                    continue
                t = sub["type"]
                if t == "instrument":
                    self.instrument = response
                elif t == "instrumentSuitability":
                    self.instrumentSuitability = response
                elif t == "stockDetails":
                    self.stockDetails = response
                elif t == "neonNews":
                    self.neonNews = response
                elif t == "ticker":
                    self.ticker = response
                elif t == "performance":
                    self.performance = response
                waiting.discard(sid)
                try:
                    await tr.unsubscribe(sid)
                except Exception:
                    pass

        # ── Phase 1: data that doesn't need an exchange ID ──────────────────
        phase1: set = {
            await tr.instrument_details(self.isin),
            await tr.instrument_suitability(self.isin),
            await tr.stock_details(self.isin),
            await tr.news(self.isin),
        }
        await drain(phase1)
        check_stop()

        # ── Phase 2: ticker + performance using the instrument's own exchange ─
        # Using the hardcoded "LSX" exchange fails silently for crypto (and any
        # asset not listed there): the server sends a C-frame, recv() discards
        # it, and the loop stalls forever waiting for a response that never arrives.
        exchange = "LSX"
        inst = getattr(self, "instrument", None) or {}
        eids = inst.get("exchangeIds") or [ex.get("id") for ex in (inst.get("exchanges") or []) if ex.get("id")]
        if eids:
            exchange = eids[0]

        phase2: set = {
            await tr.ticker(self.isin, exchange=exchange),
            await tr.performance(self.isin, exchange=exchange),
        }
        await drain(phase2)

        await tr.close()


def _print_details(d: _GUIDetails) -> None:
    """Render a Details object as human-readable text to stdout."""
    W = 62

    def section(title: str) -> None:
        print(f"\n  {title}")
        print(f"  {'─' * (W - 2)}")

    inst = getattr(d, "instrument", {}) or {}
    name = inst.get("name") or inst.get("shortName") or d.isin
    short = inst.get("shortName", "")
    typ = inst.get("typeId", "")

    print(f"\n{'═' * W}")
    print(f"  {name}")
    if short and short != name:
        print(f"  ({short})")
    print(f"  ISIN: {d.isin}   Type: {typ}")
    print(f"{'═' * W}")

    # Price
    ticker = getattr(d, "ticker", {}) or {}
    if ticker:
        last = ticker.get("last", {}) or {}
        price = last.get("price")
        bid = (ticker.get("bid") or {}).get("price")
        ask = (ticker.get("ask") or {}).get("price")
        if price is not None:
            print(f"\n  Price : {price}")
        if bid is not None and ask is not None:
            print(f"  Bid   : {bid}    Ask: {ask}")

    # Performance
    perf = getattr(d, "performance", {}) or {}
    if perf:
        section("PERFORMANCE")
        labels = [
            ("since1d", "1 Day"),
            ("since1w", "1 Week"),
            ("since1m", "1 Month"),
            ("since3m", "3 Months"),
            ("since6m", "6 Months"),
            ("since1y", "1 Year"),
            ("since3y", "3 Years"),
            ("since5y", "5 Years"),
            ("sinceIpo", "Since IPO"),
        ]
        for key, label in labels:
            v = perf.get(key)
            if v is not None:
                pct = float(v) * 100
                sign = "+" if pct >= 0 else ""
                print(f"  {label:<14}: {sign}{pct:.2f}%")

    # Exchanges
    exchanges = inst.get("exchanges") or []
    if exchanges:
        section("EXCHANGES")
        for ex in exchanges:
            slug = ex.get("slug", "?")
            sym = ex.get("symbolAtExchange", "")
            exname = ex.get("nameAtExchange", "")
            print(f"  {slug:<8} {sym:<12} {exname}")

    # Tags
    tags = inst.get("tags") or []
    if tags:
        section("TAGS / CATEGORIES")
        for tag in tags:
            print(f"  {tag.get('type', '?'):<20}: {tag.get('name', '?')}")

    # Stock / company details
    sd = getattr(d, "stockDetails", {}) or {}
    company = sd.get("company") or {}
    non_empty_company = {k: v for k, v in company.items() if v is not None and v != ""}
    if non_empty_company:
        section("COMPANY")
        for k, v in non_empty_company.items():
            vs = str(v)
            if len(vs) > 80:
                vs = vs[:80] + "…"
            print(f"  {k:<22}: {vs}")

    # Other stock detail scalars
    scalar_sd = {
        k: v
        for k, v in sd.items()
        if k != "company" and v not in (None, [], "", {}) and not isinstance(v, (dict, list))
    }
    if scalar_sd:
        section("STOCK DETAILS")
        for k, v in scalar_sd.items():
            vs = str(v)
            if len(vs) > 80:
                vs = vs[:80] + "…"
            print(f"  {k:<22}: {vs}")

    # Suitability summary
    suit = getattr(d, "instrumentSuitability", {}) or {}
    if suit:
        section("SUITABILITY")
        for k, v in suit.items():
            if v not in (None, [], "", {}):
                print(f"  {k:<22}: {v}")

    # News
    news_items = getattr(d, "neonNews", []) or []
    since = datetime.now() - timedelta(days=30)
    recent = [
        (datetime.fromtimestamp(n["createdAt"] / 1000.0), n.get("headline", ""))
        for n in news_items
        if datetime.fromtimestamp(n["createdAt"] / 1000.0) > since
    ]
    if recent:
        section("RECENT NEWS  (last 30 days)")
        for dt, headline in sorted(recent, reverse=True)[:15]:
            print(f"  {dt.strftime('%Y-%m-%d %H:%M')}  {headline}")

    print()


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------


def _generate_pdf(d: _GUIDetails) -> Path:
    """Build a formatted PDF from a Details object, save to a temp file, return path."""
    import io as _io

    from reportlab.lib import colors
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    BLUE = HexColor("#1a6e9a")
    STRIPE = HexColor("#f0f5fa")

    inst = getattr(d, "instrument", {}) or {}
    name = inst.get("name") or inst.get("shortName") or d.isin
    short = inst.get("shortName", "")
    typ = inst.get("typeId", "")

    buf = _io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Details: {name}",
        author="pytr",
    )

    styles = getSampleStyleSheet()
    H1 = ParagraphStyle("H1", parent=styles["Title"], fontSize=18, spaceAfter=2)
    H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, textColor=BLUE, spaceBefore=12, spaceAfter=3)
    GREY = ParagraphStyle("Grey", parent=styles["Normal"], fontSize=9, textColor=colors.grey, spaceAfter=8)
    SMALL = ParagraphStyle("Small", parent=styles["Normal"], fontSize=9, spaceAfter=1)

    def tbl(data, col_widths, header=True):
        t = Table(data, colWidths=col_widths, repeatRows=(1 if header else 0))
        cmds = [
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, STRIPE]),
            ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#d0d8e0")),
        ]
        if header:
            cmds += [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        else:
            cmds.append(("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"))
        t.setStyle(TableStyle(cmds))
        return t

    story: list[Any] = []

    # ── Header ───────────────────────────────────────────────────────────
    story.append(Paragraph(name, H1))
    if short and short != name:
        story.append(Paragraph(f"({short})", GREY))
    story.append(
        Paragraph(
            f"ISIN: {d.isin} &nbsp;&nbsp; Type: {typ} &nbsp;&nbsp; "
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            GREY,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceAfter=6))

    # ── Price ─────────────────────────────────────────────────────────────
    ticker = getattr(d, "ticker", {}) or {}
    if ticker:
        last = (ticker.get("last") or {}).get("price")
        bid = (ticker.get("bid") or {}).get("price")
        ask = (ticker.get("ask") or {}).get("price")
        if last is not None:
            rows = [["Current Price", str(last)]]
            if bid is not None and ask is not None:
                rows.append(["Bid / Ask", f"{bid} / {ask}"])
            story.append(tbl(rows, [5 * cm, None], header=False))
            story.append(Spacer(1, 6))

    # ── Performance ───────────────────────────────────────────────────────
    perf = getattr(d, "performance", {}) or {}
    if perf:
        story.append(Paragraph("Performance", H2))
        labels = [
            ("since1d", "1 Day"),
            ("since1w", "1 Week"),
            ("since1m", "1 Month"),
            ("since3m", "3 Months"),
            ("since6m", "6 Months"),
            ("since1y", "1 Year"),
            ("since3y", "3 Years"),
            ("since5y", "5 Years"),
            ("sinceIpo", "Since IPO"),
        ]
        rows = [["Period", "Return"]]
        for key, label in labels:
            v = perf.get(key)
            if v is not None:
                pct = float(v) * 100
                rows.append([label, f"{'+' if pct >= 0 else ''}{pct:.2f}%"])
        if len(rows) > 1:
            story.append(tbl(rows, [5 * cm, 4 * cm]))

    # ── Exchanges ─────────────────────────────────────────────────────────
    exchanges = inst.get("exchanges") or []
    if exchanges:
        story.append(Paragraph("Exchanges", H2))
        rows = [["Exchange", "Symbol", "Name"]]
        for ex in exchanges[:12]:
            rows.append([ex.get("slug", ""), ex.get("symbolAtExchange", ""), ex.get("nameAtExchange", "")])
        story.append(tbl(rows, [3 * cm, 4 * cm, None]))

    # ── Tags ─────────────────────────────────────────────────────────────
    tags = inst.get("tags") or []
    if tags:
        story.append(Paragraph("Categories & Tags", H2))
        rows = [[tag.get("type", ""), tag.get("name", "")] for tag in tags]
        story.append(tbl(rows, [5 * cm, None], header=False))

    # ── Company ───────────────────────────────────────────────────────────
    sd = getattr(d, "stockDetails", {}) or {}
    company = {k: v for k, v in (sd.get("company") or {}).items() if v not in (None, "", [], {})}
    if company:
        story.append(Paragraph("Company", H2))
        rows1: list[list[Any]] = []
        for k, v in company.items():
            vs = str(v)
            rows1.append([k, Paragraph(vs[:300] + ("…" if len(vs) > 300 else ""), SMALL)])
        story.append(tbl(rows1, [5 * cm, None], header=False))

    # ── Stock Details ─────────────────────────────────────────────────────
    scalar_sd = {
        k: v
        for k, v in sd.items()
        if k != "company" and v not in (None, [], "", {}) and not isinstance(v, (dict, list))
    }
    if scalar_sd:
        story.append(Paragraph("Stock Details", H2))
        rows2: list[list[Any]] = []
        for k, v in scalar_sd.items():
            vs = str(v)
            rows2.append([k, Paragraph(vs[:300] + ("…" if len(vs) > 300 else ""), SMALL)])
        story.append(tbl(rows2, [5 * cm, None], header=False))

    # ── Suitability ───────────────────────────────────────────────────────
    suit = {k: v for k, v in (getattr(d, "instrumentSuitability", {}) or {}).items() if v not in (None, [], "", {})}
    if suit:
        story.append(Paragraph("Suitability", H2))
        rows = [[k, str(v)] for k, v in suit.items()]
        story.append(tbl(rows, [6 * cm, None], header=False))

    # ── News ──────────────────────────────────────────────────────────────
    news_items = getattr(d, "neonNews", []) or []
    since = datetime.now() - timedelta(days=30)
    recent = sorted(
        [
            (datetime.fromtimestamp(n["createdAt"] / 1000.0), n.get("headline", ""))
            for n in news_items
            if datetime.fromtimestamp(n["createdAt"] / 1000.0) > since
        ],
        reverse=True,
    )[:20]
    if recent:
        story.append(Paragraph("Recent News  (last 30 days)", H2))
        rows3: list[list[Any]] = [["Date", "Headline"]]
        for dt, headline in recent:
            rows3.append([dt.strftime("%Y-%m-%d %H:%M"), Paragraph(headline, SMALL)])
        story.append(tbl(rows3, [3.8 * cm, None]))

    doc.build(story)

    safe = re.sub(r"[^\w\-]", "_", name)[:40]
    tmp = Path(tempfile.gettempdir()) / f"pytr_{safe}_{d.isin}.pdf"
    tmp.write_bytes(buf.getvalue())
    return tmp


# ---------------------------------------------------------------------------
# Instrument search
# ---------------------------------------------------------------------------


async def _search_async(
    tr: TradeRepublicApi,
    query: str,
    asset_type: str,
    stop_event: threading.Event | None = None,  # type: ignore[name-defined]
) -> list:
    tr.subscriptions.clear()
    tr._previous_responses.clear()

    sub_id = await tr.search(query, asset_type=asset_type, page=1, page_size=20)
    deadline = asyncio.get_event_loop().time() + 15.0
    try:
        while True:
            if stop_event and stop_event.is_set():
                raise RuntimeError(_STOPPED)
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise asyncio.TimeoutError()
            try:
                recv_id, _, response = await asyncio.wait_for(tr.recv(), timeout=min(2.0, remaining))
            except asyncio.TimeoutError:
                if asyncio.get_event_loop().time() >= deadline:
                    raise RuntimeError(
                        "Search timed out (15 s). No response from server.\n"
                        "Tip: for Bitcoin / crypto, select 'crypto' as asset type."
                    )
                continue  # retry — re-checks stop_event at top of loop
            if recv_id != sub_id:
                continue
            await tr.unsubscribe(recv_id)
            await tr.close()
            if isinstance(response, list):
                return response
            for key in ("results", "instruments", "items"):
                if key in response:
                    return response[key]
            return []
    except Exception:
        try:
            await tr.close()
        except Exception:
            pass
        raise


class _SearchDialog(tk.Toplevel):
    """Shows search results and lets the user pick an instrument."""

    def __init__(self, parent: tk.Tk, results: list) -> None:
        super().__init__(parent)
        self.title("Select Instrument")
        self.resizable(True, True)
        self.minsize(500, 300)
        self.grab_set()
        self.transient(parent)
        self.result: dict | None = None
        self._items = results
        self._build()
        self._center(parent)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._lb.focus_set()
        self.wait_window()

    def _build(self) -> None:
        f = ttk.Frame(self, padding=12)
        f.pack(fill=tk.BOTH, expand=True)
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        ttk.Label(f, text="Select an instrument:", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 6)
        )

        lf = ttk.Frame(f)
        lf.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)

        self._lb = tk.Listbox(lf, font=("Consolas", 9), width=70, height=14, selectmode=tk.SINGLE, activestyle="dotbox")
        self._lb.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(lf, command=self._lb.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._lb.config(yscrollcommand=sb.set)

        for item in self._items:
            isin = item.get("isin") or item.get("instrumentId", "?")
            name = item.get("shortName") or item.get("name", "?")
            typ = item.get("typeId", "")
            self._lb.insert(tk.END, f"  {isin}  {name:<40} {typ}")

        self._lb.bind("<Double-Button-1>", lambda _: self._select())
        self._lb.bind("<Return>", lambda _: self._select())

        bf = ttk.Frame(f)
        bf.grid(row=2, column=0, sticky=tk.W)
        ttk.Button(bf, text="Select", command=self._select, width=10).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bf, text="Cancel", command=self.destroy, width=10).pack(side=tk.LEFT)

    def _center(self, parent: tk.Tk) -> None:
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _select(self) -> None:
        sel = self._lb.curselection()
        if not sel:
            return
        self.result = self._items[sel[0]]
        self.destroy()


class _QueueWriter(io.TextIOBase):
    def __init__(self, q: "queue.Queue[str]") -> None:
        self._q = q

    def write(self, s: str) -> int:
        if s:
            self._q.put(_ANSI.sub("", s))
        return len(s)

    def flush(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Auth dialogs
# ---------------------------------------------------------------------------


class _OTPDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, countdown: int) -> None:
        super().__init__(parent)
        self.title("Verification Code")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)
        self.result: str | None = None
        self.use_sms = False
        self._countdown = countdown
        self._active = True
        self._build()
        self._center(parent)
        threading.Thread(target=self._tick, daemon=True).start()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.code_entry.focus_set()
        self.wait_window()

    def _build(self) -> None:
        f = ttk.Frame(self, padding=24)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            f,
            text="Enter the code from the\nTrade Republic app notification:",
            justify=tk.CENTER,
            font=("Segoe UI", 10),
        ).pack(pady=(0, 8))
        self._timer_var = tk.StringVar()
        ttk.Label(f, textvariable=self._timer_var, foreground="#888").pack(pady=(0, 10))
        self.code_entry = ttk.Entry(f, width=14, font=("Segoe UI", 16), justify=tk.CENTER)
        self.code_entry.pack(pady=(0, 16))
        self.code_entry.bind("<Return>", lambda _: self._submit())
        btn = ttk.Frame(f)
        btn.pack(fill=tk.X)
        ttk.Button(btn, text="Submit", command=self._submit).pack(side=tk.LEFT, expand=True, padx=4)
        ttk.Button(btn, text="Send SMS instead", command=self._sms).pack(side=tk.LEFT, expand=True, padx=4)
        ttk.Button(btn, text="Cancel", command=self._cancel).pack(side=tk.LEFT, expand=True, padx=4)

    def _center(self, parent: tk.Tk) -> None:
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _tick(self) -> None:
        r = self._countdown
        while r > 0 and self._active:
            self._timer_var.set(f"Expires in {r}s")
            time.sleep(1)
            r -= 1
        if self._active:
            self._timer_var.set("Code expired")

    def _submit(self) -> None:
        code = self.code_entry.get().strip()
        if not code:
            messagebox.showwarning("Required", "Please enter the code.", parent=self)
            return
        self._active = False
        self.result = code
        self.destroy()

    def _sms(self) -> None:
        self._active = False
        self.use_sms = True
        self.destroy()

    def _cancel(self) -> None:
        self._active = False
        self.destroy()


class _SMSDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent)
        self.title("SMS Code")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)
        self.result: str | None = None
        self._build()
        self._center(parent)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.code_entry.focus_set()
        self.wait_window()

    def _build(self) -> None:
        f = ttk.Frame(self, padding=24)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            f,
            text="An SMS was sent to your number.\nEnter the code from the SMS:",
            justify=tk.CENTER,
            font=("Segoe UI", 10),
        ).pack(pady=(0, 12))
        self.code_entry = ttk.Entry(f, width=14, font=("Segoe UI", 16), justify=tk.CENTER)
        self.code_entry.pack(pady=(0, 16))
        self.code_entry.bind("<Return>", lambda _: self._submit())
        btn = ttk.Frame(f)
        btn.pack(fill=tk.X)
        ttk.Button(btn, text="Submit", command=self._submit).pack(side=tk.LEFT, expand=True, padx=4)
        ttk.Button(btn, text="Cancel", command=self._cancel).pack(side=tk.LEFT, expand=True, padx=4)

    def _center(self, parent: tk.Tk) -> None:
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _submit(self) -> None:
        code = self.code_entry.get().strip()
        if not code:
            messagebox.showwarning("Required", "Please enter the code.", parent=self)
            return
        self.result = code
        self.destroy()

    def _cancel(self) -> None:
        self.destroy()


# ---------------------------------------------------------------------------
# Scrollable frame helper
# ---------------------------------------------------------------------------


class _ScrollFrame(ttk.Frame):
    """A frame with a vertical scrollbar."""

    def __init__(self, parent: ttk.Notebook, **kw) -> None:
        super().__init__(parent, **kw)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._canvas = tk.Canvas(self, highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=sb.set)
        self.inner = ttk.Frame(self._canvas, padding=14)
        self._win = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner)
        self._canvas.bind("<Configure>", self._on_canvas)
        self._canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _on_inner(self, _e) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas(self, e) -> None:
        self._canvas.itemconfig(self._win, width=e.width)

    def _on_wheel(self, e) -> None:
        self._canvas.yview_scroll(-1 * (e.delta // 120), "units")


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------


class PytrGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("pytr – Trade Republic")
        self.minsize(720, 680)

        self._tr: TradeRepublicApi | None = None
        self._pending_tr: TradeRepublicApi | None = None
        self._pending_countdown: int = 0
        self._pending_store: bool = False
        self._pending_phone: str = ""
        self._pending_pin: str = ""
        self._pending_callback = None

        self._stop_event = threading.Event()

        self._out_q: queue.Queue[str] = queue.Queue()
        self._redirect_output()
        self._build()
        self._load_credentials()
        self._center()
        self._poll_output()

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def _redirect_output(self) -> None:
        import sys

        writer = _QueueWriter(self._out_q)
        sys.stdout = writer  # type: ignore[assignment]
        sys.stderr = writer  # type: ignore[assignment]

    def _poll_output(self) -> None:
        try:
            while True:
                text = self._out_q.get_nowait()
                self._log.configure(state=tk.NORMAL)
                self._log.insert(tk.END, text)
                self._log.see(tk.END)
                self._log.configure(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.after(100, self._poll_output)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_creds()
        nb = ttk.Notebook(self)
        nb.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))
        self._notebook = nb
        self._build_tabs()
        self._build_log()

    def _build_creds(self) -> None:
        f = ttk.LabelFrame(self, text="Credentials", padding=8)
        f.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        for c in range(10):
            f.columnconfigure(c, weight=(1 if c in (1, 3) else 0))

        ttk.Label(f, text="Phone:").grid(row=0, column=0, sticky=tk.W, padx=(0, 4))
        self._phone_var = tk.StringVar()
        ttk.Entry(f, textvariable=self._phone_var, width=18).grid(row=0, column=1, sticky=tk.EW, padx=(0, 10))

        ttk.Label(f, text="PIN:").grid(row=0, column=2, sticky=tk.W, padx=(0, 4))
        self._pin_var = tk.StringVar()
        self._pin_entry = ttk.Entry(f, textvariable=self._pin_var, show="•", width=10)
        self._pin_entry.grid(row=0, column=3, sticky=tk.EW, padx=(0, 6))
        self._pin_entry.bind("<Return>", lambda _: self._start_login())

        self._show_pin = tk.BooleanVar()
        ttk.Checkbutton(f, text="Show", variable=self._show_pin, command=self._toggle_pin).grid(
            row=0, column=4, padx=(0, 8)
        )

        self._store_var = tk.BooleanVar()
        ttk.Checkbutton(f, text="Remember", variable=self._store_var).grid(row=0, column=5, padx=(0, 10))

        self._login_btn = ttk.Button(f, text="Login", command=self._start_login, width=9)
        self._login_btn.grid(row=0, column=6, padx=(0, 4))

        self._stop_btn = ttk.Button(f, text="Stop", command=self._stop_operation, width=7)
        self._stop_btn.grid(row=0, column=7, padx=(0, 10))

        self._status_var = tk.StringVar(value="Not logged in")
        self._status_lbl = ttk.Label(f, textvariable=self._status_var, foreground="#888", width=18)
        self._status_lbl.grid(row=0, column=8, sticky=tk.W, padx=(0, 8))

        self._progress = ttk.Progressbar(f, mode="indeterminate", length=90)
        self._progress.grid(row=0, column=9)

    def _build_log(self) -> None:
        f = ttk.LabelFrame(self, text="Output", padding=6)
        f.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        f.columnconfigure(0, weight=1)
        self._log = scrolledtext.ScrolledText(f, state=tk.DISABLED, height=10, font=("Consolas", 9), wrap=tk.WORD)
        self._log.grid(row=0, column=0, sticky="ew")
        ttk.Button(f, text="Clear", command=self._clear_log, width=7).grid(row=1, column=0, sticky=tk.E, pady=(4, 0))

    def _clear_log(self) -> None:
        self._log.configure(state=tk.NORMAL)
        self._log.delete("1.0", tk.END)
        self._log.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------

    def _build_tabs(self) -> None:
        nb = self._notebook
        nb.add(self._tab_portfolio(), text="Portfolio")
        nb.add(self._tab_details(), text="Details")
        nb.add(self._tab_dl_docs(), text="Download Docs")
        nb.add(self._tab_export_tx(), text="Export Transactions")
        nb.add(self._tab_alarms(), text="Price Alarms")
        nb.add(self._tab_savings(), text="Savings Plans")

    # --- Portfolio ---

    def _tab_portfolio(self) -> ttk.Frame:
        sf = _ScrollFrame(self._notebook)
        f = sf.inner
        f.columnconfigure(1, weight=1)
        r = 0

        ttk.Label(f, text="Output CSV (optional):").grid(row=r, column=0, sticky=tk.W, pady=4)
        self._pf_out = tk.StringVar()
        ttk.Entry(f, textvariable=self._pf_out).grid(row=r, column=1, sticky=tk.EW, padx=6)
        ttk.Button(f, text="…", width=3, command=lambda: self._save_file(self._pf_out, ".csv")).grid(row=r, column=2)
        r += 1

        ttk.Label(f, text="Sort by column:").grid(row=r, column=0, sticky=tk.W, pady=4)
        self._pf_sort_col = tk.StringVar(value="(none)")
        ttk.Combobox(
            f,
            textvariable=self._pf_sort_col,
            width=18,
            values=["(none)"] + [c.lower() for c in PORTFOLIO_COLUMNS],
            state="readonly",
        ).grid(row=r, column=1, sticky=tk.W, padx=6)
        r += 1

        self._pf_sort_asc = tk.BooleanVar()
        ttk.Checkbutton(f, text="Sort ascending", variable=self._pf_sort_asc).grid(row=r, column=1, sticky=tk.W, padx=6)
        r += 1
        self._pf_watchlist = tk.BooleanVar()
        ttk.Checkbutton(f, text="Include watchlist", variable=self._pf_watchlist).grid(
            row=r, column=1, sticky=tk.W, padx=6
        )
        r += 1

        ttk.Label(f, text="Language:").grid(row=r, column=0, sticky=tk.W, pady=4)
        self._pf_lang = tk.StringVar(value="auto")
        ttk.Combobox(
            f, textvariable=self._pf_lang, width=10, values=["auto", *sorted(SUPPORTED_LANGUAGES)], state="readonly"
        ).grid(row=r, column=1, sticky=tk.W, padx=6)
        r += 1

        self._pf_decimal = tk.BooleanVar()
        ttk.Checkbutton(f, text="Localize decimals", variable=self._pf_decimal).grid(
            row=r, column=1, sticky=tk.W, padx=6
        )
        r += 1

        ttk.Button(f, text="▶  Run Portfolio", command=self._run_portfolio).grid(
            row=r, column=1, sticky=tk.W, padx=6, pady=(14, 0)
        )
        return sf

    # --- Details ---

    def _tab_details(self) -> ttk.Frame:
        f = ttk.Frame(self._notebook, padding=14)
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="ISIN or name:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self._det_query = tk.StringVar()
        e = ttk.Entry(f, textvariable=self._det_query, width=32)
        e.grid(row=0, column=1, sticky=tk.EW, padx=6)
        e.bind("<Return>", lambda _: self._run_details())

        ttk.Label(f, text="Asset type:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self._det_asset_type = tk.StringVar(value="stock")
        ttk.Combobox(f, textvariable=self._det_asset_type, values=_ASSET_TYPES, state="readonly", width=14).grid(
            row=1, column=1, sticky=tk.W, padx=6
        )

        ttk.Label(
            f, text="(Enter a 12-char ISIN to look up directly,\nor a name to search and select)", foreground="#888"
        ).grid(row=2, column=1, sticky=tk.W, padx=6, pady=(2, 0))

        ttk.Button(f, text="▶  Run Details", command=self._run_details).grid(
            row=3, column=1, sticky=tk.W, padx=6, pady=(14, 0)
        )
        return f

    # --- Download Docs ---

    def _tab_dl_docs(self) -> _ScrollFrame:
        sf = _ScrollFrame(self._notebook)
        f = sf.inner
        f.columnconfigure(1, weight=1)
        r = 0

        def row_entry(label, var, default=""):
            nonlocal r
            ttk.Label(f, text=label).grid(row=r, column=0, sticky=tk.W, pady=3)
            var.set(default)
            ttk.Entry(f, textvariable=var).grid(row=r, column=1, sticky=tk.EW, padx=6)
            r += 1

        def row_spin(label, var, default, from_, to):
            nonlocal r
            ttk.Label(f, text=label).grid(row=r, column=0, sticky=tk.W, pady=3)
            var.set(str(default))
            ttk.Spinbox(f, textvariable=var, from_=from_, to=to, width=8).grid(row=r, column=1, sticky=tk.W, padx=6)
            r += 1

        def row_check(label, var, default=False):
            nonlocal r
            var.set(default)
            ttk.Checkbutton(f, text=label, variable=var).grid(row=r, column=1, sticky=tk.W, padx=6)
            r += 1

        ttk.Label(f, text="Output directory:").grid(row=r, column=0, sticky=tk.W, pady=3)
        self._dl_out = tk.StringVar()
        ttk.Entry(f, textvariable=self._dl_out).grid(row=r, column=1, sticky=tk.EW, padx=6)
        ttk.Button(f, text="…", width=3, command=lambda: self._open_dir(self._dl_out)).grid(row=r, column=2)
        r += 1

        self._dl_format = tk.StringVar()
        row_entry("Filename format:", self._dl_format, "{iso_date} {time} {title}")
        self._dl_last_days = tk.StringVar()
        row_spin("Last N days (0=all, -1=skip):", self._dl_last_days, 0, -1, 9999)
        self._dl_days_until = tk.StringVar()
        row_spin("Days until (0=all):", self._dl_days_until, 0, 0, 9999)
        self._dl_workers = tk.StringVar()
        row_spin("Workers:", self._dl_workers, 8, 1, 32)

        ttk.Label(f, text="Export format:").grid(row=r, column=0, sticky=tk.W, pady=3)
        self._dl_export_fmt = tk.StringVar(value="csv")
        ttk.Combobox(f, textvariable=self._dl_export_fmt, values=["csv", "json"], state="readonly", width=8).grid(
            row=r, column=1, sticky=tk.W, padx=6
        )
        r += 1

        ttk.Label(f, text="Language:").grid(row=r, column=0, sticky=tk.W, pady=3)
        self._dl_lang = tk.StringVar(value="auto")
        ttk.Combobox(
            f, textvariable=self._dl_lang, values=["auto", *sorted(SUPPORTED_LANGUAGES)], state="readonly", width=10
        ).grid(row=r, column=1, sticky=tk.W, padx=6)
        r += 1

        self._dl_export_tx = tk.BooleanVar()
        row_check("Export transactions", self._dl_export_tx, True)
        self._dl_store_db = tk.BooleanVar()
        row_check("Store event database", self._dl_store_db, True)
        self._dl_scan_dup = tk.BooleanVar()
        row_check("Scan for duplicates", self._dl_scan_dup)
        self._dl_dump_raw = tk.BooleanVar()
        row_check("Dump raw data", self._dl_dump_raw)
        self._dl_universal = tk.BooleanVar()
        row_check("Universal file names", self._dl_universal)
        self._dl_flat = tk.BooleanVar()
        row_check("Flat (no subfolders)", self._dl_flat)
        self._dl_date_time = tk.BooleanVar()
        row_check("Date with time", self._dl_date_time, True)
        self._dl_decimal = tk.BooleanVar()
        row_check("Localize decimals", self._dl_decimal)
        self._dl_sort = tk.BooleanVar()
        row_check("Sort chronologically", self._dl_sort)

        ttk.Button(f, text="▶  Run Download Docs", command=self._run_dl_docs).grid(
            row=r, column=1, sticky=tk.W, padx=6, pady=(14, 0)
        )
        return sf

    # --- Export Transactions ---

    def _tab_export_tx(self) -> _ScrollFrame:
        sf = _ScrollFrame(self._notebook)
        f = sf.inner
        f.columnconfigure(1, weight=1)
        r = 0

        ttk.Label(f, text="Output directory:").grid(row=r, column=0, sticky=tk.W, pady=3)
        self._ex_dir = tk.StringVar(value=".")
        ttk.Entry(f, textvariable=self._ex_dir).grid(row=r, column=1, sticky=tk.EW, padx=6)
        ttk.Button(f, text="…", width=3, command=lambda: self._open_dir(self._ex_dir)).grid(row=r, column=2)
        r += 1

        ttk.Label(f, text="Output file (optional):").grid(row=r, column=0, sticky=tk.W, pady=3)
        self._ex_file = tk.StringVar()
        ttk.Entry(f, textvariable=self._ex_file).grid(row=r, column=1, sticky=tk.EW, padx=6)
        ttk.Button(f, text="…", width=3, command=lambda: self._save_file(self._ex_file, ".csv")).grid(row=r, column=2)
        r += 1

        ttk.Label(f, text="Last N days (0=all):").grid(row=r, column=0, sticky=tk.W, pady=3)
        self._ex_last_days = tk.StringVar(value="0")
        ttk.Spinbox(f, textvariable=self._ex_last_days, from_=-1, to=9999, width=8).grid(
            row=r, column=1, sticky=tk.W, padx=6
        )
        r += 1

        ttk.Label(f, text="Days until (0=all):").grid(row=r, column=0, sticky=tk.W, pady=3)
        self._ex_days_until = tk.StringVar(value="0")
        ttk.Spinbox(f, textvariable=self._ex_days_until, from_=0, to=9999, width=8).grid(
            row=r, column=1, sticky=tk.W, padx=6
        )
        r += 1

        ttk.Label(f, text="Export format:").grid(row=r, column=0, sticky=tk.W, pady=3)
        self._ex_fmt = tk.StringVar(value="csv")
        ttk.Combobox(f, textvariable=self._ex_fmt, values=["csv", "json"], state="readonly", width=8).grid(
            row=r, column=1, sticky=tk.W, padx=6
        )
        r += 1

        ttk.Label(f, text="Language:").grid(row=r, column=0, sticky=tk.W, pady=3)
        self._ex_lang = tk.StringVar(value="auto")
        ttk.Combobox(
            f, textvariable=self._ex_lang, values=["auto", *sorted(SUPPORTED_LANGUAGES)], state="readonly", width=10
        ).grid(row=r, column=1, sticky=tk.W, padx=6)
        r += 1

        self._ex_store_db = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Store event database", variable=self._ex_store_db).grid(
            row=r, column=1, sticky=tk.W, padx=6
        )
        r += 1
        self._ex_scan_dup = tk.BooleanVar()
        ttk.Checkbutton(f, text="Scan for duplicates", variable=self._ex_scan_dup).grid(
            row=r, column=1, sticky=tk.W, padx=6
        )
        r += 1
        self._ex_dump_raw = tk.BooleanVar()
        ttk.Checkbutton(f, text="Dump raw data", variable=self._ex_dump_raw).grid(row=r, column=1, sticky=tk.W, padx=6)
        r += 1
        self._ex_date_time = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Date with time", variable=self._ex_date_time).grid(
            row=r, column=1, sticky=tk.W, padx=6
        )
        r += 1
        self._ex_decimal = tk.BooleanVar()
        ttk.Checkbutton(f, text="Localize decimals", variable=self._ex_decimal).grid(
            row=r, column=1, sticky=tk.W, padx=6
        )
        r += 1
        self._ex_sort = tk.BooleanVar()
        ttk.Checkbutton(f, text="Sort chronologically", variable=self._ex_sort).grid(
            row=r, column=1, sticky=tk.W, padx=6
        )
        r += 1

        ttk.Button(f, text="▶  Run Export Transactions", command=self._run_export_tx).grid(
            row=r, column=1, sticky=tk.W, padx=6, pady=(14, 0)
        )
        return sf

    # --- Price Alarms ---

    def _tab_alarms(self) -> ttk.Frame:
        f = ttk.Frame(self._notebook, padding=14)
        f.columnconfigure(1, weight=1)

        get = ttk.LabelFrame(f, text="Get Price Alarms", padding=10)
        get.grid(row=0, column=0, columnspan=3, sticky=tk.EW, pady=(0, 12))
        get.columnconfigure(1, weight=1)

        ttk.Label(get, text="ISINs (space-sep, empty=all):").grid(row=0, column=0, sticky=tk.W, pady=3)
        self._ga_isins = tk.StringVar()
        ttk.Entry(get, textvariable=self._ga_isins).grid(row=0, column=1, sticky=tk.EW, padx=6)

        ttk.Label(get, text="Save to file (empty=log):").grid(row=1, column=0, sticky=tk.W, pady=3)
        self._ga_out = tk.StringVar()
        ttk.Entry(get, textvariable=self._ga_out).grid(row=1, column=1, sticky=tk.EW, padx=6)
        ttk.Button(get, text="…", width=3, command=lambda: self._save_file(self._ga_out, ".json")).grid(row=1, column=2)

        ttk.Button(get, text="▶  Get Price Alarms", command=self._run_get_alarms).grid(
            row=2, column=1, sticky=tk.W, padx=6, pady=(10, 0)
        )

        set_ = ttk.LabelFrame(f, text="Set Price Alarms", padding=10)
        set_.grid(row=1, column=0, columnspan=3, sticky=tk.EW)
        set_.columnconfigure(1, weight=1)

        ttk.Label(set_, text="Input (ISIN price1 price2…):").grid(row=0, column=0, sticky=tk.W, pady=3)
        self._sa_input = tk.StringVar()
        ttk.Entry(set_, textvariable=self._sa_input).grid(row=0, column=1, sticky=tk.EW, padx=6)

        ttk.Label(set_, text="Input file (optional):").grid(row=1, column=0, sticky=tk.W, pady=3)
        self._sa_infile = tk.StringVar()
        ttk.Entry(set_, textvariable=self._sa_infile).grid(row=1, column=1, sticky=tk.EW, padx=6)
        ttk.Button(set_, text="…", width=3, command=lambda: self._open_file(self._sa_infile)).grid(row=1, column=2)

        self._sa_remove = tk.BooleanVar(value=True)
        ttk.Checkbutton(set_, text="Remove current alarms first", variable=self._sa_remove).grid(
            row=2, column=1, sticky=tk.W, padx=6
        )

        ttk.Button(set_, text="▶  Set Price Alarms", command=self._run_set_alarms).grid(
            row=3, column=1, sticky=tk.W, padx=6, pady=(10, 0)
        )
        return f

    # --- Savings Plans ---

    def _tab_savings(self) -> ttk.Frame:
        f = ttk.Frame(self._notebook, padding=14)
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="Save to file (empty=log):").grid(row=0, column=0, sticky=tk.W, pady=4)
        self._sp_out = tk.StringVar()
        ttk.Entry(f, textvariable=self._sp_out).grid(row=0, column=1, sticky=tk.EW, padx=6)
        ttk.Button(f, text="…", width=3, command=lambda: self._save_file(self._sp_out, ".json")).grid(row=0, column=2)

        ttk.Label(f, text="Language:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self._sp_lang = tk.StringVar(value="auto")
        ttk.Combobox(
            f, textvariable=self._sp_lang, values=["auto", *sorted(SUPPORTED_LANGUAGES)], state="readonly", width=10
        ).grid(row=1, column=1, sticky=tk.W, padx=6)

        self._sp_decimal = tk.BooleanVar()
        ttk.Checkbutton(f, text="Localize decimals", variable=self._sp_decimal).grid(
            row=2, column=1, sticky=tk.W, padx=6
        )

        ttk.Button(f, text="▶  Run Savings Plans", command=self._run_savings).grid(
            row=3, column=1, sticky=tk.W, padx=6, pady=(14, 0)
        )
        return f

    # ------------------------------------------------------------------
    # File dialogs
    # ------------------------------------------------------------------

    def _open_dir(self, var: tk.StringVar) -> None:
        p = filedialog.askdirectory()
        if p:
            var.set(p)

    def _save_file(self, var: tk.StringVar, ext: str) -> None:
        p = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(ext.lstrip(".").upper() + " files", f"*{ext}"), ("All files", "*.*")],
        )
        if p:
            var.set(p)

    def _open_file(self, var: tk.StringVar) -> None:
        p = filedialog.askopenfilename(filetypes=[("All files", "*.*")])
        if p:
            var.set(p)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _center(self) -> None:
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _toggle_pin(self) -> None:
        self._pin_entry.config(show="" if self._show_pin.get() else "•")

    def _set_status(self, msg: str, color: str = "#666") -> None:
        self._status_var.set(msg)
        self._status_lbl.config(foreground=color)

    def _set_busy(self, busy: bool) -> None:
        if busy:
            self._login_btn.config(state=tk.DISABLED)
            self._progress.start(10)
        else:
            self._progress.stop()
            self._login_btn.config(state=tk.NORMAL)

    def _load_credentials(self) -> None:
        if not CREDENTIALS_FILE.is_file():
            return
        try:
            lines = CREDENTIALS_FILE.read_text().splitlines()
            if lines:
                self._phone_var.set(lines[0].strip())
            if len(lines) > 1:
                self._pin_var.set(lines[1].strip())
            self._store_var.set(True)
            self._set_status("Credentials loaded")
        except OSError:
            pass

    def _date_range(self, last: str, until: str) -> tuple[float, float]:
        ld = int(last)
        du = int(until)
        if ld < 0:
            nb = float(-1)
        elif ld == 0:
            nb = float(0)
        else:
            nb = (datetime.now().astimezone() - timedelta(days=ld)).timestamp()
        na = (datetime.now().astimezone() - timedelta(days=du)).timestamp() if du > 0 else float("inf")
        return nb, na

    # ------------------------------------------------------------------
    # Login flow
    # ------------------------------------------------------------------

    def _start_login(self) -> None:
        phone = self._phone_var.get().strip()
        pin = self._pin_var.get().strip()
        if not phone:
            messagebox.showwarning("Missing", "Please enter your phone number.")
            return
        if not pin:
            messagebox.showwarning("Missing", "Please enter your PIN.")
            return
        self._set_busy(True)
        self._set_status("Connecting…")
        threading.Thread(target=self._login_worker, args=(phone, pin, None), daemon=True).start()

    def _ensure_logged_in(self, callback) -> None:
        if self._tr is not None:
            callback(self._tr)
            return
        phone = self._phone_var.get().strip()
        pin = self._pin_var.get().strip()
        if not phone or not pin:
            messagebox.showwarning("Not logged in", "Fill in phone number and PIN, then log in first.")
            return
        self._set_busy(True)
        self._set_status("Logging in…")
        threading.Thread(target=self._login_worker, args=(phone, pin, callback), daemon=True).start()

    def _login_worker(self, phone: str, pin: str, callback) -> None:
        log = get_logger(__name__)
        try:
            BASE_DIR.mkdir(parents=True, exist_ok=True)
            store = self._store_var.get()
            tr = TradeRepublicApi(phone_no=phone, pin=pin, save_cookies=store, waf_token="playwright")

            if tr.resume_websession():
                self.after(0, self._on_login_success, tr, callback)
                return

            countdown = tr.initiate_weblogin()
            self._pending_tr = tr
            self._pending_countdown = countdown
            self._pending_store = store
            self._pending_phone = phone
            self._pending_pin = pin
            self._pending_callback = callback
            self.after(0, self._show_otp)
        except Exception as exc:
            log.debug("Login error", exc_info=True)
            self.after(0, self._on_error, str(exc))

    def _show_otp(self) -> None:
        self._set_busy(False)
        dlg = _OTPDialog(self, self._pending_countdown)
        if dlg.use_sms:
            self._set_busy(True)
            self._set_status("Requesting SMS…")
            threading.Thread(target=self._resend_worker, daemon=True).start()
        elif dlg.result:
            self._set_busy(True)
            self._set_status("Verifying…")
            threading.Thread(target=self._complete_worker, args=(dlg.result,), daemon=True).start()
        else:
            self._set_status("Cancelled.")

    def _resend_worker(self) -> None:
        try:
            assert self._pending_tr is not None
            self._pending_tr.resend_weblogin()
            self.after(0, self._show_sms)
        except Exception as exc:
            self.after(0, self._on_error, str(exc))

    def _show_sms(self) -> None:
        self._set_busy(False)
        dlg = _SMSDialog(self)
        if dlg.result:
            self._set_busy(True)
            self._set_status("Verifying SMS…")
            threading.Thread(target=self._complete_worker, args=(dlg.result,), daemon=True).start()
        else:
            self._set_status("Cancelled.")

    def _complete_worker(self, code: str) -> None:
        try:
            assert self._pending_tr is not None
            self._pending_tr.complete_weblogin(code)
            if self._pending_store:
                CREDENTIALS_FILE.write_text(f"{self._pending_phone}\n{self._pending_pin}\n")
            self.after(0, self._on_login_success, self._pending_tr, self._pending_callback)
        except Exception as exc:
            self.after(0, self._on_error, str(exc))

    def _on_login_success(self, tr: TradeRepublicApi, callback) -> None:
        self._tr = tr
        self._set_busy(False)
        self._set_status("Logged in ✓", "#2a7a2a")
        if callback is not None:
            callback(tr)

    def _stop_operation(self) -> None:
        self._stop_event.set()
        self._set_status("Stopping…", "#888888")

    def _on_error(self, msg: str) -> None:
        self._set_busy(False)
        if msg == _STOPPED:
            self._set_status("Stopped.", "#888888")
            return
        self._set_status("Error", "#cc0000")
        messagebox.showerror("Error", msg)

    def _open_pdf(self, path: str) -> None:
        os.startfile(path)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Command runners
    # ------------------------------------------------------------------

    def _run_portfolio(self) -> None:
        self._ensure_logged_in(self._do_portfolio)

    def _do_portfolio(self, tr: TradeRepublicApi) -> None:
        col = self._pf_sort_col.get()
        out = Path(self._pf_out.get()) if self._pf_out.get() else None
        self._set_busy(True)
        self._set_status("Running…")

        def w():
            try:
                Portfolio(
                    tr,
                    self._pf_watchlist.get(),
                    lang=self._pf_lang.get(),
                    decimal_localization=self._pf_decimal.get(),
                    output=out,
                    sort_by_column=None if col == "(none)" else col,
                    sort_descending=not self._pf_sort_asc.get(),
                ).get()
                self.after(0, self._set_status, "Done ✓", "#2a7a2a")
            except Exception as exc:
                self.after(0, self._on_error, str(exc))
            finally:
                self.after(0, self._set_busy, False)

        threading.Thread(target=w, daemon=True).start()

    def _run_details(self) -> None:
        query = self._det_query.get().strip()
        if not query:
            messagebox.showwarning("Required", "Please enter an ISIN or a name.")
            return
        if _ISIN_RE.match(query):
            self._ensure_logged_in(lambda tr: self._do_details(tr, query.upper()))
        else:
            self._ensure_logged_in(lambda tr: self._do_search_then_details(tr, query))

    def _do_search_then_details(self, tr: TradeRepublicApi, query: str) -> None:
        self._stop_event.clear()
        self._set_busy(True)
        self._set_status("Searching…")
        asset_type = self._det_asset_type.get()
        stop = self._stop_event

        def w():
            try:
                results = asyncio.run(_search_async(tr, query, asset_type, stop))
                if not results:
                    self.after(0, messagebox.showinfo, "No results", f"No instruments found for '{query}'.")
                    self.after(0, self._set_busy, False)
                    self.after(0, self._set_status, "No results.")
                    return
                self.after(0, self._show_search_results, tr, results)
            except Exception as exc:
                self.after(0, self._on_error, str(exc))
            finally:
                self.after(0, self._set_busy, False)

        threading.Thread(target=w, daemon=True).start()

    def _show_search_results(self, tr: TradeRepublicApi, results: list) -> None:
        dlg = _SearchDialog(self, results)
        if dlg.result is None:
            self._set_status("Cancelled.")
            return
        isin = dlg.result.get("isin") or dlg.result.get("instrumentId", "")
        name = dlg.result.get("shortName") or dlg.result.get("name", isin)
        print(f"Selected: {name} ({isin})\n")
        self._do_details(tr, isin)

    def _do_details(self, tr: TradeRepublicApi, isin: str) -> None:
        self._stop_event.clear()
        self._set_busy(True)
        self._set_status("Fetching details…")
        stop = self._stop_event

        def w():
            try:
                d = _GUIDetails(tr, isin)
                asyncio.run(d.details_loop(stop))
                if stop.is_set():
                    self.after(0, self._on_error, _STOPPED)
                    return
                _print_details(d)
                pdf_path = _generate_pdf(d)
                self.after(0, self._set_status, "Done ✓  –  opening PDF…", "#2a7a2a")
                self.after(0, self._open_pdf, str(pdf_path))
            except Exception as exc:
                self.after(0, self._on_error, str(exc))
            finally:
                self.after(0, self._set_busy, False)

        threading.Thread(target=w, daemon=True).start()

    def _run_dl_docs(self) -> None:
        out = self._dl_out.get().strip()
        if not out:
            messagebox.showwarning("Required", "Please select an output directory.")
            return
        self._ensure_logged_in(lambda tr: self._do_dl_docs(tr, Path(out)))

    def _do_dl_docs(self, tr: TradeRepublicApi, out: Path) -> None:
        self._set_busy(True)
        self._set_status("Downloading…")
        nb, na = self._date_range(self._dl_last_days.get(), self._dl_days_until.get())

        def w():
            try:
                DL(
                    tr,
                    out,
                    self._dl_format.get(),
                    nb,
                    na,
                    self._dl_store_db.get(),
                    self._dl_scan_dup.get(),
                    self._dl_dump_raw.get(),
                    self._dl_export_tx.get(),
                    max_workers=int(self._dl_workers.get()),
                    universal_filepath=self._dl_universal.get(),
                    lang=self._dl_lang.get(),
                    date_with_time=self._dl_date_time.get(),
                    decimal_localization=self._dl_decimal.get(),
                    sort_export=self._dl_sort.get(),
                    format_export=self._dl_export_fmt.get(),
                    flat=self._dl_flat.get(),
                ).do_dl()
                self.after(0, self._set_status, "Done ✓", "#2a7a2a")
            except Exception as exc:
                self.after(0, self._on_error, str(exc))
            finally:
                self.after(0, self._set_busy, False)

        threading.Thread(target=w, daemon=True).start()

    def _run_export_tx(self) -> None:
        outdir = Path(self._ex_dir.get() or ".")
        self._ensure_logged_in(lambda tr: self._do_export_tx(tr, outdir))

    def _do_export_tx(self, tr: TradeRepublicApi, outdir: Path) -> None:
        self._set_busy(True)
        self._set_status("Exporting…")
        nb, na = self._date_range(self._ex_last_days.get(), self._ex_days_until.get())
        fmt = self._ex_fmt.get()
        out_file_str = self._ex_file.get().strip()

        def w():
            try:
                tl = Timeline(
                    tr, outdir, nb, na, self._ex_store_db.get(), self._ex_scan_dup.get(), self._ex_dump_raw.get()
                )
                asyncio.run(tl.tl_loop())
                path = Path(out_file_str) if out_file_str else outdir / f"account_transactions.{fmt}"
                with path.open("w", encoding="utf-8") as fh:
                    TransactionExporter(
                        lang=self._ex_lang.get(),
                        date_with_time=self._ex_date_time.get(),
                        decimal_localization=self._ex_decimal.get(),
                    ).export(fh, [Event.from_dict(i) for i in tl.events], sort=self._ex_sort.get(), format=fmt)
                self.after(0, self._set_status, "Done ✓", "#2a7a2a")
            except Exception as exc:
                self.after(0, self._on_error, str(exc))
            finally:
                self.after(0, self._set_busy, False)

        threading.Thread(target=w, daemon=True).start()

    def _run_get_alarms(self) -> None:
        self._ensure_logged_in(self._do_get_alarms)

    def _do_get_alarms(self, tr: TradeRepublicApi) -> None:
        self._set_busy(True)
        self._set_status("Getting alarms…")
        isins = self._ga_isins.get().split()
        out_path = self._ga_out.get().strip()

        def w():
            import sys

            try:
                fh = open(out_path, "w", encoding="utf-8") if out_path else sys.stdout
                try:
                    Alarms(tr, isins, fh).get()
                finally:
                    if out_path:
                        fh.close()
                self.after(0, self._set_status, "Done ✓", "#2a7a2a")
            except Exception as exc:
                self.after(0, self._on_error, str(exc))
            finally:
                self.after(0, self._set_busy, False)

        threading.Thread(target=w, daemon=True).start()

    def _run_set_alarms(self) -> None:
        self._ensure_logged_in(self._do_set_alarms)

    def _do_set_alarms(self, tr: TradeRepublicApi) -> None:
        self._set_busy(True)
        self._set_status("Setting alarms…")
        inp = self._sa_input.get().split()
        in_path = self._sa_infile.get().strip()

        def w():
            import sys

            try:
                fh = open(in_path, "r", encoding="utf-8") if in_path else sys.stdin
                try:
                    Alarms(tr, inp, fh, self._sa_remove.get()).set()
                finally:
                    if in_path:
                        fh.close()
                self.after(0, self._set_status, "Done ✓", "#2a7a2a")
            except Exception as exc:
                self.after(0, self._on_error, str(exc))
            finally:
                self.after(0, self._set_busy, False)

        threading.Thread(target=w, daemon=True).start()

    def _run_savings(self) -> None:
        self._ensure_logged_in(self._do_savings)

    def _do_savings(self, tr: TradeRepublicApi) -> None:
        self._set_busy(True)
        self._set_status("Getting savings plans…")
        out_path = self._sp_out.get().strip()

        def w():
            import sys

            try:
                fh = open(out_path, "w", encoding="utf-8") if out_path else sys.stdout
                try:
                    SavingsPlans(tr, fh, decimal_localization=self._sp_decimal.get(), lang=self._sp_lang.get()).get()
                finally:
                    if out_path:
                        fh.close()
                self.after(0, self._set_status, "Done ✓", "#2a7a2a")
            except Exception as exc:
                self.after(0, self._on_error, str(exc))
            finally:
                self.after(0, self._set_busy, False)

        threading.Thread(target=w, daemon=True).start()


def main() -> None:
    app = PytrGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
