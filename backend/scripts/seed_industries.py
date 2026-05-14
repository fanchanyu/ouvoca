"""5 個典型行業的 seed 腳本，給 demo / 試用 / 業務 pitch 用。

行業:
  1. metal:   金屬加工（CNC 螺絲螺帽）
  2. plastic: 塑膠射出
  3. pcb:     PCB 電子組裝
  4. food:    食品加工烘焙
  5. textile: 紡織印染

使用方式:
  python -m scripts.seed_industries metal
  python -m scripts.seed_industries plastic
  python -m scripts.seed_industries pcb
  python -m scripts.seed_industries food
  python -m scripts.seed_industries textile

每個行業會建立：
  - 8-12 個典型零件（含中文 + 英文名）
  - 2-3 個成品 + BOM
  - 3-5 個業界供應商
  - 3-5 個典型客戶
  - 1-2 個工作中心
  - 1 個示範工單
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import AsyncSessionLocal, init_db
from app.models.inventory import Part, Inventory
from app.models.product import Product, BOMItem
from app.models.purchase import Supplier
from app.models.crm_sales import Customer
from app.models.production import WorkCenter


# ============================================================
# 行業資料定義
# ============================================================

INDUSTRIES = {
    "metal": {
        "name": "金屬加工",
        "name_en": "Metal Machining",
        "tagline": "CNC 螺絲螺帽製造",
        "parts": [
            # (part_no, name_zh, name_en, category, unit, min, max, safety, lead_time, unit_cost)
            ("M-SUS304-12", "SUS304 不鏽鋼板 12mm", "SUS304 SS Plate 12mm", "raw_material", "kg", 100, 2000, 500, 14, 80.0),
            ("M-S45C-20", "S45C 中碳鋼圓棒 20mm", "S45C Carbon Steel Rod 20mm", "raw_material", "kg", 50, 1500, 300, 21, 65.0),
            ("M-CUT-OIL-A", "切削油 A 型", "Cutting Oil Type A", "consumable", "l", 20, 200, 50, 7, 350.0),
            ("M-DRILL-D6", "Φ6 鑽頭", "Drill Bit Φ6mm", "consumable", "pcs", 50, 500, 100, 10, 120.0),
            ("M-INSERT-CNC", "CNC 刀片 (TPGN)", "CNC Insert (TPGN)", "consumable", "pcs", 100, 1000, 200, 14, 95.0),
            ("M-BOLT-M8-30", "M8x30 螺絲半成品", "M8x30 Bolt Blank", "semi_finished", "pcs", 500, 50000, 2000, 5, 1.8),
            ("M-NUT-M8", "M8 螺帽半成品", "M8 Nut Blank", "semi_finished", "pcs", 500, 50000, 2000, 5, 0.9),
            ("M-WASHER-M8", "M8 墊片", "M8 Washer", "component", "pcs", 1000, 100000, 5000, 7, 0.3),
            ("M-PACK-1KG", "1kg 透明袋裝", "1kg Clear Bag", "packaging", "pcs", 200, 5000, 500, 5, 4.5),
            ("M-PACK-CART-S", "小型出貨紙箱", "Small Carton", "packaging", "pcs", 100, 3000, 300, 7, 8.0),
        ],
        "products": [
            ("PRD-BOLT-M8-30", "M8x30 不鏽鋼螺絲套組（100顆）",
             "M8x30 SS Bolt Set (100pcs)", 380.0, 220.0,
             [("M-BOLT-M8-30", 100), ("M-NUT-M8", 100), ("M-WASHER-M8", 200),
              ("M-PACK-1KG", 1)]),
            ("PRD-CUSTOM-MACHINING", "客製化精密加工件",
             "Custom Precision Part", 5800.0, 2400.0,
             [("M-SUS304-12", 1.5), ("M-CUT-OIL-A", 0.05),
              ("M-INSERT-CNC", 0.2), ("M-PACK-CART-S", 1)]),
        ],
        "suppliers": [
            ("SUP-STEEL", "中鋼鋼鐵", "T1", 14, True),
            ("SUP-TOOLS", "三鼎刀具", "T1", 7, True),
            ("SUP-OIL", "潤滑油專業", "T2", 5, True),
            ("SUP-PACK", "瑞興包材", "T3", 3, True),
        ],
        "customers": [
            ("CUST-FORMOSA", "台塑機械", "A", 8_000_000),
            ("CUST-ASUS", "華碩電腦", "A", 12_000_000),
            ("CUST-LOCAL-1", "新北精密機械社", "B", 1_500_000),
            ("CUST-LOCAL-2", "永盛五金行", "C", 500_000),
        ],
        "work_centers": [
            ("WC-CNC-1", "CNC 加工中心 #1 (M-A8)", 140, 800),
            ("WC-CNC-2", "CNC 加工中心 #2 (Mori)", 140, 850),
            ("WC-LATHE", "車床站", 120, 600),
            ("WC-QC", "QC 三次元量測", 200, 1000),
        ],
    },

    "plastic": {
        "name": "塑膠射出",
        "name_en": "Plastic Injection",
        "tagline": "模具射出成型",
        "parts": [
            ("P-ABS-WHITE", "ABS 白色塑膠粒", "ABS White Pellets", "raw_material", "kg", 100, 5000, 500, 7, 85.0),
            ("P-PC-CLEAR", "PC 透明塑膠粒", "PC Clear Pellets", "raw_material", "kg", 50, 2000, 200, 10, 125.0),
            ("P-PP-NATURAL", "PP 原色塑膠粒", "PP Natural Pellets", "raw_material", "kg", 200, 8000, 800, 7, 55.0),
            ("P-DYE-RED", "紅色色母", "Red Master Batch", "raw_material", "kg", 5, 50, 10, 14, 280.0),
            ("P-DYE-BLUE", "藍色色母", "Blue Master Batch", "raw_material", "kg", 5, 50, 10, 14, 280.0),
            ("P-MOLD-CASE-A", "外殼模具 A 型", "Case Mold Type A", "component", "set", 1, 5, 2, 60, 380000.0),
            ("P-INSERT-METAL", "金屬嵌入件", "Metal Insert", "component", "pcs", 1000, 50000, 5000, 14, 6.5),
            ("P-PACK-PE-BAG", "PE 包裝袋", "PE Bag", "packaging", "pcs", 500, 10000, 1000, 5, 2.8),
            ("P-PACK-CART-M", "中型紙箱", "Medium Carton", "packaging", "pcs", 100, 2000, 200, 7, 12.0),
        ],
        "products": [
            ("PRD-CASE-CONSUMER", "消費電子外殼（白色）",
             "Consumer Electronics Casing (White)", 180.0, 95.0,
             [("P-ABS-WHITE", 0.05), ("P-INSERT-METAL", 4),
              ("P-PACK-PE-BAG", 1)]),
            ("PRD-BOTTLE-PP", "PP 透明瓶身 500ml",
             "PP Clear Bottle 500ml", 25.0, 12.0,
             [("P-PP-NATURAL", 0.025), ("P-DYE-BLUE", 0.0005),
              ("P-PACK-CART-M", 0.02)]),
        ],
        "suppliers": [
            ("SUP-PLASTIC", "台塑石化", "T1", 7, True),
            ("SUP-DYE", "色母大廠", "T1", 14, True),
            ("SUP-MOLD", "明峰模具", "T1", 60, True),
            ("SUP-PACK", "包裝印刷廠", "T3", 5, True),
        ],
        "customers": [
            ("CUST-SAMSUNG", "三星電子", "A", 15_000_000),
            ("CUST-XIAOMI", "小米台灣", "A", 8_000_000),
            ("CUST-BOTTLE-CO", "綠色飲品", "B", 2_000_000),
            ("CUST-TOY", "玩具王國", "C", 800_000),
        ],
        "work_centers": [
            ("WC-INJ-100T", "100 噸射出機 #1", 100, 600),
            ("WC-INJ-200T", "200 噸射出機 #1", 80, 800),
            ("WC-INJ-300T", "300 噸射出機 #1", 60, 1200),
            ("WC-ASSY", "組裝線", 200, 400),
        ],
    },

    "pcb": {
        "name": "PCB 電子組裝",
        "name_en": "PCB Assembly",
        "tagline": "SMT 焊接組裝",
        "parts": [
            ("PCB-BARE-4L", "4 層裸板 100x80mm", "Bare PCB 4-layer 100x80mm", "component", "pcs", 500, 20000, 2000, 21, 45.0),
            ("PCB-IC-MCU-A", "MCU 微控器 STM32G0", "MCU STM32G0", "component", "pcs", 200, 5000, 500, 60, 18.5),
            ("PCB-RES-10K", "電阻 10kΩ 0805", "Resistor 10kΩ 0805", "component", "pcs", 5000, 200000, 10000, 14, 0.05),
            ("PCB-CAP-100NF", "電容 100nF 0603", "Capacitor 100nF 0603", "component", "pcs", 5000, 200000, 10000, 14, 0.08),
            ("PCB-CONN-USB-C", "USB-C 連接器", "USB-C Connector", "component", "pcs", 200, 5000, 500, 30, 12.5),
            ("PCB-LED-BLUE", "藍色 LED 0603", "Blue LED 0603", "component", "pcs", 1000, 30000, 2000, 14, 0.6),
            ("PCB-SOLDER-PASTE", "錫膏 SAC305", "Solder Paste SAC305", "consumable", "kg", 5, 50, 10, 14, 4800.0),
            ("PCB-FLUX", "助焊劑", "Flux", "consumable", "l", 5, 50, 10, 14, 380.0),
            ("PCB-PACK-ESD", "防靜電袋", "ESD Bag", "packaging", "pcs", 500, 20000, 1000, 7, 3.5),
        ],
        "products": [
            ("PRD-IOT-MODULE", "IoT 通訊模組",
             "IoT Module", 1280.0, 580.0,
             [("PCB-BARE-4L", 1), ("PCB-IC-MCU-A", 1), ("PCB-RES-10K", 12),
              ("PCB-CAP-100NF", 18), ("PCB-CONN-USB-C", 1), ("PCB-LED-BLUE", 2),
              ("PCB-SOLDER-PASTE", 0.002), ("PCB-PACK-ESD", 1)]),
            ("PRD-CONTROL-BOARD", "工業控制板",
             "Industrial Controller", 3200.0, 1450.0,
             [("PCB-BARE-4L", 1), ("PCB-IC-MCU-A", 2), ("PCB-RES-10K", 30),
              ("PCB-CAP-100NF", 50), ("PCB-LED-BLUE", 4),
              ("PCB-SOLDER-PASTE", 0.005), ("PCB-PACK-ESD", 1)]),
        ],
        "suppliers": [
            ("SUP-PCB-FAB", "台灣 PCB 板廠", "T1", 21, True),
            ("SUP-IC-AGENT", "代理商 (Mouser TW)", "T1", 30, True),
            ("SUP-PASSIVE", "被動元件批發", "T2", 14, True),
            ("SUP-SOLDER", "焊錫材料", "T2", 14, True),
        ],
        "customers": [
            ("CUST-FOXCONN", "鴻海科技", "A", 20_000_000),
            ("CUST-DELTA", "台達電子", "A", 12_000_000),
            ("CUST-STARTUP", "新創 IoT 公司", "B", 1_500_000),
            ("CUST-MAKER", "創客社群採購", "C", 300_000),
        ],
        "work_centers": [
            ("WC-SMT-1", "SMT 貼片線 #1", 8000, 1500),
            ("WC-REFLOW", "迴流焊", 8000, 1000),
            ("WC-DIP", "DIP 插件線", 2000, 800),
            ("WC-TEST", "ICT 測試站", 5000, 1200),
        ],
    },

    "food": {
        "name": "食品加工",
        "name_en": "Food Processing",
        "tagline": "烘焙食品",
        "parts": [
            ("F-FLOUR-HIGH", "高筋麵粉", "High Gluten Flour", "raw_material", "kg", 50, 500, 100, 7, 28.0),
            ("F-SUGAR-WHITE", "細白砂糖", "Fine White Sugar", "raw_material", "kg", 30, 300, 80, 5, 35.0),
            ("F-BUTTER", "無鹽奶油（紐西蘭）", "Unsalted Butter (NZ)", "raw_material", "kg", 20, 200, 50, 14, 280.0),
            ("F-EGG", "新鮮雞蛋（一打）", "Fresh Eggs (dozen)", "raw_material", "box", 10, 100, 30, 2, 75.0),
            ("F-YEAST", "速發乾酵母", "Instant Dry Yeast", "raw_material", "kg", 2, 20, 5, 14, 380.0),
            ("F-MILK", "全脂牛奶 1L", "Whole Milk 1L", "raw_material", "l", 20, 200, 50, 3, 45.0),
            ("F-CHOC-CHIP", "巧克力豆", "Chocolate Chips", "raw_material", "kg", 5, 50, 15, 14, 520.0),
            ("F-PACK-BREAD", "麵包袋 24x10cm", "Bread Bag 24x10cm", "packaging", "pcs", 200, 5000, 500, 7, 1.2),
            ("F-PACK-COOKIE", "餅乾密封袋", "Cookie Bag", "packaging", "pcs", 500, 10000, 1000, 7, 2.5),
            ("F-LABEL", "成分標籤貼紙", "Ingredients Label", "packaging", "pcs", 1000, 20000, 2000, 14, 0.8),
        ],
        "products": [
            ("PRD-BREAD-WHITE", "白吐司（500g）",
             "White Bread (500g)", 65.0, 32.0,
             [("F-FLOUR-HIGH", 0.35), ("F-SUGAR-WHITE", 0.04),
              ("F-BUTTER", 0.02), ("F-EGG", 0.05), ("F-YEAST", 0.005),
              ("F-MILK", 0.15), ("F-PACK-BREAD", 1), ("F-LABEL", 1)]),
            ("PRD-COOKIE-CHOC", "巧克力豆餅乾（10片裝）",
             "Chocolate Chip Cookies (10pcs)", 120.0, 58.0,
             [("F-FLOUR-HIGH", 0.15), ("F-SUGAR-WHITE", 0.08),
              ("F-BUTTER", 0.08), ("F-EGG", 0.04), ("F-CHOC-CHIP", 0.12),
              ("F-PACK-COOKIE", 1), ("F-LABEL", 1)]),
        ],
        "suppliers": [
            ("SUP-FLOUR-MILL", "聯華製粉", "T1", 7, True),
            ("SUP-DAIRY", "光泉酪農", "T1", 3, True),
            ("SUP-EGG-FARM", "凱馨蛋品", "T2", 2, True),
            ("SUP-IMPORT", "進口食材代理", "T2", 14, True),
            ("SUP-PACK-FOOD", "食品級包材", "T3", 7, True),
        ],
        "customers": [
            ("CUST-CHAIN", "全聯福利中心", "A", 5_000_000),
            ("CUST-7-11", "統一超商", "A", 8_000_000),
            ("CUST-CAFE", "在地咖啡連鎖", "B", 1_200_000),
            ("CUST-HOTEL", "知名飯店", "B", 800_000),
        ],
        "work_centers": [
            ("WC-MIX", "攪拌機線", 200, 500),
            ("WC-PROOF", "發酵箱", 300, 200),
            ("WC-OVEN-1", "烤箱 #1", 150, 600),
            ("WC-PACK", "包裝線", 500, 300),
        ],
    },

    "textile": {
        "name": "紡織印染",
        "name_en": "Textile Dyeing",
        "tagline": "棉布印染加工",
        "parts": [
            ("T-COTTON-WHITE", "白色棉布胚布 (60 支)", "White Cotton Greige (60s)", "raw_material", "m", 500, 20000, 2000, 14, 38.0),
            ("T-POLY-WHITE", "聚酯纖維胚布", "Polyester Greige", "raw_material", "m", 500, 20000, 2000, 14, 28.0),
            ("T-DYE-REACTIVE-R", "活性染料 紅 (RBL)", "Reactive Dye Red (RBL)", "raw_material", "kg", 5, 100, 20, 21, 850.0),
            ("T-DYE-REACTIVE-B", "活性染料 藍 (R)", "Reactive Dye Blue (R)", "raw_material", "kg", 5, 100, 20, 21, 920.0),
            ("T-DYE-REACTIVE-Y", "活性染料 黃 (GR)", "Reactive Dye Yellow (GR)", "raw_material", "kg", 5, 100, 20, 21, 780.0),
            ("T-CAUSTIC-SODA", "燒鹼", "Caustic Soda", "consumable", "kg", 50, 500, 100, 7, 22.0),
            ("T-SOFTENER", "柔軟劑", "Softener", "consumable", "l", 20, 200, 50, 14, 180.0),
            ("T-PACK-ROLL", "捲布管", "Roll Core", "packaging", "pcs", 100, 1000, 200, 7, 18.0),
            ("T-PACK-LABEL", "出貨標籤", "Shipping Label", "packaging", "pcs", 500, 10000, 1000, 7, 1.5),
        ],
        "products": [
            ("PRD-DYED-RED", "紅色染色棉布 (60 支)",
             "Red Dyed Cotton (60s)", 85.0, 52.0,
             [("T-COTTON-WHITE", 1), ("T-DYE-REACTIVE-R", 0.015),
              ("T-CAUSTIC-SODA", 0.02), ("T-SOFTENER", 0.008),
              ("T-PACK-ROLL", 0.02), ("T-PACK-LABEL", 0.02)]),
            ("PRD-PRINTED-BLUE", "藍色印花聚酯布",
             "Blue Printed Polyester", 95.0, 58.0,
             [("T-POLY-WHITE", 1), ("T-DYE-REACTIVE-B", 0.018),
              ("T-DYE-REACTIVE-Y", 0.005), ("T-SOFTENER", 0.008),
              ("T-PACK-ROLL", 0.02), ("T-PACK-LABEL", 0.02)]),
        ],
        "suppliers": [
            ("SUP-COTTON", "宏遠織造", "T1", 14, True),
            ("SUP-DYE-HOUSE", "永光化學", "T1", 21, True),
            ("SUP-CHEM", "助劑專業", "T2", 14, True),
            ("SUP-PACK-T", "捲布管廠", "T3", 7, True),
        ],
        "customers": [
            ("CUST-NIKE-TW", "Nike 台灣 OEM", "A", 18_000_000),
            ("CUST-UNIQLO", "迅銷台灣", "A", 12_000_000),
            ("CUST-LOCAL-CLOTH", "在地服飾廠", "B", 1_800_000),
            ("CUST-DESIGNER", "設計師工作室", "C", 400_000),
        ],
        "work_centers": [
            ("WC-DYE-1", "染缸 #1（500L）", 400, 1500),
            ("WC-DYE-2", "染缸 #2（1000L）", 800, 2200),
            ("WC-DRY", "拉幅烘乾機", 600, 800),
            ("WC-QC-COLOR", "色差比對站", 300, 600),
        ],
    },
}


# ============================================================
# Seed Function
# ============================================================

async def get_or_create(db, model, lookup, defaults=None):
    from sqlalchemy import select
    stmt = select(model)
    for k, v in lookup.items():
        stmt = stmt.where(getattr(model, k) == v)
    obj = (await db.execute(stmt)).scalar_one_or_none()
    if obj:
        return obj, False
    obj = model(id=str(uuid.uuid4()), **lookup, **(defaults or {}))
    db.add(obj)
    await db.flush()
    return obj, True


async def seed_industry(code: str):
    if code not in INDUSTRIES:
        print(f"Unknown industry: {code}")
        print(f"Available: {list(INDUSTRIES.keys())}")
        return

    industry = INDUSTRIES[code]
    print(f"\n=== Seeding industry: {industry['name']} / {industry['name_en']} ===")
    print(f"Tagline: {industry['tagline']}\n")

    await init_db()
    async with AsyncSessionLocal() as db:
        # 確保 HQ tenant 存在
        from app.models.permission import Tenant
        hq = (await db.execute(select(Tenant).where(Tenant.code == "HQ"))).scalar_one_or_none()
        if not hq:
            hq = Tenant(id=str(uuid.uuid4()), code="HQ", name="總部",
                        tenant_type="hq", mesh_role="central")
            db.add(hq)
            await db.flush()

        # Parts
        parts_map = {}
        for spec in industry["parts"]:
            part_no, name_zh, name_en, cat, unit, mn, mx, ss, lt, cost = spec
            p, created = await get_or_create(db, Part,
                {"part_no": part_no},
                {"name": name_zh,
                 "description": f"{name_en} | {name_zh}",
                 "category": cat, "unit": unit,
                 "min_stock": mn, "max_stock": mx, "safety_stock": ss,
                 "lead_time_days": lt, "unit_cost": cost})
            parts_map[part_no] = p
            if created:
                # 初始庫存：高於安全（除了一個低於以做警示 demo）
                qty = ss * 1.8 if part_no != industry["parts"][0][0] else ss * 0.4
                db.add(Inventory(
                    id=str(uuid.uuid4()), part_id=p.id,
                    qty_on_hand=qty, qty_allocated=0,
                    qty_available=qty, qty_in_transit=0,
                ))
        print(f"  ✓ Parts: {len(industry['parts'])} 個")

        # Products + BOM
        for prod_spec in industry["products"]:
            prod_no, name_zh, name_en, selling, cost, bom_list = prod_spec
            prod, created = await get_or_create(db, Product,
                {"product_no": prod_no},
                {"name": name_zh,
                 "description": f"{name_en} | {name_zh}",
                 "category": "finished", "unit": "set",
                 "selling_price": selling, "standard_cost": cost,
                 "lead_time_days": 7})
            if created:
                for seq, (part_no, qty_per) in enumerate(bom_list, 1):
                    if part_no in parts_map:
                        db.add(BOMItem(
                            id=str(uuid.uuid4()),
                            product_id=prod.id,
                            part_id=parts_map[part_no].id,
                            level=1, sequence_no=seq,
                            qty_per=qty_per, scrap_rate=0.02,
                        ))
        print(f"  ✓ Products + BOM: {len(industry['products'])} 個")

        # Suppliers
        for code_, name, tier, lt, approved in industry["suppliers"]:
            await get_or_create(db, Supplier,
                {"code": code_},
                {"name": name, "tier": tier, "lead_time_days": lt,
                 "is_approved": approved, "is_active": True,
                 "contact_email": f"{code_.lower()}@supplier.example"})
        print(f"  ✓ Suppliers: {len(industry['suppliers'])} 家")

        # Customers
        for code_, name, grade, credit in industry["customers"]:
            await get_or_create(db, Customer,
                {"code": code_},
                {"name": name, "grade": grade, "credit_limit": credit,
                 "contact_email": f"{code_.lower()}@customer.example",
                 "payment_terms": "Net 30"})
        print(f"  ✓ Customers: {len(industry['customers'])} 家")

        # Work Centers
        for code_, name, cap, rate in industry["work_centers"]:
            await get_or_create(db, WorkCenter,
                {"code": code_},
                {"name": name, "capacity_per_day": cap,
                 "efficiency": 0.9, "hourly_rate": rate})
        print(f"  ✓ Work Centers: {len(industry['work_centers'])} 個")

        await db.commit()
        print(f"\n  🎉 {industry['name']} 行業資料完成！")
        print(f"  小提示：第一個零件 {industry['parts'][0][0]} 已故意設定為低於安全庫存，可在 Dashboard 看到警示")


def main():
    if len(sys.argv) < 2:
        print("用法 Usage: python -m scripts.seed_industries <industry>")
        print(f"  可用 industries: {', '.join(INDUSTRIES.keys())}")
        print("\n例 Example:")
        for code, info in INDUSTRIES.items():
            print(f"  python -m scripts.seed_industries {code:8} # {info['name']} / {info['name_en']}")
        return

    industry = sys.argv[1]
    if industry == "all":
        for code in INDUSTRIES:
            asyncio.run(seed_industry(code))
    else:
        asyncio.run(seed_industry(industry))


if __name__ == "__main__":
    main()
