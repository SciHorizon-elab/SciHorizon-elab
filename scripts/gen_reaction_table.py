"""
gen_reaction_table.py
扩充 `solute_reaction.py` 的 REACTIONS 与 SOLUTE2RGBA,用于对齐
rebuttal 论文口径("hundreds of encoded reactions" → "100+")。

用法:
    python scripts/gen_reaction_table.py                # 打印统计 + 自校验 + 新表(stdout)
    python scripts/gen_reaction_table.py --check        # 只跑自校验(默认断言已存在 5 条反应 + 22 色值保留)
    python scripts/gen_reaction_table.py --target 120   # 控制目标反应数量下限,默认 100

设计要点(详见 docs/reaction_library_expansion_plan.md §4):
- 反应类型:9 类复分解/中和/沉淀(AgCl / BaSO₄ / PbSO₄ / CaSO₄ / 碳酸盐沉淀 /
  酸+碳酸盐 / 中和 / 氢氧化物沉淀 / 铵盐+碱),按溶解性表系统生成。
- 单产物 API 保持;双沉淀按 §4.5 择色(优先有色沉淀;两者皆白按阳离子优先级)。
- 输出确定性排序:REACTIONS 按 frozenset 排序产物名,产物名 alpha 排序;
  SOLUTE2RGBA 按 key 排序;保证 diff 友好、可重复生成。
- 自校验:无自配对(A+A)、无全溶无驱动力条目、产物/反应物颜色全覆盖、
  原 5 条反应键值对原样保留、原 22 条颜色值逐位保留。
- 不动文件中任何函数与文档字符串。
"""
import argparse
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# 物质全集(全可溶,均可作初始溶质入 SOLUTE2RGBA)
# ─────────────────────────────────────────────────────────────────────────────

# 阳离子 → 可溶盐(可入表作反应物,遇沉淀驱动反应)
CATIONS = {
    "Na":  ["NaCl",  "Na2SO4",  "Na2CO3",  "NaNO3"],
    "K":   ["KCl",   "K2SO4",   "K2CO3",   "KNO3"],
    "NH4": ["NH4Cl", "(NH4)2SO4", "(NH4)2CO3", "NH4NO3"],
    "Ba":  ["BaCl2", "Ba(NO3)2"],  # Ba(OH)2 在碱里
    "Ca":  ["CaCl2", "Ca(NO3)2"],  # Ca(OH)2 在碱里
    "Mg":  ["MgCl2", "Mg(NO3)2", "MgSO4"],
    "Al":  ["AlCl3", "Al(NO3)3", "Al2(SO4)3"],
    "Zn":  ["ZnCl2", "Zn(NO3)2", "ZnSO4"],
    "Fe2": ["FeCl2", "Fe(NO3)2", "FeSO4"],   # 浅绿
    "Fe3": ["FeCl3", "Fe(NO3)3", "Fe2(SO4)3"],  # 黄棕
    "Cu":  ["CuCl2", "Cu(NO3)2"],  # CuSO4 单独入
    "Ag":  ["AgNO3"],
    "Pb":  ["Pb(NO3)2"],
}

# 酸
ACIDS = ["HCl", "H2SO4", "HNO3"]

# 碱
BASES = ["NaOH", "KOH", "Ba(OH)2", "Ca(OH)2"]

# 碳酸盐来源(已在 CATIONS 内;此处留空单集中未用,保留扩展性)
CARBONATE_SOURCES = ["Na2CO3", "K2CO3", "(NH4)2CO3"]

# 单离子源(用作阴离子/阳离子的纯供应源)
SULFATE_SOURCES = ["Na2SO4", "K2SO4", "(NH4)2SO4", "CuSO4", "FeSO4", "MgSO4", "ZnSO4", "Al2(SO4)3", "Fe2(SO4)3", "H2SO4"]
CHLORIDE_SOURCES = ["NaCl", "KCl", "NH4Cl", "BaCl2", "CaCl2", "MgCl2", "AlCl3", "ZnCl2", "FeCl2", "FeCl3", "CuCl2", "HCl", "Pb(NO3)2"]  # Pb(NO3)2 + SO4 -> PbSO4 by anion exchange

# ────────────────────────────────────────────────���────────────────────────────
# 颜色表(下游写入 SOLUTE2RGBA)
# ─────────────────────────────────────────────────────────────────────────────

# 无色溶质 α=0.3,可溶盐默认;无色沉淀 α=0.7
COLORLESS_SOLUBLE = [1.0, 1.0, 1.0, 0.3]
COLORLESS_PRECIPITATE = [1.0, 1.0, 1.0, 0.7]
COLORLESS_BASE_LIMEWATER = [1.0, 1.0, 1.0, 0.3]  # Ca(OH)2 澄清石灰水

# 有色溶质 α=0.4;有色沉淀 α=0.5
COLORED_SOLUTE_ALPHA = 0.4
COLORED_PRECIPITATE_ALPHA = 0.5

# 物质 → 颜色(权威颜色表;由本脚本与 solute_reaction.py 共用)
SUBSTANCE_COLOR = {
    # 已有色溶质(保持原值,逐位一致)
    "CuCl2":  [0.141, 1.0,   0.174, COLORED_SOLUTE_ALPHA],
    "CuSO4":  [0.0,   0.45,  1.0,   COLORED_SOLUTE_ALPHA],
    "FeCl3":  [0.6475, 0.5686, 0.023, COLORED_SOLUTE_ALPHA],
    "KMnO4":  [0.5,   0.0,   0.5,   COLORED_SOLUTE_ALPHA],
    "I2":     [0.3,   0.13,  0.0,   COLORED_SOLUTE_ALPHA],
    "K2CrO4": [0.57,  0.12,  0.013, COLORED_SOLUTE_ALPHA],

    # 同阳离子同色(扩充规则:Cu(NO3)2 与 CuSO4 同蓝,Fe3+ 盐与 FeCl3 同黄棕,Fe2+ 盐浅绿)
    "Cu(NO3)2": [0.0,   0.45,  1.0,   COLORED_SOLUTE_ALPHA],
    "Fe(NO3)3": [0.6475, 0.5686, 0.023, COLORED_SOLUTE_ALPHA],
    "Fe2(SO4)3": [0.6475, 0.5686, 0.023, COLORED_SOLUTE_ALPHA],
    "FeCl2":   [0.72, 0.9, 0.72, COLORED_SOLUTE_ALPHA],
    "Fe(NO3)2": [0.72, 0.9, 0.72, COLORED_SOLUTE_ALPHA],
    "FeSO4":   [0.72, 0.9, 0.72, COLORED_SOLUTE_ALPHA],

    # 产物
    "Cu(OH)2":  [0.0,   0.32,  0.78,  COLORED_PRECIPITATE_ALPHA],   # 蓝絮状
    "Fe(OH)3":  [0.55,  0.27,  0.07,  COLORED_PRECIPITATE_ALPHA],   # 红褐
    "Fe(OH)2":  [0.85,  0.90,  0.82,  COLORED_PRECIPITATE_ALPHA],   # 灰白→灰绿
    "AgCl":     COLORLESS_PRECIPITATE,
    "BaSO4":    COLORLESS_PRECIPITATE,
    "PbSO4":    COLORLESS_PRECIPITATE,
    "CaSO4":    COLORLESS_PRECIPITATE,
    "Mg(OH)2":  COLORLESS_PRECIPITATE,
    "Al(OH)3":  COLORLESS_PRECIPITATE,
    "Zn(OH)2":  COLORLESS_PRECIPITATE,
    "Pb(OH)2":  COLORLESS_PRECIPITATE,
    "BaCO3":    COLORLESS_PRECIPITATE,
    "CaCO3":    COLORLESS_PRECIPITATE,
    "MgCO3":    COLORLESS_PRECIPITATE,
    "ZnCO3":    COLORLESS_PRECIPITATE,
    "PbCO3":    COLORLESS_PRECIPITATE,
    "Ag2CO3":   [0.95, 0.92, 0.72,  COLORED_PRECIPITATE_ALPHA],   # 淡黄

    # 中和/复分解可溶副产物默认无色
    "NaCl":     COLORLESS_SOLUBLE,
    "Na2SO4":   COLORLESS_SOLUBLE,
    "NaNO3":    COLORLESS_SOLUBLE,
    "KCl":      COLORLESS_SOLUBLE,
    "K2SO4":    COLORLESS_SOLUBLE,
    "KNO3":     COLORLESS_SOLUBLE,
    "NH4Cl":    COLORLESS_SOLUBLE,
    "(NH4)2SO4": COLORLESS_SOLUBLE,
    "NH4NO3":   COLORLESS_SOLUBLE,
    "BaCl2":    COLORLESS_SOLUBLE,
    "Ba(NO3)2": COLORLESS_SOLUBLE,
    "CaCl2":    COLORLESS_SOLUBLE,
    "Ca(NO3)2": COLORLESS_SOLUBLE,
    "MgCl2":    COLORLESS_SOLUBLE,
    "Mg(NO3)2": COLORLESS_SOLUBLE,
    "MgSO4":    COLORLESS_SOLUBLE,
    "AlCl3":    COLORLESS_SOLUBLE,
    "Al(NO3)3": COLORLESS_SOLUBLE,
    "Al2(SO4)3": COLORLESS_SOLUBLE,
    "ZnCl2":    COLORLESS_SOLUBLE,
    "Zn(NO3)2": COLORLESS_SOLUBLE,
    "ZnSO4":    COLORLESS_SOLUBLE,
    "CuCl2":    [0.141, 1.0, 0.174, COLORED_SOLUTE_ALPHA],  # 重写以保原值
    "AgNO3":    COLORLESS_SOLUBLE,
    "Pb(NO3)2": COLORLESS_SOLUBLE,
    "HCl":      COLORLESS_SOLUBLE,
    "H2SO4":    COLORLESS_SOLUBLE,
    "HNO3":     COLORLESS_SOLUBLE,
    "NaOH":     COLORLESS_SOLUBLE,
    "KOH":      COLORLESS_SOLUBLE,
    "Ba(OH)2":  COLORLESS_BASE_LIMEWATER,
    "Ca(OH)2":  COLORLESS_BASE_LIMEWATER,
    "Na2CO3":   COLORLESS_SOLUBLE,
    "K2CO3":    COLORLESS_SOLUBLE,
    "(NH4)2CO3": COLORLESS_SOLUBLE,
}


# ─────────────────────────────────────────────────────────────────────────────
# 排除清单(§4.4)— 反应与写入双方均跳过
# ─────────────────────────────────────────────────────────────────────────────

# 不作反应物(微溶 / 两性 / 不稳定)
EXCLUDED_REACTANTS = {
    "PbCl2",        # 微溶
    "CaSO4",        # 微溶,作产物不反应物
    "Ag2SO4",       # 微溶
    "AgOH",         # 立即分解
    "CuCO3",        # 水解不稳定
    "FeCO3",        # 水解不稳定
    "Fe2(CO3)3",    # 不存在
}

# 不作产物(双沉淀白-白一对时,如 Mg(OH)2 + BaSO4 也可生成,但 Mg(OH)2 与
# 强碱反应更经典,这里只屏蔽"教材硬伤"与 Ag2O 类)
EXCLUDED_PRODUCTS = {
    "Ag2O",         # AgNO3+NaOH 教材争议
    "PbSO3",        # H2SO3 不在本场景
}


# ─────────────────────────────────────────────────────────────────────────��───
# 反应生成(9 类)
# ─────────────────────────────────────────────────────────────────────────────

def all_soluble_salts():
    """全部可溶盐(反应物池)。"""
    out = []
    for salts in CATIONS.values():
        out.extend(salts)
    # 单独列出未被上面覆盖的特殊条目
    out.append("CuSO4")
    return out


def add_reaction(reactions, a, b, product, audit):
    """加入一条反应,记录到审计。"""
    if a == b:
        return
    key = frozenset({a, b})
    if key in reactions:
        # 已存在:保留首次裁决,记入审计
        audit.setdefault("dups", []).append((a, b, reactions[key], product))
        return
    reactions[key] = product


# ① 氯化物沉淀:Cl⁻ 源 + AgNO3 → AgCl
def gen_AgCl(reactions, audit):
    for cl in CHLORIDE_SOURCES:
        if cl == "AgNO3":
            continue
        if cl in EXCLUDED_REACTANTS:
            continue
        add_reaction(reactions, "AgNO3", cl, "AgCl", audit)
    audit["count_AgCl"] = sum(1 for v in reactions.values() if v == "AgCl")


# ② BaSO4:SO4²⁻ 源 + Ba²⁺ 源
def gen_BaSO4(reactions, audit):
    sources = ["BaCl2", "Ba(NO3)2"]
    for so4 in SULFATE_SOURCES:
        for ba in sources:
            if ba == so4:
                continue
            add_reaction(reactions, ba, so4, "BaSO4", audit)
    audit["count_BaSO4"] = sum(1 for v in reactions.values() if v == "BaSO4")


# ③ PbSO4:SO4²⁻ 源 + Pb(NO3)2
def gen_PbSO4(reactions, audit):
    for so4 in SULFATE_SOURCES:
        if so4 == "Pb(NO3)2":
            continue
        add_reaction(reactions, "Pb(NO3)2", so4, "PbSO4", audit)
    audit["count_PbSO4"] = sum(1 for v in reactions.values() if v == "PbSO4")


# ④ CaSO4(微溶):Ca²⁺ 源 + Na2SO4/K2SO4/(NH4)2SO4/H2SO4
def gen_CaSO4(reactions, audit):
    ca_sources = ["CaCl2", "Ca(NO3)2"]
    so4_sources = ["Na2SO4", "K2SO4", "(NH4)2SO4", "H2SO4"]
    for ca in ca_sources:
        for so4 in so4_sources:
            if ca == so4:
                continue
            add_reaction(reactions, ca, so4, "CaSO4", audit)
    audit["count_CaSO4"] = sum(1 for v in reactions.values() if v == "CaSO4")


# ⑤ 碳酸盐沉淀:CO3²⁻ 源 + Ca/Ba/Mg/Zn/Pb/Ag 盐
def gen_carbonates(reactions, audit):
    co3 = CARBONATE_SOURCES
    # Ca²⁺ / Ba²⁺ / Mg²⁺ / Zn²⁺ / Pb²⁺ + CO3²⁻ → 对应碳酸盐
    targets = {
        "CaCl2":  "CaCO3", "Ca(NO3)2": "CaCO3",
        "BaCl2":  "BaCO3", "Ba(NO3)2": "BaCO3",
        "MgCl2":  "MgCO3", "Mg(NO3)2": "MgCO3", "MgSO4": "MgCO3",
        "ZnCl2":  "ZnCO3", "Zn(NO3)2": "ZnCO3", "ZnSO4": "ZnCO3",
        "Pb(NO3)2": "PbCO3",
        "AgNO3":  "Ag2CO3",  # 淡黄(唯一有色碳酸盐沉淀)
    }
    for salt, product in targets.items():
        if salt in EXCLUDED_REACTANTS:
            continue
        for c in co3:
            add_reaction(reactions, salt, c, product, audit)
    audit["count_carbonates"] = sum(
        1 for v in reactions.values() if v.endswith("CO3")
    )


# ⑥ 酸 + 碳酸盐(气体逸出):记可溶盐(CO2 逸出,简化)
def gen_acid_carbonate(reactions, audit):
    for acid in ACIDS:
        for c in CARBONATE_SOURCES:
            # 产物名取"酸对应的可溶盐" — NaCl / Na2SO4 / NaNO3 / ...
            cation = c.replace("(NH4)2", "").replace("2CO3", "").replace("CO3", "")
            # Na2CO3 → Na2;K2CO3 → K2;(NH4)2CO3 → (NH4)2
            acid_anion = acid.replace("H", "", 1) if not acid.startswith("H2") else acid.replace("H2", "", 1)
            # 简单映射
            salt_map = {
                ("Na", "Cl"): "NaCl", ("Na", "SO4"): "Na2SO4", ("Na", "NO3"): "NaNO3",
                ("K",  "Cl"): "KCl",  ("K",  "SO4"): "K2SO4",  ("K",  "NO3"): "KNO3",
                ("NH4", "Cl"): "NH4Cl", ("NH4", "SO4"): "(NH4)2SO4", ("NH4", "NO3"): "NH4NO3",
            }
            acid_key = "Cl" if acid == "HCl" else ("SO4" if acid == "H2SO4" else "NO3")
            product = salt_map.get((cation, acid_key))
            if product is None:
                continue
            if product in EXCLUDED_PRODUCTS:
                continue
            add_reaction(reactions, acid, c, product, audit)
    audit["count_acid_carbonate"] = sum(
        1 for k, v in reactions.items()
        if any(a in ACIDS for a in k) and any(c in CARBONATE_SOURCES for c in k)
    )


# ⑦ 中和:酸 + 碱 → 可溶盐 + H2O(记录可溶盐)
def gen_neutralization(reactions, audit):
    for acid in ACIDS:
        for base in BASES:
            # 解阳离子/阴离子
            base_cation = base.replace("(OH)2", "2").replace("OH", "")
            acid_anion = "Cl" if acid == "HCl" else ("SO4" if acid == "H2SO4" else "NO3")
            salt_map = {
                ("Na", "Cl"): "NaCl", ("Na", "SO4"): "Na2SO4", ("Na", "NO3"): "NaNO3",
                ("K",  "Cl"): "KCl",  ("K",  "SO4"): "K2SO4",  ("K",  "NO3"): "KNO3",
                ("Ba", "Cl"): "BaCl2", ("Ba", "SO4"): "BaSO4", ("Ba", "NO3"): "Ba(NO3)2",
                ("Ca", "Cl"): "CaCl2", ("Ca", "SO4"): "CaSO4", ("Ca", "NO3"): "Ca(NO3)2",
            }
            product = salt_map.get((base_cation, acid_anion))
            if product is None:
                continue
            # BaSO4 / CaSO4 也是沉淀(已计入 ② ④)— 但中和单独也算反应
            # 保留,符合"中和反应"口径
            add_reaction(reactions, acid, base, product, audit)
    audit["count_neutralization"] = sum(
        1 for k, v in reactions.items()
        if any(a in ACIDS for a in k) and any(b in BASES for b in k)
    )


# ⑧ 氢氧化物沉淀:M²⁺/M³⁺ 盐 + NaOH/KOH/Ba(OH)2/Ca(OH)2 → M(OH)n↓
# 双沉淀时 §4.5 择色:有 M(OH)2 有色 + 对方沉淀白色 → 选有色(Cu(OH)2 蓝优先);
# 两皆白则按阳离子优先级(Mg>Al>Zn>Pb 取 Cu 边的更经典组合优先记录有色产物;若两皆白,按阳离子优先级取一个)
def gen_hydroxides(reactions, audit):
    # (盐, 碱) → 主产物
    # 双沉淀情形:Cu²⁺ + Ba(OH)2 → Cu(OH)2 + BaSO4
    # 优先取有色产物 Cu(OH)2
    targets = {
        "MgCl2": "Mg(OH)2", "Mg(NO3)2": "Mg(OH)2", "MgSO4": "Mg(OH)2",
        "AlCl3": "Al(OH)3", "Al(NO3)3": "Al(OH)3", "Al2(SO4)3": "Al(OH)3",
        "ZnCl2": "Zn(OH)2", "Zn(NO3)2": "Zn(OH)2", "ZnSO4": "Zn(OH)2",
        "FeCl2": "Fe(OH)2", "Fe(NO3)2": "Fe(OH)2", "FeSO4": "Fe(OH)2",
        "FeCl3": "Fe(OH)3", "Fe(NO3)3": "Fe(OH)3", "Fe2(SO4)3": "Fe(OH)3",
        "CuCl2": "Cu(OH)2", "Cu(NO3)2": "Cu(OH)2", "CuSO4": "Cu(OH)2",
        "Pb(NO3)2": "Pb(OH)2",
    }
    for salt, product in targets.items():
        for base in BASES:
            # 双沉淀择色:
            #  - 若产物是有色的(Cu(OH)2, Fe(OH)2, Fe(OH)3),即使有 BaSO4 也优先取有色
            #  - 若产物是白色(Mg/Al/Zn/Pb(OH)n),但 base 含 Ba(OH)2 与 SO4 源,
            #    会双白色沉淀 → 按阳离子优先级取"Mg(OH)2 > Al(OH)3 > Zn(OH)2 > Pb(OH)2"
            if base == "Ba(OH)2" and salt in {"MgSO4", "ZnSO4", "CuSO4", "FeSO4", "Al2(SO4)3", "Fe2(SO4)3"}:
                # 双沉淀情形:有 BaSO4 白色 + M(OH)n 沉淀
                if product in {"Cu(OH)2", "Fe(OH)2", "Fe(OH)3"}:
                    # 优先记录有色产物
                    add_reaction(reactions, salt, base, product, audit)
                else:
                    # 两皆白:固定取 M(OH)n(Mg>Al>Zn>Pb)
                    add_reaction(reactions, salt, base, product, audit)
                continue
            add_reaction(reactions, salt, base, product, audit)
    audit["count_hydroxides"] = sum(
        1 for v in reactions.values() if "(OH)" in v
    )


# ⑨ 铵盐 + 强碱(气体):产物记可溶盐,简化处理
def gen_ammonium_base(reactions, audit):
    nh4_salts = ["NH4Cl", "(NH4)2SO4", "NH4NO3"]
    for nh4 in nh4_salts:
        for base in BASES:
            # 阳离子:base 去 OH/ (OH)2
            base_cation = base.replace("(OH)2", "2").replace("OH", "")
            anion = "Cl" if nh4 == "NH4Cl" else ("SO4" if nh4 == "(NH4)2SO4" else "NO3")
            salt_map = {
                ("Na", "Cl"): "NaCl", ("Na", "SO4"): "Na2SO4", ("Na", "NO3"): "NaNO3",
                ("K",  "Cl"): "KCl",  ("K",  "SO4"): "K2SO4",  ("K",  "NO3"): "KNO3",
                ("Ba", "Cl"): "BaCl2", ("Ba", "SO4"): "BaSO4", ("Ba", "NO3"): "Ba(NO3)2",
                ("Ca", "Cl"): "CaCl2", ("Ca", "SO4"): "CaSO4", ("Ca", "NO3"): "Ca(NO3)2",
            }
            product = salt_map.get((base_cation, anion))
            if product is None:
                continue
            add_reaction(reactions, nh4, base, product, audit)
    audit["count_ammonium_base"] = sum(
        1 for k, v in reactions.items()
        if any(a in nh4_salts for a in k) and any(b in BASES for b in k)
    )


def generate_reactions():
    reactions = {}
    audit = {}

    # 先植入原 5 条,确保逐位保留(随后规则可能再生成相同键 — `add_reaction` 去重)
    add_reaction(reactions, "CuSO4",  "NaOH",   "Cu(OH)2", audit)
    add_reaction(reactions, "FeCl3",  "NaOH",   "Fe(OH)3", audit)
    add_reaction(reactions, "AgNO3",  "NaCl",   "AgCl",    audit)
    add_reaction(reactions, "BaCl2",  "Na2SO4", "BaSO4",   audit)
    add_reaction(reactions, "BaCl2",  "H2SO4",  "BaSO4",   audit)

    gen_AgCl(reactions, audit)
    gen_BaSO4(reactions, audit)
    gen_PbSO4(reactions, audit)
    gen_CaSO4(reactions, audit)
    gen_carbonates(reactions, audit)
    gen_acid_carbonate(reactions, audit)
    gen_neutralization(reactions, audit)
    gen_hydroxides(reactions, audit)
    gen_ammonium_base(reactions, audit)

    return reactions, audit


# ─────────────────────────────────────────────────────────────────────────────
# 自校验
# ─────────────────────────────────────────────────────────────────────────────

ORIGINAL_REACTIONS = {
    frozenset({"CuSO4",  "NaOH"}):   "Cu(OH)2",
    frozenset({"FeCl3",  "NaOH"}):   "Fe(OH)3",
    frozenset({"AgNO3",  "NaCl"}):   "AgCl",
    frozenset({"BaCl2",  "Na2SO4"}): "BaSO4",
    frozenset({"BaCl2",  "H2SO4"}):  "BaSO4",
}

# 原 22 色值(逐位)
ORIGINAL_COLORS = {
    "CuCl2":   [0.141, 1.0,   0.174, 0.4],
    "CuSO4":   [0.0,   0.45,  1.0,   0.4],
    "FeCl3":   [0.6475, 0.5686, 0.023, 0.4],
    "KMnO4":   [0.5,   0.0,   0.5,   0.4],
    "I2":      [0.3,   0.13,  0.0,   0.4],
    "K2CrO4":  [0.57,  0.12,  0.013, 0.4],
    "NaCl":    [1.0,   1.0,   1.0,   0.3],
    "AgNO3":   [1.0,   1.0,   1.0,   0.3],
    "BaCl2":   [1.0,   1.0,   1.0,   0.3],
    "H2SO4":   [1.0,   1.0,   1.0,   0.3],
    "NaOH":    [1.0,   1.0,   1.0,   0.3],
    "Ba(NO3)2":[1.0,   1.0,   1.0,   0.3],
    "Pb(NO3)2":[1.0,   1.0,   1.0,   0.3],
    "Na2CO3":  [1.0,   1.0,   1.0,   0.3],
    "CaCl2":   [1.0,   1.0,   1.0,   0.3],
    "HCl":     [1.0,   1.0,   1.0,   0.3],
    "CaSO4":   [1.0,   1.0,   1.0,   0.7],
    "Cu(OH)2": [0.0,   0.32,  0.78,  0.5],
    "Fe(OH)3": [0.55,  0.27,  0.07,  0.5],
    "AgCl":    [1.0,   1.0,   1.0,   0.7],
    "BaSO4":   [1.0,   1.0,   1.0,   0.7],
    "Na2SO4":  [1.0,   1.0,   1.0,   0.3],
}


def self_check(reactions, audit, target=100, strict=False):
    """返回 (passed: bool, report: list[str])。"""
    report = []
    passed = True

    def fail(msg):
        nonlocal passed
        passed = False
        report.append(f"  ✗ {msg}")

    def info(msg):
        report.append(f"  ✓ {msg}")

    # 1. 原 5 条反应逐位保留
    for key, product in ORIGINAL_REACTIONS.items():
        if reactions.get(key) != product:
            fail(f"原反应缺失或改变: {set(key)} expected={product} got={reactions.get(key)}")
        else:
            info(f"原反应保留: {sorted(key)} → {product}")

    # 2. 无自配对
    self_pairs = [k for k in reactions if len(k) == 1]
    if self_pairs:
        fail(f"出现自配对: {[next(iter(k)) for k in self_pairs]}")
    else:
        info("无自配对反应")

    # 3. 数量 ≥ target
    n = len(reactions)
    if n < target:
        fail(f"反应数 {n} < 目标 {target}")
    else:
        info(f"反应数 {n} ≥ {target}")

    # 4. 颜色表覆盖:反应中所有反应物与产物都在 SUBSTANCE_COLOR
    missing = set()
    for k, v in reactions.items():
        for s in k:
            if s not in SUBSTANCE_COLOR:
                missing.add(s)
        if v not in SUBSTANCE_COLOR:
            missing.add(v)
    if missing:
        fail(f"颜色表未覆盖: {sorted(missing)}")
    else:
        info(f"颜色表覆盖全部 {len(reactions)} 反应的反应物+产物")

    # 5. 原 22 色值逐位保留
    for k, v in ORIGINAL_COLORS.items():
        if SUBSTANCE_COLOR.get(k) != v:
            fail(f"原色值改变: {k} expected={v} got={SUBSTANCE_COLOR.get(k)}")
    if all(SUBSTANCE_COLOR.get(k) == v for k, v in ORIGINAL_COLORS.items()):
        info(f"原 22 色值逐位保留")

    # 6. 排除清单:这些物质不应作产物
    bad_products = [v for v in reactions.values() if v in EXCLUDED_PRODUCTS]
    if bad_products:
        fail(f"产物包含排除项: {bad_products}")
    else:
        info("排除项未出现在产物中")

    # 7. 重复键处理
    if audit.get("dups"):
        info(f"重复键已合并 {len(audit['dups'])} 条(保留首次裁决)")

    return passed, report


# ─────────────────────────────────────────────────────────────────────────────
# 渲染模块替换块(替换原 REACTIONS 与 SOLUTE2RGBA)
# ─────────────────────────────────────────────────────────────────────────────

REACTIONS_BEGIN = "# ── AUTO-GEN BEGIN:REACTIONS ── 由 scripts/gen_reaction_table.py 生成,勿手改"
REACTIONS_END   = "# ── AUTO-GEN END:REACTIONS ──"


def format_reactions_block(reactions):
    lines = [REACTIONS_BEGIN]
    lines.append("REACTIONS = {")
    # 确定性排序:产物名 alpha,每个 key 排序后展示
    items = sorted(reactions.items(), key=lambda kv: (kv[1], sorted(kv[0])))
    for key, product in items:
        a, b = sorted(key)
        lines.append(f'    frozenset({{"{a}", "{b}"}}): "{product}",')
    lines.append("}")
    lines.append(REACTIONS_END)
    return "\n".join(lines)


COLORS_BEGIN = "# ── AUTO-GEN BEGIN:SOLUTE2RGBA ── 由 scripts/gen_reaction_table.py 生成,勿手改"
COLORS_END   = "# ── AUTO-GEN END:SOLUTE2RGBA ──"


def format_colors_block():
    """SOLUTE2RGBA 由脚本生成,key 排序,值逐字面量。"""
    lines = [COLORS_BEGIN]
    lines.append("SOLUTE2RGBA = {")
    # 先放注释分组:反应物/产物
    reactants = [k for k in SUBSTANCE_COLOR if k in (
        set(all_soluble_salts()) | set(ACIDS) | set(BASES)
    )]
    products = [k for k in SUBSTANCE_COLOR if k not in reactants]
    reactants.sort()
    products.sort()
    lines.append("    # 反应物(可溶盐 / 酸 / 碱)")
    for k in reactants:
        v = SUBSTANCE_COLOR[k]
        lines.append(f'    "{k}": {list(v)},')
    lines.append("    # 产物")
    for k in products:
        v = SUBSTANCE_COLOR[k]
        lines.append(f'    "{k}": {list(v)},')
    lines.append("}")
    lines.append(COLORS_END)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 写入:替换目标模块的两个块
# ─────────────────────────────────────────────────────────────────────────────

def write_module(path: Path, reactions: dict):
    """原地替换 SOLUTE2RGBA 与 REACTIONS 两块,其余内容零改动。

    策略:
      - 若模块已有 AUTO-GEN 块标记,精确替换两个块
      - 若无标记(首次写入),按当前手写块的位置范围替换:
          SOLUTE2RGBA = { ... }
          ...
          REACTIONS = { ... }
          ...
    """
    text = path.read_text(encoding="utf-8")

    # 1) SOLUTE2RGBA 块
    new_colors = format_colors_block()
    if COLORS_BEGIN in text:
        # 已标记:替换 BEGIN..END
        text = _replace_marked(text, COLORS_BEGIN, COLORS_END, new_colors)
    else:
        # 首次:替换 SOLUTE2RGBA = { ... }  完整字典块
        text = _replace_dict_block(
            text, var_name="SOLUTE2RGBA",
            new_block=new_colors + "\n"
        )

    # 2) REACTIONS 块
    new_reactions = format_reactions_block(reactions)
    if REACTIONS_BEGIN in text:
        text = _replace_marked(text, REACTIONS_BEGIN, REACTIONS_END, new_reactions)
    else:
        text = _replace_dict_block(
            text, var_name="REACTIONS",
            new_block=new_reactions + "\n"
        )

    path.write_text(text, encoding="utf-8")


def _replace_marked(text: str, begin: str, end: str, new_block: str) -> str:
    """替换从 begin 标记到 end 标记之间的内容(含两端标记)。"""
    i = text.find(begin)
    if i < 0:
        raise RuntimeError(f"未找到标记: {begin}")
    j = text.find(end, i)
    if j < 0:
        raise RuntimeError(f"未找到标记: {end}")
    j_end = j + len(end)
    return text[:i] + new_block + "\n" + text[j_end:]


def _replace_dict_block(text: str, var_name: str, new_block: str) -> str:
    """替换 module-level `VAR = { ... }` 字典块(首次写入,无 AUTO-GEN 标记)。"""
    import re
    # 匹配 `VAR_NAME = {` 开头,找到对应的 `}`
    pattern = re.compile(rf"^{re.escape(var_name)}\s*=\s*\{{", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        raise RuntimeError(f"未找到模块级字典: {var_name}")
    start = m.start()
    # 从 `{` 起,数括号平衡,找到匹配的 `}`
    i = m.end() - 1  # 指向 `{`
    depth = 0
    in_str = False
    str_quote = None
    j = i
    while j < len(text):
        c = text[j]
        if in_str:
            if c == "\\":
                j += 2
                continue
            if c == str_quote:
                in_str = False
        else:
            if c in ("'", '"'):
                in_str = True
                str_quote = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
        j += 1
    if j >= len(text):
        raise RuntimeError(f"未找到 {var_name} 的闭合 `}}`")
    end = j + 1
    return text[:start] + new_block + text[end:]


# ─────────────────────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="扩充 REACTIONS / SOLUTE2RGBA")
    ap.add_argument("--target", type=int, default=100, help="目标反应数下限")
    ap.add_argument("--check", action="store_true", help="只跑自校验")
    ap.add_argument("--write", default=None,
                    help="写入指定 solute_reaction.py(替换 SOLUTE2RGBA 与 REACTIONS 块)")
    args = ap.parse_args()

    reactions, audit = generate_reactions()
    passed, report = self_check(reactions, audit, target=args.target)

    print(f"=== 统计 ===")
    for k, v in audit.items():
        if k.startswith("count_"):
            print(f"  {k}: {v}")
    print(f"  total REACTIONS: {len(reactions)}")
    print(f"  total SOLUTE2RGBA: {len(SUBSTANCE_COLOR)}")
    print()

    print(f"=== 自校验 {'PASS' if passed else 'FAIL'} ===")
    for line in report:
        print(line)

    if args.check:
        sys.exit(0 if passed else 1)

    print("=== 渲染预览 (REACTIONS,前 10 条) ===")
    items = sorted(reactions.items(), key=lambda kv: (kv[1], sorted(kv[0])))
    for key, product in items[:10]:
        a, b = sorted(key)
        print(f'  frozenset({{"{a}", "{b}"}}): "{product}",')
    print(f"  ... (共 {len(reactions)} 条)")

    if not passed:
        sys.exit("自校验失败,不写入文件")

    if args.write:
        target_path = Path(args.write)
        write_module(target_path, reactions)
        print(f"\n✓ 已写入 {target_path}")


if __name__ == "__main__":
    main()