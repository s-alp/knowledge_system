using System;
using System.IO;
using IcadExtraction.Runner;
using Xunit;

namespace IcadExtraction.Runner.Tests
{
    public sealed class RunnerSmokeTests
    {
        [Fact]
        public void Main_ReturnsErrorForUnsupportedCommand()
        {
            var originalError = Console.Error;
            using var error = new StringWriter();
            Console.SetError(error);
            try
            {
                var result = Program.Main(new[] { "unknown" });
                Assert.Equal(1, result);
                Assert.Contains("error[0].type=System.ArgumentException", error.ToString());
                Assert.Contains("unsupported command: unknown", error.ToString());
                Assert.Contains("error.stack_trace_begin", error.ToString());
            }
            finally
            {
                Console.SetError(originalError);
            }
        }
    }
}
