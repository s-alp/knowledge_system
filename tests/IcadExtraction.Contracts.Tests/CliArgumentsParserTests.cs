using System;
using IcadExtraction.Contracts;
using Xunit;

namespace IcadExtraction.Contracts.Tests
{
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
