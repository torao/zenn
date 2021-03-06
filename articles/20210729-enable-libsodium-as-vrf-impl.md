---
title: "Enable libsodium as VRF Implementation"
emoji: "ðº"
type: "tech" # tech: æè¡è¨äº / idea: ã¢ã¤ãã¢
topics: ["ostracon", "line", "blockchain", "cryptography", "VRF"]
published: false
---

# [ostracon1.0](https://github.com/line/ostracon): VRF å®è£ã« `libsodium` ãæå¹ã«ãã

Ostracon ã§ã¯ VRF æ©è½ã§ã BLS æ©è½ã§ãããã©ã¼ã¯åã® Tendermint ã« C/C++ ã®ãã¤ãã£ãã©ã¤ãã©ãªãä½¿ç¨ãã¦ãããã
æ­£ç´ãC/C++ ãä½¿ç¨ãã¦ãããã¤ãã£ãã©ã¤ãã©ãªã«é¢é£ãããã«ãç°å¢ã®åé¡ã¯ã¨ã¦ãæ ¹æ·±ãã

## ãã«ãç¨ã®ã©ã¤ãã©ãªãã¤ã³ã¹ãã¼ã«

Linux ã§ã macOS ã§ã libsodium ã®ãã«ãã¯è¿½å ã®éçºãã¼ã«ãã©ã¤ãã©ãªãå¿è¦ã¨ãªãã`make prepare-libsodium` ãå®è¡ããã°ç°å¢ãã¨ã«ã¤ã³ã¹ãã¼ã«ããããã«ããããæåã§å®è¡ãã¦ãè¯ãã

```
# macOS
$ brew install libtool autoconf automake

# Linux
$ apt-get update && apt-get -y install libtool libboost-all-dev autoconf build-essential
```

ãã«ãæã« `libsoilum` ã¿ã°ãæå¹ã«ãªã£ã¦ããã° libsodium ã¨ãªã³ã¯ããããã§ãªããã° VRF ã® golang å®è£ã§ãã r2ishiguro ãä½¿ç¨ãããMakefile ãè¦ãã¨ `LIBSODIUM=1` ã¨ããå®ç¾©ãããã°è¯ããããã

golangci-lint ã§å¤±æãã¦ããã`import "C"` ãèªè­ãããªãããããã­ã¼ã«ã«ã® Docker ã§å®è¡ãã¦åãã¨ã©ã¼ãåºããã¨ãç¢ºèªãã (`v1.31` ã¯ `.github/workflows/lint.yaml` ã«è¨è¿°ããããã¼ã¸ã§ã³ãä½¿ç¨ãã)ã

github actions ã¨åç­ã® lint ãã­ã¼ã«ã«ã§å®è¡ããå ´å:

```
docker run --rm -v $(pwd):/app -w /app golangci/golangci-lint:v1.31 golangci-lint run --out-format=github-actions --timeout 10m --skip-files "_test\.go"
```

ãªãã·ã§ã³ã¯ `.github/workflow/lint.yaml` åç§ã

## ãã«ãã®æé 

1. ã¾ã ãµãã¢ã¸ã¥ã¼ã«ã¨ãã¦ `crypto/vrf/internal/vrf/libsodium` ãåå¾ãã¦ãªããã° `git submodule update -i` ãå®è¡ãã¦åå¾ããã
2. libsodium ããã«ãããã
    * macos: `make prepare-libsodium-linux` ããã® `make libsodium`
    * linux: docker ã³ã³ãããããã«ã
        1. `docker run --rm -it -v \'pwd\':/opt ubuntu:latest bash`
        2. `apt-get update`
