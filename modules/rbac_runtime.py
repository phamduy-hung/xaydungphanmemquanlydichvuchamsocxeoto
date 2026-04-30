import json
from pathlib import Path


RBAC_PATH = Path("data/rbac_permissions.json")


DEFAULT_SECTION_PERMISSIONS = {
    "Quản lý": {
        "dashboard": True,
        "web": True,
        "crm": True,
        "tiepnhan": True,
        "cskh": True,
        "kho": True,
        "baocao": True,
        "pos": True,
        "nhansu": True,
        "invoices": True,
        "audit": True,
        "settings": True,
    },
    "Lễ tân": {
        "dashboard": True,
        "web": True,
        "crm": True,
        "tiepnhan": True,
        "cskh": True,
        "kho": False,
        "baocao": False,
        "pos": True,
        "nhansu": False,
        "invoices": True,
        "audit": False,
        "settings": False,
    },
}

DEFAULT_ACTION_PERMISSIONS = {
    "Quản lý": {
        "web.accept": True,
        "web.reject": True,
        "crm.create": True,
        "crm.edit": True,
        "crm.delete": True,
        "pos.apply_discount": True,
        "pos.checkout": True,
        "invoices.export": True,
        "baocao.export_excel": True,
        "baocao.export_pdf": True,
        "rbac.edit": True,
    },
    "Lễ tân": {
        "web.accept": True,
        "web.reject": True,
        "crm.create": True,
        "crm.edit": True,
        "crm.delete": False,
        "pos.apply_discount": True,
        "pos.checkout": True,
        "invoices.export": True,
        "baocao.export_excel": False,
        "baocao.export_pdf": False,
        "rbac.edit": False,
    },
}

FUNCTION_TO_SECTION_KEY = {
    "Tổng quan/KPI": "dashboard",
    "Đặt lịch web": "web",
    "Khách hàng (CRM)": "crm",
    "Tiếp nhận xe/Lệnh dịch vụ": "tiepnhan",
    "Chăm sóc khách hàng": "cskh",
    "Bán hàng POS": "pos",
    "Quản lý hóa đơn": "invoices",
    "Kho & Vật tư": "kho",
    "Báo cáo thống kê": "baocao",
    "Cài đặt hệ thống": "settings",
    "Quản lý nhân sự": "nhansu",
    "Nhật ký hệ thống": "audit",
}


def _default_payload():
    return {"sections": DEFAULT_SECTION_PERMISSIONS, "actions": DEFAULT_ACTION_PERMISSIONS}


def load_permissions():
    if not RBAC_PATH.exists():
        return _default_payload()
    try:
        raw = json.loads(RBAC_PATH.read_text(encoding="utf-8"))
        payload = _default_payload()
        if isinstance(raw, dict):
            if isinstance(raw.get("sections"), dict):
                payload["sections"].update(raw["sections"])
            if isinstance(raw.get("actions"), dict):
                payload["actions"].update(raw["actions"])
        return payload
    except Exception:
        return _default_payload()


def save_section_permissions(section_permissions):
    payload = load_permissions()
    payload["sections"] = section_permissions
    RBAC_PATH.parent.mkdir(parents=True, exist_ok=True)
    RBAC_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def allowed_sections_for_role(role):
    payload = load_permissions()
    role_map = payload.get("sections", {}).get(role, {})
    return {k for k, v in role_map.items() if bool(v)}


def can_access_section(role, section_key):
    return section_key in allowed_sections_for_role(role)


def can_do(role, action_key):
    payload = load_permissions()
    actions = payload.get("actions", {}).get(role, {})
    if action_key in actions:
        return bool(actions[action_key])
    return role == "Quản lý"
