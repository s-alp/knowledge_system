// このファイルは、ICADモデルをDXFまたはSTEPへ変換し、変換結果と警告を共通形式で返す。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    /// <summary>
    /// ICADモデルをDXFまたはSTEPへ変換し、変換結果と警告を共通形式で返す。
    /// </summary>
    public sealed class IcadCadFormatExporter
    {
        public ViewerAssetPayload Export(
            SxNetOpenContext context,
            string inputPath,
            string outputDirectory,
            string outputFormat,
            string? outputBaseName,
            int? exportFileType
        )
        {
            var format = ResolveFormat(outputFormat);
            var fullOutputDirectory = Path.GetFullPath(outputDirectory);
            Directory.CreateDirectory(fullOutputDirectory);

            var baseName = SanitizeFileName(string.IsNullOrWhiteSpace(outputBaseName)
                ? Path.GetFileNameWithoutExtension(inputPath)
                : outputBaseName!);
            var filename = baseName + "." + format.Extension;
            var targetPath = Path.Combine(fullOutputDirectory, filename);
            var startedAtUtc = DateTime.UtcNow.AddSeconds(-2);
            if (File.Exists(targetPath))
            {
                File.Delete(targetPath);
            }

            var fileType = exportFileType ?? ResolveSxOptExportInt(context.Assembly, format);
            context.ExportModel(fullOutputDirectory, baseName, fileType);
            var exportedPath = ResolveExportedPath(fullOutputDirectory, filename, format.ExportedExtensions, startedAtUtc);
            if (exportedPath == null)
            {
                throw new InvalidOperationException(
                    $"SxModel.export did not create a {string.Join("/", format.ExportedExtensions.Select(item => "." + item))} file in the output directory."
                );
            }

            var info = new FileInfo(exportedPath);
            var actualExtension = info.Extension.TrimStart('.').ToLowerInvariant();
            if (string.IsNullOrWhiteSpace(actualExtension))
            {
                actualExtension = format.Extension;
            }
            return new ViewerAssetPayload
            {
                Mode = format.Mode,
                Status = "ready",
                Source = "sxnet_export",
                Filename = info.Name,
                Extension = actualExtension,
                MimeType = format.MimeType,
                ModelFormat = format.ModelFormat,
                FilePath = info.FullName,
                SizeBytes = info.Length,
            };
        }

        public static CadExportFormat ResolveFormat(string outputFormat)
        {
            var normalized = (outputFormat ?? string.Empty).Trim().TrimStart('.').ToLowerInvariant();
            if (normalized == "stp")
            {
                normalized = "step";
            }

            if (normalized == "step")
            {
                return new CadExportFormat
                {
                    OutputFormat = "step",
                    Extension = "step",
                    ExportedExtensions = new[] { "step", "stp" },
                    Mode = "3d",
                    MimeType = "model/step",
                    ModelFormat = "step",
                    CandidateSxOptExportFields = new[] { "FILE_TYPE_STEP", "FILE_TYPE_STP" },
                };
            }

            if (normalized == "dxf")
            {
                return new CadExportFormat
                {
                    OutputFormat = "dxf",
                    Extension = "dxf",
                    ExportedExtensions = new[] { "dxf" },
                    Mode = "2d",
                    MimeType = "application/dxf",
                    ModelFormat = "dxf",
                    CandidateSxOptExportFields = new[] { "FILE_TYPE_DXF" },
                };
            }

            throw new ArgumentException($"unsupported output-format: {outputFormat}");
        }

        public static Dictionary<string, int> ListSxOptExportIntegerFields(Assembly assembly)
        {
            var type = assembly.GetType("sxnet.SxOptExport", throwOnError: false);
            if (type == null)
            {
                return new Dictionary<string, int>();
            }

            return type
                .GetFields(BindingFlags.Public | BindingFlags.Static)
                .Where(field => field.FieldType == typeof(int))
                .OrderBy(field => field.Name, StringComparer.Ordinal)
                .ToDictionary(field => field.Name, field => (int)field.GetValue(null)!);
        }

        private static int ResolveSxOptExportInt(Assembly assembly, CadExportFormat format)
        {
            var fields = ListSxOptExportIntegerFields(assembly);
            foreach (var fieldName in format.CandidateSxOptExportFields)
            {
                if (fields.TryGetValue(fieldName, out var number))
                {
                    return number;
                }
            }

            throw new InvalidOperationException(
                "SxOptExport does not expose any expected export file type constants for "
                + format.OutputFormat
                + ": "
                + string.Join(", ", format.CandidateSxOptExportFields)
                + ". Pass --export-file-type with the ICAD/SXNET environment-specific numeric value."
            );
        }

        private static string? ResolveExportedPath(
            string outputDirectory,
            string requestedFileName,
            string[] extensions,
            DateTime startedAtUtc
        )
        {
            var requestedPath = Path.Combine(outputDirectory, requestedFileName);
            if (File.Exists(requestedPath))
            {
                return requestedPath;
            }

            var requestedBaseName = Path.GetFileNameWithoutExtension(requestedFileName);
            foreach (var extension in extensions)
            {
                var exportedPath = Directory.GetFiles(outputDirectory, requestedBaseName + "*." + extension)
                    .Select(path => new FileInfo(path))
                    .Where(file => file.LastWriteTimeUtc >= startedAtUtc)
                    .OrderByDescending(file => file.LastWriteTimeUtc)
                    .Select(file => file.FullName)
                    .FirstOrDefault();
                if (exportedPath != null)
                {
                    return exportedPath;
                }
            }

            return null;
        }

        private static string SanitizeFileName(string value)
        {
            var invalid = Path.GetInvalidFileNameChars();
            var chars = value
                .Trim()
                .Select(character => invalid.Contains(character) ? '_' : character)
                .ToArray();
            var sanitized = new string(chars).Trim('.', ' ');
            return string.IsNullOrWhiteSpace(sanitized) ? "icad-converted" : sanitized;
        }
    }

    /// <summary>

    /// CadExportFormatに関する処理と状態を一つの責務としてまとめます。

    /// </summary>

    public sealed class CadExportFormat
    {
        public string OutputFormat { get; set; } = string.Empty;
        public string Extension { get; set; } = string.Empty;
        public string[] ExportedExtensions { get; set; } = Array.Empty<string>();
        public string Mode { get; set; } = string.Empty;
        public string MimeType { get; set; } = string.Empty;
        public string ModelFormat { get; set; } = string.Empty;
        public string[] CandidateSxOptExportFields { get; set; } = Array.Empty<string>();
    }
}
