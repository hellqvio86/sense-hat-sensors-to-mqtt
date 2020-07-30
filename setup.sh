#/bin/bash
cd "$(dirname "$0")"
cp systemd/sensehatsensorstomqtt.service /etc/systemd/system/sensehatsensorstomqtt.service
systemctl --user daemon-reload
systemctl daemon-reload