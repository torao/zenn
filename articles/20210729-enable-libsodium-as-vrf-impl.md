---
title: "Enable libsodium as VRF Implementation"
emoji: "🏺"
type: "tech" # tech: 技術記事 / idea: アイデア
topics: ["ostracon", "line", "blockchain", "cryptography", "VRF"]
published: false
---

# [ostracon1.0](https://github.com/line/ostracon): VRF 実装に `libsodium` を有効にする

Ostracon では VRF 機能でも BLS 機能でも、フォーク元の Tendermint に C/C++ のネイティブライブラリを使用しているが、
正直、C/C++ を使用しているネイティブライブラリに関連するビルド環境の問題はとても根深い。

## ビルド用のライブラリをインストール

Linux でも macOS でも libsodium のビルドは追加の開発ツールやライブラリが必要となる。`make prepare-libsodium` を実行すれば環境ごとにインストールするようにしたが、手動で実行しても良い。

```
# macOS
$ brew install libtool autoconf automake

# Linux
$ apt-get update && apt-get -y install libtool libboost-all-dev autoconf build-essential
```

ビルド時に `libsoilum` タグが有効になっていれば libsodium とリンクし、そうでなければ VRF の golang 実装である r2ishiguro を使用する。Makefile を見ると `LIBSODIUM=1` という定義があれば良いらしい。

golangci-lint で失敗している。`import "C"` が認識されないらしい。ローカルの Docker で実行して同じエラーが出ることを確認した (`v1.31` は `.github/workflows/lint.yaml` に記述があるバージョンを使用する)。

github actions と同等の lint をローカルで実行する場合:

```
docker run --rm -v $(pwd):/app -w /app golangci/golangci-lint:v1.31 golangci-lint run --out-format=github-actions --timeout 10m --skip-files "_test\.go"
```

オプションは `.github/workflow/lint.yaml` 参照。

## ビルドの手順

1. まだサブモジュールとして `crypto/vrf/internal/vrf/libsodium` を取得してなければ `git submodule update -i` を実行して取得する。
2. libsodium をビルドする。
    * macos: `make prepare-libsodium-linux` からの `make libsodium`
    * linux: docker コンテナからビルド
        1. `docker run --rm -it -v \'pwd\':/opt ubuntu:latest bash`
        2. `apt-get update`
