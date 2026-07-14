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
                    case "SxGeomSpline2D":
                    case "SxGeomEllipse2D":
                    case "SxGeomElparc2D":
                    case "SxGeomHatch":
                    case "SxGeomSmark":
                    case "SxGeomCutLine":
                    case "SxGeomDelta":
                    case "SxGeomTolDatum":
                        payload.GeometryPrimitives.Add(MapPrimitive(geometry, viewName, sourceItem.LayerNo));
                        break;
                    case "SxGeomWeld":
                        payload.WeldNotes.Add(new WeldNotePayload
                        {
                            ViewName = viewName,
                            LayerNo = sourceItem.LayerNo,
                            PositionX = GetPositionX(geometry, "pnt"),
                            PositionY = GetPositionY(geometry, "pnt"),
                            PositionZ = GetPositionZ(geometry, "pnt"),
                            Text = ReflectionHelpers.BuildSummaryText(geometry),
                        });
                        break;
                    case "SxGeomBalloon":
                        payload.Balloons.Add(new BalloonPayload
                        {
                            ViewName = viewName,
                            LayerNo = sourceItem.LayerNo,
                            PositionX = GetPositionX(geometry, "pnt"),
                            PositionY = GetPositionY(geometry, "pnt"),
                            PositionZ = GetPositionZ(geometry, "pnt"),
                            Text = ReflectionHelpers.BuildSummaryText(geometry),
                        });
                        break;
                    case "SxGeomTol":
                        payload.Tolerances.Add(new TolerancePayload
                        {
                            ViewName = viewName,
                            LayerNo = sourceItem.LayerNo,
                            PositionX = GetPositionX(geometry, "pnt"),
                            PositionY = GetPositionY(geometry, "pnt"),
                            PositionZ = GetPositionZ(geometry, "pnt"),
                            Text = ReflectionHelpers.BuildSummaryText(geometry),
                        });
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
                PositionX = GetPositionX(geometry, "pnt"),
                PositionY = GetPositionY(geometry, "pnt"),
                PositionZ = GetPositionZ(geometry, "pnt"),
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
                PositionX = GetPositionX(geometry, "pnt1"),
                PositionY = GetPositionY(geometry, "pnt1"),
                PositionZ = GetPositionZ(geometry, "pnt1"),
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
            var geometryType = geometry.GetType().Name;
            return new GeometryPrimitivePayload
            {
                ViewName = viewName,
                LayerNo = layerNo,
                GeometryType = geometryType,
                PositionX = ResolvePositionX(geometry, geometryType),
                PositionY = ResolvePositionY(geometry, geometryType),
                PositionZ = ResolvePositionZ(geometry, geometryType),
                EndX = ResolveEndX(geometry, geometryType),
                EndY = ResolveEndY(geometry, geometryType),
                EndZ = ResolveEndZ(geometry, geometryType),
                CenterX = ResolveCenterX(geometry),
                CenterY = ResolveCenterY(geometry),
                CenterZ = ResolveCenterZ(geometry),
                Radius = ReflectionHelpers.GetDouble(geometry, "radius"),
                Radius1 = ReflectionHelpers.GetDouble(geometry, "radius1"),
                Radius2 = ReflectionHelpers.GetDouble(geometry, "radius2"),
                StartAngle = ReflectionHelpers.GetDouble(geometry, "sang"),
                EndAngle = ReflectionHelpers.GetDouble(geometry, "eang"),
                PointCount = ResolvePointCount(geometry, geometryType),
                Summary = ReflectionHelpers.BuildSummaryText(geometry),
            };
        }

        private static double? ResolvePositionX(object geometry, string geometryType)
        {
            if (geometryType == "SxGeomLine2D")
            {
                return ReflectionHelpers.GetDouble(geometry, "x1") ?? GetPositionXFromAny(geometry, "pnt1", "pos1", "sp", "start");
            }

            return GetPositionX(geometry, ResolvePrimaryPositionMember(geometryType));
        }

        private static double? ResolvePositionY(object geometry, string geometryType)
        {
            if (geometryType == "SxGeomLine2D")
            {
                return ReflectionHelpers.GetDouble(geometry, "y1") ?? GetPositionYFromAny(geometry, "pnt1", "pos1", "sp", "start");
            }

            return GetPositionY(geometry, ResolvePrimaryPositionMember(geometryType));
        }

        private static double? ResolvePositionZ(object geometry, string geometryType)
        {
            if (geometryType == "SxGeomLine2D")
            {
                return ReflectionHelpers.GetDouble(geometry, "z1") ?? GetPositionZFromAny(geometry, "pnt1", "pos1", "sp", "start");
            }

            return GetPositionZ(geometry, ResolvePrimaryPositionMember(geometryType));
        }

        private static double? ResolveEndX(object geometry, string geometryType)
        {
            if (geometryType == "SxGeomLine2D")
            {
                return ReflectionHelpers.GetDouble(geometry, "x2") ?? GetPositionXFromAny(geometry, "pnt2", "pos2", "ep", "end");
            }

            if (geometryType == "SxGeomCutLine")
            {
                return GetPositionX(geometry, "pnt2");
            }

            return null;
        }

        private static double? ResolveEndY(object geometry, string geometryType)
        {
            if (geometryType == "SxGeomLine2D")
            {
                return ReflectionHelpers.GetDouble(geometry, "y2") ?? GetPositionYFromAny(geometry, "pnt2", "pos2", "ep", "end");
            }

            if (geometryType == "SxGeomCutLine")
            {
                return GetPositionY(geometry, "pnt2");
            }

            return null;
        }

        private static double? ResolveEndZ(object geometry, string geometryType)
        {
            if (geometryType == "SxGeomLine2D")
            {
                return ReflectionHelpers.GetDouble(geometry, "z2") ?? GetPositionZFromAny(geometry, "pnt2", "pos2", "ep", "end");
            }

            if (geometryType == "SxGeomCutLine")
            {
                return GetPositionZ(geometry, "pnt2");
            }

            return null;
        }

        private static double? ResolveCenterX(object geometry)
        {
            return GetPositionX(geometry, "cp");
        }

        private static double? ResolveCenterY(object geometry)
        {
            return GetPositionY(geometry, "cp");
        }

        private static double? ResolveCenterZ(object geometry)
        {
            return GetPositionZ(geometry, "cp");
        }

        private static int? ResolvePointCount(object geometry, string geometryType)
        {
            if (geometryType != "SxGeomSpline2D")
            {
                return null;
            }

            var vecList = ReflectionHelpers.GetMemberValue(geometry, "vec_list");
            var count = 1;
            foreach (var _ in ReflectionHelpers.Enumerate(vecList))
            {
                count++;
            }

            return count;
        }

        private static string ResolvePrimaryPositionMember(string geometryType)
        {
            switch (geometryType)
            {
                case "SxGeomSpline2D":
                    return "pos";
                case "SxGeomElparc2D":
                case "SxGeomEllipse2D":
                case "SxGeomCircle2D":
                case "SxGeomArc2D":
                    return "cp";
                case "SxGeomCutLine":
                    return "pnt1";
                default:
                    return "pnt";
            }
        }

        private static double? GetPositionX(object geometry, string memberName)
        {
            return ReflectionHelpers.GetPositionComponent(geometry, memberName, "x");
        }

        private static double? GetPositionY(object geometry, string memberName)
        {
            return ReflectionHelpers.GetPositionComponent(geometry, memberName, "y");
        }

        private static double? GetPositionZ(object geometry, string memberName)
        {
            return ReflectionHelpers.GetPositionComponent(geometry, memberName, "z");
        }

        private static double? GetPositionXFromAny(object geometry, params string[] memberNames)
        {
            return GetPositionComponentFromAny(geometry, "x", memberNames);
        }

        private static double? GetPositionYFromAny(object geometry, params string[] memberNames)
        {
            return GetPositionComponentFromAny(geometry, "y", memberNames);
        }

        private static double? GetPositionZFromAny(object geometry, params string[] memberNames)
        {
            return GetPositionComponentFromAny(geometry, "z", memberNames);
        }

        private static double? GetPositionComponentFromAny(object geometry, string componentName, params string[] memberNames)
        {
            foreach (var memberName in memberNames)
            {
                var value = ReflectionHelpers.GetPositionComponent(geometry, memberName, componentName);
                if (value.HasValue)
                {
                    return value;
                }
            }

            return null;
        }
    }
}
