using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    internal sealed class IcadPreviewAssetExporter
    {
        public List<ViewerAssetPayload> Export3DStl(
            SxNetOpenContext context,
            string inputPath,
            PreviewAssetOptions options,
            IList<WarningPayload> warnings
        )
        {
            if (!options.Enabled || string.IsNullOrWhiteSpace(options.OutputDirectory))
            {
                return new List<ViewerAssetPayload>();
            }

            var outputDirectory = Path.GetFullPath(options.OutputDirectory);
            Directory.CreateDirectory(outputDirectory);
            var filename = BuildAssetFileName(inputPath, options, ".stl");
            var targetPath = Path.Combine(outputDirectory, filename);
            var startedAtUtc = DateTime.UtcNow.AddSeconds(-2);

            try
            {
                if (File.Exists(targetPath))
                {
                    File.Delete(targetPath);
                }

                var fileType = ResolveSxOptExportInt(context.Assembly, "FILE_TYPE_STL_MULTI", fallback: 8);
                context.ExportModel(outputDirectory, filename, fileType);
                var exportedPath = ResolveExportedPath(outputDirectory, filename, startedAtUtc);
                if (exportedPath == null)
                {
                    var message = "SxModel.export did not create an STL file in the preview output directory.";
                    warnings.Add(new WarningPayload { Code = "viewer_3d_stl_export_missing", Message = message });
                    return new List<ViewerAssetPayload>
                    {
                        FailedAsset(filename, targetPath, message),
                    };
                }

                var info = new FileInfo(exportedPath);
                return new List<ViewerAssetPayload>
                {
                    new ViewerAssetPayload
                    {
                        Mode = "3d",
                        Status = "ready",
                        Source = "sxnet_export",
                        Filename = info.Name,
                        Extension = "stl",
                        MimeType = "model/stl",
                        ModelFormat = "stl",
                        FilePath = info.FullName,
                        Url = BuildAssetUrl(options.PublicBaseUrl, info.Name),
                        SizeBytes = info.Length,
                    },
                };
            }
            catch (Exception exception)
            {
                var message = "3D STL preview asset export failed: " + exception.Message;
                warnings.Add(new WarningPayload { Code = "viewer_3d_stl_export_failed", Message = message });
                return new List<ViewerAssetPayload>
                {
                    FailedAsset(filename, targetPath, message),
                };
            }
        }

        private static ViewerAssetPayload FailedAsset(string filename, string targetPath, string message)
        {
            return new ViewerAssetPayload
            {
                Mode = "3d",
                Status = "failed",
                Source = "sxnet_export",
                Filename = filename,
                Extension = "stl",
                MimeType = "model/stl",
                ModelFormat = "stl",
                FilePath = targetPath,
                Message = message,
            };
        }

        private static string BuildAssetFileName(string inputPath, PreviewAssetOptions options, string extension)
        {
            var prefix = string.IsNullOrWhiteSpace(options.FileNamePrefix)
                ? Path.GetFileNameWithoutExtension(inputPath)
                : options.FileNamePrefix;
            prefix = SanitizeFileName(prefix ?? "icad-preview");
            return prefix.EndsWith(extension, StringComparison.OrdinalIgnoreCase) ? prefix : prefix + extension;
        }

        private static string SanitizeFileName(string value)
        {
            var invalid = Path.GetInvalidFileNameChars();
            var chars = value
                .Trim()
                .Select(character => invalid.Contains(character) ? '_' : character)
                .ToArray();
            var sanitized = new string(chars).Trim('.', ' ');
            return string.IsNullOrWhiteSpace(sanitized) ? "icad-preview" : sanitized;
        }

        private static int ResolveSxOptExportInt(Assembly assembly, string fieldName, int fallback)
        {
            var type = assembly.GetType("sxnet.SxOptExport", throwOnError: false);
            var field = type?.GetField(fieldName, BindingFlags.Public | BindingFlags.Static);
            if (field == null)
            {
                return fallback;
            }

            var value = field.GetValue(null);
            return value is int number ? number : fallback;
        }

        private static string? ResolveExportedPath(string outputDirectory, string requestedFileName, DateTime startedAtUtc)
        {
            var requestedPath = Path.Combine(outputDirectory, requestedFileName);
            if (File.Exists(requestedPath))
            {
                return requestedPath;
            }

            var requestedBaseName = Path.GetFileNameWithoutExtension(requestedFileName);
            return Directory.GetFiles(outputDirectory, requestedBaseName + "*.stl")
                .Select(path => new FileInfo(path))
                .Where(file => file.LastWriteTimeUtc >= startedAtUtc)
                .OrderByDescending(file => file.LastWriteTimeUtc)
                .Select(file => file.FullName)
                .FirstOrDefault();
        }

        private static string? BuildAssetUrl(string? publicBaseUrl, string filename)
        {
            if (string.IsNullOrWhiteSpace(publicBaseUrl))
            {
                return null;
            }

            var normalizedBaseUrl = publicBaseUrl!.TrimEnd('/');
            return normalizedBaseUrl + "/" + Uri.EscapeDataString(filename);
        }
    }
}
