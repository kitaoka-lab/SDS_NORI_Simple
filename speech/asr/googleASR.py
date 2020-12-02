#!/usr/bin/env python

# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# [START speech_transcribe_streaming_mic]

##################################################
# import modules #################################
from __future__ import division

import re
import sys
import os
import signal

import numpy as np

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import pyaudio
from six.moves import queue

###################################################
# 初期設定 #########################################
#DEBUG           = True      # debug 表示のON/OFF
VIEW_VOL        = True     # 音量表示
VIEW_INTERIM    = True     # 途中結果表示
TIME_OUT        = 20        # google cS2T のタイムアウトの秒数

# 音声録音パラメータ --------------------
RATE    = 16000
CHUNK   = int(RATE / 10)  # 100ms

# APIキーファイル ----------------------
# API_KEY_FILE        = 'GoogleCloudAPI-ASRtest-3a9a386fe159.json'
API_KEY_FILE        = 'GoogleCloudAPI_secret_shirase20190618.json'

# 認識用設定 ---------------------------
LANG_CODE           = 'ja-JP'   # 認識対象言語（a BCP-47 language tag）
flag_recogRepeat    = True      # 音声認識を繰り返し行うモード（Falseだと，１発話で終了）
DECIBEL_THRESHOLD   = -30       # しきい値を超えたらgoogle音声認識開始

# START_FRAME_LEN = 4  # 録音開始のために，何フレーム連続で閾値を超えたらいいか
START_BUF_LEN = 5  # 録音データに加える，閾値を超える前のフレーム数　（START_FRAME_LENの設定によって，促音の前の音が録音されない問題への対処用）

# 認識用語彙指定 ------------------------
speech_contexts = ["きたおかのりひで","いけめん"]



# 初期設定ここまで ###################################
###################################################

# APIキー読み込み用に，環境変数を設定する ###############
ProgramPath = os.path.dirname(os.path.abspath(__file__))    ## メインのプログラム（このファイル）が置かれている場所を取得
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ProgramPath + "/" + API_KEY_FILE

# global 変数 #####################################
is_final            = False     # 最終結果が入ったかどうかのフラグ
result_final        = None      # 最終認識結果
result_interim      = None      # 認識途中結果

language_code           = LANG_CODE # a BCP-47 language tag  (http://g.co/cloud/speech/docs/languages)

# google cloud API用 config パッケージング ##########
config = types.RecognitionConfig(
    encoding            = enums.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz   = RATE,
    language_code       = language_code,
    speech_contexts=[types.cloud_speech_pb2.SpeechContext(
        phrases=speech_contexts
        )]
    )

streaming_config = types.StreamingRecognitionConfig(
    config              = config,
    interim_results     = True,
    single_utterance    = True)

# google cloud API に接続 #########################
client = speech.SpeechClient()




##################################################
##################################################
# class 定義 ######################################
class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

        self._frames_start = []     # 指定フレーム`START_BUF_LEN `分バッファする

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            self._frames_start.extend(data)
            # 促音用バッファが長過ぎたら捨てる（STARTフレームより更に前のデータを保存しているバッファ）
            if len(self._frames_start) > START_BUF_LEN:
                del self._frames_start[0:len(self._frames_start) - START_BUF_LEN]

            yield b''.join(data)

    def start_buf_appendleft(self):
        for frame in self._frames_start:
            self._buff.put(frame)


# 結果表関数 #########################################
def listen_print_loop(responses):
    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue

        result = response.results[0]
        if not result.alternatives:
            continue

        # 音声認識結果取り出し
        transcript = result.alternatives[0].transcript
        overwrite_chars = '　' * (num_chars_printed - len(transcript))

        if not result.is_final:     # is_final じゃなかったら
            if VIEW_INTERIM:
                sys.stdout.write(transcript + overwrite_chars + '\r')
                sys.stdout.flush()

                num_chars_printed = len(transcript)

        else:                       # is_final だったら
            # 音声認識結果に | （縦棒）が含まれていたら，ない状態に置き換えて認識結果として保持
            transcript = re.sub(r'(\|\S*(\s|$))?', '', transcript)

            if VIEW_INTERIM: print(transcript + overwrite_chars)
            return transcript


# main関数 ###################################################
def googleASR():
    # マイクとの接続（音声認識が終わったら，withから抜けて，マイクとの接続も切れる）
    with MicrophoneStream(RATE, CHUNK) as stream:
        # マイクから音声を取得して， audio_generatorに入れ続ける
        audio_generator = stream.generator()

        # 1フレーム目にゴミが入る場合があるので捨てる
        audio_generator.__next__()

        #############################################
        # ●●audio_generatorを監視して，音量チェック●●
        for content in audio_generator:
            # 1フレーム内の音量計算--------------------------------
            content_int16 = np.frombuffer(content,'int16') # intに変換
            sq = np.square(content_int16/32768.0)
            rm = np.mean(sq)
            rms = np.sqrt(rm)
            decibel = 20 * np.log10(rms) if rms > 0 else 0
            
            if VIEW_VOL:
                sys.stdout.write("\rrm {:15.10f} rms {:15.10f} decibel {:10.4f}".format(rm, rms, decibel))
                sys.stdout.flush()

            # 音量が閾値より大きくなったら，ループを抜ける！ ----
            if decibel > DECIBEL_THRESHOLD:
                if VIEW_VOL: print()
                stream.start_buf_appendleft()
                break

        #############################################
        # audio_generatorにデータが入ると，それをgoogleに送る形にパックする（複数列）
        requests = (types.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)

        # requestsパック（複数）をgoogleに送りつけ，結果を受け取りresponsesに入れる
        responses = client.streaming_recognize(streaming_config, requests, timeout=TIME_OUT)

        # googleから受け取った結果が解析され続ける
        try:
            transcript = listen_print_loop(responses)
        except Exception as e:
            print('\n[{}] 例外args: {}'.format(os.path.basename(__file__), e.args))
            return ''

        # 音声認識結果（Final）を返す
        return transcript


# ctrl+c 対応 ##################################################
def handler(signal, frame):
    print('\n[{}] CTRL+Cで終了します！'.format(os.path.basename(__file__)))
    sys.exit(0)

signal.signal(signal.SIGINT, handler)


# メイン部分（本スクリプトを直接実行した際に実行される部分） #########
if __name__ == '__main__':
    VIEW_VOL        = True  # 音量の表示をする
    VIEW_INTERIM    = True  # 途中結果を表示する

    # メインプログラムのメインループ ####################################
    cnt = 0
    while True:
        print('Start Rec!')
        transcript = googleASR()

        print('RESULT[{:>3}]: {}'.format(cnt, transcript))
        cnt = cnt + 1

        # 繰り返し音声認識する設定かどうか：繰り返さないなら抜ける#########
        if not flag_recogRepeat:
            break


# [END speech_transcribe_streaming_mic]
