using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace IcadExtraction.Contracts
{
    public sealed class CliCommand
    {
        public string CommandName { get; set; } = string.Empty;
        public Dictionary<string, string> Options { get; set; } = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
    }

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

    public sealed class WarningPayload
    {
        public string Code { get; set; } = string.Empty;
        public string Message { get; set; } = string.Empty;
    }

    public sealed class TopPartPayload
    {
        public string? Name { get; set; }
        public string? Comment { get; set; }
        public string? ExInfo { get; set; }
        public Dictionary<string, string> ExInfoFields { get; set; } = new Dictionary<string, string>();
    }

    public sealed class PartPayload
    {
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

    public sealed class RawExtract3DPayload
    {
        public TopPartPayload TopPart { get; set; } = new TopPartPayload();
        public List<PartPayload> Parts { get; set; } = new List<PartPayload>();
        public string MassProbeStatus { get; set; } = "not_attempted";
        public MassPropertyPayload? MassProperties { get; set; }
        public string MaterialProbeStatus { get; set; } = "not_attempted";
        public List<MaterialPayload> Materials { get; set; } = new List<MaterialPayload>();
    }

    public sealed class MaterialPayload
    {
        public string? MatId { get; set; }
        public string? Name { get; set; }
        public double? SpecificGravity { get; set; }
        public int ElementCount { get; set; }
        public Dictionary<string, string> RawFields { get; set; } = new Dictionary<string, string>();
    }

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
        public Dictionary<string, string> RawFields { get; set; } = new Dictionary<string, string>();
    }

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
        public string? JoinedText { get; set; }
    }

    public sealed class DimensionPayload
    {
        public string? ViewName { get; set; }
        public int? LayerNo { get; set; }
        public double? PositionX { get; set; }
        public double? PositionY { get; set; }
        public double? PositionZ { get; set; }
        public bool? InsidePrintArea { get; set; }
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

    public sealed class WeldNotePayload
    {
        public string? ViewName { get; set; }
        public int? LayerNo { get; set; }
        public double? PositionX { get; set; }
        public double? PositionY { get; set; }
        public double? PositionZ { get; set; }
        public bool? InsidePrintArea { get; set; }
        public string Text { get; set; } = string.Empty;
    }

    public sealed class BalloonPayload
    {
        public string? ViewName { get; set; }
        public int? LayerNo { get; set; }
        public double? PositionX { get; set; }
        public double? PositionY { get; set; }
        public double? PositionZ { get; set; }
        public bool? InsidePrintArea { get; set; }
        public string? Text { get; set; }
    }

    public sealed class TolerancePayload
    {
        public string? ViewName { get; set; }
        public int? LayerNo { get; set; }
        public double? PositionX { get; set; }
        public double? PositionY { get; set; }
        public double? PositionZ { get; set; }
        public bool? InsidePrintArea { get; set; }
        public string Text { get; set; } = string.Empty;
    }

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
        public bool? InsidePrintArea { get; set; }
        public string Summary { get; set; } = string.Empty;
    }

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

    public sealed class LayerPayload
    {
        public int No { get; set; }
        public string? Name { get; set; }
        public bool IsDisplayed { get; set; }
        public bool IsSearchable { get; set; }
    }

    public sealed class RawExtract2DPayload
    {
        public List<ViewSheetPayload> ViewSheets { get; set; } = new List<ViewSheetPayload>();
        public List<PrintFramePayload> PrintFrames { get; set; } = new List<PrintFramePayload>();
        public List<LayerPayload> Layers { get; set; } = new List<LayerPayload>();
        public List<TextPayload> Texts { get; set; } = new List<TextPayload>();
        public List<DimensionPayload> Dimensions { get; set; } = new List<DimensionPayload>();
        public List<GeometryPrimitivePayload> GeometryPrimitives { get; set; } = new List<GeometryPrimitivePayload>();
        public List<WeldNotePayload> WeldNotes { get; set; } = new List<WeldNotePayload>();
        public List<BalloonPayload> Balloons { get; set; } = new List<BalloonPayload>();
        public List<TolerancePayload> Tolerances { get; set; } = new List<TolerancePayload>();
    }

    public sealed class SourceFilePayload
    {
        public string FullPath { get; set; } = string.Empty;
        public string? DirectoryPath { get; set; }
        public string FileName { get; set; } = string.Empty;
        public string FileNameWithoutExtension { get; set; } = string.Empty;
        public string Extension { get; set; } = string.Empty;
    }

    public sealed class ExtractionEnvelope
    {
        public string InputPath { get; set; } = string.Empty;
        public SourceFilePayload SourceFile { get; set; } = new SourceFilePayload();
        public string SourceFormat { get; set; } = "icad";
        public string SourceKind { get; set; } = string.Empty;
        public string ExtractorName { get; set; } = SchemaVersions.ExtractorName;
        public string ExtractorVersion { get; set; } = SchemaVersions.SchemaVersion;
        public long ElapsedMs { get; set; }
        public List<WarningPayload> Warnings { get; set; } = new List<WarningPayload>();
        public object RawExtract { get; set; } = new Dictionary<string, object>();
    }

    public sealed class DetectionEvidence2DPayload
    {
        public bool HasContainer { get; set; }
        public bool HasContent { get; set; }
        public int ViewSheetCount { get; set; }
        public int PrintFrameCount { get; set; }
        public int SegmentCount { get; set; }
        public int GeometryCount { get; set; }
    }

    public sealed class DetectionEvidence3DPayload
    {
        public bool HasContent { get; set; }
        public string? TopPartName { get; set; }
        public int PartCount { get; set; }
    }

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
}
