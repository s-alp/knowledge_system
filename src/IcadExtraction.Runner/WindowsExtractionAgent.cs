// このファイルは、Windows上でDjangoの抽出ジョブを取得し、C# Runner実行と結果返却を繰り返す。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using IcadExtraction.Contracts;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace IcadExtraction.Runner
{
    /// <summary>
    /// Windows上でDjangoの抽出ジョブを取得し、C# Runner実行と結果返却を繰り返す。
    /// </summary>
    internal sealed class WindowsExtractionAgent : IDisposable
    {
        private readonly AgentOptions _options;
        private readonly HttpClient _httpClient;
        private bool _stopRequested;

        private WindowsExtractionAgent(AgentOptions options)
        {
            _options = options;
            _httpClient = new HttpClient
            {
                BaseAddress = options.ApiBaseUrl,
                Timeout = TimeSpan.FromSeconds(options.ApiTimeoutSeconds),
            };
            _httpClient.DefaultRequestHeaders.Authorization =
                new AuthenticationHeaderValue("Bearer", options.ApiToken);
        }

        public static int Run(IReadOnlyDictionary<string, string> commandOptions)
        {
            var options = AgentOptions.From(commandOptions);
            using var agent = new WindowsExtractionAgent(options);
            return agent.RunLoop();
        }

        public void Dispose()
        {
            _httpClient.Dispose();
        }

        private int RunLoop()
        {
            // 常駐ループはCtrl+Cを安全な停止要求へ変換し、処理中ジョブを突然中断しない。
            ConsoleCancelEventHandler cancelHandler = (_, eventArgs) =>
            {
                eventArgs.Cancel = true;
                _stopRequested = true;
            };
            Console.CancelKeyPress += cancelHandler;
            try
            {
                SendHeartbeat("starting", null, null);
                while (!_stopRequested)
                {
                    AgentJob? job;
                    try
                    {
                        SendHeartbeat("claiming", null, null);
                        job = ClaimNextJob();
                    }
                    catch (Exception exception)
                    {
                        Console.Error.WriteLine("agent_claim_failed: " + exception);
                        if (_options.Once)
                        {
                            throw;
                        }
                        SleepUntilNextPoll();
                        continue;
                    }

                    if (job == null)
                    {
                        SendHeartbeat("idle", null, null);
                        if (_options.Once)
                        {
                            return 0;
                        }
                        SleepUntilNextPoll();
                        continue;
                    }

                    var succeeded = ProcessJob(job);
                    if (_options.Once)
                    {
                        return succeeded ? 0 : 1;
                    }
                }

                return 0;
            }
            finally
            {
                Console.CancelKeyPress -= cancelHandler;
                try
                {
                    SendHeartbeat("stopping", null, null);
                }
                catch (Exception exception)
                {
                    Console.Error.WriteLine("agent_stopping_heartbeat_failed: " + exception.Message);
                }
            }
        }

        private void SleepUntilNextPoll()
        {
            var remainingMilliseconds = _options.PollSeconds * 1000;
            while (!_stopRequested && remainingMilliseconds > 0)
            {
                var wait = Math.Min(remainingMilliseconds, 500);
                Thread.Sleep(wait);
                remainingMilliseconds -= wait;
            }
        }

        private AgentJob? ClaimNextJob()
        {
            // claim APIは同じジョブを複数agentが処理しないためのlease取得も兼ねている。
            var payload = new JObject
            {
                ["workerName"] = _options.WorkerName,
                ["mode"] = _options.Mode,
                ["runnerVersion"] = SchemaVersions.SchemaVersion,
                ["processId"] = Process.GetCurrentProcess().Id,
            };
            using var response = PostJson("api/v1/drawing-metadata/agent/jobs/claim", payload);
            if (response.StatusCode == HttpStatusCode.NoContent)
            {
                return null;
            }
            EnsureSuccess(response, "agent job claim");
            var body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
            return JsonConvert.DeserializeObject<AgentJob>(body)
                ?? throw new InvalidOperationException("agent claim response is empty");
        }

        private bool ProcessJob(AgentJob job)
        {
            // ジョブ専用領域を作り、別ジョブの入力・結果・プレビュー資産が混ざらないようにする。
            var workDirectory = Path.Combine(_options.WorkRoot, job.JobId);
            var previewDirectory = Path.Combine(workDirectory, "preview");
            var resultPath = Path.Combine(workDirectory, "result.json");
            Directory.CreateDirectory(previewDirectory);

            try
            {
                // 処理中heartbeatを先に送り、Django側が長時間処理と停止を区別できるようにする。
                SendHeartbeat("processing", job.JobId, null);
                var inputPath = ResolveInputPath(job, workDirectory);
                VerifySourceHash(inputPath, job.Source.Sha256);
                RunExtractionWithHeartbeat(job, inputPath, resultPath, previewDirectory);

                // C#が返したローカルパスを、Djangoが監査・配信できる元情報と相対パスへ置き換える。
                var result = JObject.Parse(File.ReadAllText(resultPath, Encoding.UTF8));
                RewriteSourceMetadata(result, job.Source);
                RewritePreviewFilePaths(result, previewDirectory);
                UploadPreviewAssets(job, previewDirectory);
                CompleteJob(job, result);
                Console.WriteLine($"agent_job_succeeded job_id={job.JobId}");
                return true;
            }
            catch (Exception exception)
            {
                var message = LimitErrorMessage(exception.ToString());
                Console.Error.WriteLine($"agent_job_failed job_id={job.JobId}");
                Console.Error.WriteLine(message);
                FailJob(job, message);
                SendHeartbeat("error", null, message);
                return false;
            }
            finally
            {
                // 調査用に明示保存する設定でない限り、成功・失敗どちらでもジョブ作業領域を片付ける。
                if (!_options.KeepWorkFiles)
                {
                    TryDeleteWorkDirectory(workDirectory);
                }
            }
        }

        private string ResolveInputPath(AgentJob job, string workDirectory)
        {
            // Windowsから共有パスを直接読める場合はコピーを省き、読めない場合だけAPIから取得する。
            if (!string.IsNullOrWhiteSpace(job.Source.Path) && File.Exists(job.Source.Path))
            {
                return Path.GetFullPath(job.Source.Path);
            }
            if (!job.Source.DownloadAvailable || string.IsNullOrWhiteSpace(job.Source.DownloadUrl))
            {
                throw new FileNotFoundException(
                    "Windows側sourcePathにアクセスできず、Django側にもdownload可能な入力がありません。",
                    job.Source.Path
                );
            }

            var filename = SafeFileName(job.Source.Filename);
            var downloadPath = Path.Combine(workDirectory, "input", filename);
            Directory.CreateDirectory(Path.GetDirectoryName(downloadPath) ?? workDirectory);
            using var response = _httpClient.GetAsync(job.Source.DownloadUrl, HttpCompletionOption.ResponseHeadersRead)
                .GetAwaiter()
                .GetResult();
            EnsureSuccess(response, "agent source download");
            using var sourceStream = response.Content.ReadAsStreamAsync().GetAwaiter().GetResult();
            using var targetStream = new FileStream(downloadPath, FileMode.Create, FileAccess.Write, FileShare.None);
            sourceStream.CopyTo(targetStream);
            return downloadPath;
        }

        private void RunExtractionWithHeartbeat(
            AgentJob job,
            string inputPath,
            string resultPath,
            string previewDirectory
        )
        {
            var command = BuildExtractCommand(job, inputPath, resultPath, previewDirectory);
            var task = Task.Run(() => Program.ExecuteCommand(command));
            while (!task.Wait(TimeSpan.FromSeconds(_options.HeartbeatSeconds)))
            {
                SendHeartbeat("processing", job.JobId, null);
            }

            var exitCode = task.GetAwaiter().GetResult();
            if (exitCode != 0)
            {
                throw new InvalidOperationException($"extract command returned exit code {exitCode}");
            }
            if (!File.Exists(resultPath))
            {
                throw new FileNotFoundException("extract command did not create result JSON", resultPath);
            }
        }

        private CliCommand BuildExtractCommand(
            AgentJob job,
            string inputPath,
            string resultPath,
            string previewDirectory
        )
        {
            var options = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
            {
                ["input-path"] = inputPath,
                ["source-kind"] = job.ExtractionMode,
                ["output-path"] = resultPath,
                ["sxnet-dll-path"] = _options.SxNetDllPath,
                ["icad-startup-wait-seconds"] = _options.IcadStartupWaitSeconds.ToString(),
                ["shutdown-icad-if-autostarted"] = _options.ShutdownIcadIfAutostarted.ToString(),
                ["extraction-profile"] = string.IsNullOrWhiteSpace(job.ExtractionProfile)
                    ? "default"
                    : job.ExtractionProfile,
                ["extraction-options-json"] = job.ExtractionOptions.ToString(Formatting.None),
                ["preview-output-dir"] = previewDirectory,
                ["preview-public-base-url"] = job.Preview.BaseUrl,
                ["preview-file-name-prefix"] = job.JobId,
            };
            if (!string.IsNullOrWhiteSpace(_options.IcadExecutablePath))
            {
                options["icad-executable-path"] = _options.IcadExecutablePath!;
            }
            return new CliCommand
            {
                CommandName = "extract",
                Options = options,
            };
        }

        private void UploadPreviewAssets(AgentJob job, string previewDirectory)
        {
            // 抽出JSON内の相対パスと同じ階層を保って送り、複数資産でも参照先を一意にする。
            if (!Directory.Exists(previewDirectory))
            {
                return;
            }

            foreach (var filePath in Directory.GetFiles(previewDirectory, "*", SearchOption.AllDirectories))
            {
                var relativePath = RelativePath(previewDirectory, filePath);
                using var content = new MultipartFormDataContent();
                content.Add(new StringContent(_options.WorkerName), "workerName");
                content.Add(new StringContent(relativePath), "relativePath");
                using var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.Read);
                using var fileContent = new StreamContent(stream);
                fileContent.Headers.ContentType = new MediaTypeHeaderValue("application/octet-stream");
                content.Add(fileContent, "file", Path.GetFileName(filePath));
                using var response = _httpClient.PostAsync(
                        $"api/v1/drawing-metadata/agent/jobs/{job.JobId}/assets",
                        content
                    )
                    .GetAwaiter()
                    .GetResult();
                EnsureSuccess(response, $"agent preview asset upload ({relativePath})");
            }
        }

        private void CompleteJob(AgentJob job, JObject result)
        {
            var payload = new JObject
            {
                ["workerName"] = _options.WorkerName,
                ["result"] = result,
            };
            using var response = PostJson(
                $"api/v1/drawing-metadata/agent/jobs/{job.JobId}/complete",
                payload
            );
            EnsureSuccess(response, "agent job complete");
        }

        private void FailJob(AgentJob job, string message)
        {
            var payload = new JObject
            {
                ["workerName"] = _options.WorkerName,
                ["errorMessage"] = message,
            };
            using var response = PostJson(
                $"api/v1/drawing-metadata/agent/jobs/{job.JobId}/fail",
                payload
            );
            EnsureSuccess(response, "agent job fail");
        }

        private void SendHeartbeat(string state, string? jobId, string? lastError)
        {
            var payload = new JObject
            {
                ["workerName"] = _options.WorkerName,
                ["mode"] = _options.Mode,
                ["state"] = state,
                ["jobId"] = string.IsNullOrWhiteSpace(jobId) ? JValue.CreateNull() : new JValue(jobId),
                ["runnerVersion"] = SchemaVersions.SchemaVersion,
                ["processId"] = Process.GetCurrentProcess().Id,
                ["lastError"] = lastError ?? string.Empty,
            };
            using var response = PostJson("api/v1/drawing-metadata/agent/heartbeat", payload);
            EnsureSuccess(response, "agent heartbeat");
        }

        private HttpResponseMessage PostJson(string relativeUrl, JObject payload)
        {
            using var content = new StringContent(
                payload.ToString(Formatting.None),
                Encoding.UTF8,
                "application/json"
            );
            return _httpClient.PostAsync(relativeUrl, content).GetAwaiter().GetResult();
        }

        private static void EnsureSuccess(HttpResponseMessage response, string operation)
        {
            if (response.IsSuccessStatusCode)
            {
                return;
            }
            var responseBody = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
            throw new InvalidOperationException(
                $"{operation} failed: HTTP {(int)response.StatusCode} {response.ReasonPhrase}: {responseBody}"
            );
        }

        private static void VerifySourceHash(string path, string? expectedHash)
        {
            // 取得途中の破損や元ファイル差し替えを検知し、異なる図面の結果を完了登録しない。
            if (string.IsNullOrWhiteSpace(expectedHash))
            {
                return;
            }
            using var sha256 = SHA256.Create();
            using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
            var actualHash = string.Concat(sha256.ComputeHash(stream).Select(value => value.ToString("x2")));
            if (!string.Equals(actualHash, expectedHash, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException(
                    $"入力ファイルのSHA-256が登録時と一致しません。expected={expectedHash} actual={actualHash}"
                );
            }
        }

        private static void RewriteSourceMetadata(JObject result, AgentSource source)
        {
            if (string.IsNullOrWhiteSpace(source.Path))
            {
                return;
            }
            result["input_path"] = source.Path;
            var sourceFile = result["source_file"] as JObject ?? new JObject();
            sourceFile["full_path"] = source.Path;
            sourceFile["directory_path"] = Path.GetDirectoryName(source.Path);
            sourceFile["file_name"] = source.Filename;
            sourceFile["file_name_without_extension"] = Path.GetFileNameWithoutExtension(source.Filename);
            sourceFile["extension"] = Path.GetExtension(source.Filename).TrimStart('.').ToLowerInvariant();
            sourceFile["original_path_length"] = source.Path.Length;
            result["source_file"] = sourceFile;
        }

        private static void RewritePreviewFilePaths(JObject result, string previewDirectory)
        {
            foreach (var property in result.Descendants().OfType<JProperty>().Where(
                         item => string.Equals(item.Name, "file_path", StringComparison.OrdinalIgnoreCase)
                     ))
            {
                var value = property.Value.Type == JTokenType.String ? property.Value.Value<string>() : null;
                if (string.IsNullOrWhiteSpace(value))
                {
                    continue;
                }
                if (!IsPathWithin(value!, previewDirectory))
                {
                    continue;
                }
                property.Value = RelativePath(previewDirectory, value!);
            }
        }

        private static bool IsPathWithin(string path, string root)
        {
            var fullPath = Path.GetFullPath(path);
            var fullRoot = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)
                           + Path.DirectorySeparatorChar;
            return fullPath.StartsWith(fullRoot, StringComparison.OrdinalIgnoreCase);
        }

        private static string RelativePath(string root, string path)
        {
            var fullRoot = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)
                           + Path.DirectorySeparatorChar;
            var fullPath = Path.GetFullPath(path);
            if (!fullPath.StartsWith(fullRoot, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException("path is outside agent work directory");
            }
            return fullPath.Substring(fullRoot.Length).Replace('\\', '/');
        }

        private static string SafeFileName(string filename)
        {
            var safe = Path.GetFileName(filename);
            if (string.IsNullOrWhiteSpace(safe))
            {
                throw new InvalidDataException("source filename is empty");
            }
            return safe;
        }

        private static string LimitErrorMessage(string message)
        {
            const int maximumLength = 19000;
            return message.Length <= maximumLength
                ? message
                : message.Substring(0, maximumLength) + "\n...[truncated by Windows agent]";
        }

        private static void TryDeleteWorkDirectory(string workDirectory)
        {
            if (!Directory.Exists(workDirectory))
            {
                return;
            }
            try
            {
                Directory.Delete(workDirectory, recursive: true);
            }
            catch (Exception exception)
            {
                Console.Error.WriteLine(
                    $"agent_work_directory_cleanup_failed path={workDirectory}: {exception.Message}"
                );
            }
        }

        private sealed class AgentOptions
        {
            public Uri ApiBaseUrl { get; private set; } = null!;
            public string ApiToken { get; private set; } = string.Empty;
            public string WorkerName { get; private set; } = string.Empty;
            public string Mode { get; private set; } = "all";
            public string SxNetDllPath { get; private set; } = string.Empty;
            public string? IcadExecutablePath { get; private set; }
            public int IcadStartupWaitSeconds { get; private set; }
            public bool ShutdownIcadIfAutostarted { get; private set; }
            public int PollSeconds { get; private set; }
            public int HeartbeatSeconds { get; private set; }
            public int ApiTimeoutSeconds { get; private set; }
            public string WorkRoot { get; private set; } = string.Empty;
            public bool Once { get; private set; }
            public bool KeepWorkFiles { get; private set; }

            public static AgentOptions From(IReadOnlyDictionary<string, string> options)
            {
                var apiBaseUrl = Required(options, "api-base-url", "DRAWING_METADATA_AGENT_API_BASE_URL");
                if (!Uri.TryCreate(EnsureTrailingSlash(apiBaseUrl), UriKind.Absolute, out var apiBaseUri)
                    || (apiBaseUri.Scheme != Uri.UriSchemeHttp && apiBaseUri.Scheme != Uri.UriSchemeHttps))
                {
                    throw new ArgumentException("api-base-url must be an absolute HTTP(S) URL");
                }

                var mode = Optional(options, "mode", "DRAWING_METADATA_AGENT_MODE") ?? "all";
                if (mode != "2d" && mode != "3d" && mode != "all")
                {
                    throw new ArgumentException("mode must be 2d, 3d, or all");
                }

                var workRoot = Optional(options, "work-root", "DRAWING_METADATA_AGENT_WORK_ROOT")
                               ?? Path.Combine(Path.GetTempPath(), "IcadExtractionAgent");
                var parsed = new AgentOptions
                {
                    ApiBaseUrl = apiBaseUri,
                    ApiToken = Required(options, "api-token", "DRAWING_METADATA_AGENT_TOKEN"),
                    WorkerName = Optional(options, "worker-name", "DRAWING_METADATA_AGENT_WORKER_NAME")
                                 ?? Environment.MachineName,
                    Mode = mode,
                    SxNetDllPath = Path.GetFullPath(
                        Required(options, "sxnet-dll-path", "DRAWING_METADATA_SXNET_DLL_PATH")
                    ),
                    IcadExecutablePath = Optional(
                        options,
                        "icad-executable-path",
                        "DRAWING_METADATA_ICAD_EXECUTABLE"
                    ),
                    IcadStartupWaitSeconds = PositiveInt(
                        options,
                        "icad-startup-wait-seconds",
                        "DRAWING_METADATA_ICAD_STARTUP_WAIT_SECONDS",
                        8
                    ),
                    ShutdownIcadIfAutostarted = Boolean(
                        options,
                        "shutdown-icad-if-autostarted",
                        "DRAWING_METADATA_ICAD_SHUTDOWN_IF_AUTOSTARTED",
                        true
                    ),
                    PollSeconds = PositiveInt(
                        options,
                        "poll-seconds",
                        "DRAWING_METADATA_AGENT_POLL_SECONDS",
                        5
                    ),
                    HeartbeatSeconds = PositiveInt(
                        options,
                        "heartbeat-seconds",
                        "DRAWING_METADATA_AGENT_HEARTBEAT_SECONDS",
                        10
                    ),
                    ApiTimeoutSeconds = PositiveInt(
                        options,
                        "api-timeout-seconds",
                        "DRAWING_METADATA_AGENT_API_TIMEOUT_SECONDS",
                        120
                    ),
                    WorkRoot = Path.GetFullPath(workRoot),
                    Once = Boolean(options, "once", "DRAWING_METADATA_AGENT_ONCE", false),
                    KeepWorkFiles = Boolean(
                        options,
                        "keep-work-files",
                        "DRAWING_METADATA_AGENT_KEEP_WORK_FILES",
                        false
                    ),
                };

                if (!File.Exists(parsed.SxNetDllPath))
                {
                    throw new FileNotFoundException("sxnet.dll is missing", parsed.SxNetDllPath);
                }
                if (!string.IsNullOrWhiteSpace(parsed.IcadExecutablePath))
                {
                    parsed.IcadExecutablePath = Path.GetFullPath(parsed.IcadExecutablePath);
                    if (!File.Exists(parsed.IcadExecutablePath))
                    {
                        throw new FileNotFoundException("icad.exe is missing", parsed.IcadExecutablePath);
                    }
                }
                Directory.CreateDirectory(parsed.WorkRoot);
                return parsed;
            }

            private static string Required(
                IReadOnlyDictionary<string, string> options,
                string optionName,
                string environmentName
            )
            {
                var value = Optional(options, optionName, environmentName);
                if (string.IsNullOrWhiteSpace(value))
                {
                    throw new ArgumentException($"{optionName} is required (or set {environmentName})");
                }
                return value!;
            }

            private static string? Optional(
                IReadOnlyDictionary<string, string> options,
                string optionName,
                string environmentName
            )
            {
                if (options.TryGetValue(optionName, out var optionValue)
                    && !string.IsNullOrWhiteSpace(optionValue))
                {
                    return optionValue;
                }
                var environmentValue = Environment.GetEnvironmentVariable(environmentName);
                return string.IsNullOrWhiteSpace(environmentValue) ? null : environmentValue;
            }

            private static int PositiveInt(
                IReadOnlyDictionary<string, string> options,
                string optionName,
                string environmentName,
                int defaultValue
            )
            {
                var value = Optional(options, optionName, environmentName);
                if (value == null)
                {
                    return defaultValue;
                }
                if (!int.TryParse(value, out var parsed) || parsed <= 0)
                {
                    throw new ArgumentException($"{optionName} must be a positive integer");
                }
                return parsed;
            }

            private static bool Boolean(
                IReadOnlyDictionary<string, string> options,
                string optionName,
                string environmentName,
                bool defaultValue
            )
            {
                var value = Optional(options, optionName, environmentName);
                if (value == null)
                {
                    return defaultValue;
                }
                if (!bool.TryParse(value, out var parsed))
                {
                    throw new ArgumentException($"{optionName} must be boolean");
                }
                return parsed;
            }

            private static string EnsureTrailingSlash(string value)
            {
                return value.EndsWith("/", StringComparison.Ordinal) ? value : value + "/";
            }
        }

        private sealed class AgentJob
        {
            [JsonProperty("jobId")]
            public string JobId { get; set; } = string.Empty;

            [JsonProperty("extractionMode")]
            public string ExtractionMode { get; set; } = string.Empty;

            [JsonProperty("extractionProfile")]
            public string ExtractionProfile { get; set; } = "default";

            [JsonProperty("extractionOptions")]
            public JObject ExtractionOptions { get; set; } = new JObject();

            [JsonProperty("source")]
            public AgentSource Source { get; set; } = new AgentSource();

            [JsonProperty("preview")]
            public AgentPreview Preview { get; set; } = new AgentPreview();
        }

        private sealed class AgentSource
        {
            [JsonProperty("path")]
            public string Path { get; set; } = string.Empty;

            [JsonProperty("filename")]
            public string Filename { get; set; } = string.Empty;

            [JsonProperty("sha256")]
            public string? Sha256 { get; set; }

            [JsonProperty("downloadUrl")]
            public string DownloadUrl { get; set; } = string.Empty;

            [JsonProperty("downloadAvailable")]
            public bool DownloadAvailable { get; set; }
        }

        private sealed class AgentPreview
        {
            [JsonProperty("baseUrl")]
            public string BaseUrl { get; set; } = string.Empty;
        }
    }
}
