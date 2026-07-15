using System.Collections.Generic;
using IcadExtraction.Contracts;
using Xunit;

namespace IcadExtraction.SxNet.Tests
{
    public sealed class PrintAreaClassifierTests
    {
        [Fact]
        public void Resolve_ReturnsFrameNoForContainingPrintFrame()
        {
            var frames = new List<PrintFramePayload>
            {
                new PrintFramePayload { No = 2, RangeMinX = 100, RangeMinY = 0, RangeMaxX = 200, RangeMaxY = 100 },
                new PrintFramePayload { No = 1, RangeMinX = 0, RangeMinY = 0, RangeMaxX = 50, RangeMaxY = 50 },
            };

            var result = PrintAreaClassifier.Resolve(frames, 120, 40);

            Assert.True(result.InsidePrintArea);
            Assert.Equal(2, result.PrintFrameNo);
        }

        [Fact]
        public void Resolve_ReturnsOutsideWhenPointIsOutsideAllFrames()
        {
            var frames = new List<PrintFramePayload>
            {
                new PrintFramePayload { No = 1, RangeMinX = 0, RangeMinY = 0, RangeMaxX = 50, RangeMaxY = 50 },
            };

            var result = PrintAreaClassifier.Resolve(frames, 60, 40);

            Assert.False(result.InsidePrintArea);
            Assert.Null(result.PrintFrameNo);
        }

        [Fact]
        public void Resolve_ReturnsUnknownWhenPointOrFramesAreIncomplete()
        {
            var resultWithoutPoint = PrintAreaClassifier.Resolve(new List<PrintFramePayload>(), null, 40);
            var resultWithoutUsableFrame = PrintAreaClassifier.Resolve(
                new List<PrintFramePayload> { new PrintFramePayload { No = 1, RangeMinX = 0 } },
                10,
                10);

            Assert.Null(resultWithoutPoint.InsidePrintArea);
            Assert.Null(resultWithoutPoint.PrintFrameNo);
            Assert.Null(resultWithoutUsableFrame.InsidePrintArea);
            Assert.Null(resultWithoutUsableFrame.PrintFrameNo);
        }
    }
}
