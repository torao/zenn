---
title: "5分で論文略読: AT2: Asynchronous Trustworthy Transfers (2019)"
emoji: "🛋️"
type: "tech" # tech: 技術記事 / idea: アイデア
topics: ["分散システム","BFT","Blocchain"]
published: true
---

# AT2: Asynchronous Trustworthy Transfers

Bitcoin のような暗号資産の分散型資産移転システムの核心は、ビザンチン故障と非同期ネットワークを含む P2P の設定でありながら二重支払問題を解決したことである。このような分散移転にコンセンサス機構が必須だと考えられてきたが、その通説は間違いである、とこの論文では述べている。そして AT2 はそれを実現するためのプロトコルである。データセンターのようなプライベート (permissioned) と Bitcon のようなパブリック (permissionless) ネットワーク向けのアルゴリズムが説明されている。

## コンセンサス不要論

この論文で印象深い話題は繰り返し述べられるコンセンサス不要論だろう。その考え方は以下のように略述できる。

**二重支払問題** (double spending): 一貫性 (consistency) のない分散システムでは異なるノードが異なる状態を持つことができる。例えば金融システムで、ノード $X$ が残高 100 万円の口座 $A$ から別の口座 $B$ に 80 万円を移動したとする。しかしその手続きがあったことをまだ知らない別のノード $Y$ では $A$ の残高は 100 万円に見えているため別の 60 万円の送金を成功させてしまうかもしれない。一般にこのような二重支払問題を防ぐにはシステムに強い一貫性 (=コンセンサス、分散合意、全順序) を導入する必要がある。

しかし資産移転に特化すれば達成すべき制約は「口座の残高がマイナスにならないこと」だけである。そして、一般に送金トランザクションを生成する許可を持っているのは口座の所有者だけである。つまり、口座や口座の所有者が唯一かつ一意であれば、口座ごとに"happened before" で因果順序付けされたの送金トランザクションの履歴を保持すれば十分で ("口座所有者" によって直列化できるはずなので)、それを実現するためには非同期ブロードキャスト (+ 因果一貫性の考え) のみがあればよく、システム全体の分散合意や全順序性を保証するようなコンセンサスは必要ない、というのがこの論文の根本にある。まあ、現実の取引では送金に必要な入金があるまで送金を待つような動作も必要そうなので少し荒っぽい気はするが、概ね理解できる範囲と言える。

非同期ブロードキャストがこのような資産移転に利用できるという洞察は Padone と Schiper (2002) で示唆され、Gupta (2016) で AT2 と同じような資産移転を導入したとセクション 7.2 で述べている。実際、Byteball のような DAG 型ブロックチェーンでユーザごとの処理順序保証はクライアントの責務としているのも根本は同じ考えと言える (ただ既存の DAG 型は最終的にコンセンサスで全順序を作り出しているが)。また Stellar Consensus の構成もブロードキャスト + 隣接ノードとの合意のみなので AT2 と似たところが多いように見える。

## アルゴリズム

基本的に、非同期ブロードキャストと、アカウントごとに Version Clock や Version Vector のような因果一貫性の履歴の管理で構成されている。アカウント単位の履歴なので Vector Clock のように複雑にはならないとは思うが。アルゴリズムの説明は長くなるので論文参照。

論文では AT2 アルゴリズムを 4 種類のバリアントで説明している (したがって論文全体の文量が多い)。それぞれはブロードキャスト特性 (通信特性) の違いが大きく、根本説明や証明は似ている。

1. ${\sf AT2_{SM}}$: プロセスが read/write 可能な共有メモリを使って資産移転を非同期で実行する wait-free アルゴリズム。これは consensus number = 1 を達成している。
2. ${\sf AT2_{MP}}$: 1/3 までのビザンチン故障を許容するメッセージパッシングモデルでの汎用非同期アルゴリズム。
3. ${\sf AT2_{D}}$: プライベートネットワーク / permissioned 向けに数十～数百ノードを想定した決定論的 (deterministic) 非同期アルゴリズム。
4. ${\sf AT2_{P}}$: パブリックネットワーク / permissionless 向けに数万ノードにスケールし、対数オーダーの待ち時間と通信複雑性を持つ確率的 (probabilistic) 非同期アルゴリズム。

${\sf AT2_D}$ での安全なブロードキャストは Malkhi と Reiter (1997) を使用し、${\sf AT2_P}$ では確率的ブロードキャストは Erdös-Rényi Gossip の一貫性、安全性を保証するバージョンを使用すると書かれている。

## コンセンサスレスの長所

かなり根本の前提が外れるのでスマートコントラクトのようなことはできなくなる反面、直感としてシステム的にうれしいことが多いように思える。

- コンセンサスのために PoW, BFT, Paxos のような重く複雑な分散合意プロトコルを使わなくて良い。
- 非同期環境でも FLP Impossibility の影響を受けなくなるので (←マジそうだわ)、その対策でランダムさやランダムさを保証するための重い暗号処理、タイムアウト機構などを導入する必要がない。
- 合意のために n=3f+1 のような静的な定足数の委員会を選出する必要がない。
- 非効率性を解消するためのシャーディングのような仕組みも必要ない。

効果は BFT-SMaRt と比べて 1.5～6倍のスループット、最大 2 倍のレイテンシー低減らしい。

## Sybil 攻撃耐性

他のほとんどの戦略では Sybil 攻撃耐性のために PoW といった検証可能な証明に基づいているのに対して、AT2 では所有者の一意性を前提としているため、A → B の接続上で定期的にデータ (ping?) を送ることで A が本物であることを保証することで十分とのこと (Proof-of-bandwidth と呼ぶらしい)。

> GUERRAOUI, Rachid, et al. [AT2: asynchronous trustworthy transfers](https://arxiv.org/abs/1812.10844). _arXiv preprint arXiv:1812.10844_, 2018.