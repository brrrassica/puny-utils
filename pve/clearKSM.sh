#!/bin/bash
echo "Disabling KSM daemon"
systemctl stop ksmtuned.service
sleep 10
echo "Clearing KSM shared pages"
echo 2 > /sys/kernel/mm/ksm/run
sleep 20
echo "Re-enabling KSM daemon"
systemctl start ksmtuned.service
