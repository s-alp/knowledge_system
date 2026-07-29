// このファイルは、C# RunnerとDjango間で受け渡すCLI入力・抽出JSON・警告の公開契約を定義する。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace IcadExtraction.Contracts
{
    /// <summary>
    /// CLIで指定されたコマンド名と、--名前 値形式のオプションを保持します。
    /// </summary>
    public sealed class CliCommand
    {
        public string CommandName { get; set; } = string.Empty;
        public Dictionary<string, string> Options { get; set; } = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
    }

    /// <summary>

    /// 文字列配列のCLI引数を、Runner内部で扱うCliCommandへ変換します。

    /// </summary>

    public static class CliArgumentsParser
    {
        public static CliCommand Parse(string[] args)
        {
            if (args.Length == 0)
            {
                throw new ArgumentException("command is required");
            }

            var command = new CliCommand { CommandName = args[0] };
            for (var index = 1; index < args.Length; index += 2)
            {
                var key = args[index];
                if (!key.StartsWith("--", StringComparison.Ordinal))
                {
                    throw new ArgumentException("option must start with --");
                }

                if (index + 1 >= args.Length)
                {
                    throw new ArgumentException($"value is missing for {key}");
                }

                command.Options[key.Substring(2)] = args[index + 1];
            }

            return command;
        }
    }

    /// <summary>

    /// 処理を中断しない不足や制約を、機械判定用コードと説明文で返します。

    /// </summary>

    public sealed class WarningPayload
    {
        public string Code { get; set; } = string.Empty;
        public string Message { get; set; } = string.Empty;
    }

    /// <summary>

    /// ICADモデルの最上位パーツに設定された名称・コメント・付加情報を表します。

    /// </summary>

    public sealed class TopPartPayload
    {
        public string? Name { get; set; }
        public string? Comment { get; set; }
        public string? ExInfo { get; set; }
        public Dictionary<string, string> ExInfoFields { get; set; } = new Dictionary<string, string>();
    }

    /// <summary>

    /// 3Dパーツツリーの1ノードを、親子関係と外部参照状態を保って表します。

    /// </summary>

    public sealed class PartPayload
    {
        public string? NodeId { get; set; }
        public string? ParentNodeId { get; set; }
        public int Depth { get; set; }
        public int ChildCount { get; set; }
        public string EntityKind { get; set; } = string.Empty;
        public List<string> TreePath { get; set; } = new List<string>();
        public string? Name { get; set; }
        public string? Comment { get; set; }
        public string? ExInfo { get; set; }
        public Dictionary<string, string> ExInfoFields { get; set; } = new Dictionary<string, string>();
        public string? RefModelName { get; set; }
        public string? RefModelPath { get; set; }
        public bool IsExternal { get; set; }
        public bool IsMirror { get; set; }
        public bool IsReadOnly { get; set; }
        public bool IsUnloaded { get; set; }
        public List<MaterialPayload> Materials { get; set; } = new List<MaterialPayload>();
    }

    /// <summary>

    /// 3D抽出で得た未正規化データをまとめ、取得できた値だけを保持します。

    /// </summary>

    public sealed class RawExtract3DPayload
    {
        public ModelInfoPayload ModelInfo { get; set; } = new ModelInfoPayload();
        public TopPartPayload TopPart { get; set; } = new TopPartPayload();
        public List<PartPayload> Parts { get; set; } = new List<PartPayload>();
        public Dictionary<string, List<ViewerAssetPayload>> ViewerAssets { get; set; } = new Dictionary<string, List<ViewerAssetPayload>>();
        public Dictionary<string, object> ConditionDiagnostics { get; set; } = new Dictionary<string, object>();
        public string MassProbeStatus { get; set; } = "not_attempted";
        public MassPropertyPayload? MassProperties { get; set; }
        public string MaterialProbeStatus { get; set; } = "not_attempted";
        public List<MaterialPayload> Materials { get; set; } = new List<MaterialPayload>();
    }

    /// <summary>

    /// SXNETから取得した材質候補と、その候補が属するパーツを表します。

    /// </summary>

    public sealed class MaterialPayload
    {
        public string? MatId { get; set; }
        public string? Name { get; set; }
        public double? SpecificGravity { get; set; }
        public int ElementCount { get; set; }
        public Dictionary<string, string> RawFields { get; set; } = new Dictionary<string, string>();
    }

    /// <summary>

    /// ICADモデル全体の名称・コメント・付加情報などの基本情報を表します。

    /// </summary>

    public sealed class ModelInfoPayload
    {
        public string? Name { get; set; }
        public string? Comment { get; set; }
        public string? Path { get; set; }
        public bool IsReadOnly { get; set; }
        public int ViewSheetCount { get; set; }
        public int WorkPlaneCount { get; set; }
    }

    /// <summary>

    /// モデルまたはパーツの質量・重心・慣性モーメントを表します。

    /// </summary>

    public sealed class MassPropertyPayload
    {
        public int ElementCount { get; set; }
        public string UnitName { get; set; } = string.Empty;
        public int? UnitType { get; set; }
        public bool IsSi { get; set; }
        public double? Density { get; set; }
        public double? Area { get; set; }
        public double? Volume { get; set; }
        public double? Mass { get; set; }
        public double? Weight { get; set; }
        public double? Length { get; set; }
        public double? CenterOfGravityX { get; set; }
        public double? CenterOfGravityY { get; set; }
        public double? CenterOfGravityZ { get; set; }
        public Dictionary<string, double?> GlobalMoment { get; set; } = new Dictionary<string, double?>();
        public Dictionary<string, double?> GravityMoment { get; set; } = new Dictionary<string, double?>();
        public Dictionary<string, double?> MainMoment { get; set; } = new Dictionary<string, double?>();
        public Dictionary<string, string> RawFields { get; set; } = new Dictionary<string, string>();
    }

    /// <summary>

    /// 2D/3Dビューワーへ渡すプレビュー資産の場所・形式・生成状態を表します。

    /// </summary>

    public sealed class ViewerAssetPayload
    {
        public string Mode { get; set; } = string.Empty;
        public string Status { get; set; } = string.Empty;
        public string Source { get; set; } = string.Empty;
        public string? Filename { get; set; }
        public string? Extension { get; set; }
        public string? MimeType { get; set; }
        public string? ModelFormat { get; set; }
        public string? FilePath { get; set; }
        public string? Url { get; set; }
        public long? SizeBytes { get; set; }
        public string? Message { get; set; }
    }

    /// <summary>

    /// 2D図面上の文字要素を、表示内容・座標・ビュー・レイヤーとともに表します。

    /// </summary>

    public sealed class TextPayload
    {
        public List<string> TextLines { get; set; } = new List<string>();
        public int LineCount { get; set; }
        public string SourceType { get; set; } = "text";
        public string? ViewName { get; set; }
        public int? LayerNo { get; set; }
        public double? PositionX { get; set; }
        public double? PositionY { get; set; }
        public double? PositionZ { get; set; }
        public bool? InsidePrintArea { get; set; }
        public int? PrintFrameNo { get; set; }
        public string? JoinedText { get; set; }
    }

    /// <summary>

    /// 寸法値と上下公差、配置先ビュー・レイヤーなどの抽出結果を表します。

    /// </summary>

    public sealed class DimensionPayload
    {
        public string? ViewName { get; set; }
        public int? LayerNo { get; set; }
        public double? PositionX { get; set; }
        public double? PositionY { get; set; }
        public double? PositionZ { get; set; }
        public bool? InsidePrintArea { get; set; }
        public int? PrintFrameNo { get; set; }
        public string? Value1 { get; set; }
        public string? Value2 { get; set; }
        public string? FrontWord { get; set; }
        public string? BackWord { get; set; }
        public string? UpperTol { get; set; }
        public string? LowerTol { get; set; }
        public string? Mark2 { get; set; }
        public string? Mark3 { get; set; }
        public string? Summary { get; set; }
    }

    /// <summary>

    /// 溶接記号または溶接注記の候補を、取得元情報付きで表します。

    /// </summary>

    public sealed class WeldNotePayload
    {
        public string? ViewName { get; set; }
        public int? LayerNo { get; set; }
        public double? PositionX { get; set; }
        public double? PositionY { get; set; }
        public double? PositionZ { get; set; }
        public bool? InsidePrintArea { get; set; }
        public int? PrintFrameNo { get; set; }
        public string Text { get; set; } = string.Empty;
    }

    /// <summary>

    /// 部品番号などを示すバルーン要素と、その図面上の位置を表します。

    /// </summary>

    public sealed class BalloonPayload
    {
        public string? ViewName { get; set; }
        public int? LayerNo { get; set; }
        public double? PositionX { get; set; }
        public double? PositionY { get; set; }
        public double? PositionZ { get; set; }
        public bool? InsidePrintArea { get; set; }
        public int? PrintFrameNo { get; set; }
        public string? Text { get; set; }
    }

    /// <summary>

    /// 幾何公差などの公差要素を、種別・値・配置情報とともに表します。

    /// </summary>

    public sealed class TolerancePayload
    {
        public string? ViewName { get; set; }
        public int? LayerNo { get; set; }
        public double? PositionX { get; set; }
        public double? PositionY { get; set; }
        public double? PositionZ { get; set; }
        public bool? InsidePrintArea { get; set; }
        public int? PrintFrameNo { get; set; }
        public string Text { get; set; } = string.Empty;
    }

    /// <summary>

    /// 2D図面から参照される外部部品と、参照先の識別情報を表します。

    /// </summary>

    public sealed class Referenced2DPartPayload
    {
        public string EntityType { get; set; } = string.Empty;
        public string? ViewName { get; set; }
        public int? LayerNo { get; set; }
        public double? PositionX { get; set; }
        public double? PositionY { get; set; }
        public double? PositionZ { get; set; }
        public bool? InsidePrintArea { get; set; }
        public int? PrintFrameNo { get; set; }
        public string? Name { get; set; }
        public string? Comment { get; set; }
        public string? Part3DName { get; set; }
        public string? RefModelName { get; set; }
        public string? RefVsName { get; set; }
        public int? Kind { get; set; }
        public bool? IsEmpty { get; set; }
        public bool? IsMirror { get; set; }
        public double? Scale { get; set; }
        public double? Angle { get; set; }
        public string Summary { get; set; } = string.Empty;
    }

    /// <summary>

    /// 線・円・ハッチングなどの2D図形を共通形式で表します。

    /// </summary>

    public sealed class GeometryPrimitivePayload
    {
        public string? ViewName { get; set; }
        public int? LayerNo { get; set; }
        public string GeometryType { get; set; } = string.Empty;
        public double? PositionX { get; set; }
        public double? PositionY { get; set; }
        public double? PositionZ { get; set; }
        public double? EndX { get; set; }
        public double? EndY { get; set; }
        public double? EndZ { get; set; }
        public double? CenterX { get; set; }
        public double? CenterY { get; set; }
        public double? CenterZ { get; set; }
        public double? Radius { get; set; }
        public double? Radius1 { get; set; }
        public double? Radius2 { get; set; }
        public double? StartAngle { get; set; }
        public double? EndAngle { get; set; }
        public int? PointCount { get; set; }
        public int? MarkType { get; set; }
        public double? SideLength { get; set; }
        public int? Width { get; set; }
        public int? Color { get; set; }
        public bool? InsidePrintArea { get; set; }
        public int? PrintFrameNo { get; set; }
        public string Summary { get; set; } = string.Empty;
    }

    /// <summary>

    /// ICADの1ビューについて、名称・種類・配置番号・要素数を表します。

    /// </summary>

    public sealed class ViewSheetPayload
    {
        public string? Name { get; set; }
        public string? Comment { get; set; }
        public double? Scale { get; set; }
        public double? Angle { get; set; }
        public int Type { get; set; }
        public int ViewType { get; set; }
        public int GeometryCount { get; set; }
    }

    /// <summary>

    /// 印刷対象となる矩形範囲をICADモデル空間の座標で表します。

    /// </summary>

    public sealed class PrintFramePayload
    {
        public int No { get; set; }
        public string? Size { get; set; }
        public bool Vertical { get; set; }
        public List<double> Dinfo { get; set; } = new List<double>();
        public double? DrawingScale { get; set; }
        public double? RangeMinX { get; set; }
        public double? RangeMinY { get; set; }
        public double? RangeMaxX { get; set; }
        public double? RangeMaxY { get; set; }
    }

    /// <summary>

    /// 2Dレイヤーの番号・名称・表示状態・編集状態を表します。

    /// </summary>

    public sealed class LayerPayload
    {
        public int No { get; set; }
        public string? Name { get; set; }
        public bool IsDisplayed { get; set; }
        public bool IsSearchable { get; set; }
    }

    /// <summary>

    /// 2D抽出で得た要素・ビュー・レイヤー・印刷枠をまとめます。

    /// </summary>

    public sealed class RawExtract2DPayload
    {
        public ModelInfoPayload ModelInfo { get; set; } = new ModelInfoPayload();
        public Dictionary<string, object> ConditionDiagnostics { get; set; } = new Dictionary<string, object>();
        public Dictionary<string, List<ViewerAssetPayload>> ViewerAssets { get; set; } = new Dictionary<string, List<ViewerAssetPayload>>();
        public List<ViewSheetPayload> ViewSheets { get; set; } = new List<ViewSheetPayload>();
        public List<PrintFramePayload> PrintFrames { get; set; } = new List<PrintFramePayload>();
        public List<LayerPayload> Layers { get; set; } = new List<LayerPayload>();
        public List<TextPayload> Texts { get; set; } = new List<TextPayload>();
        public List<DimensionPayload> Dimensions { get; set; } = new List<DimensionPayload>();
        public List<GeometryPrimitivePayload> GeometryPrimitives { get; set; } = new List<GeometryPrimitivePayload>();
        public List<WeldNotePayload> WeldNotes { get; set; } = new List<WeldNotePayload>();
        public List<BalloonPayload> Balloons { get; set; } = new List<BalloonPayload>();
        public List<TolerancePayload> Tolerances { get; set; } = new List<TolerancePayload>();
        public List<Referenced2DPartPayload> ReferencedParts { get; set; } = new List<Referenced2DPartPayload>();
    }

    /// <summary>

    /// 抽出対象ファイルの表示名・元パス・サイズ・ハッシュを表します。

    /// </summary>

    public sealed class SourceFilePayload
    {
        public string FullPath { get; set; } = string.Empty;
        public string? DirectoryPath { get; set; }
        public string FileName { get; set; } = string.Empty;
        public string FileNameWithoutExtension { get; set; } = string.Empty;
        public string Extension { get; set; } = string.Empty;
        public string SxNetInputPath { get; set; } = string.Empty;
        public string SxNetInputStrategy { get; set; } = "original";
        public bool UsedSxNetAlternatePath { get; set; }
        public int OriginalPathLength { get; set; }
        public int SxNetInputPathLength { get; set; }
    }

    /// <summary>

    /// 1回の抽出結果として、抽出種別・rawデータ・警告・実行条件をまとめます。

    /// </summary>

    public sealed class ExtractionEnvelope
    {
        public string InputPath { get; set; } = string.Empty;
        public SourceFilePayload SourceFile { get; set; } = new SourceFilePayload();
        public string SourceFormat { get; set; } = "icad";
        public string SourceKind { get; set; } = string.Empty;
        public string ExtractionProfile { get; set; } = "default";
        public Dictionary<string, object> ExtractionOptions { get; set; } = new Dictionary<string, object>();
        public Dictionary<string, object> ConditionDiagnostics { get; set; } = new Dictionary<string, object>();
        public string ExtractorName { get; set; } = SchemaVersions.ExtractorName;
        public string ExtractorVersion { get; set; } = SchemaVersions.SchemaVersion;
        public long ElapsedMs { get; set; }
        public List<WarningPayload> Warnings { get; set; } = new List<WarningPayload>();
        public object RawExtract { get; set; } = new Dictionary<string, object>();
    }

    /// <summary>

    /// ビューワー資産の出力先と公開URLを組み立てる条件を表します。

    /// </summary>

    public sealed class PreviewAssetOptions
    {
        public bool Enabled { get; set; }
        public string? OutputDirectory { get; set; }
        public string? PublicBaseUrl { get; set; }
        public string? FileNamePrefix { get; set; }
    }

    /// <summary>

    /// 2D実体の有無を判断した根拠件数を表します。

    /// </summary>

    public sealed class DetectionEvidence2DPayload
    {
        public bool HasContainer { get; set; }
        public bool HasContent { get; set; }
        public int ViewSheetCount { get; set; }
        public int PrintFrameCount { get; set; }
        public int SegmentCount { get; set; }
        public int GeometryCount { get; set; }
    }

    /// <summary>

    /// 3D実体の有無を判断した根拠件数を表します。

    /// </summary>

    public sealed class DetectionEvidence3DPayload
    {
        public bool HasContent { get; set; }
        public string? TopPartName { get; set; }
        public int PartCount { get; set; }
    }

    /// <summary>

    /// 1ファイルに2D/3Dのどちらが存在するかと判定根拠を表します。

    /// </summary>

    public sealed class DetectionPayload
    {
        [JsonProperty("has_2d")]
        public bool Has2D { get; set; }

        [JsonProperty("has_2d_container")]
        public bool Has2DContainer { get; set; }

        [JsonProperty("has_3d")]
        public bool Has3D { get; set; }

        public DetectionEvidence2DPayload TwoD { get; set; } = new DetectionEvidence2DPayload();
        public DetectionEvidence3DPayload ThreeD { get; set; } = new DetectionEvidence3DPayload();
    }

    /// <summary>

    /// 2D/3D存在判定の結果と、判定中に発生した警告をまとめます。

    /// </summary>

    public sealed class DetectionEnvelope
    {
        public string InputPath { get; set; } = string.Empty;
        public SourceFilePayload SourceFile { get; set; } = new SourceFilePayload();
        public string SourceFormat { get; set; } = "icad";
        public string ExtractorName { get; set; } = SchemaVersions.ExtractorName;
        public string ExtractorVersion { get; set; } = SchemaVersions.SchemaVersion;
        public long ElapsedMs { get; set; }
        public List<WarningPayload> Warnings { get; set; } = new List<WarningPayload>();
        public DetectionPayload Detection { get; set; } = new DetectionPayload();
    }

    /// <summary>

    /// ICADに登録されたプロッター名・用紙・向きなどの印刷設定を表します。

    /// </summary>

    public sealed class PlotterPayload
    {
        public string? No { get; set; }
        public string? Name { get; set; }
        public bool IsDefault { get; set; }
    }

    /// <summary>

    /// 印刷API調査で取得できたプロッターと印刷枠をまとめます。

    /// </summary>

    public sealed class PrintProbePayload
    {
        public List<PrintFramePayload> PrintFrames { get; set; } = new List<PrintFramePayload>();
        public List<PlotterPayload> Plotters { get; set; } = new List<PlotterPayload>();
        public PlotterPayload? DefaultPlotter { get; set; }
        public string PrintExecutionStatus { get; set; } = "not_attempted";
        public string PrintExecutionMessage { get; set; } = "This probe reads print frames and plotter definitions only. It does not execute SxModel.print.";
    }

    /// <summary>

    /// 印刷設定調査の最上位結果と警告をまとめます。

    /// </summary>

    public sealed class PrintProbeEnvelope
    {
        public string InputPath { get; set; } = string.Empty;
        public SourceFilePayload SourceFile { get; set; } = new SourceFilePayload();
        public string SourceFormat { get; set; } = "icad";
        public string ExtractorName { get; set; } = SchemaVersions.ExtractorName;
        public string ExtractorVersion { get; set; } = SchemaVersions.SchemaVersion;
        public long ElapsedMs { get; set; }
        public List<WarningPayload> Warnings { get; set; } = new List<WarningPayload>();
        public PrintProbePayload PrintProbe { get; set; } = new PrintProbePayload();
    }
}
