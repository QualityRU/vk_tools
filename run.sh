#!/bin/bash
screen -LRR -dmS vk_tools -c /etc/screenrc venv/bin/python3 main.py
echo "VK TOOLS запущен в фоне!"