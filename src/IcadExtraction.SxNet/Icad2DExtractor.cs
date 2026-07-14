using System;
using System.Collections.Generic;
using System.Linq;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    public sealed class Icad2DExtractor
    {
        public ExtractionEnvelope Extract(string sxnetDllPath, string inputPath)
        {
            var warnings = new List<WarningPayload>();
            using (var context = SxNetOpenContext.OpenReadOnly(sxnetDllPath, inputPath))
            {
                var globalVs = context.GetGlobalVs();
                Ensure2DWindow(globalVs, warnings);
                var rawExtract = new RawExtract2DPayload();
                foreach (var viewGeometry in TryResolveAllViewGeometries(context, warnings))
                {
                    rawExtract.ViewSheets.Add(viewGeometry.ViewSheet);
                    var mapped = new GeometryMapper().Map(viewGeometry.Geometries, warnings, viewGeometry.ViewSheet.Name);
                    rawExtract.Texts.AddRange(mapped.Texts);
                    rawExtract.Dimensions.AddRange(mapped.Dimensions);
                    rawExtract.GeometryPrimitives.AddRange(mapped.GeometryPrimitives);
                    rawExtract.WeldNotes.AddRange(mapped.WeldNotes);
                    rawExtract.Balloons.AddRange(mapped.Balloons);
                    rawExtract.Tolerances.AddRange(mapped.Tolerances);
                }
                rawExtract.PrintFrames.AddRange(TryResolvePrintFrames(context, warnings));
                rawExtract.Layers.AddRange(TryResolveLayers(context, warnings));
                return new ExtractionEnvelope
                {
                    InputPath = inputPath,
                    SourceKind = "2d",
                    RawExtract = rawExtract,
                    Warnings = warnings,
                };
            }
        }

        private static IEnumerable<LayerPayload> TryResolveLayers(SxNetOpenContext context, IList<WarningPayload> warnings)
        {
            try
            {
                return context.GetInfLayerList().Select(MapLayer).ToArray();
            }
            catch (Exception exception)
            {
                warnings.Add(new WarningPayload
                {
                    Code = "layer_probe_failed",
                    Message = "2D layer probing failed: " + exception.Message,
                });
                return Array.Empty<LayerPayload>();
            }
        }

        private static LayerPayload MapLayer(object layer)
        {
            return new LayerPayload
            {
                No = ReflectionHelpers.GetInt(layer, "no"),
                Name = ReflectionHelpers.GetString(layer, "name"),
                IsDisplayed = ReflectionHelpers.GetBool(layer, "is_disp"),
                IsSearchable = ReflectionHelpers.GetBool(layer, "is_search"),
            };
        }

        private sealed class ViewGeometryPayload
        {
            public ViewGeometryPayload(ViewSheetPayload viewSheet, GeometrySourceItem[] geometries)
            {
                ViewSheet = viewSheet;
                Geometries = geometries;
            }

            public ViewSheetPayload ViewSheet { get; }
            public GeometrySourceItem[] Geometries { get; }
        }

        private static IEnumerable<PrintFramePayload> TryResolvePrintFrames(SxNetOpenContext context, IList<WarningPayload> warnings)
        {
            try
            {
                return context.GetInfPrintList().Select(MapPrintFrame).ToArray();
            }
            catch (Exception exception)
            {
                warnings.Add(new WarningPayload
                {
                    Code = "print_frame_probe_failed",
                    Message = "2D print frame probing failed: " + exception.Message,
                });
                return Array.Empty<PrintFramePayload>();
            }
        }

        private static IEnumerable<ViewGeometryPayload> TryResolveAllViewGeometries(SxNetOpenContext context, IList<WarningPayload> warnings)
        {
            try
            {
                var viewSheets = context.GetVsList().ToArray();
                if (viewSheets.Length == 0)
                {
                    var globalVs = context.GetGlobalVs();
                    var viewName = TryResolveViewSheetName(globalVs);
                    var geometries = TryResolveAllGeometries(globalVs, warnings, viewName).ToArray();
                    return new[] { new ViewGeometryPayload(MapViewSheet(globalVs, geometries.Length), geometries) };
                }

                return viewSheets
                    .Select(viewSheet =>
                    {
                        var viewName = TryResolveViewSheetName(viewSheet);
                        var geometries = TryResolveAllGeometries(viewSheet, warnings, viewName).ToArray();
                        return new ViewGeometryPayload(MapViewSheet(viewSheet, geometries.Length), geometries);
                    })
                    .ToArray();
            }
            catch (Exception exception)
            {
                warnings.Add(new WarningPayload
                {
                    Code = "view_geometry_probe_failed",
                    Message = "2D view geometry probing failed: " + exception.Message,
                });
                return Array.Empty<ViewGeometryPayload>();
            }
        }

        private static ViewSheetPayload MapViewSheet(object viewSheet, int geometryCount)
        {
            var getInfMethod = viewSheet.GetType().GetMethod("getInf", Type.EmptyTypes);
            var info = getInfMethod?.Invoke(viewSheet, null);
            return new ViewSheetPayload
            {
                Name = ReflectionHelpers.GetString(info, "name"),
                Comment = ReflectionHelpers.GetString(info, "comment"),
                Scale = ReflectionHelpers.GetDouble(info, "scale"),
                Angle = ReflectionHelpers.GetDouble(info, "angle"),
                Type = ReflectionHelpers.GetInt(info, "type"),
                ViewType = ReflectionHelpers.GetInt(info, "view_type"),
                GeometryCount = geometryCount,
            };
        }

        private static string? TryResolveViewSheetName(object viewSheet)
        {
            try
            {
                var getInfMethod = viewSheet.GetType().GetMethod("getInf", Type.EmptyTypes);
                var info = getInfMethod?.Invoke(viewSheet, null);
                return ReflectionHelpers.GetString(info, "name");
            }
            catch
            {
                return null;
            }
        }

        private static PrintFramePayload MapPrintFrame(object printFrame)
        {
            var dinfo = ReflectionHelpers.ExtractDoubleList(printFrame, "dinfo");
            return new PrintFramePayload
            {
                No = ReflectionHelpers.GetInt(printFrame, "no"),
                Size = ReflectionHelpers.GetString(printFrame, "size"),
                Vertical = ReflectionHelpers.GetBool(printFrame, "vertical"),
                Dinfo = dinfo,
                DrawingScale = dinfo.Count > 2 ? dinfo[2] : null,
                RangeMinX = dinfo.Count > 3 ? dinfo[3] : null,
                RangeMinY = dinfo.Count > 4 ? dinfo[4] : null,
                RangeMaxX = dinfo.Count > 5 ? dinfo[5] : null,
                RangeMaxY = dinfo.Count > 6 ? dinfo[6] : null,
            };
        }

        private static IEnumerable<GeometrySourceItem> TryResolveAllGeometries(object globalVs, IList<WarningPayload> warnings, string? viewName)
        {
            var vsType = globalVs.GetType();
            var getSegListMethod = vsType.GetMethods()
                .FirstOrDefault(method =>
                    method.Name == "getSegList" &&
                    method.GetParameters().Length == 4);

            if (getSegListMethod == null)
            {
                warnings.Add(new WarningPayload
                {
                    Code = "missing_get_seg_list",
                    Message = "SxVS.getSegList overload could not be resolved. Returning empty geometry list.",
                });
                return Array.Empty<GeometrySourceItem>();
            }

            try
            {
                var segments = getSegListMethod.Invoke(globalVs, new object[] { 0, int.MaxValue, false, false });
                var segmentArray = ReflectionHelpers.Enumerate(segments).ToArray();
                var segmentType = globalVs.GetType().Assembly.GetType("sxnet.SxEntSeg", throwOnError: true);
                var getGeomListMethod = segmentType.GetMethod("getGeomList", new[] { segmentType.MakeArrayType() });
                if (getGeomListMethod == null)
                {
                    warnings.Add(new WarningPayload
                    {
                        Code = "missing_get_geom_list",
                        Message = "SxEntSeg.getGeomList overload could not be resolved. Returning empty geometry list.",
                    });
                    return Array.Empty<GeometrySourceItem>();
                }

                var typedSegments = Array.CreateInstance(segmentType, segmentArray.Length);
                for (var index = 0; index < segmentArray.Length; index++)
                {
                    typedSegments.SetValue(segmentArray[index], index);
                }

                var geometries = getGeomListMethod.Invoke(null, new object[] { typedSegments });
                var geometryArray = ReflectionHelpers.Enumerate(geometries).ToArray();
                var layerNumbers = TryResolveSegmentLayers(globalVs, typedSegments, segmentArray.Length, warnings);
                if (layerNumbers.Length != geometryArray.Length)
                {
                    warnings.Add(new WarningPayload
                    {
                        Code = "geometry_layer_count_mismatch",
                        Message = $"2D geometry count ({geometryArray.Length}) and layer count ({layerNumbers.Length}) did not match in view '{viewName ?? "(unknown)"}'. Layer numbers were omitted for this view.",
                    });
                    layerNumbers = Enumerable.Repeat<int?>(null, geometryArray.Length).ToArray();
                }

                return geometryArray
                    .Select((geometry, index) => new GeometrySourceItem(geometry, layerNumbers[index]))
                    .ToArray();
            }
            catch (Exception exception)
            {
                warnings.Add(new WarningPayload
                {
                    Code = "geometry_probe_failed",
                    Message = "2D geometry probing failed: " + exception.Message,
                });
                return Array.Empty<GeometrySourceItem>();
            }
        }

        private static int?[] TryResolveSegmentLayers(object globalVs, Array typedSegments, int segmentCount, IList<WarningPayload> warnings)
        {
            try
            {
                var assembly = globalVs.GetType().Assembly;
                var entType = assembly.GetType("sxnet.SxEnt", throwOnError: true);
                var getInfListMethod = entType.GetMethod("getInfList", new[] { entType.MakeArrayType() });
                if (getInfListMethod == null)
                {
                    warnings.Add(new WarningPayload
                    {
                        Code = "missing_get_inf_list",
                        Message = "SxEnt.getInfList overload could not be resolved. Layer numbers were omitted for this view.",
                    });
                    return Array.Empty<int?>();
                }

                var typedEntities = Array.CreateInstance(entType, segmentCount);
                for (var index = 0; index < segmentCount; index++)
                {
                    typedEntities.SetValue(typedSegments.GetValue(index), index);
                }

                var infoList = getInfListMethod.Invoke(null, new object[] { typedEntities });
                return ReflectionHelpers.Enumerate(infoList)
                    .Select(info => (int?)ReflectionHelpers.GetInt(info, "layer"))
                    .ToArray();
            }
            catch (Exception exception)
            {
                warnings.Add(new WarningPayload
                {
                    Code = "segment_layer_probe_failed",
                    Message = "2D segment layer probing failed: " + exception.Message,
                });
                return Array.Empty<int?>();
            }
        }

        private static void Ensure2DWindow(object globalVs, IList<WarningPayload> warnings)
        {
            try
            {
                var getWindowMethod = globalVs.GetType().GetMethod("getWindow", Type.EmptyTypes);
                var window = getWindowMethod?.Invoke(globalVs, null);
                if (window == null)
                {
                    return;
                }

                var setDimMethod = window.GetType().GetMethod("setDim", new[] { typeof(bool) });
                setDimMethod?.Invoke(window, new object[] { false });
            }
            catch (Exception exception)
            {
                warnings.Add(new WarningPayload
                {
                    Code = "set_dim_skipped",
                    Message = "2D window setDim(false) was skipped: " + exception.Message,
                });
            }
        }
    }
}
