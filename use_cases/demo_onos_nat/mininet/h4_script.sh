#!/bin/sh
ifconfig h4-eth0 down
ifconfig h4-eth0 up
ifconfig h4-eth0 20.0.0.11/24
ifconfig h4-eth0 mtu 1450
route add default gw 20.0.0.254
tc qdisc add dev h4-eth0 root netem delay 0.250ms rate 1Gbit
