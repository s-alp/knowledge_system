# STEP Backend Replacement Guide

## 目的

STEP 変換は `ThreeDConversionBackend` 抽象に閉じ込めています。CadQuery/OCCT 以外の基盤へ置き換える場合は、この境界を維持したまま差し替えてください。

## 現在の差し替えポイント

- `backend/apps/viewer/services/converters.py`
  - `ThreeDConversionBackend`
  - `CadQueryOcctBackend`
- `backend/apps/viewer/services/runtime.py`
  - `get_conversion_backend`

## 差し替え手順

1. `ThreeDConversionBackend.convert(source_path, source_extension, output_artifact)` を満たす実装を追加する
2. `runtime.py` の `get_conversion_backend` が新しい実装を返すよう変更する
3. `requirements-step.txt` を新しい依存に合わせて更新する
4. 必要なら `VIEWER_STEP_STL_TOLERANCE` と `VIEWER_STEP_STL_ANGULAR_TOLERANCE` の扱いを新 backend に合わせて見直す
5. `docs/THIRD_PARTY_NOTICES.md` と `docs/licenses/` の内容を更新する
6. `backend/tests/test_api_3d.py` の STEP 成功ケースを実 backend でも再確認する

## 互換性要件

- 現在の既定出力は `stl`
- API 契約は変更しない
- 変換失敗時は `ConversionError` を送出し、`failed` 状態に更新する
- `modelFormat` は既存クライアントが解釈できる値だけを返す
