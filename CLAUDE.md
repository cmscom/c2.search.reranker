# Claude Code 開発ガイド

このプロジェクトはPlone (Classic)をdevcontainer環境で実行しています。

## 環境情報

- **プロジェクト**: Plone (Classic)
- **開発環境**: devcontainer (Docker Compose)
- **ワークスペース**: `/workspace`
- **アプリケーションディレクトリ**: `/app`

## パッケージ情報

### 基本情報

- **パッケージ名**: c2.search.reranker
- **バージョン**: 1.0.0a0 (アルファ版)
- **説明**: Plone用の検索リランカーアドオン
- **ライセンス**: GPL-2.0-only
- **作者**: Manabu TERADA (terada@cmscom.jp)
- **リポジトリ**: https://github.com/terapyon/c2.search.reranker

### 実行環境

- **Python**: 3.12.11
- **Plone**: 6.1.2
- **対応Ploneバージョン**: 6.0, 6.1
- **対応Pythonバージョン**: 3.10, 3.11, 3.12, 3.13

### 主要な依存パッケージ

- **Products.CMFPlone**: 6.1.2
- **plone.api**: 2.5.2
- **plone.restapi**: 9.15.1

### パッケージ構造

```
src/c2/search/reranker/
├── __init__.py           # バージョン情報とロガー設定
├── configure.zcml        # ZCML設定
├── content/              # コンテンツタイプ
├── controlpanels/        # コントロールパネル
├── indexers/             # カスタムインデクサー
├── interfaces.py         # インターフェース定義
├── locales/              # 多言語対応
├── profiles/             # GenericSetupプロファイル
├── serializers/          # REST APIシリアライザー
│   └── summary.py
├── setuphandlers/        # セットアップハンドラー
├── testing.py            # テスト用の設定
├── upgrades/             # アップグレードステップ
└── vocabularies/         # ボキャブラリー
```

### ビルドシステム

- **ビルドバックエンド**: hatchling
- **パッケージマネージャー**: uv (非管理モード)
- **リンター/フォーマッター**: ruff
- **テストフレームワーク**: pytest

## Ploneの起動方法

devcontainer内でPloneを起動するには、以下のコマンドを実行してください：

```bash
cd /app
./docker-entrypoint.sh start
```

起動後、以下のURLでアクセスできます：
- **Plone サイト**: http://localhost:8080

## ポート

- **8080**: Plone (自動転送設定済み)

## devcontainer設定

devcontainerのビルド時に以下が永続化されます：

- Claude Code認証情報: `/root/.claude`
- 追加設定: `/root/.config`
- zshコマンド履歴: `/commandhistory`

devcontainerを再ビルドしても、Claude Codeへのログインは1回だけで済みます。

## 開発について

### ローカル開発（devcontainer外）

ローカルで開発する場合は、以下のコマンドを使用します（`uv`が必要）：

```bash
# 初回セットアップ
make install

# Ploneサイトの作成
make create-site

# テストの実行
make test

# コードフォーマット
make format

# リンターチェック
make lint
```

### devcontainer開発

devcontainer内では、パッケージは既に `/workspace` にマウントされ、`/app` にインストールされています。
コードを編集すると、Plone再起動後に反映されます。

### ツール

- **リンター/フォーマッター**: ruff (設定: [pyproject.toml](/pyproject.toml))
- **テスト**: pytest
- **ビルド**: hatchling

## 参考情報

- devcontainer設定ファイル: [.devcontainer/devcontainer.json](/.devcontainer/devcontainer.json)
- Docker Compose設定: [docker-compose.yml](/docker-compose.yml)
- プロジェクト設定: [pyproject.toml](/pyproject.toml)
- README: [README.md](/README.md)
