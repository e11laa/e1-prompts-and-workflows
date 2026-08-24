# Xの「おすすめ」アルゴリズムを、会社にたとえて詳しく読む(AI記事)

Source: https://scrapbox.io/ellimissinina/X%E3%81%AE%E3%80%8C%E3%81%8A%E3%81%99%E3%81%99%E3%82%81%E3%80%8D%E3%82%A2%E3%83%AB%E3%82%B4%E3%83%AA%E3%82%BA%E3%83%A0%E3%82%92%E3%80%81%E4%BC%9A%E7%A4%BE%E3%81%AB%E3%81%9F%E3%81%A8%E3%81%88%E3%81%A6%E8%A9%B3%E3%81%97%E3%81%8F%E8%AA%AD%E3%82%80%28AI%E8%A8%98%E4%BA%8B%29

最終同期日: 2026-08-24



Xの「For You」で投稿が伸びる仕組みは、単純な「いいね数ランキング」ではありません。

公開された推薦コードを見ると、実際には、

* 投稿を意味的に整理する部署 → 候補を集める部署 → ユーザーごとの反応を予測するPhoenix → Xとしての価値を点数化する部署 → 多様性調整 → Safety審査

という、かなり大きな会社組織のような構造になっています。

この記事では、2026年8月に公開されたX/xAIの推薦アルゴリズムをもとに、「1つの投稿がFor Youに載るまで」を、非専門家にも追える形で順番に見ていきます。

なお、公開コードから分かるのは推薦システムの構造・モデル・default設定などです。実際の本番データ、checkpoint、内部サービスの一部などは公開されていないため、「現在のXを完全に再現できる」という意味ではありません。

*** まず全体像：投稿はどうやってFor Youまで届くのか

細部に入る前に、最初に流れだけ掴んでおきます。

Xでは、投稿された瞬間にまず内容を機械が読み取り、本文・画像・動画などを「意味の数値表現」に変換します。その表現はさらに、Phoenixなどが扱いやすいSemantic ID(SID)という圧縮表現にされます。

その後、あるユーザーがXを開くと、今度はユーザー側の情報が集められます。

「誰をfollowしているか」「最近どんな投稿を見たか」「何にLikeしたか」「何を長く見たか」といった履歴から、その人が今どんな投稿に反応しそうかを推測する準備をします。

次に、複数の候補探索システムがそれぞれ別ルートから大量の投稿候補を持ってきます。

	投稿側
	本文・画像・動画
	↓
	意味ベクトル化
	↓
	SID化
	↓
	投稿候補として検索可能な状態になる
	
	
	viewerがXを開く
	↓
	viewer情報・行動履歴を取得
	↓
	複数のCandidate Sourceが候補投稿を集める
	↓
	明らかに不適格な候補を除外
	↓
	Phoenix Rankingが
	「この人がこの投稿を見たら何をするか」
	を予測
	↓
	RankingScorerが
	その予測をXとしての価値に換算
	↓
	cold-start / author diversity / OON補正
	↓
	DPPで似た投稿ばかりになるのを防ぐ
	↓
	上位候補を残す
	↓
	Visibility / Safety審査
	↓
	For Youへ

会社にたとえるなら、

> 資料整理部が投稿を整理し、
> 顧客分析部がviewerを調べ、
> 営業部が候補を集め、
> Phoenix研究所が反応を予測し、
> 経営企画部が点数化し、
> 編成部と法務部が最後に整える

という流れです。

この全体像を頭に置いたうえで、各部署を詳しく見ていきます。

*** Xは「良い投稿」を探しているわけではない

最初に最も重要な前提です。

Xは基本的に、

> 「この投稿は良い投稿か？」

を全ユーザー共通で判定しているわけではありません。

より正確には、

> 「* このユーザーに、この投稿を見せたら何が起こりそうか？」

を予測しています。

たとえば同じゲーム開発動画でも、

	ゲーム制作動画をよく見る人
	政治ニュースばかり読む人

では、予測されるLike率、Reply率、Follow率などが違います。

つまり投稿Aに固定された「おすすめ力82点」があるのではなく、

	ユーザーX × 投稿A → 高評価
	ユーザーY × 投稿A → 低評価
	ユーザーZ × 投稿A → 中評価

のように、* ユーザーと投稿の組み合わせごとに評価が変わるのが基本です。

*** 第1部：投稿を「意味の座標」に変換する資料整理部

Xは投稿本文をそのままPhoenixへ渡しているわけではありません。

まず投稿は、本文、画像、動画、引用投稿などをまとめて読み取られ、* multimodal embeddingと呼ばれる数値ベクトルに変換されます。

公開されたv5系実装では、投稿本文だけでなく、作者名、画像、動画フレーム、カード、引用投稿などもrendererでまとめられます。

その後、Qwen3-VL-Embedding-8Bを利用する公開reference実装では、4096次元の表現を1024次元へ切り詰め、正規化します。

イメージとしては、

	「Godotで水面shaderを作りました」
	+ 動画
	+ 作者情報
	+ 引用など
	
	↓ 意味理解
	
	0.031, -0.182, 0.442, ...

という感じです。

この1024個の数字には、

> 37番目 = ゲーム
> 102番目 = プログラミング

のような人間が読める意味はありません。

多数の座標が分散して意味を表現する「意味空間」です。

*** 1024個の数字を6個のSIDへ圧縮する

さらにXは、この意味ベクトルを* Semantic ID(SID)という6個の整数へ圧縮します。

たとえば、

	42, 18, 203, 7, 91, 12

のような形です。

ここで誤解しやすいのですが、

	42 = ゲーム
	18 = プログラミング
	203 = shader

という分類コードではありません。

実態は* Residual Quantization(残差量子化)です。

ざっくり言えば、

1. 元ベクトルに一番近い代表ベクトルを256個から選ぶ
2. それを元ベクトルから引く
3. 残った誤差に一番近い代表ベクトルをまた選ぶ
4. これを6回行う

という処理です。

元ベクトル
	≈ C142
	 + C218
	 + C3203
	 + C47
	 + C591
	 + C612

となります。

会社でたとえるなら、SID担当は「ジャンル分類部」ではなく* 圧縮梱包係です。

> 「1024個の数字を毎回運ぶのは重いので、この6個の整理番号で扱えるようにします」

という仕事です。

*** 第2部：閲覧者がXを開くと「顧客分析部」が動く

あるユーザーがFor Youを開くと、Xはそのユーザーについて大量の情報を集めます。

これが* Query Hydrationです。

代表的には、

	過去の行動履歴
	followしている人
	block / muteしている人
	subscription
	過去に表示した投稿
	explicit / implicit engagement
	country / language / location
	年齢・性別系feature
	installed apps
	timezoneや時刻
	興味topic

などです。

公開Phoenix系configでは、Ranking側の履歴長は最大約1000イベント規模で扱える構成になっています。

つまりPhoenixは、

> 「この人はゲーム好き」

という一枚のプロフィールだけを見るのではなく、

	Godot動画を長く見る
	↓
	Pixel ArtをLike
	↓
	Unity記事はすぐ離脱
	↓
	ゲーム音楽をShare
	↓
	ゲーム開発者をFollow

という* 時系列の行動履歴そのものを見ています。

*** 第3部：候補を集める7つの営業部

次は* Candidate Retrievalです。

ここでXは、いきなり全投稿をPhoenix Rankingへ送るわけではありません。

まず複数のSourceが、それぞれ別の考え方で「このviewerに見せる候補」を集めます。

** ThunderSource

* フォロー関係担当です。

viewerがfollowしている作者から、新しい投稿を集めます。

いわゆる* in-network候補の主要ルートです。

公開baselineでは最大1200件程度を要求する設定です。

** TweetMixerSource

別のTweetMixer recommendation serviceへ問い合わせる窓口です。

viewer ID、country、language、既読投稿などを渡して候補を取得します。

ただしHome Mixer側に公開されているのはadapter部分なので、* TweetMixer内部でどう候補生成しているかまでは完全には見えません。

公開baselineではdefault offです。

** SimClustersSource

* 「過去に好きだった投稿の近所を探す担当」です。

viewerが過去に反応した投稿を起点に、SimClustersという別のinterest表現を使って類似投稿をANN検索します。

	以前このゲーム開発動画が好きだった
	↓
	これと近いinterest clusterの投稿を探す

というルートです。

最大800件程度までまとめます。

** PhoenixSource

これが* Phoenix Retrievalです。

viewerの行動履歴から「現在の興味状態」を検索用ベクトルにし、SIDなどから作った投稿側ベクトルと照合します。

簡単に言えば、

> 「この人の現在地と、この投稿の意味的位置は近いか？」

を高速に判定する検索部門です。

ここではまだ、

> Like率 13%
> Follow率 2%

のような精密予測はしません。

あくまで* 面接に呼ぶ候補を探す段階です。

** PhoenixTopicsSource

Phoenix Retrievalのtopic指定版です。

特定topicを要求する画面などで使われます。

** PhoenixMOESource

別のPhoenix Retrieval clusterを利用する追加ルートです。

公開Home Mixerから確認できるのは、「別のMOE系retrieval endpointへ行動履歴を送り候補を取得する」という部分までです。

** CachedPostsSource

既に候補とscoreがcacheされている場合、通常のretrievalを再実行せず、その候補を再利用します。

*** Sourceごとに固定倍率があるわけではない

公開コードを見る限り、

	Thunder候補だから1.2倍
	SimClusters候補だから0.8倍

のような一般的なSource別固定倍率はありません。

違いは主に、

	何件持ち込めるか
	どんな候補を持ってくるか
	後段のfilterやOON条件を受けるか

です。

その後、候補は基本的に同じPhoenix Rankingへ送られます。

*** 第4部：候補の履歴書を完成させるHydration

Sourceから来た直後のcandidateは、投稿ID中心の不完全なデータです。

そこで候補ごとに情報を補います。

たとえば、

	投稿ID
	作者ID
	in-networkか
	相互followか
	replyか
	quoteか
	media情報
	language
	subscription
	engagement count
	SID
	作者情報
	block関係

などです。

会社で言えば* 身元調査部です。

*** 第5部：Phoenixに会わせる前のFilter

Phoenixによる推論は比較的高価なので、その前に明らかに不要なcandidateを落とします。

代表的には、

	同じtweet IDの重複
	投稿情報を取得できない候補
	48時間より古い投稿
	viewer自身の投稿
	OONのreply / retweet
	特定のSimClusters由来NSFW候補
	retweet重複
	subscription条件違反
	既読投稿
	既にserve済みの投稿
	muted keyword
	block / mute関係
	topic不一致
	video除外request
	新規viewer向けminimum engagement条件
	実験用inventory holdout

などがあります。

つまり、* ここで落ちた投稿はPhoenixに採点すらされません。

*** 第6部：Phoenix Rankingが「この人は何をするか」を予測する

ここが推薦の中心です。

候補がPhoenix Rankingへ送られると、viewerごと・candidateごとに複数の行動確率を予測します。

たとえば、

	Favorite       18%
	Reply           3%
	Repost          1%
	Follow author   0.7%
	Share           0.3%
	Report          0.002%
	
	予測Dwell       12秒

のような感じです。

実際にはもっと多くのheadがあります。

Like、Reply、Quote、Repost、Followだけでなく、

	Click
	Profile click
	Share
	DM Share
	Copy Link
	Photo expand
	Video open
	Not interested
	Block
	Mute
	Report
	Dwell time

なども予測対象です。

Phoenixは、

> 「この人は喜びそうか？」

だけでなく、

> 「この人は嫌がりそうか？」

も同時に予測しています。

したがって、

	Likeしそう
	Replyしそう
	
	しかし
	Reportもしそう
	Muteもしそう

なら総合評価は下がります。

しかもこれは、

> 「この投稿は一般的に通報されやすい」

ではなく、

* 「このviewerが、この投稿を見たときに通報する確率」

です。

*** 第7部：RankingScorerが「会社として何点か」に変換する

Phoenixは予測を出すだけです。

その後に* RankingScorerという別部署が、

> 「ではXという会社は、その行動を何点として扱うのか？」

を決めます。

公開baselineの代表的なweightは、

	Actionweight	
	Favorite	+0.5
	Reply	+5
	Repost	+1
	Follow Author	+4
	Share	+2
	Share via DM	+5
	Share via Copy Link	+20
	Not Interested	-43.2
	Block Author	-31.2
	Mute Author	-58.8
	Report	-234

です。

ただし、

> 1 Report = 468 Likes

という意味ではありません。

* 実際のengagement countにweightを掛けるのではなく、Phoenixが予測した確率へ掛けます。

*** 投稿者の過去実績はどう効くのか

単純な、

	過去10投稿平均1000Like
	↓
	新投稿に+100点

という仕組みではありません。

Phoenixにはauthor ID由来の表現があり、学習を通じて、

> この作者はどんなviewerと相性が良いか
> どんな行動につながりやすいか

という情報が間接的にモデルへ染み込みます。

つまり、

	過去投稿
	↓
	誰がどう反応したか
	↓
	Phoenixが学習
	↓
	この作者とこのviewerの相性予測に反映

という経路です。

投稿者目線では、「人気スコアを貯金する」というより、

* 「自分の投稿が誰に刺さる作者なのか」という履歴を作っている

と考えた方が近いです。

*** 第8部：RankingScorer内部の補正

** Cold Start

これは「新人作者なら全員優遇」という機能ではありません。

主に、

	original post
	follower数が一定以下
	view数がまだ少ない
	元scoreもある程度見込みがある

といった候補から、限定的に1件を選び、一定順位付近まで引き上げられる探索機構です。

> 「実績がないから永遠に面接機会がないのは困るので、一人だけ試験展示する」

という* 新人発掘枠です。

** Author Diversity

同じ作者が上位を独占しないようにします。

公開defaultでは、同じ作者が既に前にいるほど、

	1回目  ×1.0
	2回目  ×0.625
	3回目  ×0.4375
	4回目  ×0.34375
	...

のように減衰します。

** OON補正

* OON(Out Of Network)とは、viewerがfollowしていない作者です。

公開baselineでは通常、

OON score × 0.75

です。

同じPhoenix scoreなら、follow中作者の方が有利ですが、OONでも十分にscoreが高ければ勝てます。

*** 第9部：DPPが「似た投稿ばかり」を防ぐ

ここまでscore順で並べるだけだと、

	Godot shader
	Godot shader
	Godot shader
	Godot shader

というfeedになりかねません。

そこでVMRankerのDPPが入ります。

DPP(Determinantal Point Process)は、簡単に言えば、

> 「高得点を維持しつつ、候補同士が似すぎない組み合わせを選ぶ」

仕組みです。

たとえば、

	A score 0.92 : Godot水shader
	B score 0.91 : Godot水shader
	C score 0.87 : Pixel Art

なら、A+BよりA+Cの方がfeed全体として選ばれやすくなることがあります。

*** 第10部：上位50件を残すTop-K

DPPまで終わると、TopK selectorは非常に単純です。

* score上位50件を残します。

公開baselineでは、

	TOP_K_CANDIDATES_TO_SELECT = 50
	RESULT_SIZE = 35

です。

つまり、いったん50件を残したあと、Safetyやconversation重複などでさらに落とせる余裕を持っています。

*** 第11部：Visibility部門は「おすすめしてよいか」を審査する

ここはPhoenixとは完全に別です。

Phoenixが、

> 「この人には絶対刺さる。score 1位」

と言っても、Visibilityが、

> 「推薦面には出せない」

と判断すれば消えます。

Phoenixは* 何を見せたいか。

Visibilityは* 何を見せてよいか。

です。

** フォロー内とフォロー外でSafety基準が違う

	in-network
	→ TimelineHome
	
	out-of-network
	→ TimelineHomeRecommendations

という別policyが使われます。

つまり、

> 「フォロワーには見せてもよい」

と、

> 「知らない人にアルゴリズムが積極的に拡散してよい」

は別問題です。

後者の方が厳しくなっています。

** Home共通で対象になるもの

公開ruleには、

	suspended / deactivated author
	protected account
	viewerとのblock / mute
	spam
	hateful conduct
	violent speech
	abuse
	civic integrity
	legal takedown
	local law
	sensitive contentの年齢制限
	stale post

などがあります。

** OON推薦ではさらに厳しい

フォロー外へのrecommendationではさらに、

	DMCA media
	geo restricted media
	NSFW author
	NSFW tweet
	NSFW text
	gore / violence
	Do Not Amplify
	malicious URL
	spam high recall
	abuse / insults
	compromised account
	impersonation
	NSFW avatar / banner
	abusive high recall author

などが追加でDrop対象になります。

つまり、

	フォロワーには普通に見えている
	しかしFor Youでは新規ユーザーへ出ない

という状態は十分あり得ます。

*** クリエイターにとって何が重要なのか

この構造を見ると、「Xで伸ばす」の意味も少し変わります。

単に、

> Likeをたくさん集めればいい

ではありません。

重要なのは、

* 誰に推薦されたときに、良い反応が予測される投稿なのか

です。

たとえばゲーム制作者なら、

> ゲーム好き全般に薄く刺さる投稿

より、

> Godot、shader、indie devなど特定のviewer層に非常に強く刺さる投稿

の方が、Phoenixにとって分かりやすい場合があります。

さらに、

	Followにつながる
	Replyにつながる
	Shareにつながる
	長く見られる
	Negative feedbackにつながりにくい

という組み合わせが重要になります。

そしてもう一つの軸が、

* Safety上「知らない人へ推薦可能な投稿・アカウント」であり続けること

です。

*** まとめ

XのFor Youは、投稿に一個の人気scoreを付ける仕組みではありません。

最初に投稿内容を意味表現へ変換し、viewerが開いた瞬間に複数のretrieval systemが候補を集め、その後Phoenixが、

> 「このviewerにこの投稿を見せたら何が起こるか」

を予測します。

その予測をRankingScorerがXとしての価値に換算し、cold-start、author diversity、OON補正、DPPを経て、最後にVisibilityが「推薦してよいか」を審査します。

つまりXのおすすめは、

> * 候補探索 → 個人別反応予測 → 価値換算 → 編成 → Safety審査

という多段構造です。

投稿者側から見るなら、

* 「良い投稿を作る」だけでなく、「誰にとって良い投稿なのかをシステムが学習しやすい状態を作る」

ことが重要です。

そして、Phoenixで高評価されることと、Visibilityで推薦可能であることは別問題です。

この二つを分けて考えると、Xのおすすめアルゴリズムはかなり理解しやすくなります。

