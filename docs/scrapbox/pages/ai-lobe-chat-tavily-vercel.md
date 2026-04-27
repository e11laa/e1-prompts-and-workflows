# 完全無料・ウェブ検索対応AIチャット構築ガイド (Lobe Chat + Tavily + Vercel)

Source: https://scrapbox.io/ellimissinina/%E5%AE%8C%E5%85%A8%E7%84%A1%E6%96%99%E3%83%BB%E3%82%A6%E3%82%A7%E3%83%96%E6%A4%9C%E7%B4%A2%E5%AF%BE%E5%BF%9CAI%E3%83%81%E3%83%A3%E3%83%83%E3%83%88%E6%A7%8B%E7%AF%89%E3%82%AC%E3%82%A4%E3%83%89%20%28Lobe%20Chat%20%2B%20Tavily%20%2B%20Vercel%29

最終同期日: 2026-04-27

維持費ゼロで、ウェブ検索・履歴同期・画像アップロードに対応したAIチャット環境を構築します。

1. 全体構成と必要なアカウント
すべてGitHub連携でログイン可能な無料アカウントを使用します。
 フロントエンド: Hugging Face (https://huggingface.co/) (Lobe Chat本体)
 AIモデル: OpenRouter (https://openrouter.ai/)
 検索エンジン: Tavily (https://tavily.com/)
 検索プラグイン: Vercel (https://vercel.com/) (通信エラー回避用)
 DB・ストレージ: Supabase (https://supabase.com/)

Step 1: 各種APIキーの取得
 1. OpenRouter: Keys (https://openrouter.ai/keys)から Create Key を実行し、APIキー(sk-or-v1-...)をメモ。
 2. Tavily: ダッシュボード (https://app.tavily.com/home)から API Key(tvly-...)をメモ。

Step 2: 検索プラグインのVercelデプロイ
 1. dielect/lobechat-tavily-plugin (https://github.com/dielect/lobechat-tavily-plugin) にアクセス。
 2. README内の 「Deploy to Vercel」 をクリック。
 3. Vercelでリポジトリを作成し、そのままデプロイ。
 4. 完了後、URL(例: https://lobechat-tavily-plugin-xxxx.vercel.app)をメモ。
👉 マニフェストURL: URLの末尾に /manifest.json を足したもの

Step 3: Supabase の準備 (DB・Storage)
 1. Supabase (https://supabase.com/) で新規プロジェクトを作成(パスワードは記号なし英数字推奨)。
 2. Database: Project Settings > Database > Connection string (URI) をコピーし、パスワード部分を置換してメモ(DATABASE_URL)。
 3. Storage (バケット): Storage から新規バケット(例: lobe-chat)を Public で作成。
 4. Storage (設定): Project Settings > Storage にて以下を取得。
  Endpoint URL(S3_ENDPOINT)
  S3 Access Keys(New access key を作成し、Access Key / Secret Key をメモ)
  公開用URL(S3_PUBLIC_DOMAIN): https://プロジェクトID.supabase.co/storage/v1/object/public(バケット名は含めない)

Step 4: Hugging Face Spaceの枠作成
 1. Create new Space (https://huggingface.co/new-space) で「Docker」>「Blank」を選択し、Free枠で作成。
 2. 右上の「⋮」>「Embed this Space」から Direct URL (https://username-spacename.hf.space) をコピーしてメモしておきます。

Step 5: GitHub OAuthアプリの作成 (ログイン用)
 1. GitHub Developer Settings (https://github.com/settings/developers) で New OAuth App を作成。
 2. 以下を入力して Register。
  Homepage URL: 【Step 4のDirect URL】
  Authorization callback URL: 【Step 4のDirect URL】/api/auth/callback/github
 3. Client ID と Client Secret をメモ。

Step 6: Lobe Chat本体のデプロイ
 1. Hugging Face Spaceの Files タブから以下の2つのファイルを作成します。
(1) README.md
```markdown
---
title: LobeChat
emoji: 🤯
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 3210
---
```

(2) Dockerfile
(※ 重要: 以下の あなたのSpaceのドメイン の4箇所を、Step 4でコピーしたURLに書き換えてください。例: https://username-spacename.hf.space)
```Dockerfile
FROM lobehub/lobe-chat-database:latest
# 内部通信パッチ (4箇所のドメイン書き換えが必要です)
RUN echo 'const originalFetch = global.fetch; global.fetch = async (...args) => { let [url, options = {}] = args; if (typeof url === "string" && url.includes("あなたのSpaceのドメイン")) { url = url.replace("https://あなたのSpaceのドメイン", "[http://127.0.0.1:3210](http://127.0.0.1:3210)"); options.headers = { ...options.headers, "Host": "あなたのSpaceのドメイン" }; } return originalFetch(url, options); };' > /tmp/fetch-patch.js
ENV NODE_OPTIONS="--require /tmp/fetch-patch.js"
# 外部向けURLの設定
ENV NEXTAUTH_URL=あなたのSpaceのドメイン/api/auth
ENV APP_URL=あなたのSpaceのドメイン
EXPOSE 3210
```

 2. Settings タブ > Variables and secrets に以下を追加。 (※任意のランダム文字列は、パスワード生成サービス等で32文字以上の複雑な文字列を作成してください。私はopensslを使いました)
Variables (Public)
  NEXT_PUBLIC_SERVICE_MODE: server
  NEXT_AUTH_SSO_PROVIDERS: githubSecrets (Private)
  OPENROUTER_API_KEY: Step 1で取得したキー
  DATABASE_URL: Step 3で取得したDB URL
  S3_ENDPOINT: Step 3で取得したエンドポイント
  S3_PUBLIC_DOMAIN: Step 3で確認した公開用URL
  S3_ACCESS_KEY_ID: Step 3で取得したAccess Key
  S3_SECRET_ACCESS_KEY: Step 3で取得したSecret Key
  S3_BUCKET: Step 3で作成したバケット名
  S3_ENABLE_PATH_STYLE: 1
  AUTH_GITHUB_ID: Step 5で取得したClient ID
  AUTH_GITHUB_SECRET: Step 5で取得したClient Secret
  KEY_VAULTS_SECRET: 任意のランダム文字列(32文字以上)
  NEXT_AUTH_SECRET: 任意のランダム文字列(32文字以上)
  AUTH_SECRET: 任意のランダム文字列(32文字以上)
 3. 設定後、右上の「⋮」から Restart this Space (Factory rebuild推奨) を実行。

Step 7: 検索プラグインの設定
 1. Lobe Chatにログインし、入力欄下の プラグインアイコン (田) をクリック。
 2. 「プラグインストア」>「＋MCPプラグインを追加」>「オンラインリンク」から Step 2のURL/manifest.json を登録。
 3. インストール後、一覧のプラグインの右側にある ⚙️(歯車) を開き、TAVILY_API_KEY の欄に Step 1で取得したTavilyキー を入力して保存。
以上で完了です。

トラブルシューティング:
	Openrouterを無料枠で使うなら、OpenRouter 内で free と検索して出てくる無料モデル（例: nvidia/nemotron-3-super-120b-a12b:free など）を Lobe Chat の設定画面で明示的に選択する必要があります。
		openrouterの小技ですが、10ドルだけチャージすると無料モデルが40倍使えたりします。
	Supabase の無料プロジェクトは、1 週間ほどアクセスがないとデータベースが自動的に停止（Pause）されます。Supabase の管理画面に行き、プロジェクトを「Restore」させる必要があります。
	ログインできない場合は、ブラウザ設定で hf.space の Cookie を許可するか、Direct URL（https://username-spacename.hf.space）に直接アクセスしているか確認してください。
	起動しない場合は、Settings から 「Factory rebuild」 を何度か試す必要があります。また、余計な環境変数を入れすぎないようにしてください。
	LobeChatはサービスの移行の途中であり、バージョン管理の問題で以下を試すと解決する問題があるかもしれません。
```diff
# 環境変数の追加・修正
- NEXT_AUTH_SECRET=...
+ AUTH_SECRET=... (32文字以上のランダム文字列)
+ NEXT_PUBLIC_AUTH_URL=https://[あなたのユーザー名]-[スペース名].hf.space/api/auth

- NEXT_AUTH_SSO_PROVIDERS=github
+ AUTH_SSO_PROVIDERS=github

# S3設定の補強
+ S3_SET_ACL=0
+ S3_REGION=ap-northeast-1 (Supabaseのリージョンに合わせて入力)
```

