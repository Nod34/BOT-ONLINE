import database as db
import discord
import os
import logging
import utils
from datetime import datetime
from discord import app_commands
from discord.ext import commands
from threading import Thread
from flask import Flask, jsonify
from dotenv import load_dotenv

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot Discord está online e rodando!", 200

@app.route('/health')
def health():
    # tenta pegar objeto do bot (suporta tanto 'bot' quanto 'client')
    bot_obj = None
    for name in ('bot', 'client'):
        obj = globals().get(name)
        if obj:
            bot_obj = obj
            break
    bot_name = "connecting"
    try:
        if bot_obj and getattr(bot_obj, "user", None):
            bot_name = bot_obj.user.name
    except Exception:
        bot_name = "connecting"
    return jsonify({"status": "healthy", "bot": bot_name}), 200

def run_flask():
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

load_dotenv()

# Adição: imports de typing (se ainda não existirem) e criação da instância do bot
from typing import Optional, Literal

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InscricaoModal(discord.ui.Modal, title="Inscrição no Sorteio"):
    primeiro_nome = discord.ui.TextInput(
        label="Primeiro Nome",
        placeholder="Digite seu primeiro nome",
        required=True,
        max_length=50
    )
    
    sobrenome = discord.ui.TextInput(
        label="Sobrenome",
        placeholder="Digite seu sobrenome",
        required=True,
        max_length=50
    )
    
    hashtag = discord.ui.TextInput(
        label="Hashtag",
        placeholder="Digite a hashtag obrigatória",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            if db.is_blacklisted(interaction.user.id):
                await interaction.followup.send(
                    "❌ Você está na blacklist e não pode se inscrever.",
                    ephemeral=True
                )
                return
            
            first_name = self.primeiro_nome.value.strip()
            last_name = self.sobrenome.value.strip()
            hashtag_input = self.hashtag.value.strip()
            
            valid, error_msg = utils.validate_full_name(first_name, last_name)
            if not valid:
                await interaction.followup.send(error_msg, ephemeral=True)
                return
            
            if db.is_name_taken(first_name, last_name):
                await interaction.followup.send(
                    "❌ Este nome já foi registrado por outro participante.",
                    ephemeral=True
                )
                return
            
            required_hashtag = db.get_hashtag()
            if not required_hashtag:
                await interaction.followup.send(
                    "⚠️ Nenhuma hashtag foi configurada ainda. Contate um administrador.",
                    ephemeral=True
                )
                return
            
            if hashtag_input.lower() != required_hashtag.lower():
                await interaction.followup.send(
                    f"❌ Hashtag incorreta! A hashtag correta é: `{required_hashtag}`",
                    ephemeral=True
                )
                return
            
            inscricao_channel_id = db.get_inscricao_channel()
            if not inscricao_channel_id:
                await interaction.followup.send(
                    "⚠️ Canal de inscrições não configurado. Contate um administrador.",
                    ephemeral=True
                )
                return
            
            inscricao_channel = interaction.guild.get_channel(inscricao_channel_id)
            if not inscricao_channel:
                await interaction.followup.send(
                    "⚠️ Canal de inscrições não encontrado. Contate um administrador.",
                    ephemeral=True
                )
                return
            
            bonus_roles = db.get_bonus_roles()
            tag_config = db.get_tag()
            
            member = interaction.user
            if isinstance(member, discord.User):
                member = interaction.guild.get_member(interaction.user.id)
            
            tickets = utils.calculate_tickets(
                member,
                bonus_roles,
                tag_config["enabled"],
                tag_config["text"],
                tag_config["quantity"]
            )
            
            total_tickets = utils.get_total_tickets(tickets)
            
            msg_content = f"{member.mention}\n{first_name} {last_name}\n{required_hashtag}"
            
            msg = await inscricao_channel.send(msg_content)
            
            db.add_participant(
                interaction.user.id,
                first_name,
                last_name,
                tickets,
                msg.id
            )
            
            logger.info(f"Nova inscrição: {first_name} {last_name} ({interaction.user.id}) - {total_tickets} fichas")
            
        except Exception as e:
            logger.error(f"Erro no modal de inscrição: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    "❌ Ocorreu um erro ao processar sua inscrição. Tente novamente.",
                    ephemeral=True
                )
            except:
                pass

class InscricaoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Inscrever-se no Sorteio",
        style=discord.ButtonStyle.green,
        custom_id="inscricao_button"
    )
    async def inscricao_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if db.is_registered(interaction.user.id):
            await interaction.response.send_message(
                "❌ Você já está inscrito no sorteio!",
                ephemeral=True
            )
            return
        modal = InscricaoModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Verificar minha inscrição",
        style=discord.ButtonStyle.secondary,
        custom_id="verificar_button"
    )
    async def verificar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        participant = db.get_participant(interaction.user.id)
        if not participant:
            await interaction.response.send_message(
                "❌ Você não está inscrito no sorteio.",
                ephemeral=True
            )
            return

        first_name = participant["first_name"]
        last_name = participant["last_name"]
        tickets = participant["tickets"]
        total_tickets = utils.get_total_tickets(tickets)

        embed = discord.Embed(
            title="✅ Seu Status de Inscrição",
            description=f"**Nome**: {first_name} {last_name}",
            color=discord.Color.green()
        )

        embed.add_field(name="Total de Fichas", value=f"🎫 {total_tickets}", inline=False)

        tickets_list = utils.format_tickets_list(tickets, interaction.guild)
        embed.add_field(
            name="Detalhamento",
            value="\n".join(tickets_list),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

class InscricaoButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Inscrever-se no Sorteio",
        style=discord.ButtonStyle.green,
        custom_id="inscricao_button"
    )
    async def inscricao_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if db.is_registered(interaction.user.id):
            await interaction.response.send_message(
                "❌ Você já está inscrito no sorteio!",
                ephemeral=True
            )
            return
        modal = InscricaoModal()
        await interaction.response.send_modal(modal)

@bot.event
async def on_ready():
    logger.info(f"Bot conectado como {bot.user}")
    
    try:
        button_msg_id = db.get_button_message_id()
        if button_msg_id:
            bot.add_view(InscricaoView(), message_id=button_msg_id)
            logger.info(f"View do botão re-registrada para message_id: {button_msg_id}")
    except Exception as e:
        logger.error(f"Erro ao re-registrar view: {e}")
    
    try:
        synced = await bot.tree.sync()
        logger.info(f"Sincronizados {len(synced)} comandos")
    except Exception as e:
        logger.error(f"Erro ao sincronizar comandos: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    chat_lock = db.get_chat_lock()
    if chat_lock["enabled"] and chat_lock["channel_id"]:
        if message.channel.id == chat_lock["channel_id"]:
            if not message.author.guild_permissions.administrator and not db.is_moderator(message.author.id):
                try:
                    await message.delete()
                except Exception as e:
                    logger.error(f"Erro ao deletar mensagem no chat bloqueado: {e}")
    
    await bot.process_commands(message)

@bot.tree.command(name="ajuda", description="Mostra a lista de comandos disponíveis")
async def ajuda(interaction: discord.Interaction):
    is_admin = interaction.user.guild_permissions.administrator
    
    embed = discord.Embed(
        title="📋 Comandos do Bot de Sorteios",
        description="Lista de comandos disponíveis",
        color=discord.Color.blue()
    )
    
    public_commands = [
        "/ajuda - Mostra esta mensagem",
        "/verificar - Verifica seu status de inscrição"
    ]
    
    embed.add_field(
        name="🔓 Comandos Públicos",
        value="\n".join(public_commands),
        inline=False
    )
    
    if is_admin:
        admin_commands = [
            "/setup_inscricao - Configura o sistema de inscrições",
            "/hashtag - Define a hashtag obrigatória",
            "/tag - Configura a tag do servidor",
            "/tag_manual - Concede TAG manual a um usuário",
            "/fichas - Adiciona cargo bônus",
            "/tirar - Remove cargo bônus",
            "/lista - Lista participantes",
            "/exportar - Exporta lista de participantes",
            "/atualizar - Recalcula fichas de todos",
            "/estatisticas - Mostra estatísticas",
            "/limpar - Limpa dados",
            "/blacklist - Gerencia blacklist",
            "/chat - Bloqueia/desbloqueia chat",
            "/anunciar - Envia anúncio",
            "/sync - Sincroniza comandos"
        ]
        
        embed.add_field(
            name="🔐 Comandos Administrativos",
            value="\n".join(admin_commands),
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="verificar", description="Verifica seu status de inscrição")
async def verificar(interaction: discord.Interaction):
    participant = db.get_participant(interaction.user.id)
    
    if not participant:
        await interaction.response.send_message(
            "❌ Você não está inscrito no sorteio.",
            ephemeral=True
        )
        return
    
    first_name = participant["first_name"]
    last_name = participant["last_name"]
    tickets = participant["tickets"]
    total_tickets = utils.get_total_tickets(tickets)
    
    embed = discord.Embed(
        title="✅ Seu Status de Inscrição",
        description=f"**Nome**: {first_name} {last_name}",
        color=discord.Color.green()
    )
    
    embed.add_field(name="Total de Fichas", value=f"🎫 {total_tickets}", inline=False)
    
    tickets_list = utils.format_tickets_list(tickets, interaction.guild)
    embed.add_field(
        name="Detalhamento",
        value="\n".join(tickets_list),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setup_inscricao", description="[ADMIN] Configura o sistema de inscrições")
@app_commands.default_prmissions(administrator=True)
@app_commands.describe(
    canal_botao="Canal onde será enviado o botão de inscrição",
    canal_inscricoes="Canal onde serão postadas as inscrições",
    mensagem="Mensagem opcional que acompanha o botão",
    midia="Imagem ou vídeo opcional"
)
async def setup_inscricao(
    interaction: discord.Interaction,
    canal_botao: discord.TextChannel,
    canal_inscricoes: discord.TextChannel,
    mensagem: Optional[str] = None,
    midia: Optional[discord.Attachment] = None
):
    try:
        await interaction.response.defer(ephemeral=True)
        
        db.set_inscricao_channel(canal_inscricoes.id)
        
        view = InscricaoView()
        
        content = mensagem or "**INSCRIÇÕES ABERTAS!**\nClique no botão em baixo para se inscrever!"
        
        files = []
        if midia:
            file = await midia.to_file()
            files.append(file)
        
        if files:
            msg = await canal_botao.send(content=content, view=view, files=files)
        else:
            msg = await canal_botao.send(content=content, view=view)
        
        db.set_button_message_id(msg.id)
        bot.add_view(view, message_id=msg.id)
        
        await interaction.followup.send(
            f"✅ Sistema de inscrições configurado!\n"
            f"**Canal do botão**: {canal_botao.mention}\n"
            f"**Canal de inscrições**: {canal_inscricoes.mention}",
            ephemeral=True
        )
        
        logger.info(f"Setup de inscrição configurado por {interaction.user}")
        
    except Exception as e:
        logger.error(f"Erro no setup_inscricao: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Erro ao configurar: {str(e)}",
            ephemeral=True
        )

def is_admin_or_moderator(interaction: discord.Interaction) -> bool:
    """Verifica se o usuário é admin ou moderador do bot"""
    return interaction.user.guild_permissions.administrator or db.is_moderator(interaction.user.id)

@bot.tree.command(name="hashtag", description="[ADMIN] Define a hashtag obrigatória")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@app_commands.describe(hashag="Hashtag obrigatória para inscrição")
async def hashtag(interaction: discord.Interaction, hashtag: str):
    if not is_admin_or_moderator(interaction):
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando.",
            ephemeral=True
        )
        return
    
    if db.is_hashtag_locked():
        await interaction.response.send_message(
            "🔒 A hashtag está bloqueada e não pode ser alterada.",
            ephemeral=True
        )
        return
    
    db.set_hashtag(hashtag.strip())
    
    await interaction.response.send_message(
        f"✅ Hashtag definida como: `{hashtag.strip()}`",
        ephemeral=True
    )
    
    logger.info(f"Hashtag definida como '{hashtag}' por {interaction.user}")

@bot.tree.command(name="tag", description="[ADMIN] Configura a tag do servidor")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    acao="Ação a realizar",
    texto="Texto da tag do servidor",
    quantidade="Quantidade de fichas bônus pela tag"
)
async def tag(
    interaction: discord.Interaction,
    acao: Literal["on", "off", "status"],
    texto: Optional[str] = None,
    quantidade: Optional[int] = 1
):
    if acao == "status":
        tag_config = db.get_tag()
        status = "✅ Ativada" if tag_config["enabled"] else "❌ Desativada"
        
        embed = discord.Embed(
            title="🏷️ Status da TAG",
            color=discord.Color.blue()
        )
        import re
        tag_text = tag_config["text"] or "Não configurado"
        tag_clean = re.sub(r'[^\w\s]', '', tag_text).strip() if tag_config["text"] else ""
        
        variations_text = f"`{tag_text}`"
        if tag_clean and tag_clean != tag_text:
            variations_text += f"\n**Também aceita**: `{tag_clean}` (sem emoji/caracteres especiais)"
        
        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(name="Texto da TAG", value=variations_text, inline=False)
        embed.add_field(name="Fichas Bônus", value=str(tag_config["quantity"]), inline=False)
        
        # Teste de detecção no usuário que executou o comando
        if tag_config["enabled"] and tag_config["text"]:
            member = interaction.user
            if isinstance(member, discord.User):
                member = interaction.guild.get_member(interaction.user.id)
            
            if member:
                # Testa se a TAG está no nome do usuário
                tag_search = tag_config["text"].strip().lower()
                fields_with_tag = []
                
                checks = [
                    ("Nome Visual", member.display_name),
                    ("Apelido do Servidor", member.nick),
                    ("Nome Global", member.global_name),
                    ("Nome de Usuário", member.name)
                ]
                
                for field_name, field_value in checks:
                    if field_value and tag_search in field_value.strip().lower():
                        fields_with_tag.append(f"✅ {field_name}: `{field_value}`")
                    elif field_value:
                        fields_with_tag.append(f"❌ {field_name}: `{field_value}`")
                    else:
                        fields_with_tag.append(f"⚪ {field_name}: [não definido]")
                
                embed.add_field(
                    name=f"Teste de Detecção (você)",
                    value="\n".join(fields_with_tag),
                    inline=False
                )
                
                # Indica se seria concedida ficha
                has_tag = any(field_value and tag_search in field_value.strip().lower() 
                             for _, field_value in checks)
                
                embed.add_field(
                    name="Resultado",
                    value=f"{'✅ Você receberia' if has_tag else '❌ Você NÃO receberia'} +{tag_config['quantity']} ficha(s) da TAG",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if acao == "on":
        if not texto:
            await interaction.response.send_message(
                "❌ Você precisa fornecer o texto da tag!",
                ephemeral=True
            )
            return
        
        db.set_tag(True, texto, quantidade)
        await interaction.response.send_message(
            f"✅ TAG ativada!\n**Texto**: {texto}\n**Fichas bônus**: {quantidade}",
            ephemeral=True
        )
        logger.info(f"TAG ativada: '{texto}' ({quantidade} fichas) por {interaction.user}")
    
    elif acao == "off":
        db.set_tag(False)
        await interaction.response.send_message("❌ TAG desativada!", ephemeral=True)
        logger.info(f"TAG desativada por {interaction.user}")

@bot.tree.command(name="fichas", description="[ADMIN] Adiciona um cargo bônus")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    cargo="Cargo que dará fichas bônus",
    quantidade="Quantidade de fichas bônus",
    abreviacao="Abreviação do cargo (ex: S.B) - OBRIGATÓRIA"
)
async def fichas(
    interaction: discord.Interaction,
    cargo: discord.Role,
    quantidade: int,
    abreviacao: str
):
    if not is_admin_or_moderator(interaction):
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando.",
            ephemeral=True
        )
        return
    
    if quantidade <= 0:
        await interaction.response.send_message(
            "❌ A quantidade deve ser maior que 0!",
            ephemeral=True
        )
        return
    
    abbrev = abreviacao.strip()
    
    db.add_bonus_role(cargo.id, quantidade, abbrev)
    
    await interaction.response.send_message(
        f"✅ Cargo {cargo.mention} configurado!\n"
        f"**Fichas bônus**: {quantidade}\n"
        f"**Abreviação**: {abbrev}",
        ephemeral=True
    )
    
    logger.info(f"Cargo bônus adicionado: {cargo.name} ({quantidade} fichas, {abbrev}) por {interaction.user}")

@bot.tree.command(name="tirar", description="[ADMIN] Remove um cargo bônus")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(cargo="Cargo a ser removido dos bônus")
async def tirar(interaction: discord.Interaction, cargo: discord.Role):
    if db.remove_bonus_role(cargo.id):
        await interaction.response.send_message(
            f"✅ Cargo {cargo.mention} removido dos bônus!",
            ephemeral=True
        )
        logger.info(f"Cargo bônus removido: {cargo.name} por {interaction.user}")
    else:
        await interaction.response.send_message(
            f"❌ Cargo {cargo.mention} não estava configurado como bônus.",
            ephemeral=True
        )

@bot.tree.command(name="lista", description="[ADMIN] Lista os participantes")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(tipo="Tipo de listagem")
async def lista(interaction: discord.Interaction, tipo: Literal["simples", "com_fichas"]):
    participants = db.get_all_participants()
    
    if not participants:
        await interaction.response.send_message(
            "📋 Nenhum participante inscrito ainda.",
            ephemeral=True
        )
        return
    
    await interaction.response.defer(ephemeral=True)
    
    lines = []
    
    if tipo == "simples":
        lines.append("📋 **Lista de Participantes (Simples)**\n")
        for i, (user_id, data) in enumerate(participants.items(), 1):
            name = utils.format_simple_entry(data["first_name"], data["last_name"])
            lines.append(f"{i}. {name}")
    
    else:
        lines.append("📋 **Lista de Participantes (Com Fichas)**\n")
        for user_id, data in participants.items():
            entries = utils.format_detailed_entry(
                data["first_name"],
                data["last_name"],
                data["tickets"]
            )
            lines.extend(entries)
            lines.append("")
    
    content = "\n".join(lines)
    
    if len(content) > 2000:
        chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
        for chunk in chunks:
            await interaction.followup.send(chunk, ephemeral=True)
    else:
        await interaction.followup.send(content, ephemeral=True)

@bot.tree.command(name="exportar", description="[ADMIN] Exporta lista de participantes")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(tipo="Tipo de exportação")
async def exportar(interaction: discord.Interaction, tipo: Literal["simples", "com_fichas"]):
    participants = db.get_all_participants()


@bot.tree.command(name="testar_tag", description="[ADMIN] Testa se a TAG está sendo detectada em um usuário")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(usuario="Usuário para testar (opcional, você se não especificar)")
async def testar_tag(interaction: discord.Interaction, usuario: Optional[discord.User] = None):
    tag_config = db.get_tag()
    
    if not tag_config["enabled"] or not tag_config["text"]:
        await interaction.response.send_message(
            "❌ A TAG não está configurada ou não está ativada!\nUse `/tag acao:on texto:SUATAG quantidade:1`",
            ephemeral=True
        )
        return
    
    # Define o usuário a ser testado
    target_user = usuario or interaction.user
    member = target_user
    
    if isinstance(member, discord.User):
        member = interaction.guild.get_member(target_user.id)
    
    if not member:
        await interaction.response.send_message(
            "❌ Usuário não encontrado no servidor!",
            ephemeral=True
        )
        return
    
    # Testa a detecção
    tag_search = tag_config["text"].strip().lower()
    
    embed = discord.Embed(
        title=f"🔍 Teste de Detecção de TAG",
        description=f"**Usuário**: {member.mention}\n**TAG procurada**: `{tag_config['text']}`",
        color=discord.Color.blue()
    )
    
    checks = [
        ("Nome Visual (display_name)", member.display_name, "Principal campo usado pelo Discord moderno"),
        ("Apelido do Servidor (nick)", member.nick, "Apelido definido pelo servidor"),
        ("Nome Global (global_name)", member.global_name, "Nome global do Discord"),
        ("Nome de Usuário (name)", member.name, "Username do Discord (@username)")
    ]
    
    fields_with_tag = []
    has_tag = False
    found_in = None
    
    for field_name, field_value, description in checks:
        if field_value:
            normalized = field_value.strip().lower()
            contains = tag_search in normalized
            
            status = "✅" if contains else "❌"
            fields_with_tag.append(
                f"{status} **{field_name}**\n"
                f"  └ Valor: `{field_value}`\n"
                f"  └ {description}"
            )
            
            if contains and not has_tag:
                has_tag = True
                found_in = field_name
        else:
            fields_with_tag.append(
                f"⚪ **{field_name}**\n"
                f"  └ Valor: [não definido]\n"
                f"  └ {description}"
            )
    
    embed.add_field(
        name="📋 Verificação em todos os campos",
        value="\n\n".join(fields_with_tag),
        inline=False
    )
    
    # Resultado final
    if has_tag:
        result = f"✅ **TAG DETECTADA!**\n\n"
        result += f"A TAG `{tag_config['text']}` foi encontrada em: **{found_in}**\n\n"
        result += f"O usuário **receberá +{tag_config['quantity']} ficha(s) extra(s)** da TAG!"
        embed.color = discord.Color.green()
    else:
        result = f"❌ **TAG NÃO DETECTADA!**\n\n"
        result += f"A TAG `{tag_config['text']}` não foi encontrada em nenhum campo do usuário.\n\n"
        result += f"**Dica**: O usuário precisa ter a TAG `{tag_config['text']}` no nome visual, apelido do servidor, nome global ou nome de usuário."
        embed.color = discord.Color.red()
    
    embed.add_field(
        name="🎯 Resultado Final",
        value=result,
        inline=False
    )
    
    # Calcula as fichas totais que o usuário teria
    bonus_roles = db.get_bonus_roles()
    tickets = utils.calculate_tickets(
        member,
        bonus_roles,
        tag_config["enabled"],
        tag_config["text"],
        tag_config["quantity"]
    )
    
    total = utils.get_total_tickets(tickets)
    
    embed.add_field(
        name="🎫 Total de Fichas (simulação)",
        value=f"Base: 1 | Cargos: {sum(r['quantity'] for r in tickets.get('roles', {}).values())} | TAG: {tickets['tag']} | **Total: {total}**",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

    
    if not participants:
        await interaction.response.send_message(
            "📋 Nenhum participante para exportar.",
            ephemeral=True
        )
        return
    
    await interaction.response.defer(ephemeral=True)
    
    lines = []
    
    if tipo == "simples":
        for user_id, data in participants.items():
            name = utils.format_simple_entry(data["first_name"], data["last_name"])
            lines.append(name)
    else:
        for user_id, data in participants.items():
            entries = utils.format_detailed_entry(
                data["first_name"],
                data["last_name"],
                data["tickets"]
            )
            lines.extend(entries)
    
    filename = f"participantes_{tipo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    
    await interaction.followup.send(
        f"✅ Exportação concluída! Total: {len(participants)} participante(s)",
        file=discord.File(filename),
        ephemeral=True
    )
    
    os.remove(filename)
    logger.info(f"Lista exportada ({tipo}) por {interaction.user}")

@bot.tree.command(name="atualizar", description="[ADMIN] Recalcula fichas de todos os participantes")
@app_commands.default_permissions(administrator=True)
async def atualizar(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    participants = db.get_all_participants()
    bonus_roles = db.get_bonus_roles()
    tag_config = db.get_tag()
    
    updated = 0
    errors = 0
    
    for user_id, data in participants.items():
        try:
            member = interaction.guild.get_member(int(user_id))
            if not member:
                continue
            
            new_tickets = utils.calculate_tickets(
                member,
                bonus_roles,
                tag_config["enabled"],
                tag_config["text"],
                tag_config["quantity"]
            )
            
            db.update_tickets(int(user_id), new_tickets)
            updated += 1
        except Exception as e:
            logger.error(f"Erro ao atualizar fichas do usuário {user_id}: {e}")
            errors += 1
    
    await interaction.followup.send(
        f"✅ Fichas atualizadas!\n"
        f"**Atualizados**: {updated}\n"
        f"**Erros**: {errors}",
        ephemeral=True
    )
    
    logger.info(f"Fichas atualizadas por {interaction.user}: {updated} sucesso, {errors} erros")

@bot.tree.command(name="estatisticas", description="[ADMIN] Mostra estatísticas do sorteio")
@app_commands.default_permissions(administrator=True)
async def estatisticas(interaction: discord.Interaction):
    stats = db.get_statistics()
    
    embed = discord.Embed(
        title="📊 Estatísticas do Sorteio",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="👥 Total de Participantes",
        value=str(stats["total_participants"]),
        inline=True
    )
    
    embed.add_field(
        name="🎫 Total de Fichas",
        value=str(stats["total_tickets"]),
        inline=True
    )
    
    embed.add_field(
        name="🏷️ Com TAG",
        value=str(stats["participants_with_tag"]),
        inline=True
    )
    
    if stats["tickets_by_role"]:
        role_info = []
        for role_id, info in stats["tickets_by_role"].items():
            role = interaction.guild.get_role(int(role_id))
            role_name = role.name if role else "Cargo Desconhecido"
            role_info.append(
                f"**{role_name}** ({info['abbreviation']}): "
                f"{info['count']} participante(s), {info['total_tickets']} ficha(s)"
            )
        
        embed.add_field(
            name="📋 Fichas por Cargo",
            value="\n".join(role_info) if role_info else "Nenhum",
            inline=False
        )
    
    embed.add_field(
        name="🚫 Blacklist",
        value=str(stats["blacklist_count"]),
        inline=True
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="limpar", description="[ADMIN] Limpa dados do sistema")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def limpar(interaction: discord.Interaction):
    if not is_admin_or_moderator(interaction):
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando.",
            ephemeral=True
        )
        return
    
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            self.value = None
            self.message = None
        
        @discord.ui.button(label="Limpar Inscrições", style=discord.ButtonStyle.danger)
        async def confirm_participants(self, inter: discord.Interaction, button: discord.ui.Button):
            participants = db.get_all_participants()
            
            deleted_count = 0
            for user_id, data in participants.items():
                if data.get("message_id"):
                    try:
                        channel = inter.guild.get_channel(db.get_inscricao_channel())
                        if channel:
                            msg = await channel.fetch_message(data["message_id"])
                            await msg.delete()
                            deleted_count += 1
                    except:
                        pass
            
            db.clear_participants()
            
            # Deletar mensagem de confirmação
            try:
                await self.message.delete()
            except:
                pass
            
            await inter.response.send_message(
                f"✅ Inscrições limpas!\n"
                f"**Participantes removidos**: {len(participants)}\n"
                f"**Mensagens deletadas**: {deleted_count}",
                ephemeral=True
            )
            self.stop()
        
        @discord.ui.button(label="Limpar Tudo", style=discord.ButtonStyle.danger)
        async def confirm_all(self, inter: discord.Interaction, button: discord.ui.Button):
            participants = db.get_all_participants()
            
            deleted_count = 0
            for user_id, data in participants.items():
                if data.get("message_id"):
                    try:
                        channel = inter.guild.get_channel(db.get_inscricao_channel())
                        if channel:
                            msg = await channel.fetch_message(data["message_id"])
                            await msg.delete()
                            deleted_count += 1
                    except:
                        pass
            
            db.clear_all()
            
            # Deletar mensagem de confirmação
            try:
                await self.message.delete()
            except:
                pass
            
            await inter.response.send_message(
                f"✅ Tudo limpo! Sistema resetado.\n"
                f"**Mensagens deletadas**: {deleted_count}",
                ephemeral=True
            )
            self.stop()
        
        @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
        async def cancel(self, inter: discord.Interaction, button: discord.ui.Button):
            # Deletar mensagem de confirmação
            try:
                await self.message.delete()
            except:
                pass
            
            await inter.response.send_message("❌ Operação cancelada.", ephemeral=True)
            self.stop()
    
    view = ConfirmView()
    msg = await interaction.response.send_message(
        "⚠️ **Escolha o tipo de limpeza:**\n"
        "• **Limpar Inscrições**: Removes only participants data\n"
        "• **Limpar Tudo**: Removes participants AND settings",
        view=view,
        ephemeral=True
    )
    view.message = await interaction.original_response()

@bot.tree.command(name="blacklist", description="[ADMIN] Gerencia a blacklist")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    acao="Ação a realizar",
    usuario="Usuário para banir/desbanir",
    motivo="Motivo do banimento"
)
async def blacklist(
    interaction: discord.Interaction,
    acao: Literal["banir", "desbanir", "lista"],
    usuario: Optional[discord.User] = None,
    motivo: Optional[str] = None
):
    if acao == "lista":
        blacklist_data = db.get_blacklist()
        
        if not blacklist_data:
            await interaction.response.send_message(
                "📋 A blacklist está vazia.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🚫 Blacklist",
            color=discord.Color.red()
        )
        
        for user_id, data in blacklist_data.items():
            user = await bot.fetch_user(int(user_id))
            embed.add_field(
                name=f"{user.name}",
                value=f"**Motivo**: {data['reason']}\n**Banido por**: <@{data['banned_by']}>",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if not usuario:
        await interaction.response.send_message(
            "❌ Você precisa especificar um usuário!",
            ephemeral=True
        )
        return
    
    if acao == "banir":
        reason = motivo or "Não especificado"
        
        if db.is_registered(usuario.id):
            participant = db.get_participant(usuario.id)
            if participant and participant.get("message_id"):
                try:
                    channel = interaction.guild.get_channel(db.get_inscricao_channel())
                    if channel:
                        msg = await channel.fetch_message(participant["message_id"])
                        await msg.delete()
                except:
                    pass
            
            db.remove_participant(usuario.id)
        
        db.add_to_blacklist(usuario.id, reason, interaction.user.id)
        
        await interaction.response.send_message(
            f"✅ {usuario.mention} foi adicionado à blacklist!\n**Motivo**: {reason}",
            ephemeral=True
        )
        logger.info(f"{usuario} banido por {interaction.user}: {reason}")
    
    elif acao == "desbanir":
        if db.remove_from_blacklist(usuario.id):
            await interaction.response.send_message(
                f"✅ {usuario.mention} foi removido da blacklist!",
                ephemeral=True
            )
            logger.info(f"{usuario} desbanido por {interaction.user}")
        else:
            await interaction.response.send_message(
                f"❌ {usuario.mention} não está na blacklist.",
                ephemeral=True
            )

@bot.tree.command(name="chat", description="[ADMIN] Bloqueia/desbloqueia chat")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    acao="Ação a realizar",
    canal="Canal a ser bloqueado"
)
async def chat(
    interaction: discord.Interaction,
    acao: Literal["on", "off", "status"],
    canal: Optional[discord.TextChannel] = None
):
    if acao == "status":
        chat_lock = db.get_chat_lock()
        status = "🔒 Bloqueado" if chat_lock["enabled"] else "🔓 Desbloqueado"
        
        channel_mention = "Nenhum"
        if chat_lock["channel_id"]:
            channel = interaction.guild.get_channel(chat_lock["channel_id"])
            if channel:
                channel_mention = channel.mention
        
        embed = discord.Embed(
            title="💬 Status do Chat Lock",
            color=discord.Color.blue()
        )
        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(name="Canal", value=channel_mention, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if acao == "on":
        if not canal:
            await interaction.response.send_message(
                "❌ Você precisa especificar um canal!",
                ephemeral=True
            )
            return
        
        db.set_chat_lock(True, canal.id)
        await interaction.response.send_message(
            f"🔒 Chat bloqueado em {canal.mention}!\n"
            f"Apenas administradores podem enviar mensagens.",
            ephemeral=True
        )
        logger.info(f"Chat bloqueado em {canal.name} por {interaction.user}")
    
    elif acao == "off":
        db.set_chat_lock(False)
        await interaction.response.send_message(
            "🔓 Chat desbloqueado!",
            ephemeral=True
        )
        logger.info(f"Chat desbloqueado por {interaction.user}")

@bot.tree.command(name="anunciar", description="[ADMIN] Envia um anúncio")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    canal="Canal onde enviar o anúncio",
    mensagem="Mensagem do anúncio",
    embed="Enviar como embed?",
    titulo="Título do embed (se embed=True)",
    cor="Cor do embed (nome ou hex)",
    imagem="Imagem ou vídeo opcional"
)
async def anunciar(
    interaction: discord.Interaction,
    canal: discord.TextChannel,
    mensagem: str,
    embed: bool = False,
    titulo: Optional[str] = None,
    cor: Optional[str] = None,
    imagem: Optional[discord.Attachment] = None
):
    try:
        await interaction.response.defer(ephemeral=True)
        
        files = []
        if imagem:
            file = await imagem.to_file()
            files.append(file)
        
        if embed:
            embed_color = utils.parse_color(cor) if cor else discord.Color.blue()
            embed_obj = discord.Embed(
                title=titulo or "Anúncio",
                description=mensagem,
                color=embed_color
            )
            
            if imagem and imagem.content_type.startswith("image"):
                embed_obj.set_image(url=f"attachment://{imagem.filename}")
            
            await canal.send(embed=embed_obj, files=files if files else None)
        else:
            if files:
                await canal.send(content=mensagem, files=files)
            else:
                await canal.send(content=mensagem)
        
        await interaction.followup.send(
            f"✅ Anúncio enviado em {canal.mention}!",
            ephemeral=True
        )
        
        logger.info(f"Anúncio enviado em {canal.name} por {interaction.user}")
        
    except Exception as e:
        logger.error(f"Erro ao enviar anúncio: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Erro ao enviar anúncio: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="controle_acesso", description="[ADMIN] Gerencia acesso de moderadores ao bot")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    acao="Ação a realizar",
    usuario="Usuário a adicionar/remover"
)
async def controle_acesso(
    interaction: discord.Interaction,
    acao: Literal["adicionar", "remover", "lista"],
    usuario: Optional[discord.User] = None
):
    if acao == "lista":
        moderators = db.get_moderators()
        
        if not moderators:
            await interaction.response.send_message(
                "📋 Nenhum moderador configurado.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="👮 Moderadores do Bot",
            color=discord.Color.blue()
        )
        
        mod_list = []
        for mod_id in moderators:
            try:
                user = await bot.fetch_user(int(mod_id))
                mod_list.append(f"• {user.mention} ({user.name})")
            except:
                mod_list.append(f"• ID: {mod_id} (usuário não encontrado)")
        
        embed.description = "\n".join(mod_list)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if not usuario:
        await interaction.response.send_message(
            "❌ Você precisa especificar um usuário!",
            ephemeral=True
        )
        return
    
    if acao == "adicionar":
        db.add_moderator(usuario.id)
        await interaction.response.send_message(
            f"✅ {usuario.mention} agora tem controle total do bot!",
            ephemeral=True
        )
        logger.info(f"Moderador adicionado: {usuario} por {interaction.user}")
    
    elif acao == "remover":
        if db.remove_moderator(usuario.id):
            await interaction.response.send_message(
                f"✅ {usuario.mention} foi removido dos moderadores!",
                ephemeral=True
            )
            logger.info(f"Moderador removido: {usuario} por {interaction.user}")
        else:
            await interaction.response.send_message(
                f"❌ {usuario.mention} não é um moderador.",
                ephemeral=True
            )

@bot.tree.command(name="tag_manual", description="[ADMIN] Concede TAG manual a um participante")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    usuario="Usuário que receberá a TAG manual",
    quantidade="Quantidade de fichas extras da TAG (padrão: 1)"
)
async def tag_manual(
    interaction: discord.Interaction,
    usuario: discord.User,
    quantidade: Optional[int] = 1
):
    if not is_admin_or_moderator(interaction):
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando.",
            ephemeral=True
        )
        return
    
    # Verifica se o usuário está inscrito
    if not db.is_registered(usuario.id):
        await interaction.response.send_message(
            f"❌ {usuario.mention} não está inscrito no sorteio!",
            ephemeral=True
        )
        return
    
    if quantidade < 0:
        await interaction.response.send_message(
            "❌ A quantidade não pode ser negativa!",
            ephemeral=True
        )
        return
    
    # Define a TAG manual
    if quantidade == 0:
        # Remove a TAG manual
        db.remove_manual_tag(usuario.id)
        await interaction.response.send_message(
            f"✅ TAG manual removida de {usuario.mention}!",
            ephemeral=True
        )
        logger.info(f"TAG manual removida de {usuario} por {interaction.user}")
    else:
        db.set_manual_tag(usuario.id, quantidade)
        
        # Obtém os dados atualizados
        participant = db.get_participant(usuario.id)
        total_tickets = utils.get_total_tickets(participant["tickets"])
        
        await interaction.response.send_message(
            f"✅ TAG manual concedida!\n"
            f"**Usuário**: {usuario.mention}\n"
            f"**Fichas da TAG**: {quantidade}\n"
            f"**Total de fichas**: {total_tickets}",
            ephemeral=True
        )
        logger.info(f"TAG manual ({quantidade} fichas) concedida a {usuario} por {interaction.user}")

@bot.tree.command(name="sync", description="[ADMIN] Sincroniza comandos do bot")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(guild_id="ID do servidor (opcional, vazio para global)")
async def sync(interaction: discord.Interaction, guild_id: Optional[str] = None):
    await interaction.response.defer(ephemeral=True)
    
    try:
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            synced = await bot.tree.sync(guild=guild)
            await interaction.followup.send(
                f"✅ Sincronizados {len(synced)} comandos no servidor {guild_id}",
                ephemeral=True
            )
        else:
            synced = await bot.tree.sync()
            await interaction.followup.send(
                f"✅ Sincronizados {len(synced)} comandos globalmente",
                ephemeral=True
            )
        
        logger.info(f"Comandos sincronizados por {interaction.user}")
        
    except Exception as e:
        logger.error(f"Erro ao sincronizar: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Erro ao sincronizar: {str(e)}",
            ephemeral=True
        )

if __name__ == "__main__":
    # carrega variáveis de ambiente (já usa load_dotenv no topo)
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN não encontrado nas variáveis de ambiente")
        exit(1)

    # inicia Flask em thread antes de iniciar o cliente/bot
    Thread(target=run_flask, daemon=True).start()
    logging.info(f"Flask server iniciado na porta {os.getenv('PORT', 5000)}")

    try:
        # use o nome real da sua instância (bot.run(...) ou client.run(...))
        if 'bot' in globals():
            globals()['bot'].run(BOT_TOKEN)
        elif 'client' in globals():
            globals()['client'].run(BOT_TOKEN)
        else:
            logging.error('Nenhuma instância de bot/client encontrada para executar.')
            exit(1)
    except Exception as e:
        logging.error(f"Erro ao iniciar o bot: {e}", exc_info=True)
        exit(1)
