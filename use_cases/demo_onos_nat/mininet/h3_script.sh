#!/bin/sh
ifconfig h3-eth0 down
ifconfig h3-eth0 up
ifconfig h3-eth0 20.0.0.10/24
ifconfig h3-eth0 mtu 1450
route add default gw 20.0.0.254
tc qdisc add dev h3-eth0 root netem delay 0.250ms rate 1Gbit
