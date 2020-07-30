#/bin/bash
echo "Changing directory to $(dirname "$0")"
cd "$(dirname "$0")"

echo "Installing systemd script"
cp systemd/sensehatsensorstomqtt.service /etc/systemd/system/sensehatsensorstomqtt.service

echo "Reloading systemd"
systemctl --user daemon-reload
systemctl daemon-reload

systemctl start sensehatsensorstomqtt