"""
台灣電子發票（B2B / B2C）對接介面 — Mock implementation。

目的：
1. 提供「**正確結構**」可直接接到客戶的電子發票加值中心（如：關貿、財政部 MIG 3.2.1）
2. 內建驗證（統一編號、發票號碼格式、稅額計算）
3. 提供 mock submit（測試用，正式環境換成 HTTP call to 加值中心）

設計：以「Adapter Pattern」抽象 — 可換 provider 而不影響呼叫端。

對應公文：
- 財政部 MIG 3.2.1（電子發票交換訊息建置指引）
- 統一發票使用辦法第 7 條（電子發票格式）
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List
import uuid


# ─── 驗證工具 ──────────────────────────────────────────────

# 台灣統一編號：8 碼數字，最後一位是檢查碼
_TAX_ID_PATTERN = re.compile(r"^\d{8}$")
# 邏輯乘數（用於統編檢查碼演算法）
_TAX_ID_WEIGHTS = [1, 2, 1, 2, 1, 2, 4, 1]


def validate_tax_id(tax_id: str) -> bool:
    """驗證台灣公司統一編號（8 碼 + 檢查碼）。

    額外排除：全 0 / 全相同數字（演算法會誤通過，實際為無效）。
    """
    if not tax_id or not _TAX_ID_PATTERN.match(tax_id):
        return False
    # 排除全相同數字（如 00000000、11111111）
    if len(set(tax_id)) == 1:
        return False

    total = 0
    for i, digit in enumerate(tax_id):
        product = int(digit) * _TAX_ID_WEIGHTS[i]
        total += sum(int(d) for d in str(product))

    # 容錯規則：第 7 碼為 7 時，可接受 total % 10 == 0 或 (total + 1) % 10 == 0
    if tax_id[6] == "7":
        return total % 10 == 0 or (total + 1) % 10 == 0
    return total % 10 == 0


# 發票字軌：兩個英文字母 + 8 碼數字（例如 AB-12345678）
_INVOICE_NO_PATTERN = re.compile(r"^[A-Z]{2}\d{8}$")


def validate_invoice_no(invoice_no: str) -> bool:
    return bool(_INVOICE_NO_PATTERN.match(invoice_no.replace("-", "")))


def calc_tax(amount_excluding_tax: float, tax_rate: float = 0.05) -> tuple[float, float]:
    """回 (tax_amount, total_with_tax)。預設稅率 5%。"""
    tax = round(amount_excluding_tax * tax_rate)
    total = round(amount_excluding_tax + tax)
    return tax, total


# ─── 資料結構（依 MIG 3.2.1）────────────────────────────────

@dataclass
class InvoiceLineItem:
    description: str        # 品名
    qty: float
    unit: str = "個"
    unit_price: float = 0.0
    amount: float = 0.0     # 含稅金額
    tax_type: str = "1"     # 1=應稅, 2=零稅率, 3=免稅
    remark: str = ""


@dataclass
class EInvoice:
    """單張電子發票（B2B 或 B2C）。"""
    invoice_no: str              # 發票號碼 AB12345678
    invoice_date: str            # YYYYMMDD
    invoice_time: str            # HH:MM:SS
    seller_tax_id: str           # 賣方統編
    seller_name: str
    buyer_tax_id: str = ""       # 買方統編（B2C 可空）
    buyer_name: str = ""
    sales_amount: float = 0.0    # 銷售額（未稅）
    tax_amount: float = 0.0
    total_amount: float = 0.0
    tax_type: str = "1"          # 1=應稅, 2=零稅率, 3=免稅
    invoice_type: str = "07"     # 07=一般稅額計算, 08=三聯式
    carrier_type: str = ""       # 載具：3J0002=手機條碼, EJ0113=自然人憑證
    carrier_id: str = ""         # 載具號碼
    npo_id: str = ""             # 捐贈代碼（捐發票才填）
    line_items: List[InvoiceLineItem] = field(default_factory=list)
    random_number: str = field(default_factory=lambda: f"{uuid.uuid4().int % 10000:04d}")
    # 撤銷 / 折讓
    cancelled: bool = False
    cancel_reason: str = ""

    def validate(self) -> tuple[bool, list[str]]:
        """完整驗證；回 (is_valid, errors)。"""
        errors: list[str] = []
        if not validate_tax_id(self.seller_tax_id):
            errors.append(f"賣方統編無效：{self.seller_tax_id}")
        if self.buyer_tax_id and not validate_tax_id(self.buyer_tax_id):
            errors.append(f"買方統編無效：{self.buyer_tax_id}")
        if not validate_invoice_no(self.invoice_no.replace("-", "")):
            errors.append(f"發票號碼格式錯：{self.invoice_no}")
        # 稅額檢核
        expected_tax = round(self.sales_amount * 0.05)
        if abs(self.tax_amount - expected_tax) > 1:  # 允許 1 元誤差（湊整）
            errors.append(
                f"稅額計算錯：sales={self.sales_amount}, "
                f"tax_amount={self.tax_amount}, expected={expected_tax}"
            )
        # 總額檢核
        if abs(self.total_amount - (self.sales_amount + self.tax_amount)) > 1:
            errors.append(
                f"總額不符：sales+tax={self.sales_amount + self.tax_amount}, "
                f"total={self.total_amount}"
            )
        return (not errors, errors)

    def to_mig_dict(self) -> dict:
        """輸出符合 MIG 3.2.1 的 dict（給加值中心 / 財政部）。"""
        return {
            "InvoiceNumber": self.invoice_no.replace("-", ""),
            "InvoiceDate": self.invoice_date,
            "InvoiceTime": self.invoice_time,
            "Seller": {
                "Identifier": self.seller_tax_id,
                "Name": self.seller_name,
            },
            "Buyer": {
                "Identifier": self.buyer_tax_id,
                "Name": self.buyer_name,
            },
            "SalesAmount": self.sales_amount,
            "TaxType": self.tax_type,
            "TaxAmount": self.tax_amount,
            "TotalAmount": self.total_amount,
            "InvoiceType": self.invoice_type,
            "RandomNumber": self.random_number,
            "Items": [asdict(it) for it in self.line_items],
            **(
                {"Carrier": {"Type": self.carrier_type, "Id": self.carrier_id}}
                if self.carrier_type else {}
            ),
            **({"NPOBAN": self.npo_id} if self.npo_id else {}),
            "Cancelled": self.cancelled,
        }


# ─── Provider 介面 ─────────────────────────────────────────

class EInvoiceProvider:
    """電子發票加值中心 adapter 基類。"""

    def submit(self, inv: EInvoice) -> dict:
        """送出發票。回 {"success": bool, "tracking_no": str, "errors": [...]}"""
        raise NotImplementedError

    def cancel(self, invoice_no: str, reason: str) -> dict:
        raise NotImplementedError

    def query(self, invoice_no: str) -> dict:
        raise NotImplementedError


class MockEInvoiceProvider(EInvoiceProvider):
    """Mock — 用於測試 + Demo 模式。
    生產環境換成 RealEInvoiceProvider（接 httpx 到加值中心）。
    """

    def __init__(self):
        self._submitted: dict[str, EInvoice] = {}

    def submit(self, inv: EInvoice) -> dict:
        ok, errors = inv.validate()
        if not ok:
            return {"success": False, "tracking_no": None, "errors": errors}
        self._submitted[inv.invoice_no] = inv
        return {
            "success": True,
            "tracking_no": f"MOCK-{uuid.uuid4().hex[:10].upper()}",
            "errors": [],
            "mig_payload": inv.to_mig_dict(),
        }

    def cancel(self, invoice_no: str, reason: str) -> dict:
        inv = self._submitted.get(invoice_no)
        if not inv:
            return {"success": False, "errors": ["發票不存在"]}
        inv.cancelled = True
        inv.cancel_reason = reason
        return {"success": True, "errors": []}

    def query(self, invoice_no: str) -> dict:
        inv = self._submitted.get(invoice_no)
        if not inv:
            return {"success": False, "errors": ["發票不存在"]}
        return {"success": True, "invoice": inv.to_mig_dict()}


# 預設 provider（生產環境可換）
default_provider = MockEInvoiceProvider()
