using System.Collections.Generic;
using IcadExtraction.SxNet;
using Xunit;

namespace IcadExtraction.SxNet.Tests
{
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
