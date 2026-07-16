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
            return Extract(sxnetDllPath, inputPath, ExtractionConditionOptions.Default);
        }

        public ExtractionEnvelope Extract(string sxnetDllPath, string inputPath, ExtractionConditionOptions options)
        {
            return Extract(sxnetDllPath, inputPath, options, new PreviewAssetOptions());
        }

        public ExtractionEnvelope Extract(
            string sxnetDllPath,
            string inputPath,
            ExtractionConditionOptions options,
            PreviewAssetOptions previewAssetOptions
        )
        {
            var warnings = new List<WarningPayload>();
            using (var context = SxNetOpenContext.OpenReadOnly(sxnetDllPath, inputPath))
            {
                var globalVs = context.GetGlobalVs();
                Ensure2DWindow(globalVs, warnings);
                var rawExtract = new RawExtract2DPayload
                {
                    ModelInfo = context.GetModelInfo(),
                };
                foreach (var viewGeometry in TryResolveAllViewGeometries(context, warnings, options))
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
                if (options.ClassifyPrintFrame)
                {
                    rawExtract.PrintFrames.AddRange(TryResolvePrintFrames(context, warnings));
                    ApplyPrintAreaClassification(rawExtract);
                    ApplyPrintAreaRetention(rawExtract, options);
                }
                if (options.ScanAllLayers)
                {
                    rawExtract.Layers.AddRange(TryResolveLayers(context, warnings));
                }
                if (previewAssetOptions.Enabled)
                {
                    const string message = "2D preview asset export is not implemented yet. Print/plot settings must be verified per ICAD environment.";
                    rawExtract.ViewerAssets["2d"] = new List<ViewerAssetPayload>
                    {
                        new ViewerAssetPayload
                        {
                            Mode = "2d",
                            Status = "unsupported",
                            Source = "sxnet_print",
                            Message = message,
                        },
                    };
                    warnings.Add(new WarningPayload { Code = "viewer_2d_asset_export_unsupported", Message = message });
                }
                rawExtract.ConditionDiagnostics = BuildConditionDiagnostics(rawExtract, options);
                return new ExtractionEnvelope
                {
                    InputPath = inputPath,
                    SourceKind = "2d",
                    RawExtract = rawExtract,
                    Warnings = warnings,
                };
            }
        }

        private static Dictionary<string, object> BuildConditionDiagnostics(RawExtract2DPayload rawExtract, ExtractionConditionOptions options)
        {
            return new Dictionary<string, object>
            {
                ["scanAllViews"] = options.ScanAllViews,
                ["scanAllLayers"] = options.ScanAllLayers,
                ["classifyPrintFrame"] = options.ClassifyPrintFrame,
                ["recordOutsidePrintFrame"] = options.RecordOutsidePrintFrame,
                ["recordUnknownPrintArea"] = options.RecordUnknownPrintArea,
                ["viewSheetCount"] = rawExtract.ViewSheets.Count,
                ["layerCount"] = rawExtract.Layers.Count,
                ["printFrameCount"] = rawExtract.PrintFrames.Count,
                ["textCount"] = rawExtract.Texts.Count,
                ["dimensionCount"] = rawExtract.Dimensions.Count,
                ["geometryPrimitiveCount"] = rawExtract.GeometryPrimitives.Count,
                ["referencedPartCount"] = rawExtract.ReferencedParts.Count,
            };
        }

        private static void ApplyPrintAreaRetention(RawExtract2DPayload rawExtract, ExtractionConditionOptions options)
        {
            if (options.RecordOutsidePrintFrame && options.RecordUnknownPrintArea)
            {
                return;
            }

            rawExtract.Texts = rawExtract.Texts.Where(item => KeepPrintAreaItem(item.InsidePrintArea, options)).ToList();
            rawExtract.Dimensions = rawExtract.Dimensions.Where(item => KeepPrintAreaItem(item.InsidePrintArea, options)).ToList();
            rawExtract.GeometryPrimitives = rawExtract.GeometryPrimitives.Where(item => KeepPrintAreaItem(item.InsidePrintArea, options)).ToList();
            rawExtract.WeldNotes = rawExtract.WeldNotes.Where(item => KeepPrintAreaItem(item.InsidePrintArea, options)).ToList();
            rawExtract.Balloons = rawExtract.Balloons.Where(item => KeepPrintAreaItem(item.InsidePrintArea, options)).ToList();
            rawExtract.Tolerances = rawExtract.Tolerances.Where(item => KeepPrintAreaItem(item.InsidePrintArea, options)).ToList();
            rawExtract.ReferencedParts = rawExtract.ReferencedParts.Where(item => KeepPrintAreaItem(item.InsidePrintArea, options)).ToList();
        }

        private static bool KeepPrintAreaItem(bool? insidePrintArea, ExtractionConditionOptions options)
        {
            if (insidePrintArea == false)
            {
                return options.RecordOutsidePrintFrame;
            }
            if (insidePrintArea == null)
            {
                return options.RecordUnknownPrintArea;
            }
            return true;
        }

        private static void ApplyPrintAreaClassification(RawExtract2DPayload rawExtract)
        {
            foreach (var text in rawExtract.Texts)
            {
                var classification = PrintAreaClassifier.Resolve(rawExtract.PrintFrames, text.PositionX, text.PositionY);
                text.InsidePrintArea = classification.InsidePrintArea;
                text.PrintFrameNo = classification.PrintFrameNo;
            }

            foreach (var dimension in rawExtract.Dimensions)
            {
                var classification = PrintAreaClassifier.Resolve(rawExtract.PrintFrames, dimension.PositionX, dimension.PositionY);
                dimension.InsidePrintArea = classification.InsidePrintArea;
                dimension.PrintFrameNo = classification.PrintFrameNo;
            }

            foreach (var primitive in rawExtract.GeometryPrimitives)
            {
                var x = primitive.PositionX ?? primitive.CenterX;
                var y = primitive.PositionY ?? primitive.CenterY;
                var classification = PrintAreaClassifier.Resolve(rawExtract.PrintFrames, x, y);
                primitive.InsidePrintArea = classification.InsidePrintArea;
                primitive.PrintFrameNo = classification.PrintFrameNo;
            }

            foreach (var weldNote in rawExtract.WeldNotes)
            {
                var classification = PrintAreaClassifier.Resolve(rawExtract.PrintFrames, weldNote.PositionX, weldNote.PositionY);
                weldNote.InsidePrintArea = classification.InsidePrintArea;
                weldNote.PrintFrameNo = classification.PrintFrameNo;
            }

            foreach (var balloon in rawExtract.Balloons)
            {
                var classification = PrintAreaClassifier.Resolve(rawExtract.PrintFrames, balloon.PositionX, balloon.PositionY);
                balloon.InsidePrintArea = classification.InsidePrintArea;
                balloon.PrintFrameNo = classification.PrintFrameNo;
            }

            foreach (var tolerance in rawExtract.Tolerances)
            {
                var classification = PrintAreaClassifier.Resolve(rawExtract.PrintFrames, tolerance.PositionX, tolerance.PositionY);
                tolerance.InsidePrintArea = classification.InsidePrintArea;
                tolerance.PrintFrameNo = classification.PrintFrameNo;
            }

            foreach (var referencedPart in rawExtract.ReferencedParts)
            {
                var classification = PrintAreaClassifier.Resolve(rawExtract.PrintFrames, referencedPart.PositionX, referencedPart.PositionY);
                referencedPart.InsidePrintArea = classification.InsidePrintArea;
                referencedPart.PrintFrameNo = classification.PrintFrameNo;
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

        private static IEnumerable<ViewGeometryPayload> TryResolveAllViewGeometries(SxNetOpenContext context, IList<WarningPayload> warnings, ExtractionConditionOptions options)
        {
            try
            {
                var viewSheets = context.GetVsList().ToArray();
                if (!options.ScanAllViews || viewSheets.Length == 0)
                {
                    var globalVs = context.GetGlobalVs();
                    var viewName = TryResolveViewSheetName(globalVs);
                    var geometries = TryResolveAllGeometries(globalVs, warnings, viewName, options).ToArray();
                    return new[] { new ViewGeometryPayload(MapViewSheet(globalVs, geometries.Length), geometries) };
                }

                return viewSheets
                    .Select(viewSheet =>
                    {
                        var viewName = TryResolveViewSheetName(viewSheet);
                        var geometries = TryResolveAllGeometries(viewSheet, warnings, viewName, options).ToArray();
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

        private static IEnumerable<GeometrySourceItem> TryResolveAllGeometries(object globalVs, IList<WarningPayload> warnings, string? viewName, ExtractionConditionOptions options)
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
                var layerNumbers = options.ScanAllLayers
                    ? TryResolveSegmentLayers(globalVs, typedSegments, segmentArray.Length, warnings)
                    : Enumerable.Repeat<int?>(null, geometryArray.Length).ToArray();
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
