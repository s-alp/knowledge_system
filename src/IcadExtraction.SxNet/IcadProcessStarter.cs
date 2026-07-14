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
        private const string IcadSessionMutexName = @"Local\KnowledgeSystem.IcadExtraction.IcadSession";
        private const int DefaultSessionLockWaitSeconds = 600;

        public sealed class IcadProcessLease : IDisposable
        {
            private readonly Process? _startedProcess;
            private readonly bool _shutdownOnDispose;
            private readonly Mutex? _sessionMutex;
            private readonly bool _sessionLockAcquired;

            public IcadProcessLease(
                WarningPayload? startupWarning,
                Process? startedProcess,
                bool shutdownOnDispose,
                Mutex? sessionMutex,
                bool sessionLockAcquired)
            {
                StartupWarning = startupWarning;
                _startedProcess = startedProcess;
                _shutdownOnDispose = shutdownOnDispose;
                _sessionMutex = sessionMutex;
                _sessionLockAcquired = sessionLockAcquired;
            }

            public WarningPayload? StartupWarning { get; }

            public void Dispose()
            {
                try
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
                finally
                {
                    ReleaseSessionLock();
                }
            }

            private void ReleaseSessionLock()
            {
                if (!_sessionLockAcquired || _sessionMutex == null)
                {
                    return;
                }

                try
                {
                    _sessionMutex.ReleaseMutex();
                }
                finally
                {
                    _sessionMutex.Dispose();
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
            var normalizedStartupWaitSeconds = Math.Max(1, startupWaitSeconds);
            var sessionLockWaitSeconds = Math.Max(DefaultSessionLockWaitSeconds, normalizedStartupWaitSeconds);
            var sessionMutex = new Mutex(false, IcadSessionMutexName);
            var lockAcquired = false;
            try
            {
                try
                {
                    lockAcquired = sessionMutex.WaitOne(TimeSpan.FromSeconds(sessionLockWaitSeconds));
                }
                catch (AbandonedMutexException)
                {
                    lockAcquired = true;
                }

                if (!lockAcquired)
                {
                    throw new TimeoutException(
                        $"ICAD session lock could not be acquired within {sessionLockWaitSeconds} seconds."
                    );
                }

                return EnsureRunningExclusive(
                    executablePath,
                    normalizedStartupWaitSeconds,
                    shutdownIfAutostarted,
                    sessionMutex,
                    lockAcquired
                );
            }
            catch
            {
                if (lockAcquired)
                {
                    sessionMutex.ReleaseMutex();
                }

                sessionMutex.Dispose();
                throw;
            }
        }

        private static IcadProcessLease EnsureRunningExclusive(
            string? executablePath,
            int startupWaitSeconds,
            bool shutdownIfAutostarted,
            Mutex sessionMutex,
            bool sessionLockAcquired)
        {
            if (IsRunning())
            {
                return new IcadProcessLease(null, null, false, sessionMutex, sessionLockAcquired);
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
                        shutdownIfAutostarted,
                        sessionMutex,
                        sessionLockAcquired
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
