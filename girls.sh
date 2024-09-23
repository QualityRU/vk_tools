#!/bin/bash
screen -LRR -dmS girls -c /etc/screenrc venv/bin/python3 main2.py
echo "Девушки запущен в фоне!"