#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 各種設定項目 ##################################################

# モジュール読み込み #############################################
import urllib.request, urllib.parse # urlエンコードや，送信など
import re                           # 検索，置換など
import sys                          # system周りの制御用（exit）

# メッセージをAPIに送信 ##########################################
def send_message(input_message):
    response = '何言ってるの？' # default の返事
    led_key = '0'

    if 'こんにちは' in input_message:
        response = 'こんにちは〜'
        led_key = 'up'
    elif '可愛い' in input_message:
        response = '恥ずかしいです'
        led_key = 'pink' 
    elif '単純' in input_message:
        response = '怒りますよ'
        led_key = 'red'
    elif 'さようなら' in input_message:
        response = 'はーい。バイバイ'
        led_key = '0'

    return (response,led_key)

# APIへメッセージを送信し，受信したメッセージをパース ###############
def send_and_get(input_message):
    return send_message(input_message)

# メイン部分（本スクリプトを直接実行した際に実行される部分） #########
def main():
    message = ''
    while message != 'バイバイ':
        print('あなた：', file=sys.stderr, end="")
        sys.stderr.flush()
        message = input('')
        resp_api = send_and_get(message)
        resp = resp_api[0]
        led_key = resp_api[1]

        print('相手　：', file=sys.stderr, end="")
        sys.stderr.flush()
        print(resp)


#################################################################
# メイン部分（本スクリプトを直接実行した際に実行される部分） #########
if __name__ == '__main__':
    main()
