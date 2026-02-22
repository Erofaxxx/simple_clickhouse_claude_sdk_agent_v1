# ClickHouse LangChain Agent

ИИ-агент на базе [LangChain](https://www.langchain.com/) для работы с ClickHouse через [MCP-сервер](https://github.com/ClickHouse/mcp-clickhouse).
Поддерживает SSL-подключение к **Яндекс Cloud ClickHouse**.

---

## Структура проекта

```
langchain_agent.py          # основной скрипт LangChain агента
requirements_langchain.txt  # Python-зависимости для LangChain
.env.example               # шаблон конфигурации (без реальных данных)
.env                       # ваш конфиг с credentials (НЕ в git)
README_LANGCHAIN.md
```

---

## Быстрый старт на Ubuntu-сервере

### 1. Клонируйте репозиторий

```bash
git clone <repo-url>
cd simple_clickhouse_claude_sdk_agent_v1
```

### 2. Запустите скрипт установки (от root или sudo)

Скрипт установит системные пакеты, Python-зависимости, `uv`, `mcp-clickhouse` и скачает SSL-сертификат Яндекс.
На серверах с ≤ 1 ГБ RAM автоматически создаст swap-файл.

```bash
bash setup_langchain.sh
```

Либо установите зависимости вручную:

```bash
# Обновите pip
pip install -q --upgrade pip

# Установите LangChain зависимости
pip install -q langchain-mcp-adapters langgraph "langchain[anthropic]"

# Или используйте requirements файл
pip install -r requirements_langchain.txt
```

> **Важно:** Для LangChain агента требуется Python 3.9 или выше.

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

### 4. Скачайте SSL сертификат (для Яндекс Cloud)

```bash
wget https://storage.yandexcloud.net/cloud-certs/CA.pem -O YandexInternalRootCA.crt
```

### 5. Установите `uv` (менеджер Python окружений)

LangChain агент использует `uv` для запуска MCP сервера. Установите его:

```bash
# macOS и Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Или через pip
pip install uv
```

### 6. Запустите агента

**Интерактивный режим:**
```bash
python3 langchain_agent.py
```

**Одиночный запрос:**
```bash
python3 langchain_agent.py "Who's committed the most code to ClickHouse?"
```

---

## Особенности LangChain агента

### Stream Handler

LangChain агент использует `UltraCleanStreamHandler` для обработки потокового вывода. Это особенно важно при работе с большими наборами данных или сложными аналитическими запросами, которые могут занять некоторое время.

Handler обеспечивает:
- ✅ Чистый вывод текста без лишних JSON-структур
- 🔧 Индикация вызова инструментов
- ✅ Подтверждение завершения операций

### Модель по умолчанию

LangChain агент использует `claude-sonnet-4-0` — быструю и эффективную модель для работы с базами данных.

### React Agent

Агент построен на архитектуре ReAct (Reasoning + Acting), которая позволяет модели:
1. Рассуждать о том, какие действия необходимо предпринять
2. Выполнять действия через инструменты MCP
3. Наблюдать результаты
4. Повторять цикл до получения ответа

---

## Доступные MCP-инструменты

| Инструмент | Описание |
|------------|----------|
| `list_databases` | Список баз данных |
| `list_tables` | Список таблиц в базе |
| `run_select_query` | Выполнить SELECT-запрос |
| `run_chdb_select_query` | SELECT через chDB (локальные файлы) |

---

## Примеры запросов

```bash
# Анализ коммитов в ClickHouse
python3 langchain_agent.py "Who's committed the most code to ClickHouse?"

# Список таблиц
python3 langchain_agent.py "Покажи все таблицы в базе данных"

# Аналитический запрос
python3 langchain_agent.py "Найди топ-10 пользователей по количеству визитов"

# Сложный запрос с агрегацией
python3 langchain_agent.py "Покажи среднее количество просмотров страниц за последний месяц по дням недели"
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
| `🔧`  | Вызов инструмента (SQL-запрос к ClickHouse) |
| `🤔`  | Обработка запроса |

### Типичные проблемы

**`ANTHROPIC_API_KEY не задан`**
→ Проверьте, что в `.env` есть строка `ANTHROPIC_API_KEY=sk-ant-...`

**`uv: command not found`**
→ Установите uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**`Ошибка DNS при обращении к <host>`**
→ Проверьте значение `CLICKHOUSE_HOST` — укажите только hostname, без `https://`

**`Таймаут подключения`**
→ Сервер недоступен из данной сети. Проверьте файервол / whitelist IP Яндекс Cloud

**`SSL сертификат не найден`**
→ Скачайте сертификат:
```bash
wget https://storage.yandexcloud.net/cloud-certs/CA.pem -O YandexInternalRootCA.crt
```

**`mcp-clickhouse: command not found`**
→ Установите mcp-clickhouse:
```bash
pip install mcp-clickhouse
```

**`Не удалось импортировать необходимые модули`**
→ Установите зависимости: `pip install -r requirements_langchain.txt`

---

## Сравнение с Claude SDK Agent

| Характеристика | Claude SDK Agent | LangChain Agent |
|----------------|------------------|-----------------|
| **Основа** | claude-agent-sdk | LangChain + LangGraph |
| **Архитектура** | Прямое взаимодействие | ReAct (Reasoning + Acting) |
| **Модель** | Настраивается через SDK | claude-sonnet-4-0 |
| **Stream Handler** | Базовый вывод | UltraCleanStreamHandler |
| **Запуск MCP** | Прямой запуск mcp-clickhouse | Через uv run |
| **Зависимости** | Минимальные (3 пакета) | Расширенные (LangChain экосистема) |
| **Потребление памяти** | ~400-600 МБ | ~600-800 МБ |

### Когда использовать LangChain Agent?

- ✅ Нужна интеграция с LangChain экосистемой
- ✅ Требуется ReAct архитектура для сложных рассуждений
- ✅ Планируется расширение функциональности через LangChain компоненты
- ✅ Необходим расширенный контроль над потоковым выводом

### Когда использовать Claude SDK Agent?

- ✅ Нужна минимальная установка и зависимости
- ✅ Критично потребление памяти (серверы ≤ 1 ГБ RAM)
- ✅ Требуется максимальная скорость работы
- ✅ Достаточно базовой функциональности без дополнительных интеграций

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

---

## Требования к системе

- **Python**: 3.9 или выше
- **RAM**: Минимум 1 ГБ (рекомендуется 2 ГБ)
- **Дисковое пространство**: ~500 МБ для зависимостей
- **Сеть**: Доступ к ClickHouse серверу и API Anthropic

---

## Дополнительная информация

### О LangChain

[LangChain](https://www.langchain.com/) — это фреймворк для разработки приложений на основе больших языковых моделей (LLM). Он предоставляет:
- Удобные абстракции для работы с LLM
- Инструменты для создания цепочек (chains) и агентов
- Интеграции с различными внешними системами
- Поддержку векторных баз данных и памяти

### О MCP (Model Context Protocol)

MCP — это открытый протокол для подключения AI-приложений к внешним источникам данных и инструментам. Подробнее: [GitHub - ClickHouse MCP](https://github.com/ClickHouse/mcp-clickhouse)

---

## Лицензия

См. основной README.md репозитория.
