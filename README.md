# ClickHouse Claude Agent

ИИ-агент на базе [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk) для работы с ClickHouse через [MCP-сервер](https://github.com/ClickHouse/mcp-clickhouse).  
Поддерживает SSL-подключение к **Яндекс Cloud ClickHouse**.

---

## Структура проекта

```
agent.py          # основной скрипт агента
.env.example      # шаблон конфигурации (без реальных данных)
.env              # ваш конфиг с credentials (НЕ в git)
requirements.txt  # Python-зависимости
setup.sh          # скрипт автоматической установки
README.md
```

---

## Быстрый старт на Ubuntu-сервере

### 1. Клонируйте репозиторий

```bash
git clone <repo-url>
cd simple_clickhouse_claude_sdk_agent_v1
```

### 2. Запустите скрипт установки (от root или sudo)

Скрипт установит системные пакеты, Python-зависимости, `mcp-clickhouse` и скачает SSL-сертификат Яндекс.  
На серверах с ≤ 1 ГБ RAM автоматически создаст swap-файл (см. раздел «OOM / нехватка памяти»).

```bash
bash setup.sh
```

Либо выполните шаги вручную (см. раздел «Ручная установка» ниже).

### 3. Создайте файл `.env`

```bash
cp .env.example .env
nano .env
```

Заполните все поля:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...
CLICKHOUSE_HOST=rc1b-xxxx.mdb.yandexcloud.net   # без https://
CLICKHOUSE_PORT=8443
CLICKHOUSE_USER=User_main
CLICKHOUSE_PASSWORD=your_password
CLICKHOUSE_DATABASE=ym_sanok
CLICKHOUSE_SSL_CERT_PATH=YandexInternalRootCA.crt
```

> **Важно:** файл `.env` прописан в `.gitignore` и **никогда не попадёт в репозиторий**.

### 4. Запустите агента

**Интерактивный режим:**
```bash
python3 agent.py
```

**Одиночный запрос:**
```bash
python3 agent.py "Покажи топ-10 визитов по количеству просмотров страниц"
```

---

## Ручная установка

```bash
# Системные пакеты
apt-get update && apt-get install -y python3 python3-pip curl wget

# Python-зависимости (включая mcp-clickhouse)
pip3 install --upgrade pip
pip3 install -r requirements.txt

# SSL-сертификат Яндекс Cloud
wget https://storage.yandexcloud.net/cloud-certs/CA.pem -O YandexInternalRootCA.crt
```

> **Примечание:** `uv` больше не требуется. Пакет `mcp-clickhouse` устанавливается напрямую через pip, что значительно снижает потребление памяти.

---

## OOM / нехватка памяти (серверы с ≤ 1 ГБ RAM)

На серверах с малым объёмом оперативной памяти (≤ 1 ГБ) процесс агента может быть убит ядром Linux (OOM Killer) с ошибкой:

```
Out of memory: Killed process ... (claude) total-vm:74340448kB
```

или при запуске `agent.py`:

```
Fatal error in message reader: Command failed with exit code -9
```

### Причина

Claude SDK + MCP-сервер суммарно требуют ~400–600 МБ RAM. Если на сервере меньше ~1.5 ГБ свободной памяти и нет swap, OOM Killer завершает процесс.

### Решение 1: Добавить swap (рекомендуется)

Скрипт `setup.sh` делает это автоматически. Вручную:

```bash
# Создать swap-файл 2 ГБ
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Сделать постоянным (после перезагрузки)
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Проверить
free -m
```

### Решение 2: Прямой запуск mcp-clickhouse (уже применено)

В текущей версии агент запускает `mcp-clickhouse` напрямую, без промежуточного менеджера `uv`. Это экономит ~200–300 МБ RAM, так как `uv` больше не создаёт отдельное окружение и дочерний процесс.

Если вы обновляете старую версию, убедитесь что `mcp-clickhouse` установлен:

```bash
pip install mcp-clickhouse

# Проверить
which mcp-clickhouse
```

### Решение 3: Увеличить RAM сервера

Если swap не помогает — рекомендуется сервер с ≥ 2 ГБ RAM.

---

## Диагностика ошибок

Агент выводит понятные сообщения на каждом шаге:

| Символ | Значение |
|--------|----------|
| `✅`  | Успех |
| `⚠️`  | Предупреждение (работа продолжается) |
| `❌`  | Критическая ошибка |
| `🔌`  | Проверка сети |
| `🛠️`  | Вызов инструмента (SQL-запрос к ClickHouse) |
| `🤖`  | Ответ агента |

### Типичные проблемы

**`ANTHROPIC_API_KEY не задан`**  
→ Проверьте, что в `.env` есть строка `ANTHROPIC_API_KEY=sk-ant-...`

**`Ошибка DNS при обращении к <host>`**  
→ Проверьте значение `CLICKHOUSE_HOST` — укажите только hostname, без `https://`

**`Таймаут подключения`**  
→ Сервер недоступен из данной сети. Проверьте файервол / whitelist IP Яндекс Cloud

**`SSL сертификат не найден`**  
→ Скачайте сертификат:
```bash
wget https://storage.yandexcloud.net/cloud-certs/CA.pem -O YandexInternalRootCA.crt
```

**`Command failed with exit code -9` / OOM Killer**  
→ Нехватка памяти. См. раздел «OOM / нехватка памяти» выше.

**`mcp-clickhouse: command not found`**  
→ Установите mcp-clickhouse:
```bash
pip install mcp-clickhouse
```

**`Не удалось импортировать claude_agent_sdk`**  
→ Установите зависимости: `pip3 install -r requirements.txt`

---

## Доступные MCP-инструменты

| Инструмент | Описание |
|------------|----------|
| `list_databases` | Список баз данных |
| `list_tables` | Список таблиц в базе |
| `run_select_query` | Выполнить SELECT-запрос |
| `run_chdb_select_query` | SELECT через chDB (локальные файлы) |

---

## Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|--------|
| `ANTHROPIC_API_KEY` | API-ключ Anthropic | `sk-ant-...` |
| `CLICKHOUSE_HOST` | Hostname ClickHouse (без протокола) | `rc1b-xxx.mdb.yandexcloud.net` |
| `CLICKHOUSE_PORT` | Порт (HTTPS) | `8443` |
| `CLICKHOUSE_USER` | Пользователь БД | `User_main` |
| `CLICKHOUSE_PASSWORD` | Пароль | `your_password` |
| `CLICKHOUSE_DATABASE` | База данных по умолчанию | `ym_sanok` |
| `CLICKHOUSE_SSL_CERT_PATH` | Путь к CA-сертификату | `YandexInternalRootCA.crt` |
