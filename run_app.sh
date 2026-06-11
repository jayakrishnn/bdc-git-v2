#!/bin/bash
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  BDC AI Assistant — starting up"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Activate venv if it exists
if [ -d "venv" ]; then
  source venv/bin/activate
  echo "✅ Virtual environment activated"source
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install streamlit requests "generative-ai-hub-sdk[all]" -q

# Run app
echo "🚀 Starting app..."
echo ""
streamlit run chat_app.py --server.port 8501 --server.headless true
