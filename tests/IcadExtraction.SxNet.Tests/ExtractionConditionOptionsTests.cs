// このファイルは、抽出条件の既定値とJSON上書きが想定どおりに合成されることを検証する。
// テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
// 外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
using System.Collections.Generic;
using IcadExtraction.SxNet;
using Xunit;

namespace IcadExtraction.SxNet.Tests
{
    /// <summary>
    /// 抽出条件の既定値とJSON上書きが想定どおりに合成されることを検証する。
    /// </summary>
    public sealed class ExtractionConditionOptionsTests
    {
        [Fact]
        public void FromDictionary_ParsesBooleanOptionsAndKeepsDefaults()
        {
            var options = ExtractionConditionOptions.FromDictionary(new Dictionary<string, object>
            {
                ["scanAllViews"] = false,
                ["scanAllLayers"] = "false",
                ["scanPartExtendedInfo"] = "true",
                ["scanMassProperties"] = false,
            });

            Assert.False(options.ScanAllViews);
            Assert.False(options.ScanAllLayers);
            Assert.True(options.ClassifyPrintFrame);
            Assert.True(options.ScanPartExtendedInfo);
            Assert.False(options.ScanMassProperties);
        }

        [Fact]
        public void ToDiagnostics_IncludesProfileAndOptionKeys()
        {
            var options = new ExtractionConditionOptions { ScanPartMaterials = false };

            var diagnostics = options.ToDiagnostics(
                "3d",
                "3d_part_tree_only",
                new[] { "scanPartMaterials" }
            );

            Assert.Equal("extract_condition_diagnostics.v1", diagnostics["schemaVersion"]);
            Assert.Equal("3d", diagnostics["sourceKind"]);
            Assert.Equal("3d_part_tree_only", diagnostics["extractionProfile"]);
            Assert.False((bool)diagnostics["scanPartMaterials"]);
            Assert.Equal(new List<string> { "scanPartMaterials" }, Assert.IsType<List<string>>(diagnostics["optionKeys"]));
        }
    }
}
