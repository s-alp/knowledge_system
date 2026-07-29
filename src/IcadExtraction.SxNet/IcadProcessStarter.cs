// このファイルは、ICADの起動状態を判定し、必要な場合だけ起動して所有関係を記録する。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    /// <summary>
    /// ICADの起動状態を判定し、必要な場合だけ起動して所有関係を記録する。
    /// </summary>
    public static class IcadProcessStarter
    {
        private const string IcadSessionMutexName = @"Local\KnowledgeSystem.IcadExtraction.IcadSession";
        private const int DefaultSessionLockWaitSeconds = 600;

        /// <summary>

        /// IcadProcessLeaseに関する処理と状態を一つの責務としてまとめます。

        /// </summary>

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

            public bool WasAutostarted => _startedProcess != null;

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

                        if (!TryCloseProcessWithoutSavingAndWaitForExit(_startedProcess, 15))
                        {
                            Console.Error.WriteLine(
                                "ICADの安全な自動終了を完了できなかったため、強制終了せず起動状態を維持しました。"
                            );
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

            Process.Start(new ProcessStartInfo
            {
                FileName = executablePath,
                UseShellExecute = true,
                WorkingDirectory = Path.GetDirectoryName(executablePath),
            });

            var deadline = DateTime.UtcNow.AddSeconds(Math.Max(1, startupWaitSeconds));
            while (DateTime.UtcNow < deadline)
            {
                var runningProcess = FindRunningProcess();
                if (runningProcess != null)
                {
                    return new IcadProcessLease(
                        new WarningPayload
                        {
                            Code = "icad_autostarted",
                            Message = $"ICAD was started automatically via {executablePath}.",
                        },
                        runningProcess,
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

        public static bool TryCloseRunningWithoutSaving(int timeoutSeconds = 15)
        {
            var normalizedTimeoutSeconds = Math.Max(1, timeoutSeconds);
            var deadline = DateTime.UtcNow.AddSeconds(normalizedTimeoutSeconds);
            var runningProcess = FindRunningProcess();
            if (runningProcess == null)
            {
                return WaitForAllCandidateProcessesToExit(deadline);
            }

            using (runningProcess)
            {
                return TryCloseProcessWithoutSavingAndWaitForExit(
                    runningProcess,
                    normalizedTimeoutSeconds
                );
            }
        }

        private static bool TryCloseProcessWithoutSavingAndWaitForExit(Process process, int timeoutSeconds)
        {
            var deadline = DateTime.UtcNow.AddSeconds(Math.Max(1, timeoutSeconds));
            if (!IcadWindowCloser.TryCloseWithoutSaving(process, TimeSpan.FromSeconds(Math.Max(1, timeoutSeconds))))
            {
                return false;
            }

            return WaitForAllCandidateProcessesToExit(deadline);
        }

        private static bool WaitForAllCandidateProcessesToExit(DateTime deadline)
        {
            while (DateTime.UtcNow < deadline)
            {
                if (!IsRunning())
                {
                    return true;
                }

                Thread.Sleep(100);
            }

            return !IsRunning();
        }

        private static Process? FindRunningProcess()
        {
            foreach (var processName in CandidateProcessNames)
            {
                foreach (var process in Process.GetProcessesByName(processName))
                {
                    try
                    {
                        process.Refresh();
                        if (!process.HasExited && process.MainWindowHandle != IntPtr.Zero)
                        {
                            return process;
                        }
                    }
                    catch (Win32Exception)
                    {
                        // 保護された補助プロセスは操作せず、同名のメインウィンドウを持つプロセスを探す。
                    }
                    catch (InvalidOperationException)
                    {
                        // 列挙後に終了したプロセスは対象外。
                    }

                    process.Dispose();
                }
            }

            return null;
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
