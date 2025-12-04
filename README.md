



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


Port 80 Binding
The "Invalid file for capability operation" error from setcap happens because /usr/bin/python3 is a symlink (likely to /usr/bin/python3.13 on Ubuntu 25). setcap only works on actual ELF binaries, not symlinks. Fix it like this:

Find the Real Python Binary:textrealpath /usr/bin/python3
Output should be something like /usr/bin/python3.13 (confirm yours).

Apply setcap to the Real Binary:
Replace /usr/bin/python3.13 with your actual path:textsudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.13
Update and Restart the Systemd Service:
Edit the service file if not already done:textsudo vim /etc/systemd/system/webhook.serviceEnsure it looks like this (use the real binary path in ExecStart if needed; /usr/bin/python3 should work now since the capability propagates):text[Unit]
Description=LuxAlgo Webhook Collector
After=network.target

[Service]
User=ryan_tischer
WorkingDirectory=/home/ryan_tischer/bot
ExecStart=/usr/bin/python3 /home/ryan_tischer/bot/webhook.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.targetReload and restart:textsudo systemctl daemon-reload
sudo systemctl restart webhook.service
sudo systemctl status webhook.service
If active, test with curl: curl -X POST http://localhost/lux_oscillator -d '{"test":1}' -H "Content-Type: application/json".

Firewall: Allow port 80 if not already:textsudo ufw allow 80/tcp
sudo ufw reload

If setcap still fails (rare), run the service as root by changing User=ryan_tischer to User=root (less secure) or use nginx as a reverse proxy (install sudo apt install nginx, configure to forward 80 to 5000).
System Time (Timezone)
Your time is in UTC (Thu Dec 4 01:13:06 UTC 2025). The bot code uses datetime.now() which respects system timezone, so for Eastern Time (ET):
textsudo timedatectl set-timezone America/New_York
date  # Verify (should show EST/EDT)

Reboot if needed: sudo reboot.
The bot's hour checks (e.g., 9-16 ET) will now align correctly without code changes.

Test the bot/webhook integration after this. If errors, share journalctl -u webhook.service -e output.
