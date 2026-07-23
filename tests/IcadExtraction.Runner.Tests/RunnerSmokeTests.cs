using System;
using System.IO;
using IcadExtraction.Runner;
using Xunit;

namespace IcadExtraction.Runner.Tests
{
    public sealed class RunnerSmokeTests
    {
        [Fact]
        public void Main_ReturnsErrorForUnsupportedCommand()
        {
            var originalError = Console.Error;
            using var error = new StringWriter();
            Console.SetError(error);
            try
            {
                var result = Program.Main(new[] { "unknown" });
                Assert.Equal(1, result);
                Assert.Contains("error[0].type=System.ArgumentException", error.ToString());
                Assert.Contains("unsupported command: unknown", error.ToString());
                Assert.Contains("error.stack_trace_begin", error.ToString());
            }
            finally
            {
                Console.SetError(originalError);
            }
        }

        [Fact]
        public void SxNetInputFileLease_UsesOriginalPathForNormalPath()
        {
            var tempPath = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".icd");
            File.WriteAllText(tempPath, "dummy");
            try
            {
                using var lease = SxNetInputFileLease.Create(tempPath);

                Assert.Equal(Path.GetFullPath(tempPath), lease.OriginalPath);
                Assert.Equal(Path.GetFullPath(tempPath), lease.SxNetInputPath);
                Assert.Equal("original", lease.Strategy);
                Assert.False(lease.UsedAlternatePath);
            }
            finally
            {
                File.Delete(tempPath);
            }
        }

        [Fact]
        public void SxNetInputFileLease_DetectsPathBeyondSxNetLegacyLimit()
        {
            var longPath = @"C:\" + new string('a', SxNetInputFileLease.WindowsLegacyPathLimit);

            Assert.True(SxNetInputFileLease.RequiresAlternatePathForSxNet(longPath));
        }

        [Fact]
        public void SxNetInputFileLease_ForceTemporaryCopyUsesShortStagedPath()
        {
            var tempPath = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".icd");
            File.WriteAllText(tempPath, "dummy");
            string stagedPath;
            try
            {
                using (var lease = SxNetInputFileLease.Create(tempPath, forceTemporaryCopy: true))
                {
                    stagedPath = lease.SxNetInputPath;

                    Assert.Equal(Path.GetFullPath(tempPath), lease.OriginalPath);
                    Assert.NotEqual(Path.GetFullPath(tempPath), lease.SxNetInputPath);
                    Assert.Equal("temporary_copy_forced", lease.Strategy);
                    Assert.True(lease.UsedAlternatePath);
                    Assert.True(File.Exists(lease.SxNetInputPath));
                }

                Assert.False(File.Exists(stagedPath));
            }
            finally
            {
                File.Delete(tempPath);
            }
        }

        [Fact]
        public void SxNetInputFileLease_ReportsTooLongStagedPathBeforeOpeningSxNet()
        {
            var tempPath = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".icd");
            var originalTemporaryRoot = Environment.GetEnvironmentVariable(SxNetInputFileLease.TemporaryRootEnvironmentVariable);
            File.WriteAllText(tempPath, "dummy");
            try
            {
                var tooLongTemporaryRoot = Path.Combine(Path.GetTempPath(), new string('a', 240));
                Environment.SetEnvironmentVariable(SxNetInputFileLease.TemporaryRootEnvironmentVariable, tooLongTemporaryRoot);

                var exception = Assert.Throws<InvalidOperationException>(
                    () => SxNetInputFileLease.Create(tempPath, forceTemporaryCopy: true)
                );

                Assert.Contains("SXNETへ渡すICADパスが長すぎます", exception.Message);
                Assert.Contains(SxNetInputFileLease.TemporaryRootEnvironmentVariable, exception.Message);
            }
            finally
            {
                Environment.SetEnvironmentVariable(SxNetInputFileLease.TemporaryRootEnvironmentVariable, originalTemporaryRoot);
                File.Delete(tempPath);
            }
        }

        [Fact]
        public void ShouldRetrySxNetInputWithTemporaryCopy_ReturnsTrueForExistingPathAndSxNetMissingFileError()
        {
            var tempPath = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".icd");
            File.WriteAllText(tempPath, "dummy");
            try
            {
                var exception = new InvalidOperationException("MSG07309 指定されたファイルは存在しません。");

                Assert.True(Program.ShouldRetrySxNetInputWithTemporaryCopy(exception, tempPath, forceSxNetStagedInput: false));
            }
            finally
            {
                File.Delete(tempPath);
            }
        }

        [Fact]
        public void ShouldRetrySxNetInputWithTemporaryCopy_ReturnsFalseWhenAlreadyForced()
        {
            var tempPath = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".icd");
            File.WriteAllText(tempPath, "dummy");
            try
            {
                var exception = new InvalidOperationException("MSG07309 指定されたファイルは存在しません。");

                Assert.False(Program.ShouldRetrySxNetInputWithTemporaryCopy(exception, tempPath, forceSxNetStagedInput: true));
            }
            finally
            {
                File.Delete(tempPath);
            }
        }
    }
}
