#!/usr/bin/env bash
# Iniciar el servidor de desarrollo
# Uso: bash start.sh [--port 8000]
set -e

PORT=${1:-8000}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3.12 -m venv venv
fi

echo "Activando entorno virtual..."
source venv/bin/activate

echo "Instalando/verificando dependencias..."
pip install -r requirements.txt -q

echo "Iniciando servidor en http://localhost:${PORT}"
echo "Abre http://localhost:${PORT}/ en tu navegador para acceder al sistema."
uvicorn main:app --reload --host 0.0.0.0 --port "$PORT" --env-file ../.env
