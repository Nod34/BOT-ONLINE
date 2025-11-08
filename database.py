import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DATABASE_FILE = "database.json"

def load() -> Dict[str, Any]:
    """
    Carrega o banco de dados JSON.
    
    Returns:
        Dict com estrutura do banco de dados
    """
    if not os.path.exists(DATABASE_FILE):
        return {
            "participants": {},
            "bonus_roles": {},
            "hashtag": {
                "value": None,
                "locked": False
            },
            "tag": {
                "enabled": False,
                "text": None,
                "quantity": 1
            },
            "inscricao_channel": None,
            # agora armazena lista de message_ids (retrocompatível com single)
            "button_message_id": [],
            "inscricoes_closed": False,
            "blacklist": {},
            "chat_lock": {
                "enabled": False,
                "channel_id": None
            },
            "moderators": []
        }
    
    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar database: {e}")
        return load()

def save(data: Dict[str, Any]) -> bool:
    """
    Salva o banco de dados JSON.
    
    Args:
        data: Dicionário com os dados a serem salvos
        
    Returns:
        True se salvou com sucesso, False caso contrário
    """
    try:
        with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar database: {e}")
        return False

def add_participant(user_id: int, first_name: str, last_name: str, 
                   tickets: Dict[str, Any], message_id: Optional[int] = None) -> bool:
    """
    Adiciona um participante ao banco de dados.
    
    Args:
        user_id: ID do usuário Discord
        first_name: Primeiro nome
        last_name: Sobrenome
        tickets: Dicionário com informações de fichas
        message_id: ID da mensagem de inscrição
        
    Returns:
        True se adicionou com sucesso
    """
    data = load()
    # garante estrutura mínima de tickets
    tickets = tickets or {}
    if "base" not in tickets:
        tickets.setdefault("base", 1)
    data["participants"][str(user_id)] = {
        "first_name": first_name,
        "last_name": last_name,
        "tickets": tickets,
        "message_id": message_id,
        "timestamp": datetime.now().isoformat()
    }
    return save(data)

def remove_participant(user_id: int) -> bool:
    """
    Remove um participante do banco de dados.
    
    Args:
        user_id: ID do usuário Discord
        
    Returns:
        True se removeu com sucesso
    """
    data = load()
    if str(user_id) in data["participants"]:
        del data["participants"][str(user_id)]
        return save(data)
    return False

def get_participant(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtém os dados de um participante.
    
    Args:
        user_id: ID do usuário Discord
        
    Returns:
        Dict com dados do participante ou None se não encontrado
    """
    data = load()
    return data["participants"].get(str(user_id))

def get_all_participants() -> Dict[str, Any]:
    """
    Obtém todos os participantes.
    
    Returns:
        Dict com todos os participantes
    """
    data = load()
    return data["participants"]

def is_registered(user_id: int) -> bool:
    """
    Verifica se um usuário está registrado.
    
    Args:
        user_id: ID do usuário Discord
        
    Returns:
        True se está registrado
    """
    data = load()
    return str(user_id) in data["participants"]

def is_name_taken(first_name: str, last_name: str, exclude_user_id: Optional[int] = None) -> bool:
    """
    Verifica se um nome completo já foi registrado.
    
    Args:
        first_name: Primeiro nome
        last_name: Sobrenome
        exclude_user_id: ID de usuário a excluir da verificação
        
    Returns:
        True se o nome já está em uso
    """
    data = load()
    for user_id, participant in data["participants"].items():
        if exclude_user_id and str(exclude_user_id) == user_id:
            continue
        if (participant["first_name"].lower() == first_name.lower() and 
            participant["last_name"].lower() == last_name.lower()):
            return True
    return False

def add_bonus_role(role_id: int, quantity: int, abbreviation: str) -> bool:
    """
    Adiciona um cargo bônus.
    
    Args:
        role_id: ID do cargo
        quantity: Quantidade de fichas do cargo
        abbreviation: Abreviação do cargo
        
    Returns:
        True se adicionou com sucesso
    """
    data = load()
    data["bonus_roles"][str(role_id)] = {
        "quantity": quantity,
        "abbreviation": abbreviation
    }
    return save(data)

def remove_bonus_role(role_id: int) -> bool:
    """
    Remove um cargo bônus.
    
    Args:
        role_id: ID do cargo
        
    Returns:
        True se removeu com sucesso
    """
    data = load()
    if str(role_id) in data["bonus_roles"]:
        del data["bonus_roles"][str(role_id)]
        return save(data)
    return False

def get_bonus_roles() -> Dict[str, Any]:
    """
    Obtém todos os cargos bônus.
    
    Returns:
        Dict com todos os cargos bônus
    """
    data = load()
    return data["bonus_roles"]

def set_hashtag(hashtag: str, locked: bool = False) -> bool:
    """
    Define a hashtag obrigatória.
    
    Args:
        hashtag: Texto da hashtag
        locked: Se deve bloquear alterações
        
    Returns:
        True se definiu com sucesso
    """
    data = load()
    if data["hashtag"]["locked"] and not locked:
        return False
    data["hashtag"]["value"] = hashtag
    data["hashtag"]["locked"] = locked
    return save(data)

def lock_hashtag(locked: bool = True) -> bool:
    """
    Bloqueia/desbloqueia a hashtag.
    
    Args:
        locked: True para bloquear, False para desbloquear
        
    Returns:
        True se atualizou com sucesso
    """
    data = load()
    data["hashtag"]["locked"] = locked
    return save(data)

def get_hashtag() -> Optional[str]:
    """
    Obtém a hashtag configurada.
    
    Returns:
        String da hashtag ou None
    """
    data = load()
    return data["hashtag"]["value"]

def is_hashtag_locked() -> bool:
    """
    Verifica se a hashtag está bloqueada.
    
    Returns:
        True se está bloqueada
    """
    data = load()
    return data["hashtag"]["locked"]

def set_tag(enabled: bool, text: Optional[str] = None, quantity: int = 1) -> bool:
    """
    Configura a tag do servidor.
    
    Args:
        enabled: Se a tag está habilitada
        text: Texto da tag
        quantity: Quantidade de fichas da tag
        
    Returns:
        True se configurou com sucesso
    """
    data = load()
    data["tag"]["enabled"] = enabled
    if text is not None:
        data["tag"]["text"] = text
    data["tag"]["quantity"] = quantity
    return save(data)

def get_tag() -> Dict[str, Any]:
    """
    Obtém a configuração da tag do servidor.
    
    Returns:
        Dict com enabled, text e quantity
    """
    data = load()
    return data["tag"]

def set_inscricao_channel(channel_id: Optional[int]) -> bool:
    """
    Define o canal de inscrições.
    
    Args:
        channel_id: ID do canal
        
    Returns:
        True se definiu com sucesso
    """
    data = load()
    data["inscricao_channel"] = channel_id
    return save(data)

def get_inscricao_channel() -> Optional[int]:
    """
    Obtém o ID do canal de inscrições.
    
    Returns:
        ID do canal ou None
    """
    data = load()
    return data["inscricao_channel"]

# button message helpers (suporta múltiplos IDs)
def add_button_message_id(message_id: int) -> bool:
    """
    Adiciona um ID de mensagem à lista de mensagens do botão de inscrição.
    
    Args:
        message_id: ID da mensagem a ser adicionada
        
    Returns:
        True se adicionou com sucesso
    """
    data = load()
    mids = data.get("button_message_id", [])
    if not isinstance(mids, list):
        # compatibilidade: transforma single em lista
        mids = [mids] if mids else []
    if str(message_id) not in [str(x) for x in mids]:
        mids.append(int(message_id))
    data["button_message_id"] = mids
    return save(data)

def set_button_message_id(message_id: Optional[int]) -> bool:
    """
    Define o ID da mensagem com o botão de inscrição.
    
    Args:
        message_id: ID da mensagem
        
    Returns:
        True se definiu com sucesso
    """
    data = load()
    data["button_message_id"] = message_id
    return save(data)

def get_button_message_id() -> Any:
    """
    Obtém o(s) ID(s) da mensagem com o botão de inscrição.
    
    Returns:
        ID da mensagem ou lista de IDs
    """
    data = load()
    return data.get("button_message_id")

def set_inscricoes_closed(enabled: bool) -> bool:
    """
    Define se as inscrições estão fechadas.
    
    Args:
        enabled: True para fechar inscrições, False para abrir
        
    Returns:
        True se atualizou com sucesso
    """
    data = load()
    data["inscricoes_closed"] = bool(enabled)
    return save(data)

def get_inscricoes_closed() -> bool:
    """
    Verifica se as inscrições estão fechadas.
    
    Returns:
        True se estão fechadas
    """
    data = load()
    return bool(data.get("inscricoes_closed", False))

def add_to_blacklist(user_id: int, reason: str, banned_by: int) -> bool:
    """
    Adiciona um usuário à blacklist.
    
    Args:
        user_id: ID do usuário
        reason: Motivo do banimento
        banned_by: ID de quem baniu
        
    Returns:
        True se adicionou com sucesso
    """
    data = load()
    data["blacklist"][str(user_id)] = {
        "reason": reason,
        "banned_by": banned_by,
        "timestamp": datetime.now().isoformat()
    }
    return save(data)

def remove_from_blacklist(user_id: int) -> bool:
    """
    Remove um usuário da blacklist.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        True se removeu com sucesso
    """
    data = load()
    if str(user_id) in data["blacklist"]:
        del data["blacklist"][str(user_id)]
        return save(data)
    return False

def get_blacklist() -> Dict[str, Any]:
    """
    Obtém a blacklist completa.
    
    Returns:
        Dict com usuários na blacklist
    """
    data = load()
    return data["blacklist"]

def is_blacklisted(user_id: int) -> bool:
    """
    Verifica se um usuário está na blacklist.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        True se está na blacklist
    """
    data = load()
    return str(user_id) in data["blacklist"]

def set_chat_lock(enabled: bool, channel_id: Optional[int] = None) -> bool:
    """
    Configura o bloqueio de chat.
    
    Args:
        enabled: Se o bloqueio está ativado
        channel_id: ID do canal a ser bloqueado
        
    Returns:
        True se configurou com sucesso
    """
    data = load()
    data["chat_lock"]["enabled"] = enabled
    if channel_id is not None:
        data["chat_lock"]["channel_id"] = channel_id
    return save(data)

def get_chat_lock() -> Dict[str, Any]:
    """
    Obtém a configuração de bloqueio de chat.
    
    Returns:
        Dict com enabled e channel_id
    """
    data = load()
    return data["chat_lock"]

def clear_participants():
    """
    Limpa apenas os participantes do sorteio, preservando quaisquer TAGs manuais.
    Move manual_tag encontradas em participantes para _db['manual_tags'] antes de limpar.
    """
    # garante estrutura
    manual_tags = _db.get("manual_tags", {}).copy() if isinstance(_db.get("manual_tags", {}), dict) else {}

    # extrai manual_tag dos participantes existentes (se houver)
    for user_id, data in list(_db.get("participants", {}).items()):
        try:
            tag_amount = data.get("tickets", {}).get("manual_tag")
            if tag_amount:
                manual_tags[str(user_id)] = int(tag_amount)
        except Exception:
            continue

    # persiste manual_tags e limpa participantes
    if manual_tags:
        _db["manual_tags"] = manual_tags
    _db["participants"] = {}

def clear_all():
    """
    Reseta o DB mantendo somente as TAGs manuais (se existirem).
    """
    # coleta manual_tags atuais e também dos participantes (por segurança)
    manual_tags = _db.get("manual_tags", {}).copy() if isinstance(_db.get("manual_tags", {}), dict) else {}

    for user_id, data in list(_db.get("participants", {}).items()):
        try:
            tag_amount = data.get("tickets", {}).get("manual_tag")
            if tag_amount:
                manual_tags[str(user_id)] = int(tag_amount)
        except Exception:
            continue

    # limpa tudo e inicializa defaults
    _db.clear()
    _init_db()

    # restaura manual_tags se houver
    if manual_tags:
        _db["manual_tags"] = manual_tags

def get_statistics() -> Dict[str, Any]:
    """
    Obtém estatísticas do banco de dados.
    
    Returns:
        Dict com estatísticas
    """
    data = load()
    participants = data["participants"]
    
    total_participants = len(participants)
    total_tickets = 0
    tickets_by_role = {}
    participants_with_tag = 0
    
    for participant in participants.values():
        tickets = participant.get("tickets", {})
        # base
        base = tickets.get("base", 1)
        total_tickets += base
        
        # roles
        if "roles" in tickets:
            for role_id, role_data in tickets["roles"].items():
                if role_id not in tickets_by_role:
                    tickets_by_role[role_id] = {
                        "count": 0,
                        "total_tickets": 0,
                        "abbreviation": role_data.get("abbreviation", "?")
                    }
                tickets_by_role[role_id]["count"] += 1
                tickets_by_role[role_id]["total_tickets"] += role_data.get("quantity", 0)
                total_tickets += role_data.get("quantity", 0)
        
        # tag automatic
        tag_amount = tickets.get("tag", 0)
        if tag_amount > 0:
            participants_with_tag += 1
            total_tickets += tag_amount
        
        # manual tag
        manual = tickets.get("manual_tag", 0)
        if manual and manual > 0:
            # if manual_tag present we also count as participant with tag (avoid double count)
            if tag_amount == 0:
                participants_with_tag += 1
            total_tickets += manual
    
    return {
        "total_participants": total_participants,
        "total_tickets": total_tickets,
        "tickets_by_role": tickets_by_role,
        "participants_with_tag": participants_with_tag,
        "blacklist_count": len(data.get("blacklist", {}))
    }

def update_tickets(user_id: int, tickets: Dict[str, Any]) -> bool:
    """
    Atualiza as fichas de um participante.
    
    Args:
        user_id: ID do usuário
        tickets: Novo dicionário de fichas
        
    Returns:
        True se atualizou com sucesso
    """
    data = load()
    if str(user_id) in data["participants"]:
        data["participants"][str(user_id)]["tickets"] = tickets
        return save(data)
    return False

def add_moderator(user_id: int) -> bool:
    """
    Adiciona um moderador.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        True se adicionou com sucesso
    """
    data = load()
    if "moderators" not in data:
        data["moderators"] = []
    if str(user_id) not in data["moderators"]:
        data["moderators"].append(str(user_id))
        return save(data)
    return False

def remove_moderator(user_id: int) -> bool:
    """
    Remove um moderador.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        True se removeu com sucesso
    """
    data = load()
    if "moderators" not in data:
        data["moderators"] = []
    if str(user_id) in data["moderators"]:
        data["moderators"].remove(str(user_id))
        return save(data)
    return False

def get_moderators() -> List[str]:
    """
    Obtém a lista de moderadores.
    
    Returns:
        Lista de IDs de moderadores
    """
    data = load()
    return data.get("moderators", [])

def is_moderator(user_id: int) -> bool:
    """
    Verifica se um usuário é moderador.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        True se é moderador
    """
    data = load()
    return str(user_id) in data.get("moderators", [])

# MANUAL TAG helpers (guardam quantidade em tickets.manual_tag)
def set_manual_tag(user_id: int, quantity: int) -> bool:
    """
    Define fichas de TAG manual para um participante.
    
    Args:
        user_id: ID do usuário
        quantity: Quantidade de fichas de TAG manual
        
    Returns:
        True se definiu com sucesso
    """
    data = load()
    if str(user_id) not in data["participants"]:
        return False
    tickets = data["participants"][str(user_id)].get("tickets", {})
    tickets["manual_tag"] = int(quantity)
    data["participants"][str(user_id)]["tickets"] = tickets
    return save(data)

def remove_manual_tag(user_id: int) -> bool:
    """
    Remove a TAG manual de um participante.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        True se removeu com sucesso
    """
    data = load()
    if str(user_id) not in data["participants"]:
        return False
    tickets = data["participants"][str(user_id)].get("tickets", {})
    if "manual_tag" in tickets:
        del tickets["manual_tag"]
    data["participants"][str(user_id)]["tickets"] = tickets
    return save(data)

def has_manual_tag(user_id: int) -> bool:
    """
    Verifica se um participante tem TAG manual.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        True se tem TAG manual
    """
    data = load()
    participant = data["participants"].get(str(user_id))
    if not participant:
        return False
    return bool(participant.get("tickets", {}).get("manual_tag", 0))
