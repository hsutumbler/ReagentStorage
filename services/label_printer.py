# services/label_printer.py — ZPL 標籤列印（Zebra GX420t / ZT410 / ZD421）

import platform
import subprocess
from config import (
    ZEBRA_PRINTER_NAME, ZEBRA_DPI, cm_to_dots,
    LABEL_LARGE_W_CM, LABEL_LARGE_H_CM,
    LABEL_SMALL_W_CM, LABEL_SMALL_H_CM,
)


# ── 依 DPI 預算各尺寸（dots） ──────────────────────────────
_LW = cm_to_dots(LABEL_LARGE_W_CM)   # 5cm
_LH = cm_to_dots(LABEL_LARGE_H_CM)   # 3.5cm
_SW = cm_to_dots(LABEL_SMALL_W_CM)   # 5cm
_SH = cm_to_dots(LABEL_SMALL_H_CM)   # 3.5cm
_SCALE = ZEBRA_DPI / 203

def _f(base: int) -> int:
    return round(base * _SCALE)


# ── 核心列印函式 ─────────────────────────────────────────

def _send_zpl(zpl: str) -> None:
    system = platform.system()
    if system == "Windows":
        _send_windows(zpl)
    else:
        _send_lp(zpl)

def _send_windows(zpl: str) -> None:
    import win32print
    name = ZEBRA_PRINTER_NAME or win32print.GetDefaultPrinter()
    handle = win32print.OpenPrinter(name)
    try:
        win32print.StartDocPrinter(handle, 1, ("ZPL Label", None, "RAW"))
        win32print.StartPagePrinter(handle)
        win32print.WritePrinter(handle, zpl.encode("utf-8"))
        win32print.EndPagePrinter(handle)
        win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)

def _send_lp(zpl: str) -> None:
    args = ["lp", "-o", "raw", "-"]
    if ZEBRA_PRINTER_NAME:
        args = ["lp", "-d", ZEBRA_PRINTER_NAME, "-o", "raw", "-"]
    proc = subprocess.run(args, input=zpl.encode("utf-8"), capture_output=True)
    if proc.returncode != 0:
        raise OSError(f"Print failed: {proc.stderr.decode()}")


# ── 入庫 — 一般標籤（5cm × 3.5cm） ──────────────────────────

def print_receive_label_large(
    rid: str,
    reagent_name: str,
    lot_number: str,
    expiry_date: str,
    received_date: str,
    copies: int = 1,
    is_new_lot: bool = False,
) -> None:
    margin = _f(20)
    name_short = reagent_name[:20]
    lot_short  = lot_number[:24]

    border_zpl = f"^FO0,0^GB{_LW},{_LH},{_f(6)},B,0^FS" if is_new_lot else ""
    new_lot_text = f"^FO{_LW - _f(90)},{_f(70)}^CF0,{_f(28)}^FD[NEW]^FS" if is_new_lot else ""

    zpl = f"""^XA
^PW{_LW}
^LL{_LH}
^CI28
{border_zpl}

^FO{_f(22)},{_f(10)}
^BY2,2.0,{_f(65)}
^BCN,{_f(65)},N,N,N
^FD{rid}^FS

^FO{margin},{_f(75)}
^CF0,{_f(22)}
^FD{rid}^FS
{new_lot_text}

^FO{margin},{_f(115)}
^CF0,{_f(28)}
^FDReagent: {name_short}^FS

^FO{margin},{_f(155)}
^CF0,{_f(24)}
^FDLot: {lot_short}^FS

^FO{margin},{_f(195)}
^CF0,{_f(24)}
^FDExp: {expiry_date}^FS

^FO{margin},{_f(235)}
^CF0,{_f(24)}
^FDRecv: {received_date}^FS

^PQ{copies},0,1,Y
^XZ"""
    _send_zpl(zpl)


# ── 入庫 — QR Code 2-in-1 輔助函式 ────────────────────────

def _get_qr_block_zpl(x_offset: int, rid: str, name: str, lot: str, exp: str, recv: str, is_new: bool) -> str:
    name_short = f"{name[:8]}[NEW]" if is_new else name[:14]
    recv_fmt = recv.replace('-', '/')
    
    # 依 Blueprint：黑點實體起於 4mm (32 dots)
    # Magnification=3，白邊=12 dots。所以 qr_xy = 32 - 12 = 20 dots
    qr_x = x_offset + _f(20)
    qr_y = _f(20)
    
    # 微調向右平移 8 dots (1mm)，達成絕對水平置中
    qr_x = x_offset + _f(34)
    qr_y = _f(16)
    
    # 遮罩方塊同步平移
    box_size = _f(32)
    box_x = x_offset + _f(92)
    box_y = _f(74)
    
    qr_data = f"{rid}|{name}|{lot}|{exp}|{recv}"
    border = f"^FO{x_offset},0^GB{_f(200)},{_SH},{_f(4)},B,0^FS" if is_new else ""
    new_mark = ""
    
    return f"""
{border}
^FO{qr_x},{qr_y}^BQN,2,4^FDMA,{qr_data}^FS
^FO{box_x},{box_y}^GB{box_size},{box_size},{box_size},W,0^FS
^FO{box_x + _f(2)},{box_y + _f(4)}^CF0,{_f(20)}^FDIN^FS
{new_mark}
^FO{x_offset},{_f(170)}^CF0,{_f(28)}^FB{_f(200)},1,0,C^FD{name_short}^FS
^FO{x_offset},{_f(200)}^CF0,{_f(24)}^FB{_f(200)},1,0,C^FDLot:{lot[:12]}^FS
^FO{x_offset},{_f(230)}^CF0,{_f(24)}^FB{_f(200)},1,0,C^FDRecv:{recv_fmt}^FS
"""


def print_receive_label_qr(
    rid: str,
    reagent_name: str,
    lot_number: str,
    expiry_date: str,
    received_date: str,
    copies: int = 1,
    is_new_lot: bool = False,
) -> None:
    """單次列印：在 5cm 標籤上印出單張 QR (位於左側)。"""
    block_l = _get_qr_block_zpl(0, rid, reagent_name, lot_number, expiry_date, received_date, is_new_lot)
    zpl = f"^XA^BY2,2,1^PW{_SW}^LL{_SH}^CI28^CW1,E:WTCHT.TTF{block_l}^FO{_f(199)},0^GB1,{_SH},1,B,0^FS^PQ{copies},0,1,Y^XZ"
    _send_zpl(zpl)


def print_receive_batch_qr(items: list) -> None:
    """批次列印：兩兩一組並排印出。"""
    for i in range(0, len(items), 2):
        item_l = items[i]
        block_l = _get_qr_block_zpl(0, **item_l)
        block_r = ""
        if i + 1 < len(items):
            item_r = items[i+1]
            block_r = _get_qr_block_zpl(_f(200), **item_r)
        zpl = f"^XA^BY2,2,1^PW{_SW}^LL{_SH}^CI28^CW1,E:WTCHT.TTF{block_l}{block_r}^FO{_f(199)},0^GB1,{_SH},1,B,0^FS^PQ1,0,1,Y^XZ"
        _send_zpl(zpl)


# ── 出庫 — 一般標籤（5cm × 3.5cm） ──────────────────────────

def print_issue_label_large(
    rid: str,
    reagent_name: str,
    lot_number: str,
    open_expiry_date: str,
    issued_date: str,
    issued_by: str,
    copies: int = 1,
) -> None:
    margin = _f(20)
    name_short = reagent_name[:20]
    lot_short  = lot_number[:24]
    zpl = f"""^XA^PW{_LW}^LL{_LH}^CI28
^CW1,E:WTCHT.TTF
^FO{margin},{_f(20)}^A1N,{_f(28)},{_f(28)}^FDReagent: {name_short}^FS
^FO{margin},{_f(65)}^CF0,{_f(24)}^FDRID: {rid}^FS
^FO{margin},{_f(105)}^CF0,{_f(24)}^FDLot: {lot_short}^FS
^FO{margin},{_f(145)}^CF0,{_f(24)}^FDOpen Exp: {open_expiry_date}^FS
^FO{margin},{_f(185)}^CF0,{_f(24)}^FDIssued: {issued_date}^FS
^FO{margin},{_f(225)}^A1N,{_f(24)},{_f(24)}^FDIssued By: {issued_by}^FS
^PQ{copies},0,1,Y^XZ"""
    _send_zpl(zpl)


# ── 出庫 — QR Code 2-in-1 輔助函式 ────────────────────────

def _get_issue_block_zpl(x: int, rid: str, name: str, lot: str, exp: str, recv: str, by: str) -> str:
    name_short = name[:14]
    
    # 依 Blueprint：實體黑邊左距 4mm(32 dots)、上距 4mm(32 dots)
    qr_x = x + _f(34)
    qr_y = _f(16)
    
    box_size = _f(32)
    box_x = x + _f(92)
    box_y = _f(74)
    
    recv_fmt = recv[:10].replace('-', '/')
    exp_fmt = exp[:10].replace('-', '/')
    
    qr_data = f"OUT|{rid}|{name}|{lot}|{exp}|{recv}"
    return f"""
^FO{qr_x},{qr_y}^BQN,2,4^FDMA,{qr_data}^FS
^FO{box_x},{box_y}^GB{box_size},{box_size},{box_size},W,0^FS
^FO{box_x + _f(2)},{box_y + _f(4)}^CF0,{_f(18)}^FDOUT^FS
^FO{x},{_f(160)}^CF0,{_f(28)}^FB{_f(200)},1,0,C^FD{name_short}^FS
^FO{x},{_f(188)}^CF0,{_f(24)}^FB{_f(200)},1,0,C^FD{recv_fmt}^FS
^FO{x},{_f(216)}^CF0,{_f(24)}^FB{_f(200)},1,0,C^FD{exp_fmt}^FS
^FO{x},{_f(244)}^CF0,{_f(24)}^FB{_f(200)},1,0,C^FD{by}^FS
"""

def print_issue_label_qr(
    rid: str,
    reagent_name: str,
    lot_number: str,
    open_expiry_date: str,
    issued_date: str,
    issued_by: str,
    copies: int = 1,
) -> None:
    """單次列印：在左側印一張。"""
    block_l = _get_issue_block_zpl(0, rid, reagent_name, lot_number, open_expiry_date, issued_date, issued_by)
    zpl = f"^XA^BY2,2,1^PW{_SW}^LL{_SH}^CI28{block_l}^FO{_f(199)},0^GB1,{_SH},1,B,0^FS^PQ{copies},0,1,Y^XZ"
    _send_zpl(zpl)

def print_issue_batch_qr(items: list) -> None:
    """出庫批次列印。"""
    for i in range(0, len(items), 2):
        block_l = _get_issue_block_zpl(0, **items[i])
        block_r = ""
        if i + 1 < len(items):
            block_r = _get_issue_block_zpl(_f(200), **items[i+1])
        zpl = f"^XA^BY2,2,1^PW{_SW}^LL{_SH}^CI28{block_l}{block_r}^FO{_f(199)},0^GB1,{_SH},1,B,0^FS^PQ1,0,1,Y^XZ"
        _send_zpl(zpl)

def print_po_label(po_code: str, vendor_name: str) -> None:
    """列印訂購單標籤（含條碼），方便入庫時掃描。"""
    margin = _f(20)
    zpl = f"""^XA
^PW{_LW}
^LL{_LH}
^CI28

^FO{margin},{_f(40)}
^CF0,{_f(30)}
^FDPurchase Order^FS

^FO{margin},{_f(90)}
^BCN,{_f(80)},Y,N,N
^FD{po_code}^FS

^FO{margin},{_f(210)}
^CF0,{_f(24)}
^FDVendor: {vendor_name}^FS

^PQ1,0,1,Y
^XZ"""
    _send_zpl(zpl)
