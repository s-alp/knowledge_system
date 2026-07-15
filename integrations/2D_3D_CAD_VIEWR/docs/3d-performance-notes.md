# 3D パフォーマンスメモ

## 方針

- 用途は編集ではなく閲覧
- 既定は見た目より速度優先
- 断面キャップは維持し、軽量化は他の要素で吸収する

## 現在の既定軽量化

- STEP は `STEP -> STL` へ変換して表示する
- STEP の STL 出力は `VIEWER_STEP_STL_TOLERANCE` と `VIEWER_STEP_STL_ANGULAR_TOLERANCE` を使う
- 輪郭強調は既定 OFF
- 断面 ON 中は輪郭強調を自動 OFF に寄せる
- 補助描画は必要最小限にとどめる

## 完了判定

- 2D は初回 draw 完了で `ready`
- 3D は backend job `ready` 後、scene 初回描画完了で `ready`
- 表示済みなのにローディングバーが残る状態は不具合として扱う

## ボトルネック

- 重い STEP の変換時間
- STL の初回ダウンロードサイズ
- 輪郭強調や補助描画の生成コスト
- 断面 ON 時の stencil/cap 描画コスト
