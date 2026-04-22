#!/bin/bash

# Configuration
CONDA_PATH="/Users/aslan_nejad/miniconda3/bin/conda"
ENV_NAME="unoconv-api"
API_DIR="api"

echo "🚀 Starting unoconv-api setup..."

# 1. Initialize Conda for this script
if [ -f "$CONDA_PATH" ]; then
    echo "✅ Found Conda at $CONDA_PATH"
    eval "$($CONDA_PATH shell.bash hook)"
    
    # Create environment if it doesn't exist
    if ! conda info --envs | grep -q "$ENV_NAME"; then
        echo "📦 Creating Conda environment '$ENV_NAME'..."
        conda create -y -n "$ENV_NAME" python=3.12
    fi
    
    echo "🔄 Activating environment '$ENV_NAME'..."
    conda activate "$ENV_NAME"
else
    echo "⚠️ Conda not found. Falling back to venv..."
    if [ ! -d "$API_DIR/venv" ]; then
        echo "📦 Creating venv (with pip workaround)..."
        python3 -m venv --without-pip "$API_DIR/venv"
        source "$API_DIR/venv/bin/activate"
        curl -s https://bootstrap.pypa.io/get-pip.py | python3
    else
        source "$API_DIR/venv/bin/activate"
    fi
fi

# 2. Check for .env file
if [ ! -f "$API_DIR/.env" ]; then
    echo "📝 Creating .env file from example..."
    cp "$API_DIR/.env.example" "$API_DIR/.env"
fi

# 3. Install dependencies
echo "📥 Installing/Updating dependencies..."
pip install -r "$API_DIR/requirements.txt"

# 4. Start the server
echo "🚀 Starting FastAPI server..."
cd "$API_DIR" && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
