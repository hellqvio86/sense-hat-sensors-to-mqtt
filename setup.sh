#!/bin/bash
LOG_DIR="/var/log/sensehatsensorstomqtt"
PID_DIR="/run/sensehatsensorstomqtt"
BIN_FILE="/usr/local/bin/sensehatsensorstomqtt"

echo "Changing directory to $(dirname "$0")"
cd "$(dirname "$0")"

if [ ! -d $LOG_DIR ]; then
  mkdir $LOG_DIR
  chown pi:pi $LOG_DIR
fi

if [ ! -d $PID_DIR ]; then
  mkdir $PID_DIR
  chown pi:pi $PID_DIR
fi

if [ ! -f $BIN_FILE ]; then
  rm $BIN_FILE
fi

pip3 install -e .

echo "Installing systemd script"
cp systemd/sensehatsensorstomqtt.service /etc/systemd/system/sensehatsensorstomqtt.service
chmod 644 /etc/systemd/system/sensehatsensorstomqtt.service

echo "Reloading systemd"
systemctl --user daemon-reload
systemctl daemon-reload

echo "Starting service"
systemctl start sensehatsensorstomqtt

echo "Enabling service on boot"
systemctl enable sensehatsensorstomqtt