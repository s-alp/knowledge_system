using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using IcadExtraction.Contracts;
using IcadExtraction.SxNet;
using Newtonsoft.Json;
using Newtonsoft.Json.Serialization;

namespace IcadExtraction.Runner
{
    public static class Program
    {
        private const int WindowsFilenameLimit = 255;
        private const int WindowsLegacyPathLimit = 259;

        public static int Main(string[] args)
        {
            try
            {
                var command = CliArgumentsParser.Parse(args);
                switch (command.CommandName)
                {
                    case "extract":
                        return RunExtract(command);
                    case "detect":
                        return RunDetect(command);
                    case "probe-2d-print":
                        return RunProbe2DPrint(command);
                    case "cancel":
                        return RunCancel(command);
                    case "clear-command":
                        return RunClearCommand(command);
                    case "shutdown-icad":
                        return RunShutdownIcad(command);
                    case "self-check":
                        return RunSelfCheck(command);
                    default:
                        throw new ArgumentException($"unsupported command: {command.CommandName}");
                }
            }
            catch (Exception exception)
            {
                WriteExceptionDiagnostics(exception);
                return 1;
            }
        }

        private static void WriteExceptionDiagnostics(Exception exception)
        {
            var depth = 0;
            for (var current = exception; current != null; current = current.InnerException)
            {
                Console.Error.WriteLine($"error[{depth}].type={current.GetType().FullName}");
                Console.Error.WriteLine($"error[{depth}].message={current.Message}");
                depth++;
            }

            Console.Error.WriteLine("error.stack_trace_begin");
            Console.Error.WriteLine(exception);
            Console.Error.WriteLine("error.stack_trace_end");
        }

        private static int RunExtract(CliCommand command)
        {
            var inputPath = RequireOption(command, "input-path");
            ValidateIcadInputPathForSxNet(inputPath);
            var sourceKind = RequireOption(command, "source-kind");
            var outputPath = RequireOption(command, "output-path");
            var sxnetDllPath = RequireOption(command, "sxnet-dll-path");
            var icadExecutablePath = OptionalOption(command, "icad-executable-path");
            var icadStartupWaitSeconds = OptionalIntOption(command, "icad-startup-wait-seconds", 8);
            var shutdownIfAutostarted = OptionalBoolOption(command, "shutdown-icad-if-autostarted", true);
            var extractionProfile = OptionalOption(command, "extraction-profile") ?? "default";
            var extractionOptions = OptionalJsonObjectOption(command, "extraction-options-json");
            var conditionOptions = ExtractionConditionOptions.FromDictionary(extractionOptions);
            var previewAssetOptions = BuildPreviewAssetOptions(command);

            var stopwatch = Stopwatch.StartNew();
            using var icadLease = IcadProcessStarter.EnsureRunning(
                icadExecutablePath,
                icadStartupWaitSeconds,
                shutdownIfAutostarted
            );
            var autostartWarning = icadLease.StartupWarning;
            ExtractionEnvelope envelope;
            if (string.Equals(sourceKind, "3d", StringComparison.OrdinalIgnoreCase))
            {
                envelope = new Icad3DExtractor().Extract(sxnetDllPath, inputPath, conditionOptions, previewAssetOptions);
            }
            else if (string.Equals(sourceKind, "2d", StringComparison.OrdinalIgnoreCase))
            {
                envelope = new Icad2DExtractor().Extract(sxnetDllPath, inputPath, conditionOptions, previewAssetOptions);
            }
            else
            {
                throw new ArgumentException($"unsupported source-kind: {sourceKind}");
            }

            envelope.ExtractorVersion = SchemaVersions.SchemaVersion;
            envelope.SourceFile = BuildSourceFilePayload(inputPath);
            envelope.ElapsedMs = stopwatch.ElapsedMilliseconds;
            envelope.ExtractionProfile = extractionProfile;
            envelope.ExtractionOptions = extractionOptions;
            envelope.ConditionDiagnostics = conditionOptions.ToDiagnostics(sourceKind, extractionProfile, extractionOptions.Keys);
            if (autostartWarning != null)
            {
                envelope.Warnings.Insert(0, autostartWarning);
            }

            Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
            var serializerSettings = new JsonSerializerSettings
            {
                ContractResolver = new DefaultContractResolver
                {
                    NamingStrategy = new SnakeCaseNamingStrategy(),
                },
                Formatting = Formatting.Indented,
                NullValueHandling = NullValueHandling.Include,
            };
            File.WriteAllText(outputPath, JsonConvert.SerializeObject(envelope, serializerSettings));
            return 0;
        }

        private static int RunSelfCheck(CliCommand command)
        {
            var sxnetDllPath = RequireOption(command, "sxnet-dll-path");
            var message = new SxNetRuntimeGuard().SelfCheck(sxnetDllPath);
            Console.WriteLine(message);
            return 0;
        }

        private static int RunCancel(CliCommand command)
        {
            var sxnetDllPath = RequireOption(command, "sxnet-dll-path");
            var sxnetPort = OptionalIntOption(command, "sxnet-port", 3999);
            new SxNetCommandController().Cancel(sxnetDllPath, sxnetPort);
            Console.WriteLine($"sxnet_cancel_requested port={sxnetPort}");
            return 0;
        }

        private static int RunClearCommand(CliCommand command)
        {
            var sxnetDllPath = RequireOption(command, "sxnet-dll-path");
            var sxnetPort = OptionalIntOption(command, "sxnet-port", 3999);
            var commandName = new SxNetCommandController().GetAndClearCommand(sxnetDllPath, sxnetPort);
            Console.WriteLine($"sxnet_command_cleared command={commandName}");
            return 0;
        }

        private static int RunShutdownIcad(CliCommand command)
        {
            var timeoutSeconds = OptionalIntOption(command, "timeout-seconds", 15);
            if (!IcadProcessStarter.TryCloseRunningWithoutSaving(timeoutSeconds))
            {
                throw new InvalidOperationException(
                    "ICADの安全な終了を完了できませんでした。強制終了は行っていません。"
                );
            }

            Console.WriteLine("icad_shutdown_without_save_completed");
            return 0;
        }

        private static int RunDetect(CliCommand command)
        {
            var inputPath = RequireOption(command, "input-path");
            ValidateIcadInputPathForSxNet(inputPath);
            var outputPath = RequireOption(command, "output-path");
            var sxnetDllPath = RequireOption(command, "sxnet-dll-path");
            var icadExecutablePath = OptionalOption(command, "icad-executable-path");
            var icadStartupWaitSeconds = OptionalIntOption(command, "icad-startup-wait-seconds", 8);
            var shutdownIfAutostarted = OptionalBoolOption(command, "shutdown-icad-if-autostarted", true);

            var stopwatch = Stopwatch.StartNew();
            using var icadLease = IcadProcessStarter.EnsureRunning(
                icadExecutablePath,
                icadStartupWaitSeconds,
                shutdownIfAutostarted
            );
            var envelope = new IcadPresenceDetector().Detect(sxnetDllPath, inputPath);
            envelope.ExtractorVersion = SchemaVersions.SchemaVersion;
            envelope.SourceFile = BuildSourceFilePayload(inputPath);
            envelope.ElapsedMs = stopwatch.ElapsedMilliseconds;
            if (icadLease.StartupWarning != null)
            {
                envelope.Warnings.Insert(0, icadLease.StartupWarning);
            }

            Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
            var serializerSettings = new JsonSerializerSettings
            {
                ContractResolver = new DefaultContractResolver
                {
                    NamingStrategy = new SnakeCaseNamingStrategy(),
                },
                Formatting = Formatting.Indented,
                NullValueHandling = NullValueHandling.Include,
            };
            File.WriteAllText(outputPath, JsonConvert.SerializeObject(envelope, serializerSettings));
            return 0;
        }

        private static int RunProbe2DPrint(CliCommand command)
        {
            var inputPath = RequireOption(command, "input-path");
            ValidateIcadInputPathForSxNet(inputPath);
            var outputPath = RequireOption(command, "output-path");
            var sxnetDllPath = RequireOption(command, "sxnet-dll-path");
            var icadExecutablePath = OptionalOption(command, "icad-executable-path");
            var icadStartupWaitSeconds = OptionalIntOption(command, "icad-startup-wait-seconds", 8);
            var shutdownIfAutostarted = OptionalBoolOption(command, "shutdown-icad-if-autostarted", true);

            var stopwatch = Stopwatch.StartNew();
            using var icadLease = IcadProcessStarter.EnsureRunning(
                icadExecutablePath,
                icadStartupWaitSeconds,
                shutdownIfAutostarted
            );
            var envelope = new Icad2DPrintProbe().Probe(sxnetDllPath, inputPath);
            envelope.ExtractorVersion = SchemaVersions.SchemaVersion;
            envelope.SourceFile = BuildSourceFilePayload(inputPath);
            envelope.ElapsedMs = stopwatch.ElapsedMilliseconds;
            if (icadLease.StartupWarning != null)
            {
                envelope.Warnings.Insert(0, icadLease.StartupWarning);
            }

            Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
            var serializerSettings = new JsonSerializerSettings
            {
                ContractResolver = new DefaultContractResolver
                {
                    NamingStrategy = new SnakeCaseNamingStrategy(),
                },
                Formatting = Formatting.Indented,
                NullValueHandling = NullValueHandling.Include,
            };
            File.WriteAllText(outputPath, JsonConvert.SerializeObject(envelope, serializerSettings));
            return 0;
        }

        private static SourceFilePayload BuildSourceFilePayload(string inputPath)
        {
            return new SourceFilePayload
            {
                FullPath = inputPath,
                DirectoryPath = Path.GetDirectoryName(inputPath),
                FileName = Path.GetFileName(inputPath),
                FileNameWithoutExtension = Path.GetFileNameWithoutExtension(inputPath),
                Extension = Path.GetExtension(inputPath),
            };
        }

        private static void ValidateIcadInputPathForSxNet(string inputPath)
        {
            var fullPath = Path.GetFullPath(inputPath);
            var fileName = Path.GetFileName(fullPath);
            if (fileName.Length > WindowsFilenameLimit)
            {
                throw new ArgumentException(
                    $"ICADファイル名が長すぎます。SXNETへ渡すファイル名は{WindowsFilenameLimit}文字以下にしてください。" +
                    $"現在の文字数: {fileName.Length}"
                );
            }

            if (fullPath.Length > WindowsLegacyPathLimit)
            {
                throw new ArgumentException(
                    $"ICADファイルのパスが長すぎます。SXNETへ渡すパスは{WindowsLegacyPathLimit}文字以下にしてください。" +
                    $"現在の文字数: {fullPath.Length}。SXNETで開く前に中断しています。短い作業フォルダへコピーして再登録してください。"
                );
            }

            if (!File.Exists(fullPath))
            {
                throw new FileNotFoundException("指定されたICADファイルが見つかりません。原本パスとネットワークドライブ接続を確認してください。", fullPath);
            }
        }

        private static PreviewAssetOptions BuildPreviewAssetOptions(CliCommand command)
        {
            var outputDirectory = OptionalOption(command, "preview-output-dir");
            return new PreviewAssetOptions
            {
                Enabled = !string.IsNullOrWhiteSpace(outputDirectory),
                OutputDirectory = outputDirectory,
                PublicBaseUrl = OptionalOption(command, "preview-public-base-url"),
                FileNamePrefix = OptionalOption(command, "preview-file-name-prefix"),
            };
        }

        private static string RequireOption(CliCommand command, string optionName)
        {
            if (!command.Options.TryGetValue(optionName, out var value) || string.IsNullOrWhiteSpace(value))
            {
                throw new ArgumentException($"{optionName} is required");
            }

            return value;
        }

        private static string? OptionalOption(CliCommand command, string optionName)
        {
            if (!command.Options.TryGetValue(optionName, out var value) || string.IsNullOrWhiteSpace(value))
            {
                return null;
            }

            return value;
        }

        private static int OptionalIntOption(CliCommand command, string optionName, int defaultValue)
        {
            var value = OptionalOption(command, optionName);
            if (value == null)
            {
                return defaultValue;
            }

            if (!int.TryParse(value, out var parsed))
            {
                throw new ArgumentException($"{optionName} must be integer");
            }

            return parsed;
        }

        private static bool OptionalBoolOption(CliCommand command, string optionName, bool defaultValue)
        {
            var value = OptionalOption(command, optionName);
            if (value == null)
            {
                return defaultValue;
            }

            if (bool.TryParse(value, out var parsed))
            {
                return parsed;
            }

            throw new ArgumentException($"{optionName} must be boolean");
        }

        private static Dictionary<string, object> OptionalJsonObjectOption(CliCommand command, string optionName)
        {
            var value = OptionalOption(command, optionName);
            if (value == null)
            {
                return new Dictionary<string, object>();
            }

            try
            {
                var parsed = JsonConvert.DeserializeObject<Dictionary<string, object>>(value);
                return parsed ?? new Dictionary<string, object>();
            }
            catch (JsonException exception)
            {
                throw new ArgumentException($"{optionName} must be JSON object: {exception.Message}", exception);
            }
        }
    }
}
