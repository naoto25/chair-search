# chair-search

中古のオカムラ「シルフィー」とイトーキ「アクト」の肘付きを見張り、30,000 円以内の出品が新しく出たとき、または値下げされたときに LINE へ通知する。

GitHub Actions が 15 分おきに次の 4 サイトを確認する。

| サイト | 読み方 |
|---|---|
| オフィスバスターズ | シリーズ別一覧ページ（新しい順の 1 ページ目）。検索ページは robots.txt で禁止されているので使わない。3 万円以内の肘付きだけ詳細ページのキャッチコピー・タグ・商品説明を見て、「固定肘」があれば除く |
| ビックリユース | 検索画面が裏で呼ぶ検索 API の JSON |
| オフィスレスキュー119 | 検索結果の HTML。肘の有無は一覧に書かれていないので、3 万円以内の候補だけ詳細ページを見る |
| メルカリ | Playwright で検索画面（販売中・3 万円以下・新しい順）を開き、画面が受け取る検索結果の JSON を読む |

価格はすべて税込の表示価格（送料は含まない）。設計は [docs/superpowers/specs](docs/superpowers/specs/2026-11-11-chair-price-monitor-design.md) にある。

## セットアップ

### 1. LINE の公式アカウントを作る

1. [LINE Developers](https://developers.line.biz/console/) にログインし、プロバイダーを作る
2. 「Messaging API」チャネルを作る（LINE Official Account Manager で公式アカウントを作る流れになる）
3. チャネルの「Messaging API 設定」で **チャネルアクセストークン（長期）** を発行する
4. 同じ画面の QR コードから、その公式アカウントを自分の LINE で友だち追加する
5. 「チャネル基本設定」の一番下にある **あなたのユーザー ID**（`U` から始まる）を控える
6. LINE Official Account Manager の応答設定で「応答メッセージ」をオフにしておくと、話しかけたときの自動返信が出ない

無料プランは月 200 通まで。1 回の実行で見つかった分は 1 通（最大 12 件のカルーセル）にまとめて送る。

### 2. GitHub の Secrets を登録する

リポジトリの Settings → Secrets and variables → Actions → New repository secret で次の 2 つを登録する。

- `LINE_CHANNEL_ACCESS_TOKEN`: 手順 1-3 のトークン
- `LINE_USER_ID`: 手順 1-5 のユーザー ID

### 3. 動かす

`main` ブランチに `.github/workflows/watch.yml` があれば 15 分おきに動く。すぐ試すときは Actions → watch → Run workflow。

最初の 1 回は、今出ている 3 万円以下の出品をまとめて通知する。LINE の Secrets が未登録のあいだは、送らずに失敗として終わり、`state.json` も更新しない（登録後の最初の実行でまとめて届く）。

## 通知の条件

- タイトル（とサイトによっては説明・カテゴリ）に「シルフィー / シルフィ / Sylphy」と「オカムラ / okamura」、または「アクト / Act」と「イトーキ / itoki」がある
- 「肘」「ひじ」「アーム」のどれかがある（メルカリだけは肘の記載がなくても通知し、カードに「肘：記載なし（写真で確認）」と出す）
- 「肘なし」「肘無」「アームレス」「固定肘」などがない
- 「シルフィー用」「パーツ」「肘置き」など部品だけの出品ではない
- 税込 30,000 円以下で、前回の記録になかった（新着）か、前回より安くなった（値下げ）

詳細ページから読んだ内容は `detail_cache.json` に保存し、同じ出品の詳細ページは 1 回しか読まない。

同じサイトの取得が 3 回続けて失敗したら、LINE で 1 回知らせる。サイトの画面が変わった可能性がある。

## 開発

```bash
uv sync --extra browser
uv run playwright install chromium
uv run pytest
uv run python -m chair_watch.main   # LINE の環境変数がなければ送らずに表示する
```
