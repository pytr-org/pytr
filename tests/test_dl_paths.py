"""Tests for dl_docs download target path computation.

Loads real fixtures from tests/events/, calls dl_callback(), and checks
the local_filepath assigned to each downloadable document.
No network or TR connection needed — DL is constructed without one.
"""

import json
import logging
from pathlib import Path

import pytest

from pytr.dl import DL

EVENTS_DIR = Path(__file__).parent / "events"
FMT = "{iso_date} {time} {title}"


def make_dl(tmp_path: Path) -> DL:
    dl = DL.__new__(DL)
    dl.tr = None
    dl.output_path = tmp_path
    dl.filename_fmt = FMT
    dl.flat = False
    dl.universal_filepath = True
    dl.dry_run = True
    dl.filepaths = []
    dl.doc_urls = []
    dl.futures = []
    dl.events_with_docs = []
    dl.events_without_docs = []
    dl.docs_request = 0
    dl.done = 0
    dl.events_processed = 0
    dl.session = None
    dl.log = logging.getLogger("test_dl_paths")
    return dl


def collect_paths(fixture_name: str, tmp_path: Path) -> list[str]:
    """Run dl_callback on a fixture; return relative posix paths of assigned documents."""
    dl = make_dl(tmp_path)
    with open(EVENTS_DIR / fixture_name, encoding="utf-8") as f:
        event = json.load(f)
    dl.dl_callback(event)
    result = []
    for section in event["details"]["sections"]:
        if section["type"] != "documents":
            continue
        for doc in section["data"]:
            if "local_filepath" in doc:
                result.append(Path(doc["local_filepath"]).relative_to(tmp_path).as_posix())
    return result


test_data: list[dict] = [
    # --- Trades: eventType-mapped ---
    {
        "filename": "buy.json",
        # ORDER_EXECUTED → Trades/; three distinct doc types
        # Note: universal_filepath=True replaces ":" with "_" in the time component
        "paths": [
            "Trades/2024-02-20 16_32 Abrechnung - Euro Stoxx 50 EUR (Dist) - Kauforder.pdf",
            "Trades/Basisinformationsblatt/2024-02-20 16_32 Basisinformationsblatt - Euro Stoxx 50 EUR (Dist) - Kauforder.pdf",
            "Trades/Kosteninformation/2024-02-20 16_32 Kosteninformation - Euro Stoxx 50 EUR (Dist) - Kauforder.pdf",
        ],
    },
    {
        "filename": "trade_invoice.json",
        # TRADE_INVOICE → Trades/
        "paths": [
            "Trades/2024-06-04 06_23 Abrechnung - DWS Group - Limit-Buy-Order.pdf",
            "Trades/Auftragsbestätigung/2024-06-04 06_23 Auftragsbestätigung - DWS Group - Limit-Buy-Order.pdf",
            "Trades/Kosteninformation/2024-06-04 06_23 Kosteninformation - DWS Group - Limit-Buy-Order.pdf",
        ],
    },
    {
        "filename": "buy_new.json",
        # trading_trade_executed (normalised → TRADING_TRADE_EXECUTED) → Trades/
        "paths": [
            "Trades/2025-10-10 19_29 Abrechnung - NVIDIA - Kauforder.pdf",
            "Trades/Kosteninformation/2025-10-10 19_29 Kosteninformation - NVIDIA - Kauforder.pdf",
        ],
    },
    {
        "filename": "limit-sell-order.json",
        # trading_trade_executed → Trades/
        "paths": [
            "Trades/Auftragsbestätigung/2025-05-20 08_03 Auftragsbestätigung - D-Wave Quantum - Limit-Sell-Order.pdf",
            "Trades/Kosteninformation/2025-05-20 08_03 Kosteninformation - D-Wave Quantum - Limit-Sell-Order.pdf",
            "Trades/2025-05-20 08_03 Abrechnung - D-Wave Quantum - Limit-Sell-Order.pdf",
        ],
    },
    {
        "filename": "bond_kauf.json",
        # TRADING_TRADE_EXECUTED; fixture has "Kosteninformation 1/2", "Abrechnung 1/2"
        # Number in title already differentiates → no dedup suffix
        "paths": [
            "Trades/Kosteninformation/2025-07-18 08_04 Kosteninformation 1 - Juli 2040 - Kauforder.pdf",
            "Trades/Kosteninformation/2025-07-18 08_04 Kosteninformation 2 - Juli 2040 - Kauforder.pdf",
            "Trades/2025-07-18 08_04 Abrechnung 1 - Juli 2040 - Kauforder.pdf",
            "Trades/2025-07-18 08_04 Abrechnung 2 - Juli 2040 - Kauforder.pdf",
        ],
    },
    {
        "filename": "verkaufsorder_abrechnung12.json",
        # TRADING_TRADE_EXECUTED; "Abrechnung 1/2", "Kosteninformation 1/2"
        # Number in title already differentiates → no dedup suffix; Abrechnung flat in Trades/
        "paths": [
            "Trades/2026-05-18 15_37 Abrechnung 1 - Zalando - Verkaufsorder.pdf",
            "Trades/2026-05-18 15_37 Abrechnung 2 - Zalando - Verkaufsorder.pdf",
            "Trades/Kosteninformation/2026-05-18 15_37 Kosteninformation 1 - Zalando - Verkaufsorder.pdf",
            "Trades/Kosteninformation/2026-05-18 15_37 Kosteninformation 2 - Zalando - Verkaufsorder.pdf",
        ],
    },
    {
        "filename": "trade_corrected.json",
        # TRADE_CORRECTED → Trades/; fixture docs named "Abrechnung 2" / "Abrechnung 1"
        # Number in title already differentiates → no dedup suffix
        "paths": [
            "Trades/2024-12-16 09_59 Abrechnung 2 - Worldline - Limit Verkauf-Order neu abgerechnet.pdf",
            "Trades/2024-12-16 09_59 Abrechnung 1 - Worldline - Limit Verkauf-Order neu abgerechnet.pdf",
            "Trades/Auftragsbestätigung/2024-12-16 09_59 Auftragsbestätigung - Worldline - Limit Verkauf-Order neu abgerechnet.pdf",
            "Trades/Kosteninformation/2024-12-16 09_59 Kosteninformation - Worldline - Limit Verkauf-Order neu abgerechnet.pdf",
        ],
    },
    {
        "filename": "savingsplan.json",
        # trading_savingsplan_executed → Sparplan/; Abrechnungsausführung → normalised to Abrechnung
        "paths": [
            "Sparplan/2025-10-23 08_26 Abrechnung - DroneShield - Sparplan ausgeführt.pdf",
        ],
    },
    {
        "filename": "trading_savingsplan_executed.json",
        # TRADING_SAVINGSPLAN_EXECUTED → Sparplan/
        "paths": [
            "Sparplan/2025-02-10 09_23 Abrechnung - BASF - Sparplan ausgeführt.pdf",
        ],
    },
    {
        "filename": "savings_plan_invoice_created.json",
        # SAVINGS_PLAN_INVOICE_CREATED → Sparplan/; Abrechnung Ausführung → normalised to Abrechnung
        "paths": [
            "Sparplan/2024-06-17 08_16 Abrechnung - Volkswagen (Vz.) - Sparplan ausgeführt.pdf",
        ],
    },
    {
        "filename": "ipo-spacex.json",
        # IPO_TRADE_EXECUTED → Trades/
        "paths": [
            "Trades/2026-06-06 04_20 Abrechnung - SpaceX - IPO.pdf",
            "Trades/Kosteninformation/2026-06-06 04_20 Kosteninformation - SpaceX - IPO.pdf",
            "Trades/Prospekt/2026-06-06 04_20 Prospekt - SpaceX - IPO.pdf",
        ],
    },
    # --- Trades: no-eventType / legacy subtitle fallback ---
    {
        "filename": "buy_no_eventType.json",
        # No eventType, subtitle=Kauforder → subtitle_subfolder_mapping → Trades/
        "paths": [
            "Trades/2024-02-20 16_32 Abrechnung - Euro Stoxx 50 EUR (Dist) - Kauforder.pdf",
            "Trades/Basisinformationsblatt/2024-02-20 16_32 Basisinformationsblatt - Euro Stoxx 50 EUR (Dist) - Kauforder.pdf",
            "Trades/Kosteninformation/2024-02-20 16_32 Kosteninformation - Euro Stoxx 50 EUR (Dist) - Kauforder.pdf",
        ],
    },
    {
        "filename": "legacy_verkauforder_neu_abgerechnet.json",
        # TIMELINE_LEGACY_MIGRATED_EVENTS, subtitle → Trades/
        # fixture docs named "Abrechnung 2" / "Abrechnung 1"; number differentiates → no dedup suffix
        "paths": [
            "Trades/2025-02-21 11_14 Abrechnung 2 - Marie Brizard Wine and Spirits - Limit Verkauf-Order neu abgerechnet.pdf",
            "Trades/2025-02-21 11_14 Abrechnung 1 - Marie Brizard Wine and Spirits - Limit Verkauf-Order neu abgerechnet.pdf",
            "Trades/Auftragsbestätigung/2025-02-21 11_14 Auftragsbestätigung - Marie Brizard Wine and Spirits - Limit Verkauf-Order neu abgerechnet.pdf",
            "Trades/Kosteninformation/2025-02-21 11_14 Kosteninformation - Marie Brizard Wine and Spirits - Limit Verkauf-Order neu abgerechnet.pdf",
        ],
    },
    # --- Dividends ---
    {
        "filename": "dividende_wahlweise2.json",
        # SSP_CORPORATE_ACTION_ACTIVITY → Misc, subtitle override → Dividende/; flat (like Dokumente)
        "paths": [
            "Dividende/2024-11-05 16_48 Dividende Wahlweise - Unilever - Dividende. Cash oder Stockdividende.pdf",
        ],
    },
    {
        "filename": "dividende_wahlweise3.json",
        # SSP_CORPORATE_ACTION_INSTRUCTION → Misc, subtitle override → Dividende/; flat (like Dokumente)
        "paths": [
            "Dividende/2026-07-29 13_38 Dividende Wahlweise - Rio Tinto - Dividende. Cash oder Stockdividende.pdf",
        ],
    },
    {
        "filename": "bardividende.json",
        # ssp_corporate_action_invoice_cash → Dividende/; doc type Dokumente → flat under subfolder
        "paths": [
            "Dividende/2025-10-23 14_19 Comcast (A) - Bardividende.pdf",
        ],
    },
    {
        "filename": "bardividende_no_eventType.json",
        # No eventType, subtitle=Bardividende → Dividende/
        "paths": [
            "Dividende/2025-11-05 18_31 Lowe's - Bardividende.pdf",
        ],
    },
    {
        "filename": "bardividende_korrigiert2.json",
        # SSP_CORPORATE_ACTION_CASH → Dividende/; doc title Dividendenbeleg → flat (like Dokumente)
        "paths": [
            "Dividende/2026-06-26 13_51 Dividendenbeleg - Medical Properties Trust - Bardividende korrigiert.pdf",
        ],
    },
    {
        "filename": "aktiendividende.json",
        # ssp_corporate_action_invoice_shares → Misc, but subtitle Aktiendividende overrides → Dividende/
        "paths": [
            "Dividende/2025-07-22 14_31 Enovix - Aktiendividende.pdf",
        ],
    },
    {
        "filename": "aktienpraemiendividende.json",
        # ssp_corporate_action_invoice_cash → Dividende/ (via subtitle_subfolder_mapping); doc: Dokumente → flat
        "paths": [
            "Dividende/2025-09-22 11_20 Glencore - Aktienprämiendividende.pdf",
        ],
    },
    {
        "filename": "aktienpraemiendividende2.json",
        # SSP_CORPORATE_ACTION_CASH_NON_DIVIDEND → Misc, subtitle Aktienprämiendividende overrides → Dividende/
        # Two Dokumente docs → second gets counter " 2" appended
        "paths": [
            "Dividende/2026-07-02 10_41 Hensoldt - Aktienprämiendividende.pdf",
            "Dividende/2026-07-02 10_41 Hensoldt - Aktienprämiendividende 2.pdf",
        ],
    },
    {
        "filename": "vorabpauschale.json",
        # ssp_corporate_action_invoice_cash → Dividende/; doc title Vorabpauschale (not Dokumente) → subdir
        "paths": [
            "Dividende/Vorabpauschale/2025-01-28 14_54 Vorabpauschale - MSCI China USD (Acc) - Vorabpauschale.pdf",
        ],
    },
    # --- Transfers / payments ---
    {
        "filename": "bank_transaction_incoming.json",
        # BANK_TRANSACTION_INCOMING → Einzahlungen/; flat (like Dokumente)
        "paths": [
            "Einzahlungen/2024-07-04 06_17 Transaktionsbestätigung - Max Mustermann - Fertig.pdf",
        ],
    },
    {
        "filename": "bank_transaction_outgoing.json",
        # BANK_TRANSACTION_OUTGOING → Auszahlungen/; flat (like Dokumente)
        "paths": [
            "Auszahlungen/2024-07-21 09_35 Transaktionsbestätigung - Max Mustermann - Gesendet.pdf",
        ],
    },
    {
        "filename": "incoming_transfer.json",
        # INCOMING_TRANSFER → Einzahlungen/; flat (like Dokumente)
        "paths": [
            "Einzahlungen/2024-09-02 17_49 Transaktionsbestätigung - Klaus Mustermann - Fertig.pdf",
        ],
    },
    {
        "filename": "outgoing_transfer.json",
        # OUTGOING_TRANSFER → Auszahlungen/; flat (like Dokumente)
        "paths": [
            "Auszahlungen/2024-07-21 09_35 Transaktionsbestätigung - Hans Mustermann - Gesendet.pdf",
        ],
    },
    # --- Interest ---
    {
        "filename": "interest_payout_created.json",
        # INTEREST_PAYOUT_CREATED → Zinsen/; flat
        "paths": [
            "Zinsen/2024-07-01 04_51 Abrechnung - Zinsen.pdf",
        ],
    },
    {
        "filename": "legacy_zinsen.json",
        # TIMELINE_LEGACY_MIGRATED_EVENTS, title=Zinsen → title_subfolder_mapping → Zinsen/; flat
        "paths": [
            "Zinsen/2024-09-01 16_39 Abrechnung - Zinsen.pdf",
        ],
    },
    {
        "filename": "legacy_zinsen_no_eventType.json",
        # no eventType, title=Zinsen → title_subfolder_mapping → Zinsen/; flat
        "paths": [
            "Zinsen/2024-09-01 16_39 Abrechnung - Zinsen.pdf",
        ],
    },
    # --- Steuerkorrektur ---
    {
        "filename": "steuerkorrektur.json",
        # ssp_tax_correction_invoice → Steuerkorrekturen/; Steuerabrechnung → flat (like Dokumente)
        "paths": [
            "Steuerkorrekturen/2025-10-28 00_00 Steuerkorrektur.pdf",
        ],
    },
    {
        "filename": "ssp_tax_correction.json",
        # SSP_TAX_CORRECTION → Steuerkorrekturen/
        "paths": [
            "Steuerkorrekturen/2024-06-11 22_45 Steuerkorrektur.pdf",
        ],
    },
    {
        "filename": "steuerkorrektur_no_eventType.json",
        # No eventType, title=Steuerkorrektur → title_subfolder_mapping → Steuerkorrekturen/
        "paths": [
            "Steuerkorrekturen/2025-11-04 23_31 Steuerkorrektur.pdf",
        ],
    },
    # --- Saveback / RoundUp ---
    {
        "filename": "saveback_aggregate.json",
        # SAVEBACK_AGGREGATE → Saveback/; Abrechnung Ausführung → normalised to Abrechnung
        "paths": [
            "Saveback/2024-07-02 13_53 Abrechnung - S&P 500 Information Tech USD (Acc) - Saveback.pdf",
            "Saveback/Kosteninformation/2024-07-02 13_53 Kosteninformation - S&P 500 Information Tech USD (Acc) - Saveback.pdf",
        ],
    },
    {
        "filename": "spare_change_aggregate.json",
        # SPARE_CHANGE_AGGREGATE → RoundUp/; Abrechnung Ausführung → normalised to Abrechnung
        "paths": [
            "RoundUp/2024-06-10 13_52 Abrechnung - S&P 500 Information Tech USD (Acc) - Round up.pdf",
            "RoundUp/Kosteninformation/2024-06-10 13_52 Kosteninformation - S&P 500 Information Tech USD (Acc) - Round up.pdf",
        ],
    },
    # --- Corporate actions ---
    {
        "filename": "aktienbonus.json",
        # ACQUISITION_TRADE_PERK → Misc/; title becomes subdir
        "paths": [
            "Misc/Aktien-Bonus/2025-10-13 14_49 Kosteninformation - Aktien-Bonus - Eingelöst.pdf",
            "Misc/Aktien-Bonus/2025-10-13 14_49 Rechnung - Aktien-Bonus - Eingelöst.pdf",
        ],
    },
    {
        "filename": "trade_perk.json",
        # ACQUISITION_TRADE_PERK → Misc/; title becomes subdir
        "paths": [
            "Misc/Aktien-Bonus/2025-04-01 14_09 Rechnung - Aktien-Bonus - Eingelöst.pdf",
            "Misc/Aktien-Bonus/2025-04-01 14_09 Kosteninformation - Aktien-Bonus - Eingelöst.pdf",
        ],
    },
    # --- Corporate actions ---
    {
        "filename": "aktiensplit.json",
        # ssp_corporate_action_invoice_shares → Misc/; Dokumente + Misc → subtitle becomes subdir
        "paths": [
            "Misc/Aktiensplit/2024-06-26 08_06 Chipotle Mexican Grill.pdf",
        ],
    },
    {
        "filename": "aktiensplit2.json",
        # SSP_CORPORATE_ACTION_NO_CASH → Misc/; Dokumente + Misc → subtitle becomes subdir
        "paths": [
            "Misc/Aktiensplit/2026-07-02 06_31 Crowdstrike Holdings (A).pdf",
        ],
    },
    {
        "filename": "spinoff.json",
        # ssp_corporate_action_invoice_shares → Misc/; Dokumente + Misc → subtitle becomes subdir
        "paths": [
            "Misc/Spin-off/2025-10-20 11_25 ThyssenKrupp.pdf",
        ],
    },
    {
        "filename": "private_markets_trade.json",
        # private_markets_trade_executed (normalised → PRIVATE_MARKETS_TRADE_EXECUTED) → Trades/
        "paths": [
            "Trades/Kosteninformation/2025-09-18 07_14 Kosteninformation - Private Equity - Kauforder.pdf",
            "Trades/2025-09-18 07_14 Abrechnung - Private Equity - Kauforder.pdf",
        ],
    },
    {
        "filename": "private_markets_vorabpauschale.json",
        # SSP_CORPORATE_ACTION_CASH_NON_DIVIDEND → Misc/; doc: Vorabpauschale (not Dokumente) → subdir
        "paths": [
            "Misc/Vorabpauschale/2026-03-09 07_56 Vorabpauschale - Private Equity - Vorabpauschale.pdf",
        ],
    },
]


@pytest.mark.parametrize("case", test_data, ids=[c["filename"] for c in test_data])
def test_dl_paths(case, tmp_path):
    assert collect_paths(case["filename"], tmp_path) == case["paths"]
