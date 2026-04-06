# docs/scrapbox

このフォルダは、公開 Scrapbox プロジェクト **[ellimissinina](https://scrapbox.io/ellimissinina)** の GitHub ミラーです。

## 構成

| パス | 説明 |
|------|------|
| `pages/` | GitHub Actions により自動生成されるページ群 |
| `01_...` / `02_...` / `03_...` | 手動で管理しているファイル（自動同期の対象外） |

## 自動同期について

`docs/scrapbox/pages/` 配下のファイルは **GitHub Actions によって毎週自動生成**されます。  
手動で編集しても、次回の同期実行時に上書きされます。編集は Scrapbox 側で行ってください。

同期ワークフロー: [`.github/workflows/sync-scrapbox.yml`](../../.github/workflows/sync-scrapbox.yml)

## リンク

- Scrapbox プロジェクト: https://scrapbox.io/ellimissinina

最終同期日: 未実行
