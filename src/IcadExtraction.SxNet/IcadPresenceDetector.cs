using System;
using System.Collections.Generic;
using System.Linq;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    public sealed class IcadPresenceDetector
    {
        public DetectionEnvelope Detect(string sxnetDllPath, string inputPath)
        {
            var warnings = new List<WarningPayload>();
            using (var context = SxNetOpenContext.OpenReadOnly(sxnetDllPath, inputPath))
            {
                var twoD = Detect2D(context, warnings);
                var threeD = Detect3D(context, warnings);
                return new DetectionEnvelope
                {
                    InputPath = inputPath,
                    Detection = new DetectionPayload
                    {
                        Has2D = twoD.HasContent,
                        Has2DContainer = twoD.HasContainer,
                        Has3D = threeD.HasContent,
                        TwoD = twoD,
                        ThreeD = threeD,
                    },
                    Warnings = warnings,
                };
            }
        }

        private static DetectionEvidence2DPayload Detect2D(SxNetOpenContext context, IList<WarningPayload> warnings)
        {
            var viewSheetCount = CountOrWarn(() => context.GetVsList().Count(), "detect_2d_vs_list_failed", warnings);
            var printFrameCount = CountOrWarn(() => context.GetInfPrintList().Count(), "detect_2d_print_frame_list_failed", warnings);
            var geometryCount = CountOrWarn(() => CountAllViewGeometries(context), "detect_2d_geometry_count_failed", warnings);
            return new DetectionEvidence2DPayload
            {
                ViewSheetCount = viewSheetCount,
                PrintFrameCount = printFrameCount,
                GeometryCount = geometryCount,
                HasContainer = viewSheetCount > 0 || printFrameCount > 0,
                HasContent = geometryCount > 0,
            };
        }

        private static DetectionEvidence3DPayload Detect3D(SxNetOpenContext context, IList<WarningPayload> warnings)
        {
            try
            {
                var globalWf = context.GetGlobalWf();
                var getInfPartTreeMethod = globalWf.GetType().GetMethod("getInfPartTree", Type.EmptyTypes);
                if (getInfPartTreeMethod == null)
                {
                    throw new MissingMethodException("sxnet.SxWF.getInfPartTree()");
                }

                var rootNode = getInfPartTreeMethod.Invoke(globalWf, null);
                if (rootNode == null)
                {
                    return new DetectionEvidence3DPayload();
                }

                var raw = new PartTreeFlattener().Flatten(rootNode, null);
                return new DetectionEvidence3DPayload
                {
                    HasContent = raw.Parts.Count > 0,
                    TopPartName = raw.TopPart.Name,
                    PartCount = raw.Parts.Count,
                };
            }
            catch (Exception exception)
            {
                warnings.Add(new WarningPayload
                {
                    Code = "detect_3d_part_tree_failed",
                    Message = "3D part tree detection failed: " + exception.Message,
                });
                return new DetectionEvidence3DPayload();
            }
        }

        private static int CountAllViewGeometries(SxNetOpenContext context)
        {
            var viewSheets = context.GetVsList().ToArray();
            if (viewSheets.Length == 0)
            {
                return CountViewGeometries(context.GetGlobalVs());
            }

            return viewSheets.Sum(CountViewGeometries);
        }

        private static int CountViewGeometries(object viewSheet)
        {
            var vsType = viewSheet.GetType();
            var getSegListMethod = vsType.GetMethods()
                .FirstOrDefault(method =>
                    method.Name == "getSegList" &&
                    method.GetParameters().Length == 4);

            if (getSegListMethod == null)
            {
                return 0;
            }

            var segments = getSegListMethod.Invoke(viewSheet, new object[] { 0, int.MaxValue, false, false });
            var segmentArray = ReflectionHelpers.Enumerate(segments).ToArray();
            if (segmentArray.Length == 0)
            {
                return 0;
            }

            var segmentType = viewSheet.GetType().Assembly.GetType("sxnet.SxEntSeg", throwOnError: true);
            var getGeomListMethod = segmentType.GetMethod("getGeomList", new[] { segmentType.MakeArrayType() });
            if (getGeomListMethod == null)
            {
                return 0;
            }

            var typedSegments = Array.CreateInstance(segmentType, segmentArray.Length);
            for (var index = 0; index < segmentArray.Length; index++)
            {
                typedSegments.SetValue(segmentArray[index], index);
            }

            var geometries = getGeomListMethod.Invoke(null, new object[] { typedSegments });
            return ReflectionHelpers.Enumerate(geometries).Count();
        }

        private static int CountOrWarn(Func<int> count, string warningCode, IList<WarningPayload> warnings)
        {
            try
            {
                return count();
            }
            catch (Exception exception)
            {
                warnings.Add(new WarningPayload
                {
                    Code = warningCode,
                    Message = exception.Message,
                });
                return 0;
            }
        }
    }
}
