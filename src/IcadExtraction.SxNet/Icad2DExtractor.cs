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
                var geometries = TryResolveAllGeometries(globalVs, warnings);
                var rawExtract = new GeometryMapper().Map(geometries, warnings);
                return new ExtractionEnvelope
                {
                    InputPath = inputPath,
                    SourceKind = "2d",
                    RawExtract = rawExtract,
                    Warnings = warnings,
                };
            }
        }

        private static IEnumerable<object> TryResolveAllGeometries(object globalVs, IList<WarningPayload> warnings)
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
                return Array.Empty<object>();
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
                    return Array.Empty<object>();
                }

                var typedSegments = Array.CreateInstance(segmentType, segmentArray.Length);
                for (var index = 0; index < segmentArray.Length; index++)
                {
                    typedSegments.SetValue(segmentArray[index], index);
                }

                var geometries = getGeomListMethod.Invoke(null, new object[] { typedSegments });
                return ReflectionHelpers.Enumerate(geometries);
            }
            catch (Exception exception)
            {
                warnings.Add(new WarningPayload
                {
                    Code = "geometry_probe_failed",
                    Message = "2D geometry probing failed: " + exception.Message,
                });
                return Array.Empty<object>();
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
