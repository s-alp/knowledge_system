// このファイルは、ICADモデルのパーツ構成・材質・質量・付加情報とプレビュー資産を抽出する。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
using System;
using System.Collections.Generic;
using System.Reflection;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    /// <summary>
    /// ICADモデルのパーツ構成・材質・質量・付加情報とプレビュー資産を抽出する。
    /// </summary>
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
            var sxnetAssembly = new SxNetRuntimeGuard().LoadAndValidateAssembly(sxnetDllPath);
            return Extract(sxnetAssembly, inputPath, options, previewAssetOptions);
        }

        public ExtractionEnvelope Extract(
            Assembly sxnetAssembly,
            string inputPath,
            ExtractionConditionOptions options,
            PreviewAssetOptions previewAssetOptions
        )
        {
            var warnings = new List<WarningPayload>();
            using (var context = SxNetOpenContext.OpenReadOnly(sxnetAssembly, inputPath))
            {
                // 3D抽出はパーツ構成を土台にし、質量・材質・プレビューを独立したprobeとして順に重ねる。
                var globalWf = context.GetGlobalWf();
                var getInfPartTreeMethod = globalWf.GetType().GetMethod("getInfPartTree", Type.EmptyTypes);
                var getInfExTopPartMethod = globalWf.GetType().GetMethod("getInfExTopPart", Type.EmptyTypes);
                var modelInfo = context.GetModelInfo();
                var rawExtract = new RawExtract3DPayload
                {
                    ModelInfo = modelInfo,
                };
                if (options.ScanPartTree)
                {
                    // パーツツリーが要求された場合は、空結果を成功扱いにせずAPI欠落・nullを明示的に失敗させる。
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
                    rawExtract.ModelInfo = modelInfo;
                }
                if (options.ScanMassProperties)
                {
                    // 質量APIはICAD環境差があるため、専用probe内で候補APIと単位を記録する。
                    new IcadMassPropertyProbe().Apply(globalWf, context.Assembly, rawExtract, warnings);
                }
                else
                {
                    rawExtract.MassProbeStatus = "skipped_by_options";
                }

                if (options.ScanPartMaterials)
                {
                    // 材質はパーツ付加情報とSXNET材質APIの両方を候補として保持し、ここでは推測しない。
                    new IcadMaterialProbe().Apply(globalWf, context.Assembly, rawExtract, warnings);
                }
                else
                {
                    rawExtract.MaterialProbeStatus = "skipped_by_options";
                }
                // メタデータ抽出が済んだ後にSTLを生成し、失敗しても警告として抽出結果を返せるよう分離する。
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
