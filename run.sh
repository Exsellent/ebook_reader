#!/bin/bash
echo ""
echo " ============================================"
echo "  ReadAloud — E-Book Reader with Edge TTS"
echo " ============================================"
echo ""

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo " [ERROR] Python 3 not found. Install Python 3.12+"
    exit 1
fi

echo " Checking dependencies..."
pip3 install -q -r requirements.txt

echo ""
echo " Starting ReadAloud → http://localhost:5000"
echo " Press Ctrl+C to stop."
echo ""

python3 app.py
