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
    /// 開いているICADモデルをSXNETの標準export APIでDXFまたはSTEPへ変換します。
    /// Django、データベース、HTTP APIには依存せず、C# Runnerや別の.NETホストから直接利用できます。
    /// </summary>
    public sealed class IcadCadFormatExporter
    {
        /// <summary>
        /// 読み取り専用で開いたSXNETコンテキストから変換ファイルを生成し、保存先・形式・サイズを返します。
        /// 出力先フォルダの作成と同名ファイルの置換を伴うため、対話利用では事前確認を行う
        /// <c>scripts/convert_icad_standalone.ps1</c>を入口にしてください。
        /// SXNETが出力形式定数を公開しない環境では、実機で確認した数値を<paramref name="exportFileType"/>へ指定します。
        /// 変換ファイルが生成されない場合は推測値で続行せず、例外として呼び出し元へ返します。
        /// </summary>
        /// <param name="context">対象ICADを開いたSXNETコンテキスト。</param>
        /// <param name="inputPath">結果メタデータの既定ファイル名に使う元ICADパス。</param>
        /// <param name="outputDirectory">変換ファイルを保存するフォルダ。</param>
        /// <param name="outputFormat"><c>dxf</c>、<c>step</c>、または<c>stp</c>。</param>
        /// <param name="outputBaseName">拡張子を除いた出力名。未指定時は元ICAD名を使います。</param>
        /// <param name="exportFileType">環境固有のSXNET出力形式番号。通常は未指定で定数を自動解決します。</param>
        /// <returns>生成ファイルを後続処理へ渡すための共通メタデータ。</returns>
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

        /// <summary>
        /// 利用者の形式指定を、SXNET出力・拡張子・MIME typeに必要な共通設定へ正規化します。
        /// 未対応形式は誤変換を防ぐため明示的に拒否します。
        /// </summary>
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

        /// <summary>
        /// 実機SXNET DLLが公開する出力形式定数を列挙します。
        /// ICADの版差を推測で吸収せず、<c>probe-cad-export-types</c>の診断結果として確認するために公開しています。
        /// </summary>
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
    /// 1つの変換形式について、SXNET出力候補と後続ビューワーへ渡すファイル情報をまとめます。
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
