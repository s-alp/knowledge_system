using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

namespace IcadExtraction.Runner
{
    public sealed class SxNetInputFileLease : IDisposable
    {
        public const string TemporaryRootEnvironmentVariable = "ICAD_SXNET_TEMP_ROOT";
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
            return Create(inputPath, forceTemporaryCopy: false);
        }

        public static SxNetInputFileLease Create(string inputPath, bool forceTemporaryCopy)
        {
            var originalPath = Path.GetFullPath(inputPath);
            EnsureInputFileExists(originalPath);

            if (forceTemporaryCopy)
            {
                return CreateTemporaryCopyLease(
                    originalPath,
                    "temporary_copy_forced",
                    "SXNETへ渡すパスを短く固定するため、ICADファイルを短い一時パスへコピーして開きました。原本パスはsource_file.full_pathに保持しています。"
                );
            }

            if (!RequiresAlternatePathForSxNet(originalPath))
            {
                EnsureSxNetInputPathIsUsable(originalPath, originalPath);
                return new SxNetInputFileLease(originalPath, originalPath, "original", null, null, null);
            }

            var shortPath = TryGetWindowsShortPath(originalPath);
            if (shortPath != null && !RequiresAlternatePathForSxNet(shortPath))
            {
                EnsureSxNetInputPathIsUsable(shortPath, originalPath);
                return new SxNetInputFileLease(
                    originalPath,
                    shortPath,
                    "windows_short_path",
                    null,
                    "sxnet_input_path_shortened",
                    "SXNETのパス長制限を避けるため、Windows短縮パスでICADファイルを開きました。"
                );
            }

            return CreateTemporaryCopyLease(
                originalPath,
                "temporary_copy",
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

        private static SxNetInputFileLease CreateTemporaryCopyLease(
            string originalPath,
            string strategy,
            string warningMessage
        )
        {
            var temporaryDirectory = Path.Combine(ResolveTemporaryRoot(), Guid.NewGuid().ToString("N"));
            var extension = Path.GetExtension(originalPath);
            var stagedPath = Path.Combine(temporaryDirectory, string.IsNullOrWhiteSpace(extension) ? "input.icd" : "input" + extension);
            EnsureSxNetInputPathIsUsable(stagedPath, originalPath);
            Directory.CreateDirectory(temporaryDirectory);
            File.Copy(ToExtendedWindowsPath(originalPath), stagedPath, overwrite: false);

            return new SxNetInputFileLease(
                originalPath,
                stagedPath,
                strategy,
                temporaryDirectory,
                "sxnet_input_path_staged",
                warningMessage
            );
        }

        private static string ResolveTemporaryRoot()
        {
            var configuredRoot = Environment.GetEnvironmentVariable(TemporaryRootEnvironmentVariable);
            if (!string.IsNullOrWhiteSpace(configuredRoot))
            {
                return Path.GetFullPath(configuredRoot);
            }

            return Path.Combine(Path.GetTempPath(), "icad-sxnet");
        }

        private static void EnsureSxNetInputPathIsUsable(string sxNetInputPath, string originalPath)
        {
            var fileName = Path.GetFileName(sxNetInputPath);
            if (fileName.Length > WindowsFilenameLimit)
            {
                throw new InvalidOperationException(
                    $"SXNETへ渡すICADファイル名が長すぎます。上限={WindowsFilenameLimit}文字、"
                    + $"現在={fileName.Length}文字、SXNET入力={sxNetInputPath}、原本={originalPath}。"
                );
            }

            if (sxNetInputPath.Length > WindowsLegacyPathLimit)
            {
                throw new InvalidOperationException(
                    $"SXNETへ渡すICADパスが長すぎます。上限={WindowsLegacyPathLimit}文字、"
                    + $"現在={sxNetInputPath.Length}文字、SXNET入力={sxNetInputPath}、原本={originalPath}。"
                    + $"{TemporaryRootEnvironmentVariable} に短い作業フォルダを指定してください。"
                );
            }
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
