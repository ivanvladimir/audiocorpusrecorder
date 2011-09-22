#!/bin/bash
IP=127.0.0.1
PORT=5000

python corpus_rec.py -n 4 --client -i $IP -p $PORT
