# e1-prompts-and-workflows

プロンプトエンジニアリングの成果物、および個人のワークフローに関するノートや設定ファイルを管理するためのリポジトリです。

## 概要 (Overview)
このプロジェクトでは、より高度な言語モデルの活用やAIエージェントの挙動を最適化するためのカスタムプロンプト(システムプロンプトやモジュール定義)を記録・共有しています。

## 内容 (Contents)

- **`any_ai_deep_research_prompt.md`** / **`.xml`**
  **DeepSeek**をはじめとする、任意のLLMを活用した**Deep Research(深掘り調査)**専用に独自開発したシステムプロンプトです。ブラウザ版の任意のAIのチャット欄に貼り付けて、トピックを最後に追記してから送信するだけで実行できます。
  以下の強力な自律型リサーチAIやエージェントのシステムプロンプトをベースに、統合・最適化を行っています：
  - [OpenManus](https://github.com/mannaandpoem/OpenManus)
  - [GPT-Researcher](https://github.com/assafelovic/gpt-researcher)
  - [STORM](https://github.com/stanford-oval/storm)
  - [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT)
  ※ 実行環境やパース要件に合わせて使い分けられるよう、Markdown形式とXML形式の2種類を用意しています。

- **[`docs/scrapbox/`](./docs/scrapbox/README.md)**
  Scrapbox プロジェクト ellimissinina の公開ページを GitHub にミラーした同期ノート。詳細は [`docs/scrapbox/README.md`](./docs/scrapbox/README.md) を参照。

## 目的 (Purpose)
- 自律的な深掘り調査(Deep Research)の精度向上
- 複雑な推論タスクにおけるプロンプトのバージョン管理
- 新しいワークフローの実験と記録

## ライセンス (License)
このリポジトリは [MIT License](./LICENSE) のもとで公開されています。
