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
        public void Parse_ThrowsWhenOptionValueIsMissing()
        {
            var exception = Assert.Throws<ArgumentException>(() => CliArgumentsParser.Parse(new[] { "extract", "--input-path" }));
            Assert.Contains("value is missing", exception.Message);
        }
    }
}
