#!/bin/bash
HOST=$(tailscale status | head -n 1 | awk '{ print $3 }')
tailscale cert --min-validity 6969699s $HOST