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

Скрипт установит системные пакеты, Python-зависимости, `uv` и скачает SSL-сертификат Яндекс:

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

# Python-зависимости
pip3 install --upgrade pip
pip3 install -r requirements.txt

# uv (требуется для mcp-clickhouse)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"   # или перелогиньтесь

# SSL-сертификат Яндекс Cloud
wget https://storage.yandexcloud.net/cloud-certs/CA.pem -O YandexInternalRootCA.crt
```

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

**`uv: command not found`**  
→ Установите uv и добавьте в PATH:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"
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
