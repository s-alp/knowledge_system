using System;
using System.Collections.Generic;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    public sealed class Icad3DExtractor
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
                var globalWf = context.GetGlobalWf();
                var getInfPartTreeMethod = globalWf.GetType().GetMethod("getInfPartTree", Type.EmptyTypes);
                var getInfExTopPartMethod = globalWf.GetType().GetMethod("getInfExTopPart", Type.EmptyTypes);
                var rawExtract = new RawExtract3DPayload();
                if (options.ScanPartTree)
                {
                    if (getInfPartTreeMethod == null)
                    {
                        throw new MissingMethodException("sxnet.SxWF.getInfPartTree()");
                    }

                    var rootNode = getInfPartTreeMethod.Invoke(globalWf, null);
                    if (rootNode == null)
                    {
                        throw new InvalidOperationException("SxWF.getInfPartTree returned null");
                    }

                    var topPartExInfo = options.ScanPartExtendedInfo ? getInfExTopPartMethod?.Invoke(globalWf, null)?.ToString() : null;
                    rawExtract = new PartTreeFlattener().Flatten(
                        rootNode,
                        topPartExInfo,
                        warnings,
                        scanPartMaterials: options.ScanPartMaterials,
                        scanPartExtendedInfo: options.ScanPartExtendedInfo
                    );
                }
                if (options.ScanMassProperties)
                {
                    new IcadMassPropertyProbe().Apply(globalWf, context.Assembly, rawExtract, warnings);
                }
                else
                {
                    rawExtract.MassProbeStatus = "skipped_by_options";
                }

                if (options.ScanPartMaterials)
                {
                    new IcadMaterialProbe().Apply(globalWf, context.Assembly, rawExtract, warnings);
                }
                else
                {
                    rawExtract.MaterialProbeStatus = "skipped_by_options";
                }
                var viewer3DAssets = new IcadPreviewAssetExporter().Export3DStl(context, inputPath, previewAssetOptions, warnings);
                if (viewer3DAssets.Count > 0)
                {
                    rawExtract.ViewerAssets["3d"] = viewer3DAssets;
                }
                rawExtract.ConditionDiagnostics = BuildConditionDiagnostics(rawExtract, options);

                return new ExtractionEnvelope
                {
                    InputPath = inputPath,
                    SourceKind = "3d",
                    RawExtract = rawExtract,
                    Warnings = warnings,
                };
            }
        }

        private static Dictionary<string, object> BuildConditionDiagnostics(RawExtract3DPayload rawExtract, ExtractionConditionOptions options)
        {
            return new Dictionary<string, object>
            {
                ["scanPartTree"] = options.ScanPartTree,
                ["scanPartMaterials"] = options.ScanPartMaterials,
                ["scanPartExtendedInfo"] = options.ScanPartExtendedInfo,
                ["scanMassProperties"] = options.ScanMassProperties,
                ["partCount"] = rawExtract.Parts.Count,
                ["materialCount"] = rawExtract.Materials.Count,
                ["massProbeStatus"] = rawExtract.MassProbeStatus,
                ["materialProbeStatus"] = rawExtract.MaterialProbeStatus,
            };
        }
    }
}
