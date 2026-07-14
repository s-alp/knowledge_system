using System.Collections.Generic;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    internal sealed class GeometrySourceItem
    {
        public GeometrySourceItem(object geometry, int? layerNo)
        {
            Geometry = geometry;
            LayerNo = layerNo;
        }

        public object Geometry { get; }
        public int? LayerNo { get; }
    }

    public sealed class GeometryMapper
    {
        public RawExtract2DPayload Map(IEnumerable<object> geometries, IList<WarningPayload> warnings, string? viewName = null)
        {
            var sourceItems = new List<GeometrySourceItem>();
            foreach (var geometry in geometries)
            {
                sourceItems.Add(new GeometrySourceItem(geometry, null));
            }

            return Map(sourceItems, warnings, viewName);
        }

        internal RawExtract2DPayload Map(IEnumerable<GeometrySourceItem> sourceItems, IList<WarningPayload> warnings, string? viewName = null)
        {
            var payload = new RawExtract2DPayload();
            foreach (var sourceItem in sourceItems)
            {
                var geometry = sourceItem.Geometry;
                var typeName = geometry.GetType().Name;
                switch (typeName)
                {
                    case "SxGeomText":
                        payload.Texts.Add(MapText(geometry, "text", viewName, sourceItem.LayerNo));
                        break;
                    case "SxGeomLabel":
                        payload.Texts.Add(MapText(geometry, "label", viewName, sourceItem.LayerNo));
                        break;
                    case "SxGeomLengthDim":
                    case "SxGeomAngDim":
                    case "SxGeomDiaDim":
                    case "SxGeomChamDim":
                    case "SxGeomArcLengDim":
                    case "SxGeomAplDim":
                        payload.Dimensions.Add(MapDimension(geometry, viewName, sourceItem.LayerNo));
                        break;
                    case "SxGeomLine2D":
                    case "SxGeomArc2D":
                    case "SxGeomCircle2D":
                        payload.GeometryPrimitives.Add(MapPrimitive(geometry, viewName, sourceItem.LayerNo));
                        break;
                    case "SxGeomWeld":
                        payload.WeldNotes.Add(new WeldNotePayload { ViewName = viewName, LayerNo = sourceItem.LayerNo, Text = ReflectionHelpers.BuildSummaryText(geometry) });
                        break;
                    case "SxGeomBalloon":
                        payload.Balloons.Add(new BalloonPayload { ViewName = viewName, LayerNo = sourceItem.LayerNo, Text = ReflectionHelpers.BuildSummaryText(geometry) });
                        break;
                    case "SxGeomTol":
                        payload.Tolerances.Add(new TolerancePayload { ViewName = viewName, LayerNo = sourceItem.LayerNo, Text = ReflectionHelpers.BuildSummaryText(geometry) });
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

        private static TextPayload MapText(object geometry, string sourceType, string? viewName, int? layerNo)
        {
            var textLines = ReflectionHelpers.ExtractStringList(geometry, "txt");
            return new TextPayload
            {
                TextLines = textLines,
                LineCount = ReflectionHelpers.GetInt(geometry, "text_line_num"),
                SourceType = sourceType,
                ViewName = viewName,
                LayerNo = layerNo,
                JoinedText = textLines.Count == 0 ? null : string.Join(" ", textLines),
            };
        }

        private static DimensionPayload MapDimension(object geometry, string? viewName, int? layerNo)
        {
            var dimensionInfo = ReflectionHelpers.GetMemberValue(geometry, "diminfo") ?? geometry;
            return new DimensionPayload
            {
                ViewName = viewName,
                LayerNo = layerNo,
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

        private static GeometryPrimitivePayload MapPrimitive(object geometry, string? viewName, int? layerNo)
        {
            return new GeometryPrimitivePayload
            {
                ViewName = viewName,
                LayerNo = layerNo,
                GeometryType = geometry.GetType().Name,
                Summary = ReflectionHelpers.BuildSummaryText(geometry),
            };
        }
    }
}
