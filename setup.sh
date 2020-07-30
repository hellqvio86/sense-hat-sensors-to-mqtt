#/bin/bash
echo "Changing directory to $(dirname "$0")"
cd "$(dirname "$0")"

if [ ! -d "/var/log/sensehatsensorstomqtt" ]; then
  # Control will enter here if $DIRECTORY doesn't exist.
  mkdir /var/log/sensehatsensorstomqtt
  chown pi:pi /var/log/sensehatsensorstomqtt
fi

echo "Installing systemd script"
cp systemd/sensehatsensorstomqtt.service /etc/systemd/system/sensehatsensorstomqtt.service

echo "Reloading systemd"
systemctl --user daemon-reload
systemctl daemon-reload

systemctl start sensehatsensorstomqtt
systemctl enable sensehatsensorstomqtt