---
name: knowledge-system-screenshot
description: 株式会社アルパイン設計事務所のナレッジシステム (PDM＋ナレッジ検索、http://210.165.3.139/web/) の主要画面を、Playwright ヘッドレス Chromium で自動キャプチャするスキル。役員報告書・社内会議資料・進捗報告などで「最新の実画面」を素材として必要とする場面で使う。ユーザーが「ナレッジシステムの画面を取って」「ナレッジの最新画面をキャプチャ」「あの社内ナレッジのスクショ」「ナレッジ画面の自動取得」「ナレッジのUI画像」等と言った場合に必ずこのスキルを発動する。引数で対象画面（ホーム／統合検索／AI検索／類似検索／図面一覧／プロジェクト一覧／製品一覧／ワークフロー設定／クロール設定）を絞り込むことも可能。
---

# Knowledge System Screenshot

社内ナレッジシステム（創屋株式会社開発、当社が投資・精度確認担当の PDM＋ナレッジ検索）の主要画面を、Cowork の bash サンドボックス上で Playwright ヘッドレス Chromium を使って自動キャプチャするスキル。

## 何を解決するか
- 役員報告／社内会議／提案書の素材として、常に **最新の実画面** を貼れるようにする
- 9画面を毎回手動で開いてスクショする手間（〜10分）を、**約30秒**に短縮
- 開発が進んで画面が更新されても、スクリプト1本で資料の差し替えが可能

## 動作環境
- Cowork mode の bash サンドボックスで動作
- 初回のみ Playwright（playwright-core）と Chromium Headless Shell をインストール
- Playwright と Chromium のキャッシュは `./node_modules` と `./browsers` に置くので、knowledge_system フォルダがマウントされていれば2回目以降は再インストール不要

## ファイル一覧（このフォルダ内）
- `SKILL.md`            — このスキル定義
- `grab_screenshots.js` — メインスクリプト（Playwright で巡回・キャプチャ）
- `setup.sh`            — 初回環境セットアップ（Playwright と chromium-headless-shell のインストール）
- `run.sh`              — 実行スクリプト（setup 済を前提に grab_screenshots.js を起動）
- `.env.example`        — 認証情報テンプレート（KNOW_ID, KNOW_PW, KNOW_BASE_URL）

## 使い方（初回）
1. このフォルダを Cowork の skills フォルダにコピー（後述）
2. `.env.example` をコピーして `.env` を作成、KNOW_ID / KNOW_PW を記入
3. ユーザーが「ナレッジシステムの画面を取って」等と発話 → このスキルが発動
4. Claude が自動で以下を実行：
   - `bash setup.sh`（playwright と chromium-headless-shell をインストール、初回のみ）
   - `bash run.sh`（巡回キャプチャ実行）
5. 取得画像は `./screenshots/01_home.png` 〜 `07_crawl.png` として保存される

## 使い方（2回目以降）
- setup は不要。`bash run.sh` だけで全画面再取得

## 取得対象画面（デフォルト9種、`grab_screenshots.js` の `pages` 配列で調整可）
| # | URL | 出力ファイル名 | 内容 |
|---|-----|----------------|------|
| 1 | `/web/` | `01_home.png` | ホーム（通知・お知らせ） |
| 2 | `/web/chat` | `02_ai_search.png` | AI検索（自然言語チャット） |
| 3 | `/web/drawing/similar_search` | `03_similar_search.png` | 類似検索（2D/3D・重みづけ） |
| 4 | `/web/drawing` | `04_drawings.png` | 図面一覧（実データ取込済） |
| 5 | `/web/product` | `05_products.png` | 製品・装置・ユニット一覧 |
| 6 | `/web/system_setting` | `06_workflow.png` | ワークフロー設定（承認ルート） |
| 7 | `/web/system_setting` (タブ切替) | `07_crawl.png` | クロール設定 |

追加で `/web/project`（プロジェクト一覧）、`/web/integrated_search`（統合検索）も `pages` 配列に追記すれば取得可能。

## カスタマイズポイント（grab_screenshots.js）
- `pages` 配列：取得対象 URL とファイル名
- `viewport`：ビューポートサイズ（既定 1440×900）
- `await page.screenshot({ fullPage: true })`：フルページ取得に変更
- ログイン処理：ナレッジシステムの認証 UI が変わったら `onLogin` ブロックを調整

## 注意事項
- ナレッジシステム URL は社内 LAN 内限定の可能性。Cowork 側からアクセス不可な場合は VPN 等の事前接続が必要
- `.env` には実 ID/パスワードが入るため、Git 等にコミットしない
- 取得は当社所有の社内システム＋当社認証情報での実行のみを想定。外部システムへの転用は不可

## トラブルシューティング
- **「Login form detected」が出るのに認証エラー** → `.env` の KNOW_ID / KNOW_PW を再確認
- **タイムアウト** → ナレッジシステムが起動中の可能性。10〜20秒待って再実行
- **画像が真っ白** → `page.waitForTimeout(3000)` をもう少し長く（5000）に
- **Chromium インストールが進まない** → `npx playwright install chromium-headless-shell` を手動で実行

## このスキルのインストール手順
1. このフォルダ全体を `C:\Users\s-iwata\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\e2639113-2d24-4c09-9ba7-065761fc450a\07067200-c91d-4b75-826b-4a00d91079e4\skills\knowledge-system-screenshot\` にコピー
2. Cowork を再起動 or 新しい会話を開始
3. 「利用可能なスキル一覧」に `knowledge-system-screenshot` が現れることを確認
4. `.env.example` を `.env` にコピーして認証情報を記入

別フォルダ構成（plugin 配下）でも、SKILL.md の場所が認識されれば動作します。
