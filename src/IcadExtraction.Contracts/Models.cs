using System;
using System.Collections.Generic;

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
    }

    public sealed class PartPayload
    {
        public List<string> TreePath { get; set; } = new List<string>();
        public string? Name { get; set; }
        public string? Comment { get; set; }
        public string? RefModelName { get; set; }
        public string? RefModelPath { get; set; }
        public bool IsExternal { get; set; }
        public bool IsMirror { get; set; }
        public bool IsReadOnly { get; set; }
        public bool IsUnloaded { get; set; }
    }

    public sealed class RawExtract3DPayload
    {
        public TopPartPayload TopPart { get; set; } = new TopPartPayload();
        public List<PartPayload> Parts { get; set; } = new List<PartPayload>();
    }

    public sealed class TextPayload
    {
        public List<string> TextLines { get; set; } = new List<string>();
        public int LineCount { get; set; }
        public string SourceType { get; set; } = "text";
        public string? JoinedText { get; set; }
    }

    public sealed class DimensionPayload
    {
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
        public string Text { get; set; } = string.Empty;
    }

    public sealed class BalloonPayload
    {
        public string? Text { get; set; }
    }

    public sealed class TolerancePayload
    {
        public string Text { get; set; } = string.Empty;
    }

    public sealed class GeometryPrimitivePayload
    {
        public string GeometryType { get; set; } = string.Empty;
        public string Summary { get; set; } = string.Empty;
    }

    public sealed class RawExtract2DPayload
    {
        public List<TextPayload> Texts { get; set; } = new List<TextPayload>();
        public List<DimensionPayload> Dimensions { get; set; } = new List<DimensionPayload>();
        public List<GeometryPrimitivePayload> GeometryPrimitives { get; set; } = new List<GeometryPrimitivePayload>();
        public List<WeldNotePayload> WeldNotes { get; set; } = new List<WeldNotePayload>();
        public List<BalloonPayload> Balloons { get; set; } = new List<BalloonPayload>();
        public List<TolerancePayload> Tolerances { get; set; } = new List<TolerancePayload>();
    }

    public sealed class ExtractionEnvelope
    {
        public string InputPath { get; set; } = string.Empty;
        public string SourceFormat { get; set; } = "icad";
        public string SourceKind { get; set; } = string.Empty;
        public string ExtractorName { get; set; } = SchemaVersions.ExtractorName;
        public string ExtractorVersion { get; set; } = SchemaVersions.SchemaVersion;
        public long ElapsedMs { get; set; }
        public List<WarningPayload> Warnings { get; set; } = new List<WarningPayload>();
        public object RawExtract { get; set; } = new Dictionary<string, object>();
    }
}
