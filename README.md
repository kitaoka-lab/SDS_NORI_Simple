# NORI_Base_simple : 雑談対話APIを用いた　音声対話システム
プログラム：徳島大学　社会産業理工学研究部　講師　西村良太　nishimura@is.tokushima-u.ac.jp
開始日：2019年10月3日

## 準備：必要となるライブラリや、pythonライブラリを入れる
```shell
$ sudo apt-get install portaudio19-dev
$ pip install pyaudio

$ pip install --upgrade google-cloud-speech
$ sudo apt install open-jtalk
```


## 実行方法

### （１）　ソースのダウンロード ＆ 展開

### （２）　以下を実行
`$ python NORI_Base.py -i julius -o jtalk -a test`

## 設定
### google 音声認識を使うとき
以下URLの，１〜３を参考にして，APIキー入りの `.json` ファイルをダウンロード．  
https://qiita.com/egplnt/items/802de5fd0f36f1af3268  
  
`SDS_NORI_Simple/speech/asr/` 内にjsonファイルをいれて，そのファイル名を，`googleASR.py` の５０行目に書き込む．
```python
API_KEY_FILE        = 'ここ'
```


## エラーが起こるとき
### 【juliusが実行できない】
./SDS_NORI_Base/speech/julius/bin/linux/ 内のバイナリファイルに実行権限を与えてください

```shell
$ cd ./SDS_NORI_Base/speech/julius/bin/linux/
$ chmod 755 *
```

### pyaudio利用時にメッセージがたくさん出る
以下のようなメッセージが、音声認識時に毎回出る。

```
ALSA lib pcm.c:2266:(snd_pcm_open_noupdate) Unknown PCM cards.pcm.rear
ALSA lib pcm.c:2266:(snd_pcm_open_noupdate) Unknown PCM cards.pcm.center_lfe
ALSA lib pcm.c:2266:(snd_pcm_open_noupdate) Unknown PCM cards.pcm.side
ALSA lib pcm_route.c:867:(find_matching_chmap) Found no matching channel map
```

これは、以下のファイルの当該行をコメントアウトすれば良い。

`usr/share/alsa/alsa.conf`

130行目あたり。

```
pcm.rear cards.pcm.rear
pcm.center_lfe cards.pcm.center_lfe
pcm.side cards.pcm.side
```
