#!/usr/bin/env bash
# setup.sh — первоначальная настройка ClickHouse Claude Agent на Ubuntu-сервере
# Запустить один раз:  bash setup.sh
set -euo pipefail

echo "============================================================"
echo "  ClickHouse Claude Agent — установка"
echo "============================================================"
echo

# ── 0. Swap (для серверов с ≤ 1 ГБ RAM) ──────────────────────────────────────
TOTAL_MEM_MB=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo)
if [ "$TOTAL_MEM_MB" -lt 1500 ]; then
    if [ "$(swapon --show | wc -l)" -le 1 ]; then
        echo "⚠️  Обнаружено мало RAM (${TOTAL_MEM_MB} МБ) и нет swap."
        echo "   Создаю swap-файл 2 ГБ для предотвращения OOM..."
        fallocate -l 2G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=2048 status=progress
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        if ! grep -q '/swapfile' /etc/fstab; then
            echo '/swapfile none swap sw 0 0' >> /etc/fstab
        fi
        echo "✅ Swap 2 ГБ создан и активирован."
    else
        echo "✅ Swap уже активен."
    fi
    echo
fi

# ── 1. Зависимости системы ────────────────────────────────────────────────────
echo "📦 Обновление пакетов и установка системных зависимостей..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip curl wget ca-certificates

# ── 2. pip-зависимости (включая mcp-clickhouse) ──────────────────────────────
echo
echo "🐍 Установка Python-зависимостей..."
pip3 install --upgrade pip --quiet
pip3 install -r "$(dirname "$0")/requirements.txt" --quiet
echo "   claude-agent-sdk, python-dotenv и mcp-clickhouse установлены."

# ── 3. SSL-сертификат Яндекс ─────────────────────────────────────────────────
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

# ── 4. .env файл ──────────────────────────────────────────────────────────────
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
