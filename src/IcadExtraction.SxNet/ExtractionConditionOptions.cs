using System;
using System.Collections.Generic;

namespace IcadExtraction.SxNet
{
    public sealed class ExtractionConditionOptions
    {
        public bool ScanAllViews { get; set; } = true;
        public bool ScanAllLayers { get; set; } = true;
        public bool ClassifyPrintFrame { get; set; } = true;
        public bool RecordOutsidePrintFrame { get; set; } = true;
        public bool RecordUnknownPrintArea { get; set; } = true;
        public bool ScanPartTree { get; set; } = true;
        public bool ScanPartMaterials { get; set; } = true;
        public bool ScanPartExtendedInfo { get; set; } = true;
        public bool ScanMassProperties { get; set; } = true;

        public static ExtractionConditionOptions Default => new ExtractionConditionOptions();

        public static ExtractionConditionOptions FromDictionary(IDictionary<string, object>? values)
        {
            var options = new ExtractionConditionOptions();
            if (values == null)
            {
                return options;
            }

            options.ScanAllViews = BoolOption(values, "scanAllViews", options.ScanAllViews);
            options.ScanAllLayers = BoolOption(values, "scanAllLayers", options.ScanAllLayers);
            options.ClassifyPrintFrame = BoolOption(values, "classifyPrintFrame", options.ClassifyPrintFrame);
            options.RecordOutsidePrintFrame = BoolOption(values, "recordOutsidePrintFrame", options.RecordOutsidePrintFrame);
            options.RecordUnknownPrintArea = BoolOption(values, "recordUnknownPrintArea", options.RecordUnknownPrintArea);
            options.ScanPartTree = BoolOption(values, "scanPartTree", options.ScanPartTree);
            options.ScanPartMaterials = BoolOption(values, "scanPartMaterials", options.ScanPartMaterials);
            options.ScanPartExtendedInfo = BoolOption(values, "scanPartExtendedInfo", options.ScanPartExtendedInfo);
            options.ScanMassProperties = BoolOption(values, "scanMassProperties", options.ScanMassProperties);
            return options;
        }

        public Dictionary<string, object> ToDiagnostics(string sourceKind, string extractionProfile, IEnumerable<string> optionKeys)
        {
            return new Dictionary<string, object>
            {
                ["schemaVersion"] = "extract_condition_diagnostics.v1",
                ["sourceKind"] = sourceKind,
                ["extractionProfile"] = extractionProfile,
                ["optionKeys"] = new List<string>(optionKeys),
                ["scanAllViews"] = ScanAllViews,
                ["scanAllLayers"] = ScanAllLayers,
                ["classifyPrintFrame"] = ClassifyPrintFrame,
                ["recordOutsidePrintFrame"] = RecordOutsidePrintFrame,
                ["recordUnknownPrintArea"] = RecordUnknownPrintArea,
                ["scanPartTree"] = ScanPartTree,
                ["scanPartMaterials"] = ScanPartMaterials,
                ["scanPartExtendedInfo"] = ScanPartExtendedInfo,
                ["scanMassProperties"] = ScanMassProperties,
            };
        }

        private static bool BoolOption(IDictionary<string, object> values, string key, bool defaultValue)
        {
            if (!values.TryGetValue(key, out var rawValue) || rawValue == null)
            {
                return defaultValue;
            }

            if (rawValue is bool boolValue)
            {
                return boolValue;
            }

            if (bool.TryParse(Convert.ToString(rawValue), out var parsed))
            {
                return parsed;
            }

            return defaultValue;
        }
    }
}
