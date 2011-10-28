#!/bin/bash
IP=192.168.1.76
PORT=5000

python corpus_rec.py -n 4 --client -i $IP -p $PORT
