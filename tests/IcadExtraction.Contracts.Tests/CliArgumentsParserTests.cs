// このファイルは、Runnerへ渡すコマンド名とオプションの解析規則を検証する。
// テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
// 外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
using System;
using IcadExtraction.Contracts;
using Xunit;

namespace IcadExtraction.Contracts.Tests
{
    /// <summary>
    /// Runnerへ渡すコマンド名とオプションの解析規則を検証する。
    /// </summary>
    public sealed class CliArgumentsParserTests
    {
        [Fact]
        public void Parse_ParsesOptions()
        {
            var command = CliArgumentsParser.Parse(new[]
            {
                "extract",
                "--input-path", @"C:\temp\sample.icd",
                "--source-kind", "3d",
                "--output-path", @"C:\temp\sample.json",
            });

            Assert.Equal("extract", command.CommandName);
            Assert.Equal("3d", command.Options["source-kind"]);
        }

        [Fact]
        public void Parse_PreservesExtractionConditionOptions()
        {
            var command = CliArgumentsParser.Parse(new[]
            {
                "extract",
                "--input-path", @"C:\temp\sample.icd",
                "--source-kind", "2d",
                "--output-path", @"C:\temp\sample.json",
                "--extraction-profile", "2d_all_views_layers_print_frame",
                "--extraction-options-json", "{\"scanAllViews\":true}",
            });

            Assert.Equal("2d_all_views_layers_print_frame", command.Options["extraction-profile"]);
            Assert.Equal("{\"scanAllViews\":true}", command.Options["extraction-options-json"]);
        }

        [Fact]
        public void Parse_ThrowsWhenOptionValueIsMissing()
        {
            var exception = Assert.Throws<ArgumentException>(() => CliArgumentsParser.Parse(new[] { "extract", "--input-path" }));
            Assert.Contains("value is missing", exception.Message);
        }
    }
}
