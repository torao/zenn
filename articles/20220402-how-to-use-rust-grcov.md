---
title: "How to Use grcov with Rust"
emoji: "⚙"
type: "tech" # tech: 技術記事 / idea: アイデア
topics: ["Rust", "development"]
published: false
---

# grcov を使った Rust のカバレッジ収集

Mozilla の [grcov](https://github.com/mozilla/grcov)

```
C:\Users\torao\git\kademlia>rustup install nightly

C:\Users\torao\git\kademlia>rustup override set nightly
```

[README](https://github.com/mozilla/grcov) に書いてあるとおりに実行すれば良い。

```
C:\Users\torao\git\kademlia>cargo install grcov
    Updating crates.io index
  Downloaded grcov v0.8.9
  Downloaded 1 crate (85.6 KB) in 3.31s
...

C:\Users\torao\git\kademlia>rustup component add llvm-tools-preview
info: downloading component 'llvm-tools-preview'
info: installing component 'llvm-tools-preview'
 38.3 MiB /  38.3 MiB (100 %)  15.8 MiB/s in  2s ETA:  0s

C:\Users\torao\git\kademlia>set "RUSTFLAGS=-C instrument-coverage"
```

カレントディレクトリに `default.profraw` というファイルができあがる。

