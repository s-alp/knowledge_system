using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    public static class IcadProcessStarter
    {
        public sealed class IcadProcessLease : IDisposable
        {
            private readonly Process? _startedProcess;
            private readonly bool _shutdownOnDispose;

            public IcadProcessLease(WarningPayload? startupWarning, Process? startedProcess, bool shutdownOnDispose)
            {
                StartupWarning = startupWarning;
                _startedProcess = startedProcess;
                _shutdownOnDispose = shutdownOnDispose;
            }

            public WarningPayload? StartupWarning { get; }

            public void Dispose()
            {
                if (!_shutdownOnDispose || _startedProcess == null)
                {
                    return;
                }

                try
                {
                    if (_startedProcess.HasExited)
                    {
                        return;
                    }

                    if (_startedProcess.CloseMainWindow())
                    {
                        if (_startedProcess.WaitForExit(5000))
                        {
                            return;
                        }
                    }

                    if (!_startedProcess.HasExited)
                    {
                        _startedProcess.Kill();
                        _startedProcess.WaitForExit(5000);
                    }
                }
                catch
                {
                    // 後処理での失敗は抽出結果自体を壊さない。
                }
            }
        }

        private static readonly string[] CandidateExecutablePaths =
        {
            @"C:\ICADSX\bin\icad.exe",
            @"C:\ICADSX\bin\icadsx02.exe",
            @"C:\ICADSX\bin\icadsx02_x86.exe",
        };

        private static readonly string[] CandidateProcessNames =
        {
            "icad",
            // この環境の ICAD SX 2025 は実行本体が ICADX4J.EXE として残る。
            "icadx4j",
            "icadsx02",
            "icadsx02_x86",
            "RICAD",
        };

        public static IcadProcessLease EnsureRunning(string? executablePath, int startupWaitSeconds, bool shutdownIfAutostarted)
        {
            if (IsRunning())
            {
                return new IcadProcessLease(null, null, false);
            }

            if (string.IsNullOrWhiteSpace(executablePath))
            {
                executablePath = ResolveExecutablePath();
            }

            if (!File.Exists(executablePath))
            {
                throw new FileNotFoundException("ICAD executable was not found", executablePath);
            }

            var startedProcess = Process.Start(new ProcessStartInfo
            {
                FileName = executablePath,
                UseShellExecute = true,
                WorkingDirectory = Path.GetDirectoryName(executablePath),
            });

            var deadline = DateTime.UtcNow.AddSeconds(Math.Max(1, startupWaitSeconds));
            while (DateTime.UtcNow < deadline)
            {
                if (IsRunning())
                {
                    return new IcadProcessLease(
                        new WarningPayload
                        {
                            Code = "icad_autostarted",
                            Message = $"ICAD was started automatically via {executablePath}.",
                        },
                        startedProcess,
                        shutdownIfAutostarted
                    );
                }

                Thread.Sleep(500);
            }

            throw new TimeoutException($"ICAD did not become ready within {startupWaitSeconds} seconds.");
        }

        private static bool IsRunning()
        {
            return CandidateProcessNames.Any(name => Process.GetProcessesByName(name).Length > 0);
        }

        private static string ResolveExecutablePath()
        {
            var resolvedPath = CandidateExecutablePaths.FirstOrDefault(File.Exists);
            if (string.IsNullOrWhiteSpace(resolvedPath))
            {
                throw new InvalidOperationException(
                    "ICAD process is not running and no candidate executable path could be resolved."
                );
            }

            return resolvedPath;
        }
    }
}
