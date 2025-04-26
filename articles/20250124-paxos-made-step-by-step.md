---
title: "Paxos Made Stepwise"
emoji: "🛋️"
type: "tech" # tech: 技術記事 / idea: アイデア
topics: ["Paxos","分散合意","分散システム"]
published: true
published_at: 2025-01-25 23:20
---

# Paxos Made Stepwise

## 1. Introduction

[Martin Fowler シリーズ](https://martinfowler.com/articles/patterns-of-distributed-systems/)の **[Patterns of Distributed Systems](https://amzn.to/4he05LV)**[^1] (2023) を読んだんですけど、分散システムのコアとなる構成要素や基礎技術を用途や動機別にうまく整理していて、広く浅く (言葉とその役割や仕組み程度を) 把握するには良い書籍でした。分散システムで使われている技法を効率的に学ぶなら、この本を一度さっと通読してから興味のあるトピックを深掘りするのがおすすめできそう。

中でも Chapter 11 の Paxos ではシーケンス図やステップごとの手続きが具体的に示されていて、Paxos を説明する他の多くの記事よりも理解しやすそうでした。この記事ではその Chapter 11 の解説をなぞり、再説明を試みる過程で自分の理解を固めることを目的としています。これは Paxos の動作の一部分に過ぎませんが、これから Paxos を深掘りしてゆく人にとって先に代表的な動作を把握しておくことは後の理解の大きな助けになると思います。

## 2. Step-by-Step Paxos

Paxos には MultiPaxos や Fast Paxos など多くの拡張版が存在しますが、ここで扱うのは Single-Decree Paxos と呼ばれる基本的なアルゴリズムです。

A, B, C, D, E の 5 つのノードが存在する Paxos 合意クラスタについて考えます。すべてのノードは最初 **Acceptor** の状態から開始します。

### 2.1 Prepare フェーズ

![Sequence Chart 1](/images/20250124-paxos-made-step-by-step/fig1.png)

まずシーケンス図の左側から。ノード A はクライアントから name = alice を設定するリクエストを受け付けます。これにより A は **Proposer** になって Prepare フェーズが開始します。

A は自身の**世代クロック**から世代番号を取得し (この場合は初期状態なので 1)、自分を含むすべての Acceptor に **Prepare リクエスト** を送信します。

上のシーケンス図ではどのノードもまだ Promise していないため、A の Prepare リクエストに対して A, B, C は Promised Generation を [1,A] に更新して Promise を返しました。これで A は過半数の Promise が確保できたので Accept フェーズに移行します。

それと並行して別のクライアントからノード E に対して name = elanor を設定するリクエストがありました。これによりノード E は Proposer となり、自身の世代クロックから世代番号 1 を取得し、E と D に Prepare リクエストを送ってそれぞれの Promised Generation が [1,E] に更新されました。

### 2.2 Accept フェーズの失敗

![Sequence Chart 2](/images/20250124-paxos-made-step-by-step/fig2.png)

さて、ノード A による Accept フェーズと E による Prepare フェーズは並行して進みます。

ノード C は E から Prepare リクエストを受信します。ここで、Prepare リクエストの世代番号 [1,E] は既に C が Promise した [1,A] より大きいため、C は Promised Generation を [1,E] に更新して Promise で応答します (世代番号が同じ場合はノード ID で大小比較するものとします)。これで E が過半数の Promise を確保できたので Accept フェーズに移行します。しかし不幸にも*ノード E は Accept フェーズ中に故障してしまいました*。

一方、Accept フェーズを進行中の A は、それに少し遅れてノード C に Accept リクエストを送信します。しかし、ノード C は Accept リクエストの世代番号 [1,A] が自身の Promise している [1,E] より小さいことから REJECT で応答します。A は、この C の離反により Prepare フェーズで確保した Promise が過半数を失ったことから Accept フェーズは失敗します。

通常、E が処理を続行することでその提案が合意に至ること期待されています。しかし E は過半数の Promise を持ったまま停止しています。このような状況であっても A の再提案が合意に達するようにプロトコルを設計する必要があります (さもなくばデッドロックになります)。

### 2.3 Prepare フェーズの再実行

![Sequence Chart 3](/images/20250124-paxos-made-step-by-step/fig3.png)

提案が REJECT されため、ノード A は自身の認識している世代番号より一つ大きい [2,A] で Prepare フェーズを再開します。A は A, C, D に Prepare リクエストを送信して過半数の Promise を確保しました。

ただし、以前の Prepare フェーズとの大きな違いは、A は世代番号 [1,A] で alice を Accept しており、D は [1,E] で elanor を Accept している点です。Accept 済みの値は Promise 応答と共に A に伝達されます。

過半数の Promise を確保した A は Accept フェーズに移行します。このとき Promise に Accept 済みの値が追加されている場合、その中で最も高い世代番号を持つ値を提案する必要があります。つまり、ここで A は最も高い世代番号 [1,E] で Accept されている値 elanor を提案しなければなりません。

### Accept フェーズの再実行

![Sequence Chart 4](/images/20250124-paxos-made-step-by-step/fig4.png)

A は Accept フェーズを開始します。まず A 自身に Accept リクエストを送り、世代番号が問題ないため A の Accepted Value は elanor に更新されます。

しかし不幸にも A の Prepare リクエストが終わってすぐに*ノード A は故障してしまいました* (この例では合意クラスタから Proposer が居なくなって合意が進行しなくなりますが、現実的な実装では他のノードが新たな Proposer となり、より大きな世代番号で試みることで合意が進行します)。

### 別のリクエストによる回復

![Sequence Chart 5](/images/20250124-paxos-made-step-by-step/fig5.png)

ここでクライアントからノード C に name = carol を設定するリクエストがありました。C は Proposer となり、Prepare フェーズを開始し、自身が認識している Promised Generation より大きい 3 を世代番号として B, C, D に Prepare リクエストを送信します。

![Sequence Chart 6](/images/20250124-paxos-made-step-by-step/fig6.png)

C は過半数の Promise を確保したので Accept フェーズに移行します。ここで、収集した Promise から Accept 済みの値を調べると、もっとも大きい世代番号 [2,A] を持つ値は elanor でした。したがって、C は値 elanor で Accept リクエストを行います。

この Accept フェーズは成功し、クラスタの過半数のノードに elanor が Accept されました。これにより、A や E が復帰して Prepare フェーズを開始したとしても、クラスタの過半数から Promise を集めた時点で少なくともその 1 つの Promise に高い世代番号を持つ elanor を観測することになり、結局 elanor の値を採用することが保証されます。

### Commit フェーズ

![Sequence Chart 7](/images/20250124-paxos-made-step-by-step/fig7.png)

最後にノード C は Commit を送信して合意を終了します。将来的にノード A や E が復帰しても elanor が Commit されていることを知ることができるでしょう。

### 役割ごとの動作

フェーズごとの Proposer と Acceptor の動作をまとめると次のようになります。

- **Proposer**
  - **Prepare フェーズ**: 自分が認識している世代クロックをインクリメントして世代番号を採番し、その世代番号を追加した Prepare リクエストをすべての Acceptor に送信します。
    - **成功**: 過半数の Acceptor から Promise を収集すると、Accept フェーズに移行します。
      - 収集した Promise の中に別のノードが既に Accept している値が含まれている場合、自分が提案しようとしていた値を破棄し、そのなかで最も世代番号の高い値を自分の提案する値として使用します。
    - **失敗**: 過半数の Acceptor から Promise を収集できなかった場合、Prepare フェーズは失敗します。自身の認識する世代番号より一つ大きい世代番号で Prepare フェーズを再試行します。
  - **Accept フェーズ**: Promise を収集した Acceptor に世代番号と値を付加した Accept リクエストを送信します。
    - **成功**: 過半数の Acceptor から OK 応答を確認すると提案した値が確定したことになります。Commit フェーズに進みます。
    - **失敗**: REJECT 応答があり、以前に収集した Promise がもはや過半数ではなくなってしまった場合、Accept フェーズは失敗します。自身の認識する世代番号より一つ大きい世代番号で Prepare フェーズを再試行します。
  - **Commit フェーズ**: すべての Acceptor に確定した値を追加した Commit メッセージを送信します。
- **Acceptor**
  - **Prepare フェーズ**: Prepare リクエストを受信すると、自身の Promise 済み世代番号と、そのリクエストの世代番号を比較します。
    - **成功**: Promise 済みの世代番号より Prepare リクエストの世代番号の方が大きい場合、自身の Promise 済み世代番号をその世代番号で更新し、Promise を返します。
      - このとき、すでに Accept 済みの値を持っている場合は、この Promise に以前の世代番号と Accept 済みの値を追加して応答します。
    - **失敗**: 既にもっと大きい世代番号に Promise をしている場合、NG で応答します (あるいは応答しません)。
  - **Accept フェーズ**: Accept リクエストを受信すると、自身の Promise 済み世代番号と、そのリクエストの世代番号を比較します。
    - **成功**: Promise 済みの世代番号と Accept リクエストの世代番号が等しい場合、自身の Accept 済みの値を更新して OK を返します。
    - **失敗**: 既にもっと大きい世代番号に Promise を返している場合、REJECT で応答します (あるいは応答しません)。
  - **Commit フェーズ**: 合意クラスタで値が確定したことを認識します。

## 3. Conclusion

一連の流れで alice, carol, elanor の 3 つの値が提案されましたが、この Paxos 合意クラスタは最終的に elanor を採用することで合意しました。Single-Decree Paxos は 1 回限りの合意を保証することに限定されていますので、仕組みとしてはここで終わりです。

しかし、この一連の操作をラウンドごとに繰り返して複数のノード間でコマンドの実行順序を決定することができそうです。Single-Decree Paxos を拡張して複数回の合意を効率的に行えるようにした Mutli-Paxos などのバリアントでは、この仕組みを進展して Serializability を達成し、Replicated State Machine を構築できるようになります。

FLP Impossibility により、Paxos であっても 1 つのノードの故障を許容 (想定) するだけで合意に到達できないケースがあることに注意してください。この例での具体的なケースは書籍[^1]に書かれています。

[^1]: Unmesh Joshi. [Patterns of Distributed Systems](https://amzn.to/4he05LV). Addison-Wesley Professional (2023); [O'REILLY Safari Online](https://learning.oreilly.com/library/view/patterns-of-distributed/9780138222246/ch11.xhtml#ch11lev1sec2) で読むこともできる。
