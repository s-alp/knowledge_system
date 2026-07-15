# 2D/3D PDM Embedded Viewer 仕様書

## 目的

この文書は、PDM の図面詳細画面へ埋め込む viewer の対応範囲、公開 API、状態遷移、制約をまとめた仕様書です。

## 入口仕様

- viewer の標準入口は `/drawing/{drawingId}`
- `drawingId` は PDM 側の図面内部識別子 UUID を指す
- frontend は `window.location.pathname` から `drawingId` を解析する
- 開発時のみ `?drawingId=` のフォールバックを許可する
- Vite 開発モードでは URL 入力 / ローカルファイル upload UI を既定で表示する
- 開発画面では `DrawingEntryPanel` から `drawingId / URL` 入力とローカルファイル起動の両方を提供する

## 対応形式

### 2D

- `PDF`
- `JPEG`
- `TIFF`

### 3D

- `STL`
- `STEP`
- `STP`

## 表示仕様

### bootstrap

- `GET /api/v1/drawings/{drawingId}/bootstrap` で図面メタ情報と availability を返す
- bootstrap は重い 3D 変換を行わない
- frontend は bootstrap の `defaultMode` と `availability` を使って初期表示タブを決める
- frontend は bootstrap の基本情報を詳細画面へ表示し、`metadata.tagAttributes` がある場合は図面/プロジェクト/製品・装置・ユニット/部品別のタグ・属性候補を補助パネルへ表示する
- 改訂履歴・関連情報・変更履歴・属性情報・備考の補助セクションは mock detail で補完する
- 補助セクションの mock detail は見た目合わせ用であり、実データ連携の対象外とする

### 2D

- `POST /api/v1/drawings/{drawingId}/viewer2d/open` で 2D セッションを開く
- `PDF` と `JPEG` は単一ソースとして扱う
- `TIFF` はバックエンドでページ数を取得し、ページごとの PNG 画像として返す
- フロントエンドは `pageCount` と `pageImageUrls` を使ってページ移動を行う
- 2D 画面はナレッジ風の基本情報カード、属性情報、備考、プレビュー領域で構成する
- 2D プレビュー上部には `戻る / 進む / 拡大 / 縮小 / リセット / 左回転 / 右回転 / 枠線クリア` を並べる
- 2D の viewport state は `Viewer2DPreviewPane` が持ち、toolbar と canvas が共有する
- パン入力は pointer capture を使い、ドラッグ中に表示面が切り替わっても操作を継続できる
- ホイールズームはカーソル位置をアンカーにして `offsetX / offsetY` を補正し、ズーム時の意図しない表示ずれを抑える
- PDF は表示幅ベースで描画し、操作終了後に高解像度描画へ差し替える

### 3D

- `POST /api/v1/drawings/{drawingId}/viewer3d/open` で 3D ジョブを開く
- `STL` はそのまま表示する
- `STEP / STP` は既定で `STL` に変換して表示する
- 断面キャップは閉じた STL メッシュに対してのみ有効
- 輪郭強調は切り替え式で、断面 ON 中は自動 OFF に寄せる
- 3D 画面も 2D と同じ基本情報カードを使い、プレビュー領域だけを 3D 向けに切り替える
- 3D プレビュー右上には `拡大 / 縮小 / リセット / 断面オン/オフ / 輪郭強調 ON/OFF` を並べる
- 3D の左右回転ボタンは提供しない
- `☆` は配置のみを持つ装飾で、状態保存や API 更新は行わない

## 公開 API

### 埋込向け API

- `GET /api/v1/drawings/{drawingId}/bootstrap`
  - PDM API から図面メタ情報と 2D/3D availability を解決する
- `POST /api/v1/drawings/{drawingId}/viewer2d/open`
  - drawingId から 2D ソースを解決し、2D セッションを開く
- `POST /api/v1/drawings/{drawingId}/viewer3d/open`
  - drawingId から 3D ソースを解決し、3D ジョブを作成する

### PDM API 解決契約

- viewer backend は `PDM_DRAWING_RESOLVE_PATH_TEMPLATE` で指定された PDM API を呼ぶ
- PDM API の返却形は、少なくとも次のどちらかを満たす必要がある
  - `source_2d_url` と `source_3d_url` を返す
  - `drawing_file_versions` 相当の配列で `file_name` と `file_path` を返す
- `drawing_file_versions` 方式では、viewer backend が `file_name` の拡張子から 2D / 3D の候補を判定する
- `file_path` は viewer backend から取得可能な URL である必要がある
- `drawing_name`、`drawing_no`、`drawing_type`、`drawing_status`、`paper_size`、`intention`、`owner`、`tags` は bootstrap 表示用メタ情報として利用する
- `tagAttributes` は本番登録ではなく、viewer 右側の補助パネル表示用 payload として利用する

### セッション / ジョブ API

- `GET /api/v1/viewer2d/sessions/{id}/source`
  - 元ファイルを返す
- `GET /api/v1/viewer2d/sessions/{id}/pages/{page}/image`
  - TIFF のページ画像を PNG で返す
- `GET /api/v1/viewer3d/jobs/{id}`
  - ジョブ状態を返す
- `GET /api/v1/viewer3d/jobs/{id}/model`
  - 表示用モデルを返す

### 開発・検証用 API

- `POST /api/v1/viewer2d/open`
- `POST /api/v1/viewer2d/upload`
- `POST /api/v1/viewer3d/open`
- `POST /api/v1/viewer3d/upload`
- これらは開発・検証用導線で使い、PDM 埋込の本番導線では使わない
- 開発画面のローカルファイル導線では、拡張子から 2D/3D を自動判定して上記 upload API へ送る

### ICADタグ・属性統合 API

統合先 `knowledge_system/backend` が次のAPIを提供する。いずれもローカル抽出・レビュー用であり、創屋本番DBへ書き込まない。

| API | 用途 |
| --- | --- |
| `POST /drawing-metadata/registrations/upload` | ICADファイルをローカル登録 |
| `POST /drawing-metadata/registrations/{drawingId}/extract` | 2D/3D抽出を起票 |
| `GET /drawing-metadata/jobs/{jobId}` | 待機中/抽出中/完了/失敗を確認 |
| `PATCH /drawing-metadata/registrations/{drawingId}/overrides` | 候補を手直し |
| `PATCH /drawing-metadata/registrations/{drawingId}/review` | 候補を確認済みまたは要手直しにする |
| `GET /knowledge-entities?target=product|part` | 対象物一覧を取得 |
| `GET /knowledge-entities/{entityId}` | 対象物詳細・親子関係・根拠を取得 |
| `GET /drawing-metadata/settings/tag-automation` | 秘密値を除いた現在設定を取得 |

3D対象物の分類は構成階層で行う。子ノードありは製品・装置・ユニット、子ノードなしは部品とし、ファイル名だけでは分類しない。

## レスポンス項目

### bootstrap

```ts
type DrawingBootstrapResponse = {
  drawingId: string;
  title: string;
  version?: string | null;
  defaultMode: "2d" | "3d";
  availability: { has2d: boolean; has3d: boolean };
  metadata: {
    drawingNumber?: string | null;
    drawingName?: string | null;
    drawingType?: string | null;
    paperSize?: string | null;
    status?: string | null;
    owner?: string | null;
    designPurpose?: string | null;
    tags?: string[];
    tagAttributes?: {
      schemaVersion?: string | null;
      sourceSchemaVersion?: string | null;
      displayPolicy?: string | null;
      targetCount?: number;
      reviewRequired?: boolean;
      targets?: Array<{
        targetKey?: string | null;
        label?: string | null;
        existingReception?: string | null;
        tagApiStatus?: string | null;
        writePolicy?: string | null;
        tags?: string[];
        attributes?: Array<{
          name?: string | null;
          value?: string | null;
          sourcePath?: string | null;
          entityHint?: string | null;
          bindingStatus?: string | null;
        }>;
        reviewRequired?: boolean;
        notes?: string[];
      }>;
    };
    extractionDiagnostics?: {
      schemaVersion?: string | null;
      status?: string | null;
      missingModes?: string[];
      policy?: string | null;
    };
  };
};
```

### 2D セッション

- `sessionId`
- `filename`
- `extension`
- `mimeType`
- `sourceUrl`
- `pageCount`
- `pageImageUrls`

### 3D ジョブ

- `jobId`
- `filename`
- `sourceExtension`
- `modelFormat`
- `status`
- `modelUrl`
- `error`

## 状態遷移

### フロントエンド表示状態

- `idle`
- `file_selected`
- `uploading`
- `processing`
- `rendering`
- `ready`
- `failed`

### 3D ジョブ状態

- `queued`
- `processing`
- `ready`
- `failed`

`ready` はバックエンド完了だけでなく、フロントエンドの初回描画完了も考慮して切り替えます。

## 環境変数

### バックエンド

- `VIEWER_TIMEOUT_SECONDS`
- `VIEWER_MAX_DOWNLOAD_BYTES`
- `VIEWER_ARTIFACT_TTL_SECONDS`
- `VIEWER_ALLOWED_SCHEMES`
- `VIEWER_STEP_ENABLED`
- `VIEWER_STORAGE_ROOT`
- `VIEWER_STEP_STL_TOLERANCE`
- `VIEWER_STEP_STL_ANGULAR_TOLERANCE`
- `VIEWER_LOCAL_FILE_ENABLED`
- `PDM_API_BASE_URL`
- `PDM_DRAWING_RESOLVE_PATH_TEMPLATE`
- `PDM_REQUEST_TIMEOUT_SECONDS`

### フロントエンド

- `VITE_API_BASE_URL`
- `VITE_LOCAL_FILE_ENABLED`
- 開発用 `docker-compose.dev.yml` では frontend から backend へ `http://localhost:8000/api/v1` を直接使う構成を許容する

## 制約

- PDM 側は `drawingId` を渡すだけで、複雑な viewer 専用処理を持たない前提
- backend は受信した Cookie / Authorization を PDM API へ引き継ぎ、自分ではログイン状態を保持しない
- TIFF はブラウザで直接デコードしない
- STEP は既定で STL に変換するため、ソリッド情報を保ったままの表示はしない
- 断面キャップは閉じた STL メッシュのみ対象
- ローカルファイル機能は開発・検証用で、開発モードでは既定 ON、本番ビルドでは既定 OFF
- ライセンス導線として UI のライセンス開示導線を削除しない
- 改訂履歴、関連情報、変更履歴、属性情報、備考は現時点では frontend の mock detail で表現しており、PDM API の正式契約が固まり次第差し替える前提
- 納品時点では補助セクションをモック表示のままとし、viewer の必須実装範囲には含めない
- `枠線クリア` は現時点では見た目のみの表示で、実機能は持たない

## 非対応事項

- 複数断面
- 編集系 CAD 操作
- DXF など追加形式
- STEP の別形式出力を前提にしたクライアント
