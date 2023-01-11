---
title: "Run Cosmos SDK on Raspberry Pi"
emoji: "🏺"
type: "tech" # tech: 技術記事 / idea: アイデア
topics: []
published: false
---

# Raspberry Pi 上で Cosmos SDK を動かす

```
pi@pirite:~ $ sudo apt install -y build-essential
```

[go.dev/dl](https://go.dev/dl/) から Linux/ARM64 用 go 1.18 バイナリの最新版をダウンロードして展開。

```
pi@pirite:~ $ wget https://go.dev/dl/go1.18.4.linux-arm64.tar.gz
pi@pirite:~ $ sudo tar -C /usr/local -xzf go1.18.4.linux-arm64.tar.gz
pi@pirite:~ $ /usr/local/go/bin/go version
go version go1.18.4 linux/arm64   ✅
```

目的のバージョンを取得してビルドを行う。

```
pi@pirite:~ $ cd git
pi@pirite:~/git $ git clone https://github.com/cosmos/cosmos-sdk.git -b v0.45.6
pi@pirite:~/git/cosmos-sdk $ make build
pi@pirite:~/git/cosmos-sdk $ build/simd version
0.45.6   ✅
```