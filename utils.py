import re
from typing import Dict, List, Any, Optional
import discord
import logging

logger = logging.getLogger(__name__)

def validate_name(name: str, field_name: str = "Nome") -> tuple[bool, Optional[str]]:
    """
    Valida um nome (primeiro nome ou sobrenome).
    
    Regras:
    - Sem números
    - Sem caracteres especiais (exceto espaços, hífens e apóstrofos)
    - Mínimo 2 caracteres
    - Apenas letras
    
    Args:
        name: Nome a ser validado
        field_name: Nome do campo (para mensagens de erro)
        
    Returns:
        Tupla (válido: bool, mensagem_erro: Optional[str])
    """
    if not name or len(name.strip()) < 2:
        return False, f"❌ {field_name} deve ter pelo menos 2 caracteres."
    
    # Verificar números
    if any(char.isdigit() for char in name):
        return False, f"❌ {field_name} não pode conter números."
    
    # Verificar caracteres especiais inválidos
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZáàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ '-")
    if not all(char in allowed_chars for char in name):
        return False, f"❌ {field_name} contém caracteres inválidos. Use apenas letras."
    
    # Verificar se tem pelo menos uma letra
    if not any(char.isalpha() for char in name):
        return False, f"❌ {field_name} deve conter pelo menos uma letra."
    
    # Verificar partes do nome
    parts = name.strip().split()
    for part in parts:
        # Remover hífens e apóstrofos para validação
        clean_part = part.replace("-", "").replace("'", "")
        if len(clean_part) < 2:
            return False, f"❌ Cada parte do {field_name.lower()} deve ter pelo menos 2 letras."
    
    return True, None

def validate_full_name(first_name: str, last_name: str) -> tuple[bool, Optional[str]]:
    """
    Valida nome completo (primeiro nome + sobrenome).
    
    Args:
        first_name: Primeiro nome
        last_name: Sobrenome
        
    Returns:
        Tupla (válido: bool, mensagem_erro: Optional[str])
    """
    valid_first, error_first = validate_name(first_name, "Primeiro nome")
    if not valid_first:
        return False, error_first
    
    valid_last, error_last = validate_name(last_name, "Sobrenome")
    if not valid_last:
        return False, error_last
    
    return True, None

def calculate_tickets(member: discord.Member, bonus_roles: Dict[str, Any], 
                     tag_enabled: bool, server_tag: Optional[str], 
                     tag_quantity: int) -> Dict[str, Any]:
    """
    Calcula as fichas de um participante.
    
    Estrutura de retorno:
    {
        'base': 1,
        'roles': {
            'role_id': {
                'quantity': n,
                'abbreviation': 'AB'
            }
        },
        'tag': n
    }
    
    Args:
        member: Membro do Discord
        bonus_roles: Dict com cargos bônus configurados
        tag_enabled: Se a tag do servidor está habilitada
        server_tag: Texto da tag do servidor
        tag_quantity: Quantidade de fichas da tag
        
    Returns:
        Dict com estrutura de fichas
    """
    tickets = {
        "base": 1,
        "roles": {},
        "tag": 0
    }
    
    member_role_ids = [str(role.id) for role in member.roles]
    
    for role_id, role_data in bonus_roles.items():
        if role_id in member_role_ids:
            tickets["roles"][role_id] = {
                "quantity": role_data["quantity"],
                "abbreviation": role_data["abbreviation"]
            }
    
    if tag_enabled and server_tag:
        # Prepara a tag para busca (remove espaços e normaliza)
        tag_search_original = server_tag.strip().lower()
        
        # Cria variações da TAG (com e sem emojis)
        # Remove emojis/caracteres especiais para criar versão "limpa"
        import re
        # Remove emojis e caracteres especiais, mantendo apenas letras/números
        tag_search_clean = re.sub(r'[^\w\s]', '', tag_search_original).strip()
        
        # Lista de variações para buscar
        tag_variations = [tag_search_original]
        if tag_search_clean and tag_search_clean != tag_search_original:
            tag_variations.append(tag_search_clean)
        
        # Lista TODOS os campos possíveis onde a TAG pode aparecer
        names_to_check = [
            ("display_name", member.display_name),      # Nome visual (principal no Discord moderno)
            ("nick", member.nick),                      # Apelido do servidor (Server Nickname)
            ("global_name", member.global_name),        # Nome global do Discord
            ("name", member.name),                      # Nome de usuário (@username)
        ]
        
        # Log detalhado para debug
        logger.info(f"╔══════════════════════════════════════════════════════════")
        logger.info(f"║ TAG CHECK - Iniciando verificação")
        logger.info(f"║ Usuário: {member.name} (ID: {member.id})")
        logger.info(f"║ TAG configurada: '{server_tag}'")
        logger.info(f"║ Buscando variações: {tag_variations}")
        logger.info(f"║ Quantidade de fichas: {tag_quantity}")
        logger.info(f"╠══════════════════════════════════════════════════════════")
        
        tag_found = False
        found_variation = None
        
        # Verifica em cada campo
        for field_name, field_value in names_to_check:
            if field_value is None:
                logger.info(f"║ {field_name}: [NULL]")
                continue
            
            # Normaliza o campo
            field_normalized = field_value.strip().lower()
            
            # Testa todas as variações
            contains_tag = False
            for variation in tag_variations:
                if variation in field_normalized:
                    contains_tag = True
                    found_variation = variation
                    break
            
            logger.info(f"║ {field_name}: '{field_value}'")
            logger.info(f"║   → Normalizado: '{field_normalized}'")
            logger.info(f"║   → TAG encontrada? {'✅ SIM' if contains_tag else '❌ NÃO'}")
            if contains_tag:
                logger.info(f"║   → Variação detectada: '{found_variation}'")
            
            if contains_tag:
                tickets["tag"] = tag_quantity
                tag_found = True
                logger.info(f"║ ✅ TAG ENCONTRADA em '{field_name}' (variação: '{found_variation}')!")
                logger.info(f"║ ✅ +{tag_quantity} ficha(s) concedida(s)!")
                break
        
        if not tag_found:
            logger.info(f"║ ❌ TAG NÃO ENCONTRADA em nenhum campo")
            logger.info(f"║ 💡 Aceita qualquer variação: {tag_variations}")
        
        logger.info(f"║ Fichas da TAG concedidas: {tickets['tag']}")
        logger.info(f"╚══════════════════════════════════════════════════════════")
    
    return tickets

def get_total_tickets(tickets_dict: Dict[str, Any]) -> int:
    """
    Soma o total de fichas de um dicionário de tickets.
    
    Args:
        tickets_dict: Dicionário com estrutura de fichas
        
    Returns:
        Total de fichas
    """
    total = tickets_dict.get("base", 1)
    
    if "roles" in tickets_dict:
        for role_data in tickets_dict["roles"].values():
            total += role_data.get("quantity", 0)
    
    total += tickets_dict.get("tag", 0)
    
    return total

def format_tickets_list(tickets_dict: Dict[str, Any], guild: Optional[discord.Guild] = None) -> List[str]:
    """
    Formata a lista de fichas para exibição.
    
    Args:
        tickets_dict: Dicionário com estrutura de fichas
        guild: Guild do Discord (para obter nomes dos cargos)
        
    Returns:
        Lista de strings formatadas
    """
    lines = []
    
    base = tickets_dict.get("base", 1)
    lines.append(f"🎫 **Ficha base**: {base}")
    
    if "roles" in tickets_dict and tickets_dict["roles"]:
        lines.append(f"\n**Fichas por cargo**:")
        for role_id, role_data in tickets_dict["roles"].items():
            quantity = role_data.get("quantity", 0)
            abbreviation = role_data.get("abbreviation", "?")
            
            role_name = abbreviation
            if guild:
                role = guild.get_role(int(role_id))
                if role:
                    role_name = f"{role.name} ({abbreviation})"
            
            lines.append(f"  • {role_name}: {quantity} ficha(s)")
    
    tag_tickets = tickets_dict.get("tag", 0)
    if tag_tickets > 0:
        lines.append(f"\n🏷️ **Fichas da TAG**: {tag_tickets}")
    
    return lines

def format_detailed_entry(first_name: str, last_name: str, tickets_dict: Dict[str, Any]) -> List[str]:
    """
    Formata uma entrada detalhada para exportação.
    
    Formato:
    - "PrimeiroNome primeiras2letras." — ficha base
    - "PrimeiroNome primeiras2letras. AB" — para cada ficha de cargo
    - "PrimeiroNome primeiras2letras. TAG" — para cada ficha de tag
    
    Args:
        first_name: Primeiro nome
        last_name: Sobrenome
        tickets_dict: Dicionário com estrutura de fichas
        
    Returns:
        Lista de strings (uma por ficha)
    """
    entries = []
    
    # Primeiras 2 letras do sobrenome em minúsculas
    first_two = last_name[:2].lower() if len(last_name) >= 2 else last_name.lower()
    base_name = f"{first_name} {first_two}."
    
    base = tickets_dict.get("base", 1)
    for _ in range(base):
        entries.append(base_name)
    
    if "roles" in tickets_dict:
        for role_data in tickets_dict["roles"].values():
            quantity = role_data.get("quantity", 0)
            abbreviation = role_data.get("abbreviation", "?")
            for _ in range(quantity):
                entries.append(f"{base_name} {abbreviation}")
    
    tag_tickets = tickets_dict.get("tag", 0)
    for _ in range(tag_tickets):
        entries.append(f"{base_name} TAG")
    
    return entries

def format_simple_entry(first_name: str, last_name: str) -> str:
    """
    Formata uma entrada simples para exportação.
    
    Args:
        first_name: Primeiro nome
        last_name: Sobrenome
        
    Returns:
        String formatada: "PrimeiroNome Sobrenome"
    """
    return f"{first_name} {last_name}"

def create_embed(title: str, description: str, color: discord.Color = discord.Color.blue()) -> discord.Embed:
    """
    Cria um embed Discord.
    
    Args:
        title: Título do embed
        description: Descrição do embed
        color: Cor do embed
        
    Returns:
        discord.Embed
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    return embed

def parse_color(color_str: str) -> discord.Color:
    """
    Converte uma string de cor em discord.Color.
    
    Args:
        color_str: String da cor (hex, nome, etc)
        
    Returns:
        discord.Color
    """
    color_str = color_str.lower().strip()
    
    color_map = {
        "azul": discord.Color.blue(),
        "vermelho": discord.Color.red(),
        "verde": discord.Color.green(),
        "amarelo": discord.Color.gold(),
        "roxo": discord.Color.purple(),
        "rosa": discord.Color.magenta(),
        "laranja": discord.Color.orange(),
        "preto": discord.Color.from_rgb(0, 0, 0),
        "branco": discord.Color.from_rgb(255, 255, 255),
    }
    
    if color_str in color_map:
        return color_map[color_str]
    
    if color_str.startswith("#"):
        try:
            hex_color = color_str[1:]
            return discord.Color(int(hex_color, 16))
        except ValueError:
            return discord.Color.blue()
    
    return discord.Color.blue()

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Trunca um texto se exceder o tamanho máximo.
    
    Args:
        text: Texto a ser truncado
        max_length: Tamanho máximo
        
    Returns:
        Texto truncado
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
