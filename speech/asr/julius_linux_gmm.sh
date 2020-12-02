#! /bin/sh

$1/julius/bin/linux/julius -C $1/julius/main.jconf -C $1/julius/am-gmm.jconf -input mic -module $2 $3

