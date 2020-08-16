#!/bin/bash
LOG_DIR="/var/log/enviroplussensorstomqtt"
PID_DIR="/run/enviroplussensorstomqtt"

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

echo "Installing systemd script"
cp systemd/enviroplussensorstomqtt.service /etc/systemd/system/enviroplussensorstomqtt.service
chmod 644 /etc/systemd/system/enviroplussensorstomqtt.service

echo "Reloading systemd"
systemctl --user daemon-reload
systemctl daemon-reload

echo "Starting service"
systemctl start enviroplussensorstomqtt

echo "Enabling service on boot"
systemctl enable enviroplussensorstomqtt