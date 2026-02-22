#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "langchain-mcp-adapters",
#   "langgraph",
#   "langchain",
#   "langchain-anthropic",
#   "python-dotenv",
# ]
# ///
"""
ClickHouse LangChain Agent
--------------------------
ИИ-агент на базе LangChain для работы с ClickHouse через MCP-сервер.
Поддерживает SSL-подключение к Яндекс Cloud ClickHouse.

Использование:
    python langchain_agent.py                     # интерактивный режим
    python langchain_agent.py "Ваш вопрос сюда"  # один запрос и выход
"""

import asyncio
import os
import socket
import sys
from pathlib import Path

# ─── Загрузка .env ────────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent
_ENV_FILE = _SCRIPT_DIR / ".env"

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

# ─── Импорт зависимостей ──────────────────────────────────────────────────────

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from langchain_mcp_adapters import load_mcp_tools
    from langgraph.prebuilt import create_react_agent
except ImportError as exc:
    print(f"\n❌ Не удалось импортировать необходимые модули: {exc}")
    print("   Установите зависимости:  pip install langchain-mcp-adapters langgraph langchain[anthropic]")
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


# ─── Stream Handler ───────────────────────────────────────────────────────────


class UltraCleanStreamHandler:
    """Обработчик потокового вывода для LangChain агента."""

    def __init__(self):
        self.buffer = ""
        self.in_text_generation = False
        self.last_was_tool = False

    def handle_chunk(self, chunk):
        event = chunk.get("event", "")

        if event == "on_chat_model_stream":
            data = chunk.get("data", {})
            chunk_data = data.get("chunk", {})

            # Only handle actual text content, skip tool invocation streams
            if hasattr(chunk_data, "content"):
                content = chunk_data.content
                if isinstance(content, str) and not content.startswith("{\""):
                    # Add space after tool completion if needed
                    if self.last_was_tool:
                        print(" ", end="", flush=True)
                        self.last_was_tool = False
                    print(content, end="", flush=True)
                    self.in_text_generation = True
                elif isinstance(content, list):
                    for item in content:
                        if (
                            isinstance(item, dict)
                            and item.get("type") == "text"
                            and "partial_json" not in str(item)
                        ):
                            text = item.get("text", "")
                            if text and not text.startswith("{\""):
                                # Add space after tool completion if needed
                                if self.last_was_tool:
                                    print(" ", end="", flush=True)
                                    self.last_was_tool = False
                                print(text, end="", flush=True)
                                self.in_text_generation = True

        elif event == "on_tool_start":
            if self.in_text_generation:
                print(f"\n🔧 {chunk.get('name', 'tool')}", end="", flush=True)
                self.in_text_generation = False

        elif event == "on_tool_end":
            print(" ✅", end="", flush=True)
            self.last_was_tool = True


# ─── Запуск агента ────────────────────────────────────────────────────────────


async def _run_agent(prompt: str, env: dict) -> None:
    """Выполняет один запрос к агенту и печатает результат."""
    # Убираем пустые значения чтобы не передавать пустые строки в MCP
    mcp_env = {k: v for k, v in env.items() if v}

    # Параметры MCP сервера
    server_params = StdioServerParameters(
        command="uv",
        args=[
            "run",
            "--with",
            "mcp-clickhouse",
            "--python",
            "3.13",
            "mcp-clickhouse",
        ],
        env=mcp_env,
    )

    print("\n🤔 Обработка запроса...\n")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
                agent = create_react_agent("anthropic:claude-sonnet-4-6", tools)

                handler = UltraCleanStreamHandler()
                async for chunk in agent.astream_events(
                    {"messages": [{"role": "user", "content": prompt}]}, version="v1"
                ):
                    handler.handle_chunk(chunk)

                print("\n")
    except Exception as exc:
        print(f"\n❌ Ошибка при выполнении запроса: {exc}")
        exc_str = str(exc).lower()

        if "anthropic_api_key" in exc_str or "authentication" in exc_str:
            print("   → Проверьте правильность ANTHROPIC_API_KEY в файле .env")
        elif "mcp-clickhouse" in exc_str:
            print("   → Убедитесь, что mcp-clickhouse установлен: pip install mcp-clickhouse")
        elif "mcp" in exc_str or "clickhouse" in exc_str or "connect" in exc_str:
            print(
                "   → Проверьте настройки ClickHouse (хост, порт, пользователь, пароль, сертификат)"
            )
        raise


# ─── Точка входа ──────────────────────────────────────────────────────────────


def main() -> None:
    print("=" * 60)
    print("  ClickHouse LangChain Agent")
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
