---
title: "How to build the Ostracon documents"
emoji: "🤔"
type: "tech" # tech: 技術記事 / idea: アイデア
topics: ["ostracon"]
published: true
---

# [Ostracon v1.0](https://github.com/line/ostracon) でのドキュメントビルド方法

Tendermint は静的サイトジェネレータに Vue.js のブログサイト向けフレームワークの Vuepress を使っているらしい。それで `docs/` ディレクトリの下に Markdown で記述したドキュメントを保存しておけばいい感じの HTML ファイルに変換してくれる。

## ドキュメントのビルド

ドキュメントのビルドには node.js が必要なのでインストールしておく。

```
% npm --version
6.14.13
```

ドキュメントを作成する `make build-docs` コマンドは `docs/versions` ファイルに記述しているブランチをチェックアウトしようとするので、修正中のファイルがあるなら commit するなり stash するなりしておく。

Ostracon 開発ディレクトリに移動して `make build-docs` を実行すればドキュメントが生成される。


```
% cd git/ostracon
% make build-docs
```

正常終了すれば `~/output` にドキュメントが生成されている。

`docs/versions` に行を分けて複数のブランチを記述しておけば、それらのブランチごとに `~/output/<branch>` というディレクトリに出力される。

## ブラウザで確認

`~/output` ディレクトリに移動する。

```
% cd ~/output/main
```

ローカルでの確認だけなのでここでは簡易 HTTPd として express を使っておく。まだインストールしていなければ npm でインストールしてスクリプト `httpd.mjs` を作成する。


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
% npm install express
% node httpd.mjs
```

## 設定の拡張

数式を使用するために MathJax の JavaScript を追加した。このような JS や CSS フレームワークの追加は `.vuepress/config.js` の `head` エントリに HTML タグのように入れれば良いらしい。

```json
head: [
  ['script', { src: 'https://polyfill.io/v3/polyfill.min.js?features=es6' }],
  ['script', { id: 'MathJax-script', src: 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js', async: "async"}]
],
```
