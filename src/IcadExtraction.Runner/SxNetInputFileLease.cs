using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

namespace IcadExtraction.Runner
{
    public sealed class SxNetInputFileLease : IDisposable
    {
        public const int WindowsFilenameLimit = 255;
        public const int WindowsLegacyPathLimit = 259;

        private readonly string? _temporaryDirectory;

        private SxNetInputFileLease(
            string originalPath,
            string sxNetInputPath,
            string strategy,
            string? temporaryDirectory,
            string? warningCode,
            string? warningMessage
        )
        {
            OriginalPath = originalPath;
            SxNetInputPath = sxNetInputPath;
            Strategy = strategy;
            _temporaryDirectory = temporaryDirectory;
            WarningCode = warningCode;
            WarningMessage = warningMessage;
        }

        public string OriginalPath { get; }

        public string SxNetInputPath { get; }

        public string Strategy { get; }

        public string? WarningCode { get; }

        public string? WarningMessage { get; }

        public bool UsedAlternatePath => !string.Equals(OriginalPath, SxNetInputPath, StringComparison.OrdinalIgnoreCase);

        public static SxNetInputFileLease Create(string inputPath)
        {
            var originalPath = Path.GetFullPath(inputPath);
            EnsureInputFileExists(originalPath);

            if (!RequiresAlternatePathForSxNet(originalPath))
            {
                return new SxNetInputFileLease(originalPath, originalPath, "original", null, null, null);
            }

            var shortPath = TryGetWindowsShortPath(originalPath);
            if (shortPath != null && !RequiresAlternatePathForSxNet(shortPath))
            {
                return new SxNetInputFileLease(
                    originalPath,
                    shortPath,
                    "windows_short_path",
                    null,
                    "sxnet_input_path_shortened",
                    "SXNETのパス長制限を避けるため、Windows短縮パスでICADファイルを開きました。"
                );
            }

            var temporaryDirectory = Path.Combine(Path.GetTempPath(), "icad-sxnet", Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(temporaryDirectory);
            var extension = Path.GetExtension(originalPath);
            var stagedPath = Path.Combine(temporaryDirectory, string.IsNullOrWhiteSpace(extension) ? "input.icd" : "input" + extension);
            File.Copy(ToExtendedWindowsPath(originalPath), stagedPath, overwrite: false);

            return new SxNetInputFileLease(
                originalPath,
                stagedPath,
                "temporary_copy",
                temporaryDirectory,
                "sxnet_input_path_staged",
                "SXNETのパス長制限を避けるため、ICADファイルを短い一時パスへコピーして開きました。外部参照がある図面では参照先の解決結果を確認してください。"
            );
        }

        public static bool RequiresAlternatePathForSxNet(string fullPath)
        {
            var fileName = Path.GetFileName(fullPath);
            return fullPath.Length > WindowsLegacyPathLimit || fileName.Length > WindowsFilenameLimit;
        }

        public void Dispose()
        {
            if (string.IsNullOrWhiteSpace(_temporaryDirectory) || !Directory.Exists(_temporaryDirectory))
            {
                return;
            }

            try
            {
                Directory.Delete(_temporaryDirectory, recursive: true);
            }
            catch
            {
                // 一時コピーの掃除失敗で、抽出成功結果を失敗扱いにしない。
            }
        }

        private static void EnsureInputFileExists(string originalPath)
        {
            if (!File.Exists(originalPath) && !File.Exists(ToExtendedWindowsPath(originalPath)))
            {
                throw new FileNotFoundException("指定されたICADファイルが見つかりません。原本パスとネットワークドライブ接続を確認してください。", originalPath);
            }
        }

        private static string? TryGetWindowsShortPath(string path)
        {
            if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                return null;
            }

            var buffer = new StringBuilder(WindowsLegacyPathLimit + 1);
            var length = GetShortPathName(path, buffer, buffer.Capacity);
            if (length <= 0)
            {
                return null;
            }

            if (length > buffer.Capacity)
            {
                buffer.EnsureCapacity(length);
                length = GetShortPathName(path, buffer, buffer.Capacity);
                if (length <= 0)
                {
                    return null;
                }
            }

            return buffer.ToString();
        }

        private static string ToExtendedWindowsPath(string path)
        {
            if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows) || path.StartsWith(@"\\?\", StringComparison.Ordinal))
            {
                return path;
            }

            if (path.StartsWith(@"\\", StringComparison.Ordinal))
            {
                return @"\\?\UNC\" + path.Substring(2);
            }

            return @"\\?\" + path;
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern int GetShortPathName(string longPath, StringBuilder shortPath, int bufferLength);
    }
}
