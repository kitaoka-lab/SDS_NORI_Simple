#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

def out_tts(t):
    print('あなた：' + t, file=sys.stderr)

if __name__ == '__main__':
    while True:
        print('あなた：', end="")
        message = input('')

        out_tts(message)
