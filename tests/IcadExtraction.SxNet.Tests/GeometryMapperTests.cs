using System.Collections.Generic;
using IcadExtraction.Contracts;
using IcadExtraction.SxNet;
using Xunit;

namespace IcadExtraction.SxNet.Tests
{
    public sealed class GeometryMapperTests
    {
        [Fact]
        public void Map_MapsKnownGeometryTypesAndWarnings()
        {
            var warnings = new List<WarningPayload>();
            var geometries = new object[]
            {
                new SxGeomText { txt = new[] { "澁谷工業", "SES" }, text_line_num = 2 },
                new SxGeomLabel { txt = new[] { "ロボット" }, text_line_num = 1 },
                new SxGeomLengthDim { diminfo = new DimInfo { value_1 = "100", mark_2 = "M5" } },
                new SxGeomLine2D { x1 = 0.0, y1 = 1.0, x2 = 2.0, y2 = 3.0 },
                new SxGeomWeld { atr_weld = "WELD-A" },
                new SxGeomBalloon { txt = "B1" },
                new SxGeomTol { atr_geotol = "±0.1" },
                new UnknownGeometry(),
            };

            var payload = new GeometryMapper().Map(geometries, warnings);
            Assert.Equal(2, payload.Texts.Count);
            Assert.Single(payload.Dimensions);
            Assert.Single(payload.GeometryPrimitives);
            Assert.Single(payload.WeldNotes);
            Assert.Single(payload.Balloons);
            Assert.Single(payload.Tolerances);
            Assert.Single(warnings);
        }

        public sealed class SxGeomText
        {
            public string[]? txt;
            public int text_line_num;
        }

        public sealed class SxGeomLabel
        {
            public string[]? txt;
            public int text_line_num;
        }

        public sealed class SxGeomLengthDim
        {
            public DimInfo? diminfo;
        }

        public sealed class DimInfo
        {
            public string? value_1;
            public string? mark_2;
        }

        public sealed class SxGeomWeld
        {
            public string? atr_weld;
        }

        public sealed class SxGeomLine2D
        {
            public double x1;
            public double y1;
            public double x2;
            public double y2;
        }

        public sealed class SxGeomBalloon
        {
            public string? txt;
        }

        public sealed class SxGeomTol
        {
            public string? atr_geotol;
        }

        public sealed class UnknownGeometry
        {
        }
    }
}
