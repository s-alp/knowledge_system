using System;
using IcadExtraction.Runner;
using Xunit;

namespace IcadExtraction.Runner.Tests
{
    public sealed class RunnerSmokeTests
    {
        [Fact]
        public void Main_ReturnsErrorForUnsupportedCommand()
        {
            var result = Program.Main(new[] { "unknown" });
            Assert.Equal(1, result);
        }
    }
}
