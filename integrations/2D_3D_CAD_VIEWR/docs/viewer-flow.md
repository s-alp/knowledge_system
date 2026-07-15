# 2D/3D PDM Embedded Viewer データフロー

## コンセプト

この viewer は、PDM の図面詳細画面から受け取った `drawingId` を起点に、PDM API で図面メタ情報と 2D/3D ソースを解決し、既存ナレッジ画面に近い詳細 UI で軽量に閲覧することだけに責務を絞っています。業務ロジックそのものは持たず、表示に必要な取得・変換・保存・配信を担当します。

## 全体像

```mermaid
flowchart LR
    pdm["PDM 図面詳細画面\n/web/drawing/{drawingId}"] --> ui["Frontend UI\nReact / Vite"]
    ui --> bootstrap["GET /api/v1/drawings/{drawingId}/bootstrap"]
    bootstrap --> api["Django / DRF API"]
    api --> resolver["PdmDrawingResolver"]
    resolver --> pdmApi["PDM API\n図面メタ情報 + source URL 解決"]

    ui --> mockDetail["drawingKnowledge mock\n補助セクションを構成"]
    ui --> open2d["POST /api/v1/drawings/{drawingId}/viewer2d/open"]
    ui --> open3d["POST /api/v1/drawings/{drawingId}/viewer3d/open"]
    open2d --> api
    open3d --> api

    api --> fetch["source URL 取得 / 形式判定"]
    fetch --> storage["Storage\n元ファイルを一時保存"]

    storage --> session2d["Viewer2DSession"]
    storage --> job3d["Viewer3DJob"]

    session2d --> tiff["TIFFページ化"]
    tiff --> pageImage["GET /viewer2d/sessions/{id}/pages/{page}/image"]
    session2d --> source2d["GET /viewer2d/sessions/{id}/source"]
    source2d --> ui
    pageImage --> ui

    job3d --> stl["STLはそのままready"]
    job3d --> step["STEPは変換backendでSTLへ変換"]
    step --> model3d["GET /viewer3d/jobs/{id}/model"]
    stl --> model3d
    ui --> poll["GET /viewer3d/jobs/{id} を poll"]
    poll --> job3d
    model3d --> ui
    mockDetail --> ui
    ui --> sandbox["DrawingEntryPanel\n開発用入口 / ローカルファイル起動"]
```

## 役割分担

- PDM
  - `/web/drawing/{drawingId}` の画面導線を持つ
  - viewer には `drawingId` だけを渡す
- フロントエンド
  - drawingId の解析、bootstrap 読み込み、ナレッジ風詳細 UI の構成、2D/3D の描画を担当する
- バックエンド
  - PDM API 解決、形式判定、TIFF ページ化、STEP 変換、成果物配信を担当する
- Storage
  - 取得元ファイルと変換済みファイルを一時保存する
- Conversion Backend
  - STEP を表示用 STL へ変換する

## 2D 詳細図

```mermaid
flowchart TD
    pdm["PDM 図面詳細 URL"] --> app["App"]
    app --> route["drawingId を pathname から抽出"]
    route --> bootstrap["useDrawingBootstrap"]
    bootstrap --> apiBootstrap["GET /api/v1/drawings/{drawingId}/bootstrap"]
    apiBootstrap --> resolve2d["PdmDrawingResolver"]

    bootstrap --> mock2d["buildDrawingKnowledgeMock"]
    mock2d --> overview2d["DrawingOverviewPanel"]
    mock2d --> supplement2d["DrawingSupplementPanels"]
    entry2d["DrawingEntryPanel"] --> page2d

    app --> page2d["Viewer2DPage"]
    page2d --> apiOpen2d["POST /api/v1/drawings/{drawingId}/viewer2d/open"]
    apiOpen2d --> view2d["DrawingViewer2DOpenView"]
    view2d --> service2d["viewer2d service"]
    service2d --> fetch2d["resolved 2D URL 取得"]
    fetch2d --> detect2d["filetypes で形式判定"]
    detect2d --> store2d["artifact storage に保存"]
    store2d --> session2d["Viewer2DSession 作成"]

    session2d --> sourceResp["sourceUrl を返す"]
    session2d --> tiffCheck["TIFFか判定"]
    tiffCheck -->|TIFF| tiffPage["pageCount / pageImageUrls を返す"]
    tiffCheck -->|PDF/JPEG| sourceResp

    sourceResp --> docHook["useViewer2DDocument"]
    tiffPage --> docHook
    docHook --> adapter2d["pdf / raster / tiff adapter"]
    adapter2d --> preview2d["Viewer2DPreviewPane"]
    preview2d --> viewport2d["Viewer2DPreviewPane が viewport state を保持"]
    viewport2d --> canvas2d["TwoDViewerCanvas"]
    viewport2d --> toolbar2d["Viewer2DToolbar / MetadataBar / IconToolbarButton"]
    canvas2d --> rerender2d["操作後に PDF を高解像度再描画"]
    page2d --> overview2d
    app --> supplement2d

    canvas2d -->|TIFFページ要求| pageApi["GET /viewer2d/sessions/{id}/pages/{page}/image"]
    pageApi --> pageView["Viewer2DPageImageView"]
    pageView --> tiffRender["render_tiff_page_png"]
    tiffRender --> canvas2d
```

## 2D の流れ

1. PDM 画面上で viewer が `/drawing/{drawingId}` として開く
2. フロントエンドが `drawingId` を解析し、`GET /api/v1/drawings/{drawingId}/bootstrap` を呼ぶ
3. バックエンドが PDM API を呼んで図面メタ情報と 2D availability を解決する
4. フロントエンドが bootstrap から基本情報を描き、不足する補助セクションは mock detail で構成する
5. 開発画面では `DrawingEntryPanel` からローカルファイルを選び、拡張子で 2D/3D を自動判定して詳細画面へ入る
6. フロントエンドが `POST /api/v1/drawings/{drawingId}/viewer2d/open` または `POST /api/v1/viewer2d/upload` を呼ぶ
7. バックエンドが 2D ソースまたは upload ファイルを形式判定し、`Viewer2DSession` を作成する
8. TIFF の場合はページ数を取得し、各ページ画像 URL を返す
9. フロントエンドは `Viewer2DPreviewPane` で viewport state を持ち、toolbar と canvas の双方からズーム・回転・リセットを制御する
10. `TwoDViewerCanvas` は pointer 入力を使ってパンを処理し、ホイールズームではカーソル位置をアンカーにして offset を補正する
11. `sourceUrl` を読み込み、形式ごとの adapter で描画を開始する
12. PDF は表示幅ベースの描画に加え、操作終了後に高解像度描画へ差し替える

## 3D 詳細図

```mermaid
flowchart TD
    pdm["PDM 図面詳細 URL"] --> app["App"]
    app --> route["drawingId を pathname から抽出"]
    route --> bootstrap["useDrawingBootstrap"]
    bootstrap --> apiBootstrap["GET /api/v1/drawings/{drawingId}/bootstrap"]
    apiBootstrap --> resolve3d["PdmDrawingResolver"]

    bootstrap --> mock3d["buildDrawingKnowledgeMock"]
    mock3d --> overview3d["DrawingOverviewPanel"]
    mock3d --> supplement3d["DrawingSupplementPanels"]
    entry3d["DrawingEntryPanel"] --> page3d

    app --> page3d["Viewer3DPage"]
    page3d --> apiOpen3d["POST /api/v1/drawings/{drawingId}/viewer3d/open"]
    apiOpen3d --> view3d["DrawingViewer3DOpenView"]
    view3d --> service3d["viewer3d service"]
    service3d --> fetch3d["resolved 3D URL 取得"]
    fetch3d --> detect3d["filetypes で形式判定"]
    detect3d --> store3d["artifact storage に保存"]
    store3d --> job3d["Viewer3DJob 作成"]

    job3d --> stlCheck["STLかSTEPか判定"]
    stlCheck -->|STL| ready3d["ready で応答"]
    stlCheck -->|STEP| convert3d["conversion backend で STL へ変換"]
    convert3d --> modelStore["変換後 STL を保存"]
    modelStore --> ready3d

    ready3d --> pollHook["useViewer3DJob"]
    page3d --> pollHook
    pollHook -->|poll| jobApi["GET /api/v1/viewer3d/jobs/{id}"]
    jobApi --> jobView["Viewer3DJobView"]
    jobView --> pollHook

    pollHook -->|ready後に取得| modelApi["GET /api/v1/viewer3d/jobs/{id}/model"]
    modelApi --> modelView["Viewer3DModelView"]
    modelView --> scene3d["ThreeDViewerScene"]
    page3d --> toolbar3d["Viewer3DToolbar / MetadataBar / IconToolbarButton"]
    toolbar3d --> scene3d
    page3d --> overview3d
    app --> supplement3d
```

## 3D の流れ

1. フロントエンドが bootstrap で 3D availability を確認する
2. フロントエンドが bootstrap から基本情報を描き、不足する補助セクションは mock detail で構成する
3. 開発画面では `DrawingEntryPanel` からローカルファイルを選び、拡張子で 2D/3D を自動判定して詳細画面へ入る
4. 3D タブを開いたタイミングで `POST /api/v1/drawings/{drawingId}/viewer3d/open` または `POST /api/v1/viewer3d/upload` を呼ぶ
5. バックエンドが解決済み 3D URL または upload ファイルを形式判定し、`Viewer3DJob` を作成する
6. STL はそのまま ready にし、STEP は conversion backend で STL に変換する
7. フロントエンドは `GET /api/v1/viewer3d/jobs/{id}` を poll して job 状態を追う
8. ready になったら `GET /api/v1/viewer3d/jobs/{id}/model` のモデルを `ThreeDViewerScene` へ渡して描画する
9. 3D のズーム・リセット・断面操作はプレビュー右上の `Viewer3DToolbar` から Scene へ伝播する

## 画面と API の対応

- 画面入口: `frontend/src/App.tsx`
- 開発用入口: `frontend/src/shared/components/DrawingEntryPanel.tsx`
- drawingId 解析: `frontend/src/shared/drawingRoute.ts`
- bootstrap 読み込み: `frontend/src/shared/hooks/useDrawingBootstrap.ts`
- mock detail 構成: `frontend/src/shared/mock/drawingKnowledge.ts`
- 基本情報カード: `frontend/src/shared/components/DrawingOverviewPanel.tsx`
- 補助セクション: `frontend/src/shared/components/DrawingSupplementPanels.tsx`
- 操作アイコン: `frontend/src/shared/components/IconToolbarButton.tsx`
- 2D 画面: `frontend/src/features/viewer2d/pages/Viewer2DPage.tsx`
- 3D 画面: `frontend/src/features/viewer3d/pages/Viewer3DPage.tsx`
- drawing 解決: `backend/apps/viewer/services/pdm.py`
- drawing API 入口: `backend/apps/viewer/api/views.py`

## なぜこの分離か

- PDM 側の変更を `drawingId を渡す` だけに抑えるため
- PDM API 解決の責務を backend へ閉じ込め、frontend を描画に集中させるため
- 既存ナレッジ画面に近い見た目を、実データと mock detail を分けて保守しやすくするため
- TIFF と STEP の特殊処理を viewer ごとの service / adapter に閉じ込め、公開 API を薄く保つため
- API と画面の責務境界を人力で追いやすくするため
