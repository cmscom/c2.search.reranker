# c2.search.reranker

コンテンツタイプのブースト重み付けと半減期による時間減衰を使って、検索結果をリランキングするPloneアドオンです。

[English](README.md)

## 機能

### コンテンツタイプのブースト重み付け

コンテンツタイプをグループ（一般ページ、お知らせ、ナレッジ、その他）に割り当て、各グループにブースト係数を設定できます。ブースト値が高いコンテンツタイプは、検索結果でより上位に表示されます。

### 半減期による時間減衰

各グループに半減期（日数）を設定できます。古いコンテンツは指数関数的な減衰式に基づいて、徐々に関連性が低下します。

```
decay = 0.5 ^ (経過日数 / 半減期日数)
```

### 複合スコアリング

最終スコアは以下の式で計算されます：

```
final_score = original_score * boost * decay
```

`original_score` はZCTextIndexからの関連性スコアです。

### コントロールパネル

すべての設定はPloneコントロールパネル（サイト設定 > Search Reranker Settings）およびREST API（`@controlpanels/reranker`）から変更できます。

### ベクトル検索連携（計画中）

コントロールパネルには `collective.vectorsearch` によるベクトル検索連携の設定が含まれています。キーワード検索とベクトル検索の比率を設定可能です。この機能は将来のリリースで実装予定です。

### テスト用ブラウザビュー

`@@reranker-search?SearchableText=keyword` でアクセスできるテストビューがあります。リランキング結果をスコアの詳細（元スコア、ブースト、減衰、最終スコア）とともに表示します。

### REST API サマリーシリアライザー

plone.restapi のリスティングレスポンスに追加のメタデータフィールド（`image_field`、`image_scales`、`effective`、`Subject`）を付与します。

## 動作要件

- Python 3.10 - 3.13
- Plone 6.0 または 6.1

## インストール

`pip` でインストールします：

```shell
pip install c2.search.reranker
```

その後、Ploneサイトの **サイト設定 > アドオン** からアドオンをインストールしてください。

## 開発

### 前提条件

- [uv](https://docs.astral.sh/uv/)
- [Make](https://www.gnu.org/software/make/)
- [Git](https://git-scm.com/)

### セットアップ

```shell
git clone git@github.com:terapyon/c2.search.reranker.git
cd c2.search.reranker
make install
```

### 主なコマンド

```shell
make test           # テストの実行
make format         # コードフォーマット
make lint           # リンターチェック
make i18n           # ロケールファイルの更新
make start          # Ploneインスタンスを localhost:8080 で起動
make create-site    # 新規Ploneサイトを作成
```

### ツール

- **リンター / フォーマッター**: [ruff](https://docs.astral.sh/ruff/)
- **テスト**: [pytest](https://docs.pytest.org/)
- **ビルド**: [hatchling](https://hatch.pypa.io/)

## コントリビュート

- [Issue tracker](https://github.com/terapyon/c2.search.reranker/issues)
- [ソースコード](https://github.com/terapyon/c2.search.reranker/)

## ライセンス

このプロジェクトは [GPL-2.0-only](https://spdx.org/licenses/GPL-2.0-only.html) でライセンスされています。
