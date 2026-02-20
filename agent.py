#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "claude-agent-sdk",
#   "python-dotenv",
# ]
# ///
"""
ClickHouse Claude Agent
-----------------------
ИИ-агент на базе Claude SDK для работы с ClickHouse через MCP-сервер.
Поддерживает SSL-подключение к Яндекс Cloud ClickHouse.

Использование:
    python agent.py                     # интерактивный режим
    python agent.py "Ваш вопрос сюда"  # один запрос и выход
"""

import asyncio
import os
import socket
import sys
from pathlib import Path

# ─── Загрузка .env ────────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent
_ENV_FILE = _SCRIPT_DIR / ".env"
_MAX_DISPLAY_LENGTH = 200  # максимальная длина значения инструмента в выводе

try:
    from dotenv import load_dotenv

    if _ENV_FILE.exists():
        load_dotenv(_ENV_FILE)
        print(f"✅ Конфиг загружен из: {_ENV_FILE}")
    else:
        print(f"⚠️  Файл .env не найден: {_ENV_FILE}")
        print("   Используются переменные окружения системы.")
        print("   Создайте .env из шаблона:  cp .env.example .env")
except ImportError:
    print("⚠️  python-dotenv не установлен. Переменные окружения берутся из системы.")
    print("   Установите: pip install python-dotenv")

# ─── Импорт SDK ───────────────────────────────────────────────────────────────

try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        TextBlock,
        ToolUseBlock,
        UserMessage,
        query,
    )
except ImportError as exc:
    print(f"\n❌ Не удалось импортировать claude_agent_sdk: {exc}")
    print("   Установите зависимости:  pip install -r requirements.txt")
    sys.exit(1)


# ─── Проверка конфигурации ────────────────────────────────────────────────────


def _check_config() -> dict:
    """Читает и валидирует настройки; при критических ошибках завершает процесс."""
    errors: list[str] = []
    warnings: list[str] = []

    # Anthropic API key
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        errors.append("ANTHROPIC_API_KEY не задан")
    elif not anthropic_key.startswith("sk-ant-"):
        warnings.append(
            "ANTHROPIC_API_KEY выглядит нестандартно (ожидается префикс 'sk-ant-')"
        )

    # ClickHouse host — убираем протокол, если пользователь вставил полный URL
    ch_host = os.environ.get("CLICKHOUSE_HOST", "").strip()
    if not ch_host:
        errors.append("CLICKHOUSE_HOST не задан")
    else:
        for prefix in ("https://", "http://"):
            if ch_host.startswith(prefix):
                ch_host = ch_host[len(prefix):]
                warnings.append(
                    f"Убран протокол из CLICKHOUSE_HOST, используется: {ch_host}"
                )
                break

    ch_port = os.environ.get("CLICKHOUSE_PORT", "8443").strip()
    ch_user = os.environ.get("CLICKHOUSE_USER", "").strip()
    if not ch_user:
        errors.append("CLICKHOUSE_USER не задан")

    ch_password = os.environ.get("CLICKHOUSE_PASSWORD", "")
    ch_database = os.environ.get("CLICKHOUSE_DATABASE", "default").strip()

    # SSL сертификат
    ssl_ca_cert = ""
    ssl_cert_setting = os.environ.get("CLICKHOUSE_SSL_CERT_PATH", "").strip()

    if ssl_cert_setting:
        cert_path = Path(ssl_cert_setting)
        if not cert_path.is_absolute():
            cert_path = _SCRIPT_DIR / cert_path
        if cert_path.exists():
            ssl_ca_cert = str(cert_path)
            print(f"✅ SSL сертификат найден: {cert_path}")
        else:
            warnings.append(
                f"SSL сертификат не найден: {cert_path}\n"
                "   Скачайте сертификат Яндекс:\n"
                f"     wget https://storage.yandexcloud.net/cloud-certs/CA.pem"
                f" -O {cert_path}"
            )
    else:
        # Поиск в стандартных местах
        fallback_paths = [
            _SCRIPT_DIR / "YandexInternalRootCA.crt",
            Path("/root/.clickhouse-client/root.crt"),
            Path("/etc/ssl/certs/YandexInternalRootCA.crt"),
        ]
        for p in fallback_paths:
            if p.exists():
                ssl_ca_cert = str(p)
                print(f"✅ SSL сертификат обнаружен автоматически: {p}")
                break
        if not ssl_ca_cert:
            warnings.append(
                "CLICKHOUSE_SSL_CERT_PATH не задан и сертификат не найден.\n"
                "   Для Яндекс ClickHouse скачайте сертификат:\n"
                "     wget https://storage.yandexcloud.net/cloud-certs/CA.pem"
                " -O YandexInternalRootCA.crt"
            )

    for w in warnings:
        print(f"⚠️  {w}")

    if errors:
        print("\n❌ Критические ошибки конфигурации:")
        for e in errors:
            print(f"   • {e}")
        print("\n   Создайте файл .env на основе .env.example и заполните данные.")
        sys.exit(1)

    return {
        "CLICKHOUSE_HOST": ch_host,
        "CLICKHOUSE_PORT": ch_port,
        "CLICKHOUSE_USER": ch_user,
        "CLICKHOUSE_PASSWORD": ch_password,
        "CLICKHOUSE_DATABASE": ch_database,
        "CLICKHOUSE_SECURE": "true",
        "CLICKHOUSE_VERIFY": "true" if ssl_ca_cert else "false",
        "CLICKHOUSE_CA_CERT": ssl_ca_cert,
        "CLICKHOUSE_CONNECT_TIMEOUT": "30",
        "CLICKHOUSE_SEND_RECEIVE_TIMEOUT": "60",
    }


# ─── Проверка TCP-подключения ─────────────────────────────────────────────────


def _check_connectivity(host: str, port: int) -> bool:
    """Проверяет TCP-достижимость хоста. Возвращает True при успехе."""
    try:
        with socket.create_connection((host, port), timeout=10):
            return True
    except socket.timeout:
        print(f"❌ Таймаут подключения к {host}:{port} (10 сек)")
    except socket.gaierror as exc:
        print(f"❌ Ошибка DNS при обращении к {host}: {exc}")
    except ConnectionRefusedError:
        print(f"❌ Соединение отклонено {host}:{port}")
    except OSError as exc:
        print(f"❌ Сетевая ошибка при подключении к {host}:{port}: {exc}")
    return False


# ─── Запуск агента ────────────────────────────────────────────────────────────


def _sanitize_string(s: str) -> str:
    """Sanitizes a string to ensure valid Unicode for JSON encoding.

    Removes any surrogate characters and ensures the string can be safely
    serialized to JSON without encoding errors. Uses 'surrogateescape' error
    handler to properly handle any invalid UTF-8 sequences.
    """
    # First, encode with surrogateescape to handle any existing surrogates
    # Then decode back to string with replace to fix any invalid sequences
    try:
        # Try to encode/decode to ensure valid UTF-8
        return s.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')
    except (UnicodeDecodeError, UnicodeEncodeError):
        # Fallback: use strict ASCII-safe encoding
        return s.encode('ascii', errors='replace').decode('ascii')


async def _run_agent(prompt: str, env: dict) -> None:
    """Выполняет один запрос к агенту и печатает результат."""
    # Sanitize the prompt to prevent JSON encoding errors
    prompt = _sanitize_string(prompt)

    # Убираем пустые значения чтобы не передавать пустые строки в MCP
    # Also sanitize all environment variable values to prevent encoding issues
    mcp_env = {k: _sanitize_string(v) for k, v in env.items() if v}

    options = ClaudeAgentOptions(
        allowed_tools=[
            "mcp__mcp-clickhouse__list_databases",
            "mcp__mcp-clickhouse__list_tables",
            "mcp__mcp-clickhouse__run_select_query",
            "mcp__mcp-clickhouse__run_chdb_select_query",
        ],
        mcp_servers={
            "mcp-clickhouse": {
                "command": "mcp-clickhouse",
                "args": [],
                "env": mcp_env,
            }
        },
    )

    print("\n🤔 Обработка запроса...\n")
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"🤖 {block.text}")
                    elif isinstance(block, ToolUseBlock):
                        print(f"🛠️  {block.name}")
                        if block.input:
                            for k, v in block.input.items():
                                # Обрезаем длинные значения для читаемости
                                display = str(v)
                                if len(display) > _MAX_DISPLAY_LENGTH:
                                    display = display[:_MAX_DISPLAY_LENGTH] + "…"
                                print(f"     {k}: {display}")
            elif isinstance(message, UserMessage):
                for block in message.content:
                    if isinstance(block, TextBlock) and block.text.strip():
                        print(f"📊 {block.text}")
    except Exception as exc:
        print(f"\n❌ Ошибка при выполнении запроса: {exc}")
        exc_str = str(exc).lower()
        if "anthropic_api_key" in exc_str or "authentication" in exc_str:
            print("   → Проверьте правильность ANTHROPIC_API_KEY в файле .env")
        elif "mcp-clickhouse" in exc_str:
            print("   → Убедитесь, что mcp-clickhouse установлен: pip install mcp-clickhouse")
        elif "mcp" in exc_str or "clickhouse" in exc_str or "connect" in exc_str:
            print("   → Проверьте настройки ClickHouse (хост, порт, пользователь, пароль, сертификат)")
        raise


# ─── Точка входа ──────────────────────────────────────────────────────────────


def main() -> None:
    print("=" * 60)
    print("  ClickHouse Claude Agent")
    print("=" * 60)
    print()

    # 1. Конфигурация
    print("📋 Проверка конфигурации...")
    env = _check_config()

    # 2. Проверка сети
    host = env["CLICKHOUSE_HOST"]
    port = int(env["CLICKHOUSE_PORT"])
    print(f"\n🔌 Проверка TCP-подключения к {host}:{port}...")
    if _check_connectivity(host, port):
        print(f"✅ {host}:{port} доступен")
    else:
        print(f"\n⚠️  Не удалось подключиться к {host}:{port}")
        print("   Возможные причины:")
        print("   • Неправильный хост или порт в .env")
        print("   • Хост недоступен из данной сети / заблокирован файерволом")
        print("   • Сервер ClickHouse остановлен")
        try:
            answer = input("   Продолжить всё равно? (y/n): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)
        if answer != "y":
            sys.exit(0)

    print()

    # 3. Режим работы
    if len(sys.argv) > 1:
        # Одиночный запрос из аргументов командной строки
        prompt = " ".join(sys.argv[1:])
        asyncio.run(_run_agent(prompt, env))
    else:
        # Интерактивный режим
        print("💬 Интерактивный режим. Введите 'выход' или 'exit' для завершения.\n")
        print(f"   База данных: {env['CLICKHOUSE_DATABASE']}")
        print()
        while True:
            try:
                prompt = input("❓ Ваш вопрос: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\nЗавершение работы.")
                break

            if not prompt:
                continue
            if prompt.lower() in ("выход", "exit", "quit", "q"):
                print("До свидания!")
                break

            try:
                asyncio.run(_run_agent(prompt, env))
            except Exception:
                pass  # ошибка уже напечатана в _run_agent
            print()


if __name__ == "__main__":
    main()
