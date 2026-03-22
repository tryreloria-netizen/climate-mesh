#!/bin/bash
# Climate Mesh — Raspberry Pi setup script
# Run: chmod +x setup_pi.sh && ./setup_pi.sh

set -e

echo "=================================="
echo "  Climate Mesh — Pi Setup"
echo "=================================="

# 1. Python dependencies
echo "[1/4] Installing Python packages..."
pip install -r requirements.txt
pip install adafruit-circuitpython-ads1x15

# 2. Vernier GDX helper module
if [ ! -d "gdx" ]; then
    echo "[2/4] Downloading Vernier GDX helper module..."
    tmp_dir=$(mktemp -d)
    git clone --depth 1 https://github.com/VernierST/godirect-examples.git "$tmp_dir"
    cp -r "$tmp_dir/python/gdx" ./gdx
    rm -rf "$tmp_dir"
else
    echo "[2/4] GDX helper already present, skipping."
fi

# 3. Enable I2C if not already enabled
if ! raspi-config nonint get_i2c 2>/dev/null | grep -q "0"; then
    echo "[3/4] Enabling I2C..."
    sudo raspi-config nonint do_i2c 0
else
    echo "[3/4] I2C already enabled."
fi

# 4. Create default sensor config if missing
config_file="data/sensor_config.json"
if [ ! -f "$config_file" ]; then
    echo "[4/4] Creating default sensor config..."
    mkdir -p data
    cat > "$config_file" << 'CONF'
{
    "mode": "auto",
    "pi_nodes": [
        {
            "node_id": "PI-01",
            "environment": "residential",
            "gdx_connection": "usb",
            "ads1115_channel": 0,
            "poll_interval_seconds": 2
        }
    ]
}
CONF
else
    echo "[4/4] Sensor config already exists, skipping."
fi

echo ""
echo "=================================="
echo "  Setup complete!"
echo "=================================="
echo ""
echo "To run Climate Mesh:"
echo "  Terminal 1:  python run.py --mode auto"
echo "  Terminal 2:  python -m streamlit run dashboard/app.py"
