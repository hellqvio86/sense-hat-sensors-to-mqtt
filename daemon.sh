#/bin/bash
cd /home/pi/git/sensehatsensorstomqtt
/usr/bin/python3 -m src.sensehatsensorstomqtt.__main__ --config_file /etc/sensehatsensorstomqtt.yaml --daemon
