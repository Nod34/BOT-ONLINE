# 🎉 Bot de Discord para Sorteios

Bot completo de Discord para gerenciar sorteios com sistema de inscrições via modal, cálculo de fichas por cargos e tags, e funcionalidades administrativas avançadas.

## ✨ Funcionalidades

### 🔓 Comandos Públicos
- `/ajuda` - Mostra a lista de comandos disponíveis
- `/verificar` - Verifica seu status de inscrição e total de fichas

### 🔐 Comandos Administrativos
- `/setup_inscricao` - Configura o sistema de inscrições (botão persistente)
- `/hashtag` - Define a hashtag obrigatória para inscrição
- `/tag` - Configura a tag do servidor (bônus de fichas)
- `/fichas` - Adiciona cargo bônus com quantidade de fichas
- `/tirar` - Remove cargo bônus
- `/lista` - Lista participantes (simples ou detalhada)
- `/exportar` - Exporta lista de participantes (arquivo .txt)
- `/atualizar` - Recalcula fichas de todos os participantes
- `/estatisticas` - Mostra estatísticas completas do sorteio
- `/limpar` - Limpa dados (inscrições ou tudo)
- `/blacklist` - Gerencia blacklist de usuários
- `/chat` - Bloqueia/desbloqueia chat para direcionar ao botão
- `/anunciar` - Envia anúncios com suporte a embeds e mídia
- `/sync` - Sincroniza comandos do bot

## 🎫 Sistema de Fichas

O bot calcula automaticamente as fichas de cada participante:

1. **Ficha Base**: 1 ficha por participação
2. **Fichas de Cargo**: Cargos configurados com `/fichas` dão fichas extras
3. **Fichas de TAG**: Se o usuário tiver a tag do servidor no nick/nome

### Exemplo de Exportação Detalhada

```
Rafael Fe.
Rafael Fe. S.B
Rafael Fe. TAG
```

Onde:
- Primeira linha: ficha base
- Segunda linha: ficha do cargo "S.B" (abreviação configurada)
- Terceira linha: ficha da TAG do servidor

## 🚀 Deploy no Render

### Passo 1: Criar Bot no Discord

1. Acesse [Discord Developer Portal](https://discord.com/developers/applications)
2. Clique em "New Application" e dê um nome ao seu bot
3. Vá em "Bot" → "Add Bot"
4. Copie o **Token** (você vai precisar dele)
5. Em "Privileged Gateway Intents", ative:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent
6. Em "OAuth2" → "URL Generator":
   - Selecione `bot` e `applications.commands`
   - Em "Bot Permissions", selecione:
     - Administrator (ou as permissões necessárias)
   - Copie o link gerado e adicione o bot ao seu servidor

### Passo 2: Fazer Deploy no Render

1. **Criar conta no Render**: Acesse [render.com](https://render.com) e crie uma conta gratuita

2. **Criar novo Web Service**:
   - Clique em "New +" → "Web Service"
   - Conecte seu repositório GitHub ou faça upload dos arquivos

3. **Configurar o serviço**:
   - **Name**: `discord-bot-sorteios` (ou qualquer nome)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: `Free` (ou pago se preferir)

4. **Adicionar variáveis de ambiente**:
   - Clique em "Environment" → "Add Environment Variable"
   - Adicione as seguintes variáveis:
     - `BOT_TOKEN`: Cole o token do seu bot Discord
     - `PORT`: `8080`

5. **Deploy**: Clique em "Create Web Service"

6. **Copiar URL do serviço**: Após o deploy, você terá uma URL tipo:
   ```
   https://discord-bot-sorteios.onrender.com
   ```

### Passo 3: Configurar UptimeRobot

O UptimeRobot mantém seu bot sempre online fazendo requisições periódicas ao endpoint Flask.

1. **Criar conta**: Acesse [uptimerobot.com](https://uptimerobot.com) e crie uma conta gratuita

2. **Adicionar novo monitor**:
   - Clique em "+ Add New Monitor"
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `Bot Discord Sorteios`
   - **URL**: Cole a URL do Render + `/health`
     ```
     https://discord-bot-sorteios.onrender.com/health
     ```
   - **Monitoring Interval**: `5 minutes` (plano gratuito)
   - Clique em "Create Monitor"

3. **Pronto!** O UptimeRobot agora vai fazer requisições a cada 5 minutos para manter o bot ativo.

## 📝 Configuração Inicial do Bot

Após o bot estar online no seu servidor Discord:

1. **Configurar Hashtag Obrigatória**:
   ```
   /hashtag hashtag:#SORTEIO2025
   ```

2. **Configurar Sistema de Inscrições**:
   ```
   /setup_inscricao 
     canal_botao: #sorteios
     canal_inscricoes: #inscricoes-confirmadas
     mensagem: "🎉 Participe do nosso sorteio incrível!"
   ```

3. **Adicionar Cargos Bônus** (opcional):
   ```
   /fichas cargo:@Servidor Boost quantidade:5 abreviacao:S.B
   /fichas cargo:@VIP quantidade:3 abreviacao:VIP
   ```

4. **Ativar TAG do Servidor** (opcional):
   ```
   /tag acao:on texto:[CLAN] quantidade:2
   ```

## 🛠️ Desenvolvimento Local

Para rodar o bot localmente:

1. **Clone o repositório**:
   ```bash
   git clone <seu-repositorio>
   cd discord-bot-sorteios
   ```

2. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure as variáveis de ambiente**:
   - Copie `.env.example` para `.env`
   - Adicione seu `BOT_TOKEN`

4. **Execute o bot**:
   ```bash
   python bot.py
   ```

O servidor Flask estará disponível em `http://localhost:8080`

## 📂 Estrutura do Projeto

```
.
├── bot.py              # Bot principal com todos os comandos
├── database.py         # Gerenciamento do banco de dados JSON
├── utils.py            # Funções auxiliares (validação, cálculos)
├── requirements.txt    # Dependências do projeto
├── .env.example        # Exemplo de arquivo de ambiente
├── .gitignore         # Arquivos ignorados pelo git
└── README.md          # Este arquivo
```

## 🔒 Segurança

- **Nunca compartilhe seu BOT_TOKEN**
- O arquivo `.env` está no `.gitignore` e não deve ser commitado
- Use variáveis de ambiente no Render para armazenar credenciais
- Apenas administradores podem usar comandos sensíveis

## 📊 Sistema de Validação

O bot valida automaticamente:

- ✅ Nomes sem números
- ✅ Mínimo de 3 caracteres
- ✅ Cada parte do nome com >2 caracteres
- ✅ Pelo menos uma letra em cada campo
- ✅ Nomes duplicados não são permitidos
- ✅ Verificação de blacklist
- ✅ Hashtag obrigatória correta

## 💾 Banco de Dados

O bot usa um arquivo `database.json` para armazenar:

- Participantes e suas fichas
- Configurações de cargos bônus
- Hashtag obrigatória
- TAG do servidor
- Blacklist
- Configurações de canal

**Importante**: No Render, o disco é efêmero. Se você reiniciar o serviço, os dados podem ser perdidos. Para produção, considere usar um banco de dados externo (MongoDB, PostgreSQL, etc).

## 🆘 Solução de Problemas

### Bot não responde aos comandos
- Verifique se o bot está online no Discord
- Execute `/sync` para sincronizar os comandos
- Verifique os logs no Render

### Botão de inscrição não funciona após reiniciar
- O bot re-registra automaticamente o botão no `on_ready`
- Se não funcionar, execute `/setup_inscricao` novamente

### Erro ao exportar lista
- Verifique se há participantes inscritos
- Verifique as permissões do bot no canal

## 📝 Exemplo de Uso Completo

1. Admin configura o sistema:
   ```
   /hashtag hashtag:#SORTEIO2025
   /setup_inscricao canal_botao:#sorteios canal_inscricoes:#confirmacoes
   /fichas cargo:@Boost quantidade:5 abreviacao:S.B
   /tag acao:on texto:[CLAN] quantidade:2
   ```

2. Usuário clica no botão "Inscrever-se no Sorteio"

3. Preenche o modal:
   - Primeiro Nome: Rafael
   - Sobrenome: Fernandes
   - Hashtag: #SORTEIO2025

4. Bot calcula fichas automaticamente:
   - 1 ficha base
   - 5 fichas do cargo Boost (se tiver)
   - 2 fichas da TAG [CLAN] (se tiver no nick)

5. Admin pode:
   - Ver estatísticas: `/estatisticas`
   - Exportar lista: `/exportar tipo:detalhada`
   - Atualizar fichas: `/atualizar`

## 📄 Licença

Este projeto é de código aberto e está disponível para uso livre.

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

---

**Desenvolvido para facilitar sorteios no Discord** 🎉
