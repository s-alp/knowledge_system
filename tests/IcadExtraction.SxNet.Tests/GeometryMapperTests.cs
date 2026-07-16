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
                new SxGeomPoint2D { pnt = new SxPos { x = 34.0, y = 35.0, z = 0.0 } },
                new SxGeomSpline2D { pos = new SxPos { x = 5.0, y = 6.0, z = 0.0 }, vec_list = new[] { new SxVec(), new SxVec() } },
                new SxGeomElparc2D { cp = new SxPos { x = 7.0, y = 8.0, z = 0.0 }, radius1 = 11.0, radius2 = 4.0, sang = 10.0, eang = 90.0 },
                new SxGeomSmark { pnt = new SxPos { x = 9.0, y = 10.0, z = 0.0 }, val1 = "Ra 6.3" },
                new SxGeomCutLine { pnt1 = new SxPos { x = 1.0, y = 2.0, z = 0.0 }, pnt2 = new SxPos { x = 3.0, y = 4.0, z = 0.0 } },
                new SxGeomSymbol { pnt = new SxPos { x = 14.0, y = 15.0, z = 0.0 }, name = "DETAIL-A" },
                new SxGeomArrow { pnt = new SxPos { x = 15.0, y = 16.0, z = 0.0 }, name = "矢印" },
                new SxGeomArrowView { pnt = new SxPos { x = 16.0, y = 17.0, z = 0.0 }, name = "A" },
                new SxGeomOtherDraft { pnt = new SxPos { x = 18.0, y = 19.0, z = 0.0 }, name = "補助図形" },
                new SxGeomFinishMark { pnt = new SxPos { x = 12.0, y = 13.0, z = 0.0 }, mark_type = 3, side_leng = 4.5, width = 2, color = 7 },
                new SxGeomWeld { atr_weld = "WELD-A" },
                new SxGeomBalloon { txt = "B1" },
                new SxGeomTol { atr_geotol = "±0.1" },
                new SxEntRPart
                {
                    Detail = new InfRPart
                    {
                        name = "BASE-PLATE",
                        comment = "実像部品",
                        part3d_name = "BASE-3D",
                        ref_model_name = "BASE_MODEL",
                        ref_vs_name = "VS-A",
                        is_mirror = true,
                        angle = 90.0,
                        pos = new SxPos { x = 40.0, y = 41.0, z = 0.0 },
                    },
                },
                new SxEntRefer
                {
                    Detail = new InfRefer
                    {
                        kind = 1,
                        is_empty = false,
                        is_mirror = false,
                        ref_model_name = "CHILD_MODEL",
                        ref_vs_name = "VS-B",
                        scale = 0.5,
                        angle = 15.0,
                        pos = new SxPos { x = 50.0, y = 51.0, z = 0.0 },
                    },
                },
                new UnknownGeometry(),
            };

            var payload = new GeometryMapper().Map(geometries, warnings);
            Assert.Equal(2, payload.Texts.Count);
            Assert.Single(payload.Dimensions);
            Assert.Equal(12, payload.GeometryPrimitives.Count);
            Assert.Single(payload.WeldNotes);
            Assert.Single(payload.Balloons);
            Assert.Single(payload.Tolerances);
            Assert.Equal(2, payload.ReferencedParts.Count);
            Assert.Single(warnings);
            Assert.Equal(10.5, payload.Texts[0].PositionX);
            Assert.Equal(20.25, payload.Texts[0].PositionY);
            Assert.Equal(-1.0, payload.Dimensions[0].PositionX);
            Assert.Equal(2.0, payload.Dimensions[0].PositionY);
            Assert.Equal(2.0, payload.GeometryPrimitives[0].EndX);
            Assert.Equal(30.0, payload.GeometryPrimitives[1].PositionX);
            Assert.Equal(33.0, payload.GeometryPrimitives[1].EndY);
            Assert.Equal("SxGeomPoint2D", payload.GeometryPrimitives[2].GeometryType);
            Assert.Equal(34.0, payload.GeometryPrimitives[2].PositionX);
            Assert.Equal(5.0, payload.GeometryPrimitives[3].PositionX);
            Assert.Equal(3, payload.GeometryPrimitives[3].PointCount);
            Assert.Equal(7.0, payload.GeometryPrimitives[4].CenterX);
            Assert.Equal(11.0, payload.GeometryPrimitives[4].Radius1);
            Assert.Equal(9.0, payload.GeometryPrimitives[5].PositionX);
            Assert.Equal(3.0, payload.GeometryPrimitives[6].EndX);
            Assert.Equal("SxGeomSymbol", payload.GeometryPrimitives[7].GeometryType);
            Assert.Equal(14.0, payload.GeometryPrimitives[7].PositionX);
            Assert.Equal("SxGeomArrow", payload.GeometryPrimitives[8].GeometryType);
            Assert.Equal(16.0, payload.GeometryPrimitives[8].PositionY);
            Assert.Equal("SxGeomArrowView", payload.GeometryPrimitives[9].GeometryType);
            Assert.Equal(17.0, payload.GeometryPrimitives[9].PositionY);
            Assert.Equal("SxGeomOtherDraft", payload.GeometryPrimitives[10].GeometryType);
            Assert.Equal(19.0, payload.GeometryPrimitives[10].PositionY);
            Assert.Equal("SxGeomFinishMark", payload.GeometryPrimitives[11].GeometryType);
            Assert.Equal(3, payload.GeometryPrimitives[11].MarkType);
            Assert.Equal(4.5, payload.GeometryPrimitives[11].SideLength);
            Assert.Equal(2, payload.GeometryPrimitives[11].Width);
            Assert.Equal(7, payload.GeometryPrimitives[11].Color);
            Assert.Equal("rpart", payload.ReferencedParts[0].EntityType);
            Assert.Equal("BASE-PLATE", payload.ReferencedParts[0].Name);
            Assert.Equal("BASE-3D", payload.ReferencedParts[0].Part3DName);
            Assert.Equal("BASE_MODEL", payload.ReferencedParts[0].RefModelName);
            Assert.True(payload.ReferencedParts[0].IsMirror);
            Assert.Equal(40.0, payload.ReferencedParts[0].PositionX);
            Assert.Equal("refer", payload.ReferencedParts[1].EntityType);
            Assert.Equal(1, payload.ReferencedParts[1].Kind);
            Assert.Equal("CHILD_MODEL", payload.ReferencedParts[1].RefModelName);
            Assert.Equal(0.5, payload.ReferencedParts[1].Scale);
            Assert.Equal(51.0, payload.ReferencedParts[1].PositionY);
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

        public sealed class SxGeomPoint2D
        {
            public SxPos? pnt;
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

        public sealed class SxGeomSymbol
        {
            public SxPos? pnt;
            public string? name;
        }

        public sealed class SxGeomArrowView
        {
            public SxPos? pnt;
            public string? name;
        }

        public sealed class SxGeomArrow
        {
            public SxPos? pnt;
            public string? name;
        }

        public sealed class SxGeomOtherDraft
        {
            public SxPos? pnt;
            public string? name;
        }

        public sealed class SxGeomFinishMark
        {
            public SxPos? pnt;
            public int mark_type;
            public double side_leng;
            public int width;
            public int color;
        }

        public sealed class SxGeomBalloon
        {
            public string? txt;
        }

        public sealed class SxGeomTol
        {
            public string? atr_geotol;
        }

        public sealed class SxEntRPart
        {
            public InfRPart? Detail { get; set; }

            public InfRPart? getInfDetail()
            {
                return Detail;
            }
        }

        public sealed class InfRPart
        {
            public string? name;
            public string? comment;
            public string? part3d_name;
            public string? ref_model_name;
            public string? ref_vs_name;
            public bool is_mirror;
            public double angle;
            public SxPos? pos;
        }

        public sealed class SxEntRefer
        {
            public InfRefer? Detail { get; set; }

            public InfRefer? getInfDetail()
            {
                return Detail;
            }
        }

        public sealed class InfRefer
        {
            public int kind;
            public bool is_empty;
            public bool is_mirror;
            public string? ref_model_name;
            public string? ref_vs_name;
            public double scale;
            public double angle;
            public SxPos? pos;
        }

        public sealed class UnknownGeometry
        {
        }
    }
}
