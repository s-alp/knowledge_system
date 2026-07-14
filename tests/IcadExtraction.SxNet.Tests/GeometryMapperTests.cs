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
                new SxGeomText { txt = new[] { "澁谷工業", "SES" }, text_line_num = 2, pnt = new SxPos { x = 10.5, y = 20.25, z = 0.0 } },
                new SxGeomLabel { txt = new[] { "ロボット" }, text_line_num = 1 },
                new SxGeomLengthDim { diminfo = new DimInfo { value_1 = "100", mark_2 = "M5" }, pnt1 = new SxPos { x = -1.0, y = 2.0, z = 0.0 } },
                new SxGeomLine2D { x1 = 0.0, y1 = 1.0, x2 = 2.0, y2 = 3.0 },
                new SxGeomLine2D { pnt1 = new SxPos { x = 30.0, y = 31.0, z = 0.0 }, pnt2 = new SxPos { x = 32.0, y = 33.0, z = 0.0 } },
                new SxGeomSpline2D { pos = new SxPos { x = 5.0, y = 6.0, z = 0.0 }, vec_list = new[] { new SxVec(), new SxVec() } },
                new SxGeomElparc2D { cp = new SxPos { x = 7.0, y = 8.0, z = 0.0 }, radius1 = 11.0, radius2 = 4.0, sang = 10.0, eang = 90.0 },
                new SxGeomSmark { pnt = new SxPos { x = 9.0, y = 10.0, z = 0.0 }, val1 = "Ra 6.3" },
                new SxGeomCutLine { pnt1 = new SxPos { x = 1.0, y = 2.0, z = 0.0 }, pnt2 = new SxPos { x = 3.0, y = 4.0, z = 0.0 } },
                new SxGeomWeld { atr_weld = "WELD-A" },
                new SxGeomBalloon { txt = "B1" },
                new SxGeomTol { atr_geotol = "±0.1" },
                new UnknownGeometry(),
            };

            var payload = new GeometryMapper().Map(geometries, warnings);
            Assert.Equal(2, payload.Texts.Count);
            Assert.Single(payload.Dimensions);
            Assert.Equal(6, payload.GeometryPrimitives.Count);
            Assert.Single(payload.WeldNotes);
            Assert.Single(payload.Balloons);
            Assert.Single(payload.Tolerances);
            Assert.Single(warnings);
            Assert.Equal(10.5, payload.Texts[0].PositionX);
            Assert.Equal(20.25, payload.Texts[0].PositionY);
            Assert.Equal(-1.0, payload.Dimensions[0].PositionX);
            Assert.Equal(2.0, payload.Dimensions[0].PositionY);
            Assert.Equal(2.0, payload.GeometryPrimitives[0].EndX);
            Assert.Equal(30.0, payload.GeometryPrimitives[1].PositionX);
            Assert.Equal(33.0, payload.GeometryPrimitives[1].EndY);
            Assert.Equal(5.0, payload.GeometryPrimitives[2].PositionX);
            Assert.Equal(3, payload.GeometryPrimitives[2].PointCount);
            Assert.Equal(7.0, payload.GeometryPrimitives[3].CenterX);
            Assert.Equal(11.0, payload.GeometryPrimitives[3].Radius1);
            Assert.Equal(9.0, payload.GeometryPrimitives[4].PositionX);
            Assert.Equal(3.0, payload.GeometryPrimitives[5].EndX);
        }

        public sealed class SxPos
        {
            public double x;
            public double y;
            public double z;
        }

        public sealed class SxVec
        {
            public double x;
            public double y;
            public double z;
        }

        public sealed class SxGeomText
        {
            public string[]? txt;
            public int text_line_num;
            public SxPos? pnt;
        }

        public sealed class SxGeomLabel
        {
            public string[]? txt;
            public int text_line_num;
        }

        public sealed class SxGeomLengthDim
        {
            public DimInfo? diminfo;
            public SxPos? pnt1;
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
            public double? x1;
            public double? y1;
            public double? x2;
            public double? y2;
            public SxPos? pnt1;
            public SxPos? pnt2;
        }

        public sealed class SxGeomSpline2D
        {
            public SxPos? pos;
            public SxVec[]? vec_list;
        }

        public sealed class SxGeomElparc2D
        {
            public SxPos? cp;
            public double radius1;
            public double radius2;
            public double sang;
            public double eang;
        }

        public sealed class SxGeomSmark
        {
            public SxPos? pnt;
            public string? val1;
        }

        public sealed class SxGeomCutLine
        {
            public SxPos? pnt1;
            public SxPos? pnt2;
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
