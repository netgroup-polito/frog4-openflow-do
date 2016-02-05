#!/bin/bash

# Certificates on Ubuntu
# This script generate a self-signed certificate.
# (Based on https://help.ubuntu.com/12.04/serverguide/certificates-and-security.html)

rm *.crt *.csr *.key*

openssl genrsa -des3 -out server.key 2048

openssl rsa -in server.key -out server.key.insecure

openssl req -new -key server.key -out server.csr

openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt
