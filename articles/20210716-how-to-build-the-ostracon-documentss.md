---
title: "How to build the Ostracon documents"
emoji: "🏺"
type: "tech" # tech: 技術記事 / idea: アイデア
topics: ["ostracon", "line", "blockchain", "tendermint"]
published: true
---

# [ostracon1.0](https://github.com/line/ostracon): ドキュメントビルド方法

Tendermint は Vue.js のブログサイト向けフレームワークであるところの [VuePress](https://vuepress.vuejs.org/) を静的サイトジェネレータとして使っている。それを fork した Ostracon も `docs/` ディレクトリの下に Markdown で記述したドキュメントを作成すれば HTML のサイトを作成してくれる。

## ドキュメントのビルド

ドキュメントのビルドには [node.js](https://nodejs.org/) が必要なのでインストールしておく。

```
% npm --version
6.14.13
```

Ostracon 開発ディレクトリに移動して `make build-docs` を実行すればドキュメントが生成される。


```
% cd git/ostracon
% make build-docs
```

Tendermint の `Makefile` では `make build-docs` で (`docs/versions` に記述している) `main` ブランチをチェックアウトする動作だった。これによってローカルの commit 前の更新が上書きされてしまうため、現在のローカルの状態に対して実行するように修正した。

正常終了すれば `~/output` にドキュメントが生成されている。

## ブラウザで確認

`~/output` ディレクトリに移動する。

```
% cd ~/output
```

生成される HTML のパス構成はサイトのトップからを想定しているため、表示を確認するには `~/output` を docroot とする HTTP サーバが必要となる。ローカルでの確認だけなのでここでは簡易 HTTPd として express を使っておく。まだインストールしていなければ npm でインストールしてスクリプト `httpd.mjs` を作成する。

```
% npm install express
```


```js
import Express from 'express'

const app = Express();
app.use(Express.static('./'))
app.listen(8001, () => {
    console.log('server running on: http://localhost:8001')
})
```

httpd を起動してブラウザから [http://localhost:8001/main/](http://localhost:8001/main/) を表示する。

```
% node httpd.mjs
```

## HTML に拡張を加える

JS や CSS フレームワークを追加したい場合は `.vuepress/config.js` の [`head` エントリ](https://vuepress.vuejs.org/config/#head)に HTML タグのように入れれば良い。ここではドキュメント内で数式の記述ができるようにするために MathJax を導入している。

```json
head: [
  ['script', { src: 'https://polyfill.io/v3/polyfill.min.js?features=es6' }],
  ['script', { id: 'MathJax-script', src: 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js', async: "async"}]
],
```
