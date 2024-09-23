#!/bin/bash
screen -LRR -dmS auto -c /etc/screenrc venv/bin/python3 main.py
echo "Авто запущен в фоне!"