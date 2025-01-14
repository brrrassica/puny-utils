#/bin/bash

systemctl stop corosync.service
systemctl stop pve-cluster.service
systemctl stop corosync
systemctl stop pve-cluster

pmxcfs -l
rm /etc/pve/corosync.conf
rm /etc/corosync/*
rm /var/lib/corosync/*

# Nuke all currently available nodes. Destructive, but sometimes useful if you wanna start over.
# rm -rf /etc/pve/nodes/*

killall pmxcfs
sleep 30

# Sometimes this will fail
#systemctl start pve-cluster
systemctl start corosync
systemctl start pve-cluster.service
systemctl start corosync.service

