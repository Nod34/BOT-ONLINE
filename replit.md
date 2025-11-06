# Discord Raffle Bot

## Overview

A comprehensive Discord bot for managing raffles/giveaways with a modal-based registration system, role-based ticket calculations, and advanced administrative features. The bot uses a persistent button interface for user registration and calculates tickets based on base participation, configured role bonuses, and server tag bonuses.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Technology Stack
- **Runtime**: Python 3.x
- **Discord Library**: discord.py v2.3.2 with app_commands (slash commands)
- **Web Server**: Flask (for keepalive/health checks on deployment platforms)
- **Data Storage**: JSON file-based database (database.json)

### Application Structure

**Entry Point (`bot.py`)**
- Discord bot initialization with required intents (message_content, members, guilds)
- Flask web server running on separate thread for platform keepalive
- Command registration and event handling
- Environment variable management via python-dotenv

**Data Layer (`database.py`)**
- JSON file-based persistence
- Core data structure includes:
  - `participants`: User registration data with ticket breakdown
  - `bonus_roles`: Role-to-ticket mapping with abbreviations
  - `hashtag`: Required registration hashtag (lockable)
  - `tag`: Server tag configuration for bonus tickets
  - `inscricao_channel`: Registration channel ID
  - `button_message_id`: Persistent button message reference
  - `blacklist`: Blocked users
  - `chat_lock`: Channel lock configuration
- CRUD operations for participants, roles, settings

**Utilities (`utils.py`)**
- Name validation (no numbers, minimum 3 characters, parts >2 characters)
- Full name validation combining first and last names
- Additional helper functions for data processing

### Registration System Architecture

**Modal-Based Registration**
- Custom `InscricaoModal` with fields: first_name, last_name, hashtag
- Multi-layer validation:
  1. Name format validation (no numbers, character minimums)
  2. Duplicate name checking
  3. Blacklist verification
  4. Required hashtag matching
- Automatic ticket calculation upon successful registration

**Persistent Button System**
- Button deployed via `/setup_inscricao` command to specified channel
- View registered with `timeout=None` for persistence
- Button message ID stored in database
- View re-registration on bot restart via `on_ready` event
- Prevents button functionality loss after bot restarts

### Ticket Calculation System

**Multi-Source Ticket Aggregation**
1. **Base Ticket**: 1 ticket for participation
2. **Role Bonuses**: Configured roles grant additional tickets
3. **Tag Bonus**: Matching server tag in username/nickname grants tickets

**Function**: `calculate_tickets(member, bonus_roles, tag_enabled, server_tag, tag_quantity)`
- Checks member roles against configured bonus roles
- Verifies tag presence in display_name (nome visual), nick, global_name, ou username (nessa ordem)
- Returns breakdown: `{base: 1, roles: {...}, tag: 0|quantity}`

**Correções Recentes (2025-11-06)**:
- Bug corrigido: formato de nome agora usa primeiras 2 letras do sobrenome (não últimas)
- TAG agora detecta corretamente em `display_name` (nome visual do Discord moderno)
- Emoji removido do botão de inscrição
- Mensagem de inscrição simplificada (sem embed): @mention + Nome Completo + #hashtag
- Comandos /lista e /exportar: "detalhada" renomeado para "com_fichas"
- Comando /sync corrigido para não duplicar comandos
- Botão verifica se usuário já está inscrito antes de abrir modal
- Mensagem padrão do botão alterada para: "INSCRIÇÕES ABERTAS!\nClique no botão em baixo para se inscrever!"

### Export Formats

**Detailed Format Pattern ("com_fichas")**
- Each participant generates multiple lines (one per ticket)
- Line format: `FirstName First2Letters. [ABBREVIATION]` (primeiras 2 letras em minúsculas)
- Base ticket: No abbreviation
- Role tickets: Role abbreviation from configuration
- Tag tickets: "TAG" abbreviation

Example output:
```
Rafael fe.
Rafael fe. S.B
Rafael fe. TAG
```

**Simple Format Pattern**
- One line per participant with full name
- Format: `FirstName LastName`

### Administrative Features

**Setup Commands**
- `/setup_inscricao`: Configure registration system with custom message and optional media
- `/hashtag`: Set required registration hashtag
- `/tag`: Configure server tag for bonus tickets
- `/fichas`: Add role bonus with ticket quantity and abbreviation
- `/tirar`: Remove role bonus

**Management Commands**
- `/lista`: View participants (simple or com_fichas format)
- `/exportar`: Export participant list as .txt file (simple or com_fichas)
- `/atualizar`: Recalculate all participant tickets (importante após configurar TAG/cargos)
- `/estatisticas`: Display comprehensive raffle statistics
- `/limpar`: Clear data (registrations only or complete reset)
- `/blacklist`: Manage user blacklist
- `/chat`: Lock/unlock channels to direct users to registration button
- `/anunciar`: Send announcements with embed and media support
- `/sync`: Synchronize bot commands with Discord (não duplica mais comandos)

**Public Commands**
- `/ajuda`: Display available commands
- `/verificar`: Check personal registration status and ticket breakdown

### Deployment Architecture

**Platform Compatibility**
- Designed for Replit and similar platforms (Render mentioned in README)
- Flask server provides HTTP endpoint for platform health checks
- Routes: `/` (status), `/health` (JSON health check)
- Runs on configurable PORT (default 5000)

**Configuration Management**
- Environment variables via `.env` file
- Required: `BOT_TOKEN`
- Optional: `PORT` (defaults to 5000)

### Error Handling & Logging

- Centralized logging with INFO level
- Format: timestamp, logger name, level, message
- Exception handling in database operations
- Validation error messages user-facing and descriptive

## External Dependencies

### Discord API
- **discord.py v2.3.2**: Complete Discord bot functionality
- Requires: message content intent, members intent, guilds intent
- Uses: slash commands (app_commands), modals, buttons (persistent views), embeds

### Web Framework
- **Flask 3.0.0**: Lightweight HTTP server for keepalive
- Runs on separate thread to avoid blocking Discord client
- Provides health check endpoints for deployment platforms

### Configuration
- **python-dotenv 1.0.0**: Environment variable management
- Loads `.env` file for secure token storage

### Data Storage
- **JSON files**: No external database required
- Single file: `database.json`
- Manual file I/O with error recovery
- In-memory operations with periodic saves

### Deployment Platforms
- **Primário**: Render (com UptimeRobot para keepalive)
- **Secundário**: Replit
- Requires: HTTP endpoint for keepalive pings (porta 5000)
- No specific database service required
- File system persistence sufficient for operation

**Instruções de Deploy**:
1. Criar conta no Render (render.com)
2. Fazer deploy do repositório
3. Configurar variável de ambiente `BOT_TOKEN`
4. Configurar UptimeRobot para monitorar endpoint `/health`
5. Ver README.md para instruções completas