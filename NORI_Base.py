#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
# 雑談対話APIを用いた　音声対話システム
プログラム：北岡研究室　講師　西村良太　nishimura@is.tokushima-u.ac.jp
開始日：2019年10月3日
'''

# モジュール読み込み #############################################
from optparse import OptionParser   # オプション解析用
import platform                     # 利用中のOSの名前を読み込む
import sys                          # system周りの制御用
import time                         # sleepを利用する
import glob, os                     # APIのファイル名を取得する
from datetime import datetime       # ファイル名のために
import signal                       # ctrl+c をつかむため

import threading                    # 音声合成を別スレッドで実行（ボタンで停止させるため）
import socket                       # ボタン状態取得用

# 各種設定項目 ##################################################
OSlist = ["Windows", "Darwin", "Linux"]     # 対応するOSのリスト（platform.system()で得られる値にすること）

JULIUS_HOST = 'localhost'
JULIUS_PORT = 10500

NORI_STARTTIME = datetime.now()
START_DATE = NORI_STARTTIME.strftime("%Y%m%d_%H%M%S")
LOG_DIR = os.path.abspath(os.path.dirname(__file__)) + '/log/' + START_DATE +'/'


# ctrl+c 対応 ##################################################
def handler(signal, frame):
    print('\nCTRL+Cで終了します！')
    if options.input == "julius":     # 入力方法が julius なら
        julius.kill()
    sys.exit(0)

signal.signal(signal.SIGINT, handler)


# オプション解析 #################################################
def readOption():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage, version="%prog 1.0")
    parser.add_option("-a", "--api",        type="string",          dest="api",     default=Dialog_APIList[0],
                    help="select dialogue API (" + ', '.join(Dialog_APIList) + ")",     metavar="API")

    parser.add_option("-i", "--input",      type="string",          dest="input",   default=IN_APIList[0],
                    help="select input method (" + ', '.join(IN_APIList) + ")",         metavar="InputMethod")

    parser.add_option("-o", "--output",     type="string",          dest="output",  default=OUT_APIList[0],
                    help="select output method (" + ', '.join(OUT_APIList) + ")",       metavar="OutputMethod")

    parser.add_option("-r", "--sp_rate",    type="string",          dest="sp_rate", default="1.0", action="store",
                    help="[speech rate] for TTS system")

    parser.add_option("-p", "--sp_pause",   type="float",           dest="sp_pause",default="0.0", action="store",
                    help="[speech pause] for TTS system")

    parser.add_option("-l", "--log",        action="store_false",   dest="log",     default=True,
                    help="NOT log the text & speech data")                

    parser.add_option("-L", "--led",        action="store_true",    dest="led",     default=False,
                    help="use LED HIKARI agent")

    parser.add_option("-d", "--debug",      action="store_true",    dest="debug",   default=False,
                    help="print all debug messages")

    return parser.parse_args()


# カウントダウン スリープ #########################################
def countdown(t): # in seconds
    print('count down: ', end="")
    for i in range(t,0,-1):
        print(str(i) + " ", end="")
        sys.stdout.flush()
        time.sleep(1)
    print("")


#################################################################
# メイン部分（本スクリプトを直接実行した際に実行される部分） #########
if __name__=="__main__":


    ##################################################################
    # オプション関連処理                                                #
    ##################################################################

    # APIファイルの存在をチェックする(オプション表示用にリストを作る) %%%%%%%%%%%%%%%%%%%
    # 対話処理API -------------------------------------
    Dialog_APIList = [os.path.basename(r.replace('.py', '')) for r in glob.glob('./DialogAPI/*.py')]    # APIディレクトリをlsして，パスをファイル名だけにして，リスト化
    Dialog_APIList.remove('__init__')

    # 音声認識API -------------------------------------
    IN_APIList = [os.path.basename(r.replace('.py', '')) for r in glob.glob('./speech/asr/*.py')]       # APIディレクトリをlsして，パスをファイル名だけにして，リスト化

    # 音声合成API -------------------------------------
    OUT_APIList = [os.path.basename(r.replace('.py', '')) for r in glob.glob('./speech/tts/*.py')]      # APIディレクトリをlsして，パスをファイル名だけにして，リスト化


    # オプションチェック %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    (options, args) = readOption()
    
    # 指定されたAPIファイルがあるかどうか確認 %%%%%%%%%%%%%%%%%%%%%%%%
    # Dialog API -------------------------------------
    if options.api in Dialog_APIList:
        print ("Dialog API: " + options.api)
    else:
        print ("\n[ERROR] There is no such API (" + options.api + "). Only for (" + ', '.join(Dialog_APIList) + ").")
        sys.exit()

    # INPUT Method -------------------------------------
    if options.input in IN_APIList:
        print ("Input: " + options.input)
    else:
        print ("\n[ERROR] There is no such INPUT (" + options.input + "). Only for (" + ', '.join(IN_APIList) + ").")
        sys.exit()

    # Output Method -------------------------------------
    if options.output in OUT_APIList:
        print ("Output: " + options.output)
    else:
        print ("\n[ERROR] There is no such OUTPUT (" + options.output + "). Only for (" + ', '.join(OUT_APIList) + ").")
        sys.exit()
    
    # log flag ----------------------------------------
    if options.log:
        print ("LOG: " + str(options.log))

    # debug flag ----------------------------------------
    if options.debug:
        print ("DEBUG: " + str(options.debug))


    # OSチェック %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    if platform.system() in OSlist:
        print ("OS: " + platform.system())
    else:
        print ("\n[ERROR] This program does not support this OS (" + platform.system() + "). Only for (" + ', '.join(OSlist) + ").")
        sys.exit()



    ##################################################################
    # API読み込み ＆ 関連サーバ起動処理                                   #
    ##################################################################

    # API 読み込み %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # 対話処理API --------------------------------
    api_module = __import__('DialogAPI.' + options.api)             # モジュールの動的インポート

    # 音声認識API --------------------------------
    in_api_module = __import__('speech.asr.' + options.input)       # モジュールの動的インポート
    print ("SUCCESS! (launch the input method)")

    # 音声合成API --------------------------------
    out_api_module = __import__('speech.tts.' + options.output)     # モジュールの動的インポート
    print ("SUCCESS! (launch the output method)")
        

    # 音声認識器がjuliusの場合，その起動処理 %%%%%%%%%%%%%%%%%%%%%%
    if options.input == "julius":               # input オプションが「julius」に設定されていたら
        from speech.asr import julius           # Juliusモジュール読み込み（サーバ起動など，初期化処理もなされる）
        import socket                           # juliusとのソケット通信用

        # LOG設定とjulius起動
        if options.log:
            julius.LOG_OPT = '-record'              # オプション設定
            julius.LOG_DIR = LOG_DIR + 'user_julius/'    # ディレクトリ設定
            if not os.path.exists(julius.LOG_DIR):
                os.makedirs(julius.LOG_DIR)         # ディレクトリが無かったら作る

        julius.prog_starttime = NORI_STARTTIME
        julius.startup()

        # julius起動を待つ：DNN版だと起動に8秒ほどかかる（1秒毎にカウントダウンを表示）
        print ("Waiting for julius... ", end="")
        countdown(10)

         # TCPクライアントを作成し，本プログラムとjuliusサーバを接続
        print ("Connect to julius server ...  ")
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect((JULIUS_HOST, JULIUS_PORT))
        except:
            print ('Unalbe to connect julius server ...')  

            exit()
        print ("OK!")

    # 音声認識器がgoogleの場合，その起動処理 %%%%%%%%%%%%%%%%%%%%%%
    if options.input == "googleASR":            # input オプションが「google」に設定されていたら
        from speech.asr import googleASR as asr    # googleモジュール読み込み

        # # google ASRの設定
        # asr.VIEW_VOL       = True              # 音量表示
        # asr.VIEW_INTERIM   = True              # 途中結果表示
        # asr.TIME_OUT       = 20                # google cS2T のタイムアウトの秒数


    # 音声合成器(openJTalk)モジュール読み込み %%%%%%%%%%%%
    if options.output == "jtalk":               # input オプションが「julius」に設定されていたら
        from speech.tts import jtalk            # Juliusモジュール読み込み（サーバ起動など，初期化処理もなされる）

        jtalk.prog_starttime = NORI_STARTTIME

        # 話速とポーズの値を伝える
        jtalk.speech_rate = options.sp_rate
        jtalk.speech_pause = options.sp_pause

        if options.log:
            jtalk.LOG_DIR = LOG_DIR + 'system_open_jtalk/'
            if not os.path.exists(jtalk.LOG_DIR):
                os.makedirs(jtalk.LOG_DIR)         # ディレクトリが無かったら作る


    # 対話ログ保存テキスト作成 %%%%%%%%%%%%
    if options.log:
        # ログ保存ディレクトリ作成 ---
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)

        # ログ保存テキスト作成 ---
        fp_log_txt = open(LOG_DIR + "dialog_log_" + START_DATE + ".txt", 'w')



    ##################################################################
    # 対話処理                                                         #
    ##################################################################

    # 対話ループ ##################################
    message = ''
    sys.stderr.flush()
    sys.stdout.flush()

    while True:
        # 初期化：１ターン毎 %%%%%%%%%%%%%%%%%%%
        start_asr   = '0'   # 音声認識開始時間
        end_asr     = '0'   # 音声錦終了時間
        start_tts   = '0'   # 音声合成開始時間
        end_tts     = '0'   # 音声合成終了時間

        # ユーザ入力ターン %%%%%%%%%%%%%%%%%%%%%
        print('>', file=sys.stderr, end="")
        sys.stderr.flush()

        if options.input == "text":         # 入力方法が text なら
            message = input('')

        elif options.input == "julius":     # 入力方法が julius なら
            (start_asr, end_asr, message) = julius.julius_output(client)
            print (message)
            sys.stdout.flush()
            julius.julius_pause(client)     # juliusエンジンを止める

        elif options.input == "googleASR":     # 入力方法が google なら
            st = datetime.now() - NORI_STARTTIME    # 音声認識開始時間取得
            start_asr = '%02d:%02d:%02d.%06d'%(st.seconds//3600, (st.seconds//60)%60, st.seconds%60, st.microseconds)
            
            message   = asr.googleASR()            # 音声認識

            st = datetime.now() - NORI_STARTTIME    # 音声認識終了時間取得
            end_asr   = '%02d:%02d:%02d.%06d'%(st.seconds//3600, (st.seconds//60)%60, st.seconds%60, st.microseconds)

            print (message)
            sys.stdout.flush()


        # 対話ログ保存 %%%%%%%%%%%%
        if options.log:
            fp_log_txt.write(start_asr + '\t' + end_asr + '\tUSR:\t' + message + '\n')


        # ユーザ入力を，APIに投げる %%%%%%%%%%%%%
        resp = eval('api_module.' + options.api + '.send_and_get')(message)


        # システム応答表示 %%%%%%%%%%%%%%%%%%%%%
        print('相手　：', file=sys.stderr, end="")
        sys.stderr.flush()
        print(resp)
        sys.stdout.flush()


        # 音声合成器(OpenJTalk)起動 & 再生 %%%%%
        if options.output == "jtalk":
            (start_tts, end_tts) = jtalk.jtalk(resp)


        # 対話ログ保存 %%%%%%%%%%%%
        if options.log:
            fp_log_txt.write(start_tts + '\t' + end_tts + '\tSYS:\t' + resp + '\n')


        # julius再開 %%%%%%%%%%%%
        if options.input == "julius":     # 入力方法が julius なら
            julius.julius_resume(client)     # juliusエンジン再開


    # 終了処理 %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    if options.input == "julius":
        julius.kill()

