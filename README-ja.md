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

### ベクトル検索連携（オプション）

`collective.vectorsearch` がインストールされている場合、キーワード検索とベクトル検索（意味的類似性）を組み合わせることができます。キーワード／ベクトルの比率は設定可能です（例：キーワード50% / ベクトル50%）。

### コントロールパネル

すべての設定はPloneコントロールパネル（サイト設定 > Search Reranker Settings）およびREST API（`@controlpanels/reranker`）から変更できます。

### テスト用ブラウザビュー

検索結果のデバッグと比較のためのテストビューが2つあります：

- `@@reranker-search?SearchableText=keyword` — キーワードのみのリランキング（スコア詳細付き）
- `@@hybrid-search?SearchableText=keyword` — ハイブリッド検索（キーワード＋ベクトル、全スコア内訳付き）

### REST API サマリーシリアライザー

plone.restapi のリスティングレスポンスに追加のメタデータフィールド（`image_field`、`image_scales`、`effective`、`Subject`）を付与します。

## スコアリングアルゴリズム

このアドオンは3つのスコアリングパターンを提供します。すべてのパターンで、**ブースト**と**時間減衰**は基本の関連性スコアが計算された後の最終ステップで適用されます。

### パターン1：キーワードのみ（ベクトル検索なし）

ベクトル検索が無効、または `collective.vectorsearch` が未インストールの場合：

```
final_score = original_score * boost * decay
```

- `original_score`: ZCTextIndexからの関連性スコア（`data_record_normalized_score_`）
- `boost`: コンテンツタイプグループの係数（グループごとに設定可能、デフォルト1.0）
- `decay`: 時間減衰係数 `0.5 ^ (経過日数 / 半減期日数)`（グループごとに設定可能、デフォルト半減期60日）

### パターン2：ハイブリッド — Scoreモード（加重平均）

正規化されたスコアを使ってキーワード検索とベクトル検索を結合します：

```
keyword_score  = 正規化されたZCTextIndexスコア (0.0 - 1.0)
vector_score   = VectorIndexのコサイン類似度 (0.0 - 1.0)
combined_score = keyword_score * keyword_weight + vector_score * vector_weight
final_score    = combined_score * boost * decay
```

- キーワードスコアは結果セット内の最大値で割って正規化
- `keyword_weight = keyword_search_ratio / 100`（設定可能、デフォルト50%）
- `vector_weight = 1.0 - keyword_weight`
- 片方の検索メソッドでのみ見つかった結果は、もう一方のスコアが0.0になる

### パターン3：ハイブリッド — RRFモード（Reciprocal Rank Fusion）[デフォルト]

生のスコアではなく順位を使ってキーワード検索とベクトル検索を結合します。2つの検索手法間のスコアスケールの違いに影響されない堅牢な手法です。

```
keyword_rrf    = 1 / (k + keyword_rank)
vector_rrf     = 1 / (k + vector_rank)
combined_score = keyword_rrf * keyword_weight + vector_rrf * vector_weight
final_score    = combined_score * boost * decay
```

- `k = 60`（上位ランクの項目が支配的になりすぎるのを防ぐ定数）
- 各結果セットを独自のスコアでソートして順位を割り当て（1 = 最上位）
- 片方の検索でのみ見つかった結果は、もう一方のRRFが0.0になる
- `keyword_weight` と `vector_weight` はScoreモードと同じ

### スコアリングパイプラインの概要

```
ステップ1: キーワード検索を実行（常時）
ステップ2: ベクトル検索を実行（有効かつ利用可能な場合）
ステップ3: スコアを結合（ScoreモードまたはRRFモード）
ステップ4: boost * decay を適用して final_score を算出
ステップ5: final_score の降順でソート
```

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
