import re
import discord
from typing import Dict, Any, List, Optional

def _clean_text(s: Optional[str]) -> str:
    if not s:
        return ""
    # remove emojis/caracteres especiais mantendo letras/números/espacos
    return re.sub(r'[^\w\s]', '', s).strip().casefold()

def calculate_tickets(
    member: discord.abc.User,
    bonus_roles: Dict[str, Any],
    tag_enabled: bool,
    tag_text: Optional[str],
    tag_quantity: int,
    manual_tag: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calcula o dicionário de 'tickets' para um membro.
    - bonus_roles: dict do DB com keys = role_id (str) -> {quantity, abbreviation}
    - Detecta TAGs tanto em nomes (nick/display/global/name) quanto em roles (role.name).
    - Se manual_tag for fornecido, ele será incluído em tickets['manual_tag'] (útil ao recalcular).
    """
    tickets: Dict[str, Any] = {}
    tickets["base"] = 1

    # roles -> armazena por id string com quantity e abbreviation
    roles_dict: Dict[str, Dict[str, Any]] = {}
    try:
        member_roles = getattr(member, "roles", []) or []
        for r in member_roles:
            rid = str(r.id)
            if str(r.id) in bonus_roles or rid in bonus_roles:
                entry = bonus_roles.get(rid) or bonus_roles.get(str(r.id))
                if entry:
                    roles_dict[rid] = {
                        "quantity": int(entry.get("quantity", 0)),
                        "abbreviation": entry.get("abbreviation", "")
                    }
    except Exception:
        # membro pode ser discord.User (sem roles) — ignora roles
        member_roles = []

    if roles_dict:
        tickets["roles"] = roles_dict

    # Detecção da TAG automática em vários campos do membro
    found = False
    if tag_enabled and tag_text:
        tag_search = tag_text.strip()
        tag_clean = _clean_text(tag_search)

        # 1) checa nomes (display_name, nick, global_name, name)
        checks = []
        if hasattr(member, "display_name"):
            checks.append(getattr(member, "display_name", "") or "")
        if hasattr(member, "nick"):
            checks.append(getattr(member, "nick", "") or "")
        if hasattr(member, "global_name"):
            checks.append(getattr(member, "global_name", "") or "")
        checks.append(getattr(member, "name", "") or "")

        for field in checks:
            if not field:
                continue
            f_raw = field.strip().casefold()
            f_clean = _clean_text(field)
            if tag_search.casefold() in f_raw or (tag_clean and tag_clean in f_clean):
                found = True
                break

        # 2) se não achou nos nomes, checa roles (role.name)
        if not found:
            try:
                for r in member_roles:
                    rn = (r.name or "").strip()
                    if not rn:
                        continue
                    # compara exatidão ou substring, case-insensitive
                    if tag_search.casefold() == rn.casefold() or tag_search.casefold() in rn.casefold():
                        found = True
                        break
            except Exception:
                pass

        if found:
            tickets["tag"] = int(tag_quantity or 1)

    # Mescla manual_tag se fornecido (útil ao recalcular mantendo o valor manual do DB)
    if manual_tag is not None and int(manual_tag) > 0:
        tickets["manual_tag"] = int(manual_tag)

    return tickets

def get_total_tickets(tickets: Optional[Dict[str, Any]]) -> int:
    if not tickets:
        return 1
    total = int(tickets.get("base", 1))
    # roles
    for role_info in tickets.get("roles", {}).values():
        try:
            total += int(role_info.get("quantity", 0))
        except Exception:
            pass
    # tag automatic
    total += int(tickets.get("tag", 0))
    # tag manual (se existir)
    total += int(tickets.get("manual_tag", 0))
    return max(1, total)

def format_tickets_list(tickets: Optional[Dict[str, Any]], guild: Optional[discord.Guild]) -> List[str]:
    lines: List[str] = []
    if not tickets:
        lines.append("• Ficha base: 1")
        return lines

    lines.append("• Ficha base: 1")

    # cargos (mantém abreviação se presente)
    roles = tickets.get("roles", {})
    for rid, info in roles.items():
        qty = info.get("quantity", 0)
        abbr = info.get("abbreviation", "")
        try:
            if guild:
                role_obj = guild.get_role(int(rid))
                role_name = role_obj.name if role_obj else f"Cargo ({rid})"
            else:
                role_name = f"Cargo ({rid})"
        except Exception:
            role_name = f"Cargo ({rid})"
        lines.append(f"• {qty} ficha(s) por cargo: {role_name} {f'({abbr})' if abbr else ''}".strip())

    # TAG automática
    tag_amount = tickets.get("tag", 0)
    if tag_amount:
        lines.append(f"• Fichas da TAG: {tag_amount}")

    # TAG manual (agora exibe como TAG normal)
    manual = tickets.get("manual_tag", 0)
    if manual:
        lines.append(f"• Fichas da TAG: {manual}")

    return lines

def format_detailed_entry(first_name: str, last_name: str, tickets: Dict[str, Any], guild: Optional[discord.Guild] = None) -> List[str]:
    """
    Formata uma entrada detalhada usada em /lista com_fichas e /exportar com_fichas.
    Gera:
      Nome Completo
      Nome Completo <SUFIXO_DO_CARGO_1>
      Nome Completo TAG
      ...
    Não adiciona linhas em branco entre participantes.
    """
    lines: List[str] = []
    name = f"{first_name} {last_name}".strip()
    # linha base (sempre)
    lines.append(name)

    # cargos: uma linha por cargo (usa abreviação se existir, senão nome do cargo quando guild for fornecido)
    roles = tickets.get("roles", {}) if tickets else {}
    for rid, info in roles.items():
        abbr = (info.get("abbreviation") or "").strip()
        suffix = abbr if abbr else None
        if not suffix:
            if guild:
                try:
                    role_obj = guild.get_role(int(rid))
                    suffix = role_obj.name if role_obj else f"Cargo_{rid}"
                except Exception:
                    suffix = f"Cargo_{rid}"
            else:
                suffix = f"Cargo_{rid}"
        lines.append(f"{name} {suffix}")

    # TAG automática (aparece como uma linha separada)
    if tickets and int(tickets.get("tag", 0)) > 0:
        lines.append(f"{name} TAG")

    # TAG manual (também aparece como linha separada)
    if tickets and int(tickets.get("manual_tag", 0)) > 0:
        # se já existe TAG automática e você não quer duplicar, remova a checagem abaixo
        # aqui adicionamos sempre que manual_tag estiver presente
        lines.append(f"{name} TAG")

    return lines

def validate_full_name(first_name: str, last_name: str) -> tuple:
    """
    Valida primeiro e último nome inseridos no modal.
    Retorna (True, "") se válido ou (False, "mensagem de erro") se inválido.
    Regras:
      - não vazios
      - pelo menos 2 caracteres cada
      - sem dígitos
      - comprimento total razoável (<= 100)
    """
    if not first_name or not last_name:
        return False, "❌ Primeiro nome e sobrenome são obrigatórios."
    fn = first_name.strip()
    ln = last_name.strip()
    if len(fn) < 2 or len(ln) < 2:
        return False, "❌ Nome e sobrenome devem ter ao menos 2 caracteres."
    if len(fn) + len(ln) > 100:
        return False, "❌ Nome muito longo."
    for ch in fn + ln:
        if ch.isdigit():
            return False, "❌ Nomes não podem conter números."
    # opcional: outros caracteres permitidos: letras, espaços, - . '
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZáàâãäéèêëíìîïóòôõöúùûüçÇÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜ-' .")
    for ch in fn + ln:
        if ch not in allowed and not ch.isspace():
            return False, "❌ Caractere inválido no nome."
    return True, ""
