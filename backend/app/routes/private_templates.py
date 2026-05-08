"""Server-side preset template definitions for private entries.

Templates are NOT user-configurable in V1 — they live as Python constants and
are exposed via GET /api/private/templates.
"""
from typing import Any

PRIVATE_TEMPLATES: list[dict[str, Any]] = [
    {
        "type": "tax",
        "label": "税务情况",
        "default_directory": "税务",
        "fields": [
            {"key": "filing_status", "label": "申报状态", "type": "text", "placeholder": "如：Single / MFJ / HoH"},
            {"key": "tax_bracket", "label": "税率档位", "type": "text", "placeholder": "如：22% / 24%"},
            {"key": "agi", "label": "调整后总收入 (AGI)", "type": "number", "placeholder": "USD"},
            {"key": "fbar_fatca", "label": "FBAR / FATCA 情况", "type": "textarea", "placeholder": "海外账户合规相关"},
            {"key": "notes", "label": "备注", "type": "textarea", "placeholder": "其他税务上下文"},
        ],
    },
    {
        "type": "retirement",
        "label": "退休账户",
        "default_directory": "退休账户",
        "fields": [
            {"key": "k401_balance", "label": "401(k) 余额", "type": "number", "placeholder": "USD"},
            {"key": "k401_contrib", "label": "401(k) 年度供款", "type": "number", "placeholder": "USD"},
            {"key": "roth_ira_balance", "label": "Roth IRA 余额", "type": "number", "placeholder": "USD"},
            {"key": "trad_ira_balance", "label": "Traditional IRA 余额", "type": "number", "placeholder": "USD"},
            {"key": "notes", "label": "备注", "type": "textarea", "placeholder": "雇主匹配 / vesting / rollover 等"},
        ],
    },
    {
        "type": "portfolio",
        "label": "投资持仓",
        "default_directory": "投资持仓",
        "fields": [
            {"key": "brokerage", "label": "券商", "type": "text", "placeholder": "如：Fidelity / Schwab"},
            {"key": "holdings", "label": "持仓清单", "type": "textarea", "placeholder": "Ticker · 股数 · 成本基础"},
            {"key": "total_value", "label": "总市值", "type": "number", "placeholder": "USD"},
            {"key": "strategy", "label": "投资策略", "type": "textarea", "placeholder": "长期 / 趋势 / 价值 等"},
        ],
    },
    {
        "type": "personal",
        "label": "个人基本情况",
        "default_directory": "个人基本情况",
        "fields": [
            {"key": "income", "label": "年度收入", "type": "number", "placeholder": "USD"},
            {"key": "family", "label": "家庭情况", "type": "textarea", "placeholder": "婚姻 / 子女 / 受抚养人"},
            {"key": "goals", "label": "财务目标", "type": "textarea", "placeholder": "短中长期目标"},
            {"key": "risk_tolerance", "label": "风险偏好", "type": "text", "placeholder": "保守 / 平衡 / 激进"},
        ],
    },
    {
        "type": "real_estate",
        "label": "房产资产",
        "default_directory": "房产资产",
        "fields": [
            {"key": "address", "label": "房产地址", "type": "text", "placeholder": "如：城市 / 州"},
            {"key": "market_value", "label": "市场估值", "type": "number", "placeholder": "USD"},
            {"key": "mortgage_balance", "label": "贷款余额", "type": "number", "placeholder": "USD"},
            {"key": "rental_income", "label": "租金收入", "type": "number", "placeholder": "USD/月，自住填 0"},
            {"key": "notes", "label": "备注", "type": "textarea", "placeholder": "贷款类型 / 利率 / 装修等"},
        ],
    },
    {
        "type": "freeform",
        "label": "自由格式",
        "default_directory": "自由格式",
        "fields": [
            {"key": "content", "label": "内容", "type": "textarea", "placeholder": "Markdown 自由记录"},
        ],
    },
]

VALID_TEMPLATE_TYPES = {t["type"] for t in PRIVATE_TEMPLATES}
TEMPLATE_DEFAULT_DIRECTORIES = {t["type"]: t["default_directory"] for t in PRIVATE_TEMPLATES}


def template_default_directory(template_type: str) -> str:
    return TEMPLATE_DEFAULT_DIRECTORIES.get(template_type, "")


def derive_text_for_embedding(template_type: str, title: str, content_json: dict) -> str:
    """Combine title and content fields into a single string suitable for embedding.

    Fields are emitted in template-defined order to keep embeddings stable across
    repeated calls with the same content.
    """
    parts: list[str] = [f"{title}".strip()]
    template = next((t for t in PRIVATE_TEMPLATES if t["type"] == template_type), None)
    if template is None:
        # Unknown template_type: fall back to dumping all values
        for v in content_json.values():
            if v is not None and str(v).strip():
                parts.append(str(v))
        return "\n".join(p for p in parts if p)

    for field in template["fields"]:
        key = field["key"]
        value = content_json.get(key)
        if value is None or str(value).strip() == "":
            continue
        parts.append(f"{field['label']}: {value}")
    return "\n".join(p for p in parts if p)
