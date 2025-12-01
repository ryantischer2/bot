# bot

[Unit]
Description=LuxAlgo Webhook Collector
After=network.target

[Service]
User=ryan_tischer
WorkingDirectory=/home/ryan_tischer
ExecStart=/home/ryan_tischer/bot_env/bin/python /home/ryan_tischer/webhook.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
