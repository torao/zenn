---
title: "Linux ネットワーク不安定性シミュレーション入門"
emoji: "🔬"
type: "tech" # tech: 技術記事 / idea: アイデア
topics: ["システムテスト", "障害注入", "システム信頼性", "SRE", "Resilience"]
published: true
published_at: 2025-05-06 06:37
keywords: ["Linux tc", "netem", "iptables", "ネットワーク障害試験", "Chaos Engineering"]
description: "Linux ネイティブの tc/netem と iptables を使ってネットワーク遅延や不安定性の注入を行うハンズオン記事。Ubuntu/CentOS 対応。"
---

## 1. はじめに

現代的な分散システムやマイクロサービスアーキテクチャでは複数のノードが非同期に連携しながら複雑に協調動作するケースが多く存在します。このような環境下ではネットワーク品質のわずかな変動がシステム全体に大きな影響を及ぼすことがあり、システム運用時に想定する最悪ケースの通信品質を再現したテスト環境を構築することが重要です。一般的に、完全に通信できなくなるような完全なネットワーク障害よりも、著しい遅延や確率的な瞬断が発生しながらも駆動し続けるような部分的な障害の方が、システム全体としての問題をより複雑で深刻化させる傾向があります。

ネットワークに不安定性 (遅延や瞬断など) が発生した場合、非同期システムでは次のような挙動が顕在化する可能性があります。

- バックプレッシャーによる送信側キューの肥大化
- スレッドプールの枯渇
- クライアントの接続拒否
- ネットワーク遅延に起因するノード故障の誤判定
- Socket Timeout や Read Timeout の発動
- エラー時処理、または再試行などのリカバリ機能の発動
- ジッター (遅延時間のばらつき) によるイベント順序の逆転

この記事では Linux ネイティブのネットワーク制御ツールである **tc** (+ netem モジュール) と **iptables** を使い、テスト環境でネットワーク遅延や通信中の切断などの不安定性を再現する実践的な手順をハンズオン形式で解説します。

## 2. 前提と準備

**対象**: TCP/IP の基本的な知識を持ち、Linux のネイティブツールの扱いに慣れているエンジニア。

**重要な注意点**: 設定ミスや解除漏れによってシステムが意図しない状態に陥り、最悪の場合、元に戻せなくなるリスクを伴います。操作は隔離された環境で慎重に行ってください。

**環境**:

ハンズオン形式で進めるために、通信可能な 2 つのノードを次の環境で用意してください。

1. 物理マシン上で動作する仮想化されていない Linux 環境、あるいは
2. VirtualBox (Windows または MacOS) や KVM (Linux) などの完全仮想化で動作する Linux 環境

Docker コンテナはカーネルモジュールの操作にさまざまな制約があり、この記事で扱う `tc` の利用が困難になりがちですのでおすすめしません。

代表的な 2 種類の Linux ディストリビューションでの操作を説明するために、この記事では 2 つのノードに異なる Linux 環境を導入しています。自分の環境に合わせて該当するディストリビューションの説明を参照してください。

- `alpha-ub01`: Ubuntu 24.04 環境のノード
- `beta-ce01`: CentOS Stream 9 環境のノード (10 は VirtualBox で panic を起し動作しなかったため)

用意した双方のノードから `ping` を実行し、相互に通信できることを確認してください。

```text
torao@alpha-ub01:~$ ping -c 3 beta-ce01
PING beta-ce01 (192.168.150.51) 56(84) bytes of data.
64 bytes from beta-ce01 (192.168.150.51): icmp_seq=1 ttl=64 time=0.701 ms
64 bytes from beta-ce01 (192.168.150.51): icmp_seq=2 ttl=64 time=0.725 ms
64 bytes from beta-ce01 (192.168.150.51): icmp_seq=3 ttl=64 time=0.832 ms

--- beta-ce01 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2074ms
rtt min/avg/max/mdev = 0.701/0.752/0.832/0.056 ms
```

上記の出力例は `alpha-ub01` から `beta-ce01` へ正常に ICMP パケットが送受信できていることを示しています。

### 2.1 テストツールのインストール

ここからは `alpha-ub01` (Ubuntu 24.04) と `beta-ce-01` (CentOS Stream 9) の説明を併記します。最初にそれぞれの環境でテストに必要なツールをインストールします。

```text
torao@alpha-ub01:~$ sudo apt update &&
  sudo apt install -y iproute2 iptables iperf3
```

```text
[torao@beta-ce01 ~]$ sudo dnf update &&
  sudo dnf install -y iproute iptables iperf3
```

構成を簡単にするため、ファイアウォールが設置されているならテスト終了までオフにします (**重要**: セキュリティ上のリスクを理解した上で行い、テスト終了後は必ず有効に戻してください)。

```text
torao@alpha-ub01:~$ sudo ufw disable
```

```text
[torao@beta-ce01 ~]$ sudo systemctl stop firewalld
```

ファイアウォールを有効にしたままテストを行う必要がある場合は、`iperf3` の 5201 ポートなど、この記事の挙動確認で使用するプロトコルや各ポートの通信を許可するように設定を追加してください。

この状態で `iperf3` を使って正常状態での TCP ベースの帯域速度を測定してみましょう。以下の例では `alpha-ub01` でサーバを起動し `beta-ce01` から接続しています。速度がネットワーク構成で想定するスペックに近ければ OK です (例えばギガビットイーサネット環境であれば 950Mbps 程度になるでしょう)。

Ubuntu 24.04 では `iperf3` をインストールすると自動的に `systemctl` によって起動されるようになります。以下のコマンドで `iperf3` がサーバとして起動しているか確認してください。

```text
torao@alpha-ub01:~$ systemctl list-unit-files -t service | grep iperf3
iperf3.service                               enabled         enabled
```

それ以外の Linux や自動起動をオフにしている場合は、以下のように手動でサーバとして起動します。

```text
torao@alpha-ub01:~$ iperf3 -s
-----------------------------------------------------------
Server listening on 5201 (test #1)
-----------------------------------------------------------
```

クライアントからは以下のように接続できます。これはクライアントからサーバ方向にデータを送信して計測していることに注意してください。

```text
[torao@beta-ce01 ~]$ iperf3 -c alpha-ub01 -t 3
Connecting to host alpha-ub01, port 5201
[  5] local 192.168.150.51 port 57838 connected to 192.168.150.50 port 5201
[ ID] Interval           Transfer     Bitrate         Retr  Cwnd
[  5]   0.00-1.00   sec   227 MBytes  1.90 Gbits/sec  122    242 KBytes
[  5]   1.00-2.00   sec   227 MBytes  1.90 Gbits/sec  236    247 KBytes
[  5]   2.00-3.00   sec   222 MBytes  1.86 Gbits/sec  218    226 KBytes
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-3.00   sec   676 MBytes  1.89 Gbits/sec  576             sender
[  5]   0.00-3.00   sec   674 MBytes  1.88 Gbits/sec                  receiver

iperf Done.
```

### 2.2 カーネルモジュールの確認とロード

`netem` やクラス/フィルター設定に必要なカーネルモジュールが読み込まれているかを確認し、不足していればロードします。

```shell
# netem モジュールがロードされているか確認
lsmod | grep -E 'sch_netem|sch_htb|cls_fw|cls_u32'

# ロードされていなければ以下のようにロードする
sudo modprobe sch_netem   # tc でパケット遅延、ロス、重複、リオーダーなどを注入する netem モジュール
sudo modprobe sch_htb     # 階層的な帯域制御を行う HTB (hierarchical token bucket) qdisc
sudo modprobe cls_fw      # ファイアウォールマークに基づいてトラフィックを分類するクラス
sudo modprobe cls_u32     # より複雑な条件でトラフィックを分類する汎用的なクラス
```

これらをロードすることで `tc qdisc add ...` コマンドが正常に動作します。

> [!TIP]
> 使用するネットワークインターフェース (`eth0` や `enp0s3` など) に対して、パケットの集約 (GRO, LRO) と分割 (GSO, TSO) に関するハードウェアオフロードを無効化する必要があるかもしれません。これらが有効になっていると、ハードウェアがパケットの分割と集約を行うため `tc netem` の遅延や損失が個々のパケットに正確に反映されず、計測に影響を与える可能性があります。
>
> ```shell
> # 現在のハードウェアオフロードの設定を確認 (例: enp0s3)
> sudo ethtool -k enp0s3 | grep tcp-segmentation-offload
>
> # TCP TSO を無効化
> sudo ethtool -K enp0s3 tso off
> ```

## 3. 基本的なネットワーク遅延の注入と検証

次に Linux のトラフィック制御ツール `tc` (traffic control) とネットワークエミュレーション機能を提供する `netem` を使ってネットワークにパケット遅延を加え、その影響を `ping` や `iperf3` などのツールで確認します。遅延以外で `tc` を使って可能な動作、例えばパケット破損や帯域制限などは後にまとめています。

`tc` は Linux カーネルのトラフィック制御を設定するための強力なコマンドラインツールです。ネットワークインターフェースに対してパケットの送受信を制御し、さまざまな QoS やトラフィックシェーピングのルールを提供できます。

`tc` の基本的な概念として **qdisc** (キューイングディシプリン) があります。qdisc は、ネットワークインターフェースに出入りするパケットの待ち行列を管理し、どのようにパケットを処理（送信またはドロップ）するかを決定します。**netem はこの qdisc の一種であり**、パケットの遅延、損失、重複、破損などのネットワーク障害をエミュレートする機能を提供します。

### 3.1 netem (Network Emulator) の基本的な使い方

この記事では以下のように想定していますので、自分の環境に合わせて以下のホスト名などを読み替えてください。

| ホスト名      | IP アドレス    | ネットワークインターフェース |
|:-------------|:---------------|:---------|
| `alpha-ub01` | 192.168.150.50 | `enp0s3` |
| `beta-ce01`  | 192.168.150.51 | `enp0s3` |

デフォルト状態で `enp0s3` は、遅延の影響を低減するためのアクティブキュー管理を行う `fq_codel` (Fair Queue CoDel) という qdisc が 1 つだけ設定されています。

```text
torao@alpha-ub01:~$ sudo tc qdisc show dev enp0s3
qdisc fq_codel 0: root refcnt 2 limit 10240p flows 1024 quantum 1514 target 5ms interval 100ms memory_limit 32Mb ecn drop_batch 64
```

#### 3.1.1 特定の NIC から送信されるすべてのパケットに遅延を設定する

まず最も簡単な構成として、`alpha-ub01` の `enp0s3` インターフェースに qdisc を追加し、その NIC から送信されるすべてのパケットに 120 ミリ秒の送信遅延を加えます。この操作は既存の `fq_codel` qdisc を `netem` qdisc で置き換えます。

```shell
# netem qdisc を root としてセット
sudo tc qdisc add dev enp0s3 root netem delay 120ms
```

このコマンドの実行により `enp0s3` に設定されていたデフォルトの qdisc が置き換えられます。

```text
torao@alpha-ub01:~$ sudo tc qdisc show dev enp0s3
qdisc netem 8002: root refcnt 2 limit 1000 delay 120ms
```

この設定によって `alpha-ub01` から `enp0s3` を通して送信されるすべてのパケットに 120ms の遅延が加算されます。`ping` で確認すると RTT (往復遅延時間) が約 121 ミリ秒程度になっていることがわかるでしょう。`ping` のパケットは往復するため `alpha-ub01` と `beta-ce01` のどちら側で `ping` を実行してもこの遅延の影響を受けます。

```text
[torao@beta-ce01 ~]$ ping alpha-ub01 -c 3
PING alpha-ub01 (192.168.150.50) 56(84) bytes of data.
64 バイト応答 送信元 alpha-ub01 (192.168.150.50): icmp_seq=1 ttl=64 時間=121 ミリ秒
64 バイト応答 送信元 alpha-ub01 (192.168.150.50): icmp_seq=2 ttl=64 時間=121 ミリ秒
64 バイト応答 送信元 alpha-ub01 (192.168.150.50): icmp_seq=3 ttl=64 時間=121 ミリ秒

--- alpha-ub01 ping 統計 ---
送信パケット数 3, 受信パケット数 3, 0% packet loss, time 2004ms
rtt min/avg/max/mdev = 120.684/120.967/121.341/0.275 ms
```

設定した `netem` qdisc を削除するには以下のコマンドを実行します。`ping` を動作させたままで行えば、ある時点から 120 ミリ秒の遅延がなくなっているのがわかるでしょう。

```shell
sudo tc qdisc del dev enp0s3 root
```

デフォルトの qdisc に戻っていることが確認できます。

```text
torao@alpha-ub01:~$ sudo tc qdisc show dev enp0s3
qdisc fq_codel 0: root refcnt 2 limit 10240p flows 1024 quantum 1514 target 5ms interval 100ms memory_limit 32Mb ecn drop_batch 64
```

#### 3.1.2 特定の IP アドレス宛のパケットに遅延を設定する

`tc filter` を使用すると特定の IP アドレス宛のパケットに対してのみネットワーク障害を注入することができます。これはより現実的で複雑なネットワーク環境のシミュレーションを可能にします。

- **ネットワーク遅延の差異**: ローカルネットワーク内のノードと地理的に離れた場所に存在するノードとの間の遅延差を再現する。
- **外部サービスとの通信**: 外部の API サービスやデータベースとの通信で不安定性の発生をシミュレーションする。
- **段階的な影響調査**: ネットワーク不安定性の注入範囲を部分的なノードから開始し徐々に拡大してゆくことで、システム全体への影響を段階的に調査する。

まず `prio` qdisc を追加し、その中の優先度バンド (ここでは band 3) に対して `netem` qdisc をぶら下げ、さらにその qdisc に filter で宛先 IP アドレスを一致させます。`prio` qdisc は複数の優先度を持つキューイング規律であり、ここでは異なる種類のトラフィックを異なるバンドに分類するために使用します。

例えば `alpha-ub01` 上の `enp0s3` から `beta-ce01` (192.168.150.51) 宛に送信されるパケットにのみ 120ms の遅延を追加するには以下のように設定します。

```shell
# 1. prio qdisc を root としてセット
sudo tc qdisc add dev enp0s3 root handle 1: prio

# 2. prio の band 3 (handle 1:3) に netem qdisc をセットして 120ms 遅延
sudo tc qdisc add dev enp0s3 parent 1:3 handle 30: netem delay 120ms

# 3. filter で IP アドレス 192.168.150.51 宛のパケットのみ band 3 に振り分け
sudo tc filter add dev enp0s3 protocol ip parent 1: prio 3 u32 match ip dst 192.168.150.51 flowid 1:3
```

ここで `tc filter` に設定する IP アドレスを 192.168.150.0/24 のようにネットワーク範囲で指定することもできます。複数のデータセンターをシミュレーションする場合などでは、各ノードの IP アドレスを所属するネットワークでシミュレーションして設定しておくと `tc` の設定が簡単になります。

設定を確認します。

```text
torao@alpha-ub01:~$ tc qdisc show dev enp0s3
qdisc prio 1: root refcnt 2 bands 3 priomap 1 2 2 2 1 2 0 0 1 1 1 1 1 1 1 1
qdisc netem 30: parent 1:3 limit 1000 delay 120ms

torao@alpha-ub01:~$ tc filter show dev enp0s3
filter parent 1: protocol ip pref 3 u32 chain 0
filter parent 1: protocol ip pref 3 u32 chain 0 fh 800: ht divisor 1
filter parent 1: protocol ip pref 3 u32 chain 0 fh 800::800 order 2048 key ht 800 bkt 0 *flowid 1:3 not_in_hw
  match c0a89633/ffffffff at 16
```

この設定も `ping` を用いて検証できます。`alpha-ub01` と `beta-ce01` 間では約 120ms の遅延が発生しますが、それ以外のノードから `alpha-ub01` へ `ping` を送信しても遅延は発生しないはずです。

以下の手順は設定した順に削除しています。

```shell
# 1. まず宛先 IP アドレスを一致させていたフィルタのみを削除 (これで遅延は発生しなくなる)
sudo tc filter del dev enp0s3 protocol ip parent 1: prio 3

# 2. netem qdisc を削除
sudo tc qdisc del dev enp0s3 parent 1:3 handle 30:

# 3. prio qdisc を削除
sudo tc qdisc del dev enp0s3 root handle 1:
```

または `root` qdisc を削除すれば下層の qdisc や filter もまとめて削除されます。

```shell
# root qdisc を削除
sudo tc qdisc del dev enp0s3 root
```

```text
torao@alpha-ub01:~$ tc qdisc show dev enp0s3
qdisc fq_codel 0: root refcnt 2 limit 10240p flows 1024 quantum 1514 target 5ms interval 100ms memory_limit 32Mb ecn drop_batch 64
```

#### 3.1.3 ポート単位またはより詳細な遅延を設定する

特定のポート番号 (例えば TCP の 80 ポート) での通信に対して遅延を設定するには、`iptables` と `tc` を連携する必要があります。ここでは TCP の 5201 ポートを使用する `iperf3` で遅延を観測します。

`iperf3` はクライアントからサーバに対してペイロードを送信するため、クライアント側の `beta-ce01` 側で遅延を設定します (サーバ側に設置しただけでは ACK が遅延するだけです)。まず `iptables` の `mangle` テーブルの `OUTPUT` チェーンにルールを追加し、遅延を追加したい対象のパケット (宛先ポートが 5201 の TCP パケット) にマーク `1` を付けます。

```shell
sudo iptables -t mangle -A OUTPUT -p tcp --dport 5201 -j MARK --set-mark 1
```

`mangle` テーブルはパケットのヘッダ情報を変更するために使用されます。

次に、`tc filter` でマーク `1` の付いたパケットに対して遅延を適用します。

```shell
# 1. prio qdisc を root としてセット
sudo tc qdisc add dev enp0s3 root handle 1: prio

# 2. prio の band 3 (handle 1:3) に netem qdisc をセットして 120ms 遅延
sudo tc qdisc add dev enp0s3 parent 1:3 handle 30: netem delay 120ms

# 3. マーク 1 の付いたパケットを band 3 (flowid 1:3) に振り分け (fw はファイアウォールマークとのマッチングを表す)
sudo tc filter add dev enp0s3 protocol ip parent 1: prio 3 handle 1 fw flowid 1:3
```

上記の設定を `beta-ce01` 側で行い、`alpha-ub01` で `iperf3 -s -p 5202` も起動して `beta-ce01` から帯域速度を計測すると、5201 ポートではビットレートが 50Mbps 程度まで低下していることがわかります。

```text
[torao@beta-ce01 ~]$ iperf3 -c alpha-ub01 -p 5201 -t 3
Connecting to host alpha-ub01, port 5201
[  5] local 192.168.150.51 port 35916 connected to 192.168.150.50 port 5201
[ ID] Interval           Transfer     Bitrate         Retr  Cwnd
[  5]   0.00-1.00   sec  5.29 MBytes  44.3 Mbits/sec   51    707 KBytes
[  5]   1.00-2.00   sec  6.25 MBytes  52.4 Mbits/sec    0    800 KBytes
[  5]   2.00-3.00   sec  6.25 MBytes  52.4 Mbits/sec    0    875 KBytes
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-3.00   sec  17.8 MBytes  49.7 Mbits/sec   51             sender
[  5]   0.00-3.12   sec  15.1 MBytes  40.6 Mbits/sec                  receiver

iperf Done.

[torao@beta-ce01 ~]$ iperf3 -c alpha-ub01 -p 5202 -t 3
Connecting to host alpha-ub01, port 5202
[  5] local 192.168.150.51 port 51414 connected to 192.168.150.50 port 5202
[ ID] Interval           Transfer     Bitrate         Retr  Cwnd
[  5]   0.00-1.00   sec   235 MBytes  1.97 Gbits/sec  221    297 KBytes
[  5]   1.00-2.00   sec   226 MBytes  1.90 Gbits/sec   85    242 KBytes
[  5]   2.00-3.00   sec   231 MBytes  1.94 Gbits/sec  199    212 KBytes
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-3.00   sec   692 MBytes  1.94 Gbits/sec  505             sender
[  5]   0.00-3.00   sec   690 MBytes  1.93 Gbits/sec                  receiver

iperf Done.
```

この遅延を削除するには `iptables` と `tc filter`、`tc qdisc` の設定を順に削除します。

```shell
# 1. まず宛先 IP アドレスを一致させていたフィルタのみを削除 (これで遅延は発生しなくなる)
sudo tc filter del dev enp0s3 protocol ip parent 1: prio 3

# 2. netem qdisc を削除
sudo tc qdisc del dev enp0s3 parent 1:3 handle 30:

# 3. prio qdisc を削除
sudo tc qdisc del dev enp0s3 root handle 1:

# 4. ルール番号を確認
sudo iptables -t mangle -L OUTPUT --line-numbers

# 5. ルール番号を指定して削除 (例えば 5201 をマーク 1 とするルールが #1 にある場合)
sudo iptables -t mangle -D OUTPUT 1
```

または、他に `mangle` テーブルの `OUTPUT` チェーンに有効な設定が存在しないことが分っている場合に限り、以下のコマンドでチェーンをすべて削除できます。

```shell
sudo iptables -t mangle -F OUTPUT
```

この `iptables` と連携する方法の応用として、ポート番号以外にも多くの属性を組み合わせてパケットにマークを付けることができます。以下は `iptables` で使用できる代表的なパターンです (`tc` と連携可否や注意点については、個々の属性の組み合わせによって異なる場合があります)。

| 分類対象の属性         | 説明                                     | iptables の一致例                                                      |
|------------------------|------------------------------------------|------------------------------------------------------------------------|
| ポート番号             | TCP/UDP の送受信ポート                   | `-p tcp --dport 5201`                                                  |
| IP アドレス/サブネット| 送信元/宛先 IP やサブネット               | `-s 10.0.0.0/24`, `-d 192.168.1.100`                                    |
| ネットワークインターフェース | 出力インターフェース                  | `-o eth2` (Egress)                              |
| プロトコル             | TCP, UDP, ICMP など                      | `-p icmp`, `-p udp`                                                     |
| 接続状態 (conntrack)  | NEW, ESTABLISHED, RELATED 等             | `-m conntrack --ctstate NEW`                                           |
| DSCP/TOS              | QoS 用 DiffServ コードポイント            | `-m dscp --dscp-class EF`, `-m tos --tos 0x10`                          |
| TCP フラグ             | SYN, ACK, RST などのフラグ                | `-p tcp --syn`, `-p tcp --tcp-flags RST RST`                                   |
| パケット長             | パケットのバイト長                       | `-m length --length 1500:65535`                                         |
| MAC アドレス           | 送信元または宛先の L2 MAC                 | `-m mac --mac-source AA:BB:CC:DD:EE:FF` (`PREROUTING` チェーン)                                |
| 時刻/曜日             | 特定の時間帯や曜日のみ適用                | `-m time --timestart 18:00 --timestop 20:00`                            |
| UID/GID               | ローカル発信パケットのユーザー/グループ識別 | `-m owner --uid-owner 1001`, `-m owner --gid-owner 1001`                         |

## 4. パケット損失・重複・リオーダー・破損の注入と検証

ここまでの説明では `netem` を用いてパケット遅延 `delay` を追加してきました。しかし `netem` は他にもパケット損失、重複、リオーダー、破損といった、より複雑なネットワーク障害を注入することができます。

| パケット障害の種類 | `netem` オプションの例 | 挙動の確認方法 |
|:--|:--|:--|
| 遅延 | `delay 50ms` | `ping` の RTT で確認。 |
| 損失     | `loss 0.2%` | `ping` 終了時のロス率 (`packet loss`) を確認。 |
| 重複      | `duplicate 5%` | `ping` のシーケンス番号が重複することを確認。 |
| リオーダー | `reorder 5%` | `ping` のシーケンス番号の順序が逆転することを確認。 |
| 破損      | `corrupt 2%` | `tcpdump` や `wireshark` など。また暗黙的に破棄され損失として計上されることもある。 |
| 帯域制限 | `rate 64kbit` | `iperf3` の Bitrate で確認。 |

詳細は [tc-netem(8)](https://man7.org/linux/man-pages/man8/tc-netem.8.html) を参照してください。

またこれらのパケット障害を組み合わせて、より複雑なネットワーク状況をエミュレーションすることもできます。以下の例では 100ms の遅延、5% のパケット損失、2% のパケット重複を同時に注入します。

```shell
sudo tc qdisc add dev enp0s3 root netem \
  delay 100ms \
  loss 5% \
  duplicate 2%
```

ただし、このような IP パケットレベルの障害は TCP のレイヤーで検知され再送や訂正が行われることが予想されます。これらの訂正動作は TCP 再送信 (TCP retransmission) の発生数の増加として観測されます。`tcpdump -n -i enp0s3 'tcp and port 5201' -v | grep retrans` のようなコマンドで TCP 再送信の数を監視すると影響を定量的に把握する手助けになります。

## 5. TCP 接続の確率的な障害

前章で説明した中でもパケット破損やリオーダーといった IP レベルでの細かな障害注入は、TCP プロトコルが持つ再送制御や順序制御の仕組みによって吸収されるため、アプリケーションが直接的な影響を受けにくい可能性があります。アプリケーションのネットワーク障害耐性をより直接的に評価するには、TCP レベルでの接続断や接続拒否といった、より影響の大きい障害のエミュレーションを優先する方が効果的です。

### 5.1 アクティブな TCP セッションの乱断

ここでは `iptables` を使って特定の条件に一致するアクティブな TCP セッションからの送信パケットを確率的に遮断し、強制的に接続をリセットする方法を紹介します。

以下のコマンドは `iptables` の `OUTPUT` チェーンにルールを追加し、送信元ポート 5201 を使用する確立済みの TCP セッションからの送信パケットを 5% の確率で遮断します。このとき、接続相手に TCP RST (Reset) パケットを送信して接続を強制的にリセットします。

```shell
sudo iptables -t filter -A OUTPUT \
  -p tcp --sport 5201 \
  -m statistic --mode random --probability 0.05 \
  -j REJECT --reject-with tcp-reset
```

この設定を削除するには `-A` を `-D` に変更して実行します。

```shell
sudo iptables -t filter -D OUTPUT \
  -p tcp --sport 5201 \
  -m statistic --mode random --probability 0.05 \
  -j REJECT --reject-with tcp-reset
```

この挙動を確認してみましょう。`iptables` の設定を行った `alpha-ub01` で `iperf3 -s` を起動し、`beta-ce01` から `alpha-ub01` の 5201 ポートへ `iperf3` で接続すると、データ転送中にランダムに切断される様子が観測できます (運が悪いと接続時のハンドシェイクで遮断され無応答になることがあります)。

```text
[torao@beta-ce01 ~]$ iperf3 -c alpha-ub01 -p 5201 -b 1M -t 60
Connecting to host alpha-ub01, port 5201
[  5] local 192.168.150.51 port 59390 connected to 192.168.150.50 port 5201
[ ID] Interval           Transfer     Bitrate         Retr  Cwnd
[  5]   0.00-1.00   sec   128 KBytes  1.05 Mbits/sec    0    109 KBytes
…
iperf3: error - unable to write to stream socket: Connection reset by peer
```

切断は送信パケット数に対して確率的に発生します。帯域速度が速すぎると一瞬で切断されてしまいますし、遅すぎるとなかなか切断されず観測に時間がかかります。私の環境では `-b 1M` で 1Mbps 程度の帯域制限を設定するとおおむね 10 秒以内に切断が発生して観測しやすくなりました。

### 5.2 ランダムな接続拒否

確立済みの接続を遮断するだけではなく、新しい接続の試行を意図的に拒否することも、アプリケーションの耐性を評価する上で重要です。ここでも `iptables` を使用して、特定のポートへの新しい TCP 接続を確率的に拒否する方法を紹介します。

以下のコマンドは `filter` テーブルの `INPUT` チェーンにルールを追加し、宛先ポートが 5201 の新しい TCP SYN パケット (TCP 接続の開始要求) を 50% の確率で拒否します。この場合、接続元に TCP RST (Reset) パケットを送信して接続を拒否したことを通知します。

```shell
sudo iptables -t filter -A INPUT \
  -p tcp --dport 5201 --syn \
  -m statistic --mode random --probability 0.5 \
  -j REJECT --reject-with tcp-reset
```

この設定を削除するには `-A` を `-D` に変更して実行します。

```shell
sudo iptables -t filter -D INPUT \
  -p tcp --dport 5201 --syn \
  -m statistic --mode random --probability 0.5 \
  -j REJECT --reject-with tcp-reset
```

ここでも `iperf3` を使って挙動を確認しましょう。`iptables` の設定を行った `alpha-ub01` で `iperf3 -s` を起動して `beta-ce01` から `iperf3` の接続を試みると、約 50% の確率で接続が拒否されます。

```text
[torao@beta-ce01 ~]$ iperf3 -c alpha-ub01 -p 5201 -t 3
Connecting to host alpha-ub01, port 5201
iperf3: error - unable to connect stream: Connection refused
```

## 6. まとめと今後の進展

この記事では、ネットワーク上に構築された現代的なシステムに制御可能なネットワークの不安定性を作り出し、アプリケーションの耐障害性を評価するための実践的な手法について解説しました。この方法は、地理分散された大規模システムから、帯域の貧弱なコンシューマ端末やデバイスを想定したアプリケーションのシステムテストに応用できるでしょう。

まとめると、この記事で紹介したネットワーク不安定性テストは、以下の 2 つを組み合わせることでより効率的に実施できます。

- ネットワークのパケット遅延や帯域制限を `tc netem` で注入する。
- TCP の接続拒否やアクティブなセッションの乱断を `iptables` で注入する。

ネットワークの不安定性は、大規模分散システムにおける避けられないリスクです。これらの手段によって、実際のデータセンター間やクラウド環境、公衆モバイル回線などで起こりうる様々なネットワークの不安定な状況を、制御されたテスト環境で再現することが可能です。

これにより、開発者はアプリケーションの潜在的な問題を早期に発見し、より堅牢で信頼性の高いシステムを構築できます。これはユーザに安定したサービスを提供することにつながるでしょう。

また、ここで解説している方法はしばしばアプリケーションに「不可解な挙動」を引き起こす可能性があります。しかし、注入した障害によって生じたその挙動の原因を想像し、考察することは、問題解決能力とシステム開発の理解を深めるための貴重な訓練となるでしょう。

次のステップ:

- 実際の分散システム環境で実施: 可観測性の導入 (Prometheus, Grafana, OpenTelemetry)
- 発生した問題のより深い問題分析のための手段: `tcpdump` や Wireshark を使ったパケットキャプチャとその分析。
- 他のネットワークへ応用: Kubernetes や SD-WAN へ展開。
- カオスエンジニアリングに関連する類似の商用ソリューション: [Gremlin](https://www.hitachi-systems.com/sp/chaos_engineering/)
