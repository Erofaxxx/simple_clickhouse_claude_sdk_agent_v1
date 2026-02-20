#!/usr/bin/env bash
# setup.sh — первоначальная настройка ClickHouse Claude Agent на Ubuntu-сервере
# Запустить один раз:  bash setup.sh
set -euo pipefail

echo "============================================================"
echo "  ClickHouse Claude Agent — установка"
echo "============================================================"
echo

# ── 1. Зависимости системы ────────────────────────────────────────────────────
echo "📦 Обновление пакетов и установка системных зависимостей..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip curl wget ca-certificates

# ── 2. pip-зависимости ────────────────────────────────────────────────────────
echo
echo "🐍 Установка Python-зависимостей..."
pip3 install --upgrade pip --quiet
pip3 install -r "$(dirname "$0")/requirements.txt" --quiet
echo "   claude-agent-sdk и python-dotenv установлены."

# ── 3. uv (требуется для mcp-clickhouse) ─────────────────────────────────────
if command -v uv &>/dev/null; then
    echo
    echo "✅ uv уже установлен: $(uv --version)"
else
    echo
    echo "⬇️  Установка uv (менеджер Python-окружений)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Добавляем uv в PATH для текущей сессии
    export PATH="$HOME/.cargo/bin:$PATH"
    echo "✅ uv установлен: $(uv --version)"
fi

# ── 4. SSL-сертификат Яндекс ─────────────────────────────────────────────────
CERT_FILE="$(dirname "$0")/YandexInternalRootCA.crt"
if [ -f "$CERT_FILE" ]; then
    echo
    echo "✅ SSL-сертификат уже существует: $CERT_FILE"
else
    echo
    echo "⬇️  Скачивание SSL-сертификата Яндекс Cloud..."
    wget -q "https://storage.yandexcloud.net/cloud-certs/CA.pem" -O "$CERT_FILE"
    echo "✅ Сертификат сохранён: $CERT_FILE"
fi

# ── 5. .env файл ──────────────────────────────────────────────────────────────
ENV_FILE="$(dirname "$0")/.env"
EXAMPLE_FILE="$(dirname "$0")/.env.example"
if [ -f "$ENV_FILE" ]; then
    echo
    echo "✅ Файл .env уже существует."
else
    echo
    cp "$EXAMPLE_FILE" "$ENV_FILE"
    echo "📝 Создан файл .env из шаблона."
    echo "   ВАЖНО: заполните .env своими данными перед запуском агента!"
    echo "   nano $ENV_FILE"
fi

echo
echo "============================================================"
echo "  Установка завершена!"
echo "============================================================"
echo
echo "Следующие шаги:"
echo "  1. Откройте .env и заполните ваши credentials:"
echo "       nano $ENV_FILE"
echo "  2. Запустите агента:"
echo "       python3 $(dirname "$0")/agent.py"
echo
