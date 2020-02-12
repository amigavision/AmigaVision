#!/usr/bin/env python3

with open("gamelist.txt", "r") as f:
    for l in f:
        l = l.replace("\n", "")
        l = l.split("/", 1)[0]
        print(l)
