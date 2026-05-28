using System;
using System.Collections.Generic;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    public sealed class Icad3DExtractor
    {
        public ExtractionEnvelope Extract(string sxnetDllPath, string inputPath)
        {
            var warnings = new List<WarningPayload>();
            using (var context = SxNetOpenContext.OpenReadOnly(sxnetDllPath, inputPath))
            {
                var globalWf = context.GetGlobalWf();
                var getInfPartTreeMethod = globalWf.GetType().GetMethod("getInfPartTree", Type.EmptyTypes);
                var getInfExTopPartMethod = globalWf.GetType().GetMethod("getInfExTopPart", Type.EmptyTypes);
                if (getInfPartTreeMethod == null)
                {
                    throw new MissingMethodException("sxnet.SxWF.getInfPartTree()");
                }

                var rootNode = getInfPartTreeMethod.Invoke(globalWf, null);
                if (rootNode == null)
                {
                    throw new InvalidOperationException("SxWF.getInfPartTree returned null");
                }

                var topPartExInfo = getInfExTopPartMethod?.Invoke(globalWf, null)?.ToString();
                var rawExtract = new PartTreeFlattener().Flatten(rootNode, topPartExInfo);

                return new ExtractionEnvelope
                {
                    InputPath = inputPath,
                    SourceKind = "3d",
                    RawExtract = rawExtract,
                    Warnings = warnings,
                };
            }
        }
    }
}
