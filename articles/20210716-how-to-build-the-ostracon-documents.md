---
title: "How to build the Ostracon documents"
emoji: "đș"
type: "tech" # tech: æèĄèšäș / idea: ăąă€ăăą
topics: ["ostracon", "line", "blockchain", "tendermint"]
published: true
---

# [ostracon1.0](https://github.com/line/ostracon): ăă­ă„ăĄăłăăă«ăæčæł

Tendermint ăŻ Vue.js ăźăă­ă°ă”ă€ăćăăăŹăŒă ăŻăŒăŻă§ăăăšăăăź [VuePress](https://vuepress.vuejs.org/) ăéçă”ă€ăăžă§ăăŹăŒăżăšăăŠäœżăŁăŠăăăăăă fork ăă Ostracon ă `docs/` ăăŁăŹăŻăăȘăźäžă« Markdown ă§èšèż°ăăăă­ă„ăĄăłăăäœæăăă° HTML ăźă”ă€ăăäœæăăŠăăăă

## ăă­ă„ăĄăłăăźăă«ă

ăă­ă„ăĄăłăăźăă«ăă«ăŻ [node.js](https://nodejs.org/) ăćżèŠăȘăźă§ă€ăłăčăăŒă«ăăŠăăă

```
% npm --version
6.14.13
```

Ostracon éçșăăŁăŹăŻăăȘă«ç§»ćăăŠ `make build-docs` ăćźèĄăăă°ăă­ă„ăĄăłăăçæăăăă


```
% cd git/ostracon
% make build-docs
```

Tendermint ăź `Makefile` ă§ăŻ `make build-docs` ă§ (`docs/versions` ă«èšèż°ăăŠăă) `main` ăă©ăłăăăă§ăăŻăąăŠăăăćäœă ăŁăăăăă«ăăŁăŠă­ăŒă«ă«ăź commit ćăźæŽæ°ăäžæžăăăăŠăăŸăăăăçŸćšăźă­ăŒă«ă«ăźç¶æă«ćŻŸăăŠćźèĄăăăăă«äżźæ­Łăăă

æ­Łćžžç”äșăăă° `~/output` ă«ăă­ă„ăĄăłăăçæăăăŠăăă

## ăă©ăŠă¶ă§çąșèȘ

`~/output` ăăŁăŹăŻăăȘă«ç§»ćăăă

```
% cd ~/output
```

çæăăă HTML ăźăăčæ§æăŻă”ă€ăăźăăăăăăæłćźăăŠăăăăăèĄšç€șăçąșèȘăăă«ăŻ `~/output` ă docroot ăšăă HTTP ă”ăŒăăćżèŠăšăȘăăă­ăŒă«ă«ă§ăźçąșèȘă ăăȘăźă§ăăă§ăŻç°Ąæ HTTPd ăšăăŠ express ăäœżăŁăŠăăăăŸă ă€ăłăčăăŒă«ăăŠăăȘăăă° npm ă§ă€ăłăčăăŒă«ăăŠăčăŻăȘăă `httpd.mjs` ăäœæăăă

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

httpd ăè”·ćăăŠăă©ăŠă¶ăă [http://localhost:8001/main/](http://localhost:8001/main/) ăèĄšç€șăăă

```
% node httpd.mjs
```

## HTML ă«æĄćŒ”ăć ăă

JS ă CSS ăăŹăŒă ăŻăŒăŻăèżœć ăăăć ŽćăŻ `.vuepress/config.js` ăź [`head` ăšăłăăȘ](https://vuepress.vuejs.org/config/#head)ă« HTML ăżă°ăźăăă«ć„ăăă°èŻăăăăă§ăŻăă­ă„ăĄăłăćă§æ°ćŒăźèšèż°ăă§ăăăăă«ăăăăă« MathJax ăć°ć„ăăŠăăă

```json
head: [
  ['script', { src: 'https://polyfill.io/v3/polyfill.min.js?features=es6' }],
  ['script', { id: 'MathJax-script', src: 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js', async: "async"}]
],
```
