#!/bin/bash
# Setup script for ClickHouse LangChain Agent
# Устанавливает все необходимые зависимости для работы LangChain агента

set -e  # Завершить при ошибке

echo "=========================================="
echo "  ClickHouse LangChain Agent Setup"
echo "=========================================="
echo

# Проверка прав root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Запуск от root. Пакеты Python будут установлены глобально."
else
    echo "ℹ️  Запуск от обычного пользователя. Используйте sudo для системных пакетов."
fi

echo

# 1. Обновление системы и установка базовых пакетов
echo "📦 Установка системных пакетов..."
if command -v apt-get &> /dev/null; then
    apt-get update -qq
    apt-get install -y python3 python3-pip curl wget > /dev/null 2>&1
    echo "✅ Системные пакеты установлены"
else
    echo "⚠️  apt-get не найден. Убедитесь, что python3, pip, curl и wget установлены."
fi

echo

# 2. Обновление pip
echo "🔄 Обновление pip..."
python3 -m pip install --upgrade pip -q
echo "✅ pip обновлён"

echo

# 3. Установка uv (менеджер Python окружений)
echo "📥 Установка uv..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✅ uv установлен"
    echo "   Добавьте в PATH: export PATH=\"\$HOME/.cargo/bin:\$PATH\""
else
    echo "✅ uv уже установлен"
fi

echo

# 4. Установка Python зависимостей для LangChain
echo "🐍 Установка Python зависимостей для LangChain..."
pip3 install -q langchain-mcp-adapters langgraph "langchain[anthropic]" python-dotenv mcp-clickhouse
echo "✅ Python зависимости установлены"

echo

# 5. Скачивание SSL сертификата Яндекс Cloud
CERT_FILE="YandexInternalRootCA.crt"
if [ ! -f "$CERT_FILE" ]; then
    echo "🔒 Скачивание SSL сертификата Яндекс Cloud..."
    wget -q https://storage.yandexcloud.net/cloud-certs/CA.pem -O "$CERT_FILE"
    echo "✅ SSL сертификат скачан: $CERT_FILE"
else
    echo "✅ SSL сертификат уже существует: $CERT_FILE"
fi

echo

# 6. Проверка памяти и swap
echo "💾 Проверка памяти системы..."
TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
SWAP_MEM=$(free -m | awk '/^Swap:/{print $2}')

echo "   Оперативная память: ${TOTAL_MEM} МБ"
echo "   Swap: ${SWAP_MEM} МБ"

if [ "$TOTAL_MEM" -le 1024 ] && [ "$SWAP_MEM" -eq 0 ]; then
    echo "⚠️  Обнаружено ≤ 1 ГБ RAM и нет swap"
    echo "   Создание swap-файла 2 ГБ..."

    if [ "$EUID" -ne 0 ]; then
        echo "   ❌ Требуются права root для создания swap"
        echo "   Запустите: sudo bash setup_langchain.sh"
    else
        if [ ! -f /swapfile ]; then
            fallocate -l 2G /swapfile
            chmod 600 /swapfile
            mkswap /swapfile > /dev/null 2>&1
            swapon /swapfile
            echo '/swapfile none swap sw 0 0' >> /etc/fstab
            echo "✅ Swap-файл создан и активирован"
        else
            echo "✅ Swap-файл уже существует"
        fi
    fi
elif [ "$TOTAL_MEM" -le 1024 ]; then
    echo "⚠️  Система имеет ≤ 1 ГБ RAM (рекомендуется ≥ 2 ГБ)"
    echo "   Swap обнаружен (${SWAP_MEM} МБ), но могут быть проблемы с производительностью"
else
    echo "✅ Памяти достаточно"
fi

echo

# 7. Создание .env файла
if [ ! -f .env ]; then
    echo "📝 Создание файла .env из шаблона..."
    cp .env.example .env
    echo "✅ Файл .env создан"
    echo "   ⚠️  Отредактируйте .env и заполните свои данные:"
    echo "   nano .env"
else
    echo "✅ Файл .env уже существует"
fi

echo
echo "=========================================="
echo "  ✅ Установка завершена!"
echo "=========================================="
echo
echo "Следующие шаги:"
echo "1. Отредактируйте .env и заполните свои данные:"
echo "   nano .env"
echo
echo "2. Если установили uv, добавьте в PATH:"
echo "   export PATH=\"\$HOME/.cargo/bin:\$PATH\""
echo "   source ~/.bashrc  # или ~/.zshrc"
echo
echo "3. Запустите LangChain агента:"
echo "   python3 langchain_agent.py"
echo
echo "Документация: README_LANGCHAIN.md"
echo
