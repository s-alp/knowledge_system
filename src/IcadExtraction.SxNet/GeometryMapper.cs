using System.Collections.Generic;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    public sealed class GeometryMapper
    {
        public RawExtract2DPayload Map(IEnumerable<object> geometries, IList<WarningPayload> warnings)
        {
            var payload = new RawExtract2DPayload();
            foreach (var geometry in geometries)
            {
                var typeName = geometry.GetType().Name;
                switch (typeName)
                {
                    case "SxGeomText":
                        payload.Texts.Add(MapText(geometry, "text"));
                        break;
                    case "SxGeomLabel":
                        payload.Texts.Add(MapText(geometry, "label"));
                        break;
                    case "SxGeomLengthDim":
                    case "SxGeomAngDim":
                    case "SxGeomDiaDim":
                    case "SxGeomChamDim":
                    case "SxGeomArcLengDim":
                    case "SxGeomAplDim":
                        payload.Dimensions.Add(MapDimension(geometry));
                        break;
                    case "SxGeomLine2D":
                    case "SxGeomArc2D":
                    case "SxGeomCircle2D":
                        payload.GeometryPrimitives.Add(MapPrimitive(geometry));
                        break;
                    case "SxGeomWeld":
                        payload.WeldNotes.Add(new WeldNotePayload { Text = ReflectionHelpers.BuildSummaryText(geometry) });
                        break;
                    case "SxGeomBalloon":
                        payload.Balloons.Add(new BalloonPayload { Text = ReflectionHelpers.BuildSummaryText(geometry) });
                        break;
                    case "SxGeomTol":
                        payload.Tolerances.Add(new TolerancePayload { Text = ReflectionHelpers.BuildSummaryText(geometry) });
                        break;
                    default:
                        warnings.Add(new WarningPayload
                        {
                            Code = "unsupported_geometry",
                            Message = $"Unhandled geometry type: {typeName}",
                        });
                        break;
                }
            }

            return payload;
        }

        private static TextPayload MapText(object geometry, string sourceType)
        {
            var textLines = ReflectionHelpers.ExtractStringList(geometry, "txt");
            return new TextPayload
            {
                TextLines = textLines,
                LineCount = ReflectionHelpers.GetInt(geometry, "text_line_num"),
                SourceType = sourceType,
                JoinedText = textLines.Count == 0 ? null : string.Join(" ", textLines),
            };
        }

        private static DimensionPayload MapDimension(object geometry)
        {
            var dimensionInfo = ReflectionHelpers.GetMemberValue(geometry, "diminfo") ?? geometry;
            return new DimensionPayload
            {
                Value1 = ReflectionHelpers.GetString(dimensionInfo, "value_1"),
                Value2 = ReflectionHelpers.GetString(dimensionInfo, "value_2"),
                FrontWord = ReflectionHelpers.GetString(dimensionInfo, "front_word"),
                BackWord = ReflectionHelpers.GetString(dimensionInfo, "back_word"),
                UpperTol = ReflectionHelpers.GetString(dimensionInfo, "upper_tol"),
                LowerTol = ReflectionHelpers.GetString(dimensionInfo, "lower_tol"),
                Mark2 = ReflectionHelpers.GetString(dimensionInfo, "mark_2"),
                Mark3 = ReflectionHelpers.GetString(dimensionInfo, "mark_3"),
                Summary = ReflectionHelpers.BuildSummaryText(dimensionInfo),
            };
        }

        private static GeometryPrimitivePayload MapPrimitive(object geometry)
        {
            return new GeometryPrimitivePayload
            {
                GeometryType = geometry.GetType().Name,
                Summary = ReflectionHelpers.BuildSummaryText(geometry),
            };
        }
    }
}
