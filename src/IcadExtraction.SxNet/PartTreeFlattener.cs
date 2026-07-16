using System.Collections.Generic;
using System.Text.RegularExpressions;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    public sealed class PartTreeFlattener
    {
        public RawExtract3DPayload Flatten(object rootNode, string? topPartExInfo, List<WarningPayload>? warnings = null)
        {
            return Flatten(rootNode, topPartExInfo, warnings, scanPartMaterials: true, scanPartExtendedInfo: true);
        }

        public RawExtract3DPayload Flatten(
            object rootNode,
            string? topPartExInfo,
            List<WarningPayload>? warnings,
            bool scanPartMaterials,
            bool scanPartExtendedInfo)
        {
            var payload = new RawExtract3DPayload();
            var rootInf = ReflectionHelpers.GetMemberValue(rootNode, "inf");
            var resolvedTopPartExInfo = scanPartExtendedInfo ? topPartExInfo ?? ReflectionHelpers.GetString(rootNode, "ex_inf") : null;
            payload.TopPart = new TopPartPayload
            {
                Name = ReflectionHelpers.GetString(rootInf, "name"),
                Comment = ReflectionHelpers.GetString(rootInf, "comment"),
                ExInfo = resolvedTopPartExInfo,
            };
            payload.TopPart.ExInfoFields = ParseExInfoFields(payload.TopPart.ExInfo);

            var sequence = 0;
            VisitNode(rootNode, new List<string>(), null, payload.Parts, warnings, scanPartMaterials, scanPartExtendedInfo, ref sequence);
            return payload;
        }

        private void VisitNode(
            object node,
            List<string> ancestorPath,
            string? parentNodeId,
            List<PartPayload> output,
            List<WarningPayload>? warnings,
            bool scanPartMaterials,
            bool scanPartExtendedInfo,
            ref int sequence)
        {
            var info = ReflectionHelpers.GetMemberValue(node, "inf");
            var name = ReflectionHelpers.GetString(info, "name");
            var currentPath = new List<string>(ancestorPath);
            if (!string.IsNullOrWhiteSpace(name))
            {
                currentPath.Add(name!);
            }

            var children = new List<object>(ReflectionHelpers.Enumerate(ReflectionHelpers.GetMemberValue(node, "child_list")));
            var nodeId = $"node-{sequence:D6}";
            sequence += 1;

            if (info != null)
            {
                var exInfo = scanPartExtendedInfo ? ReflectionHelpers.GetString(node, "ex_inf") : null;
                var refModelName = ReflectionHelpers.GetString(info, "ref_model_name");
                var refModelPath = ReflectionHelpers.GetString(info, "path");
                var isExternal = ReflectionHelpers.GetBool(info, "is_external");
                var hasExternalReference = isExternal || !string.IsNullOrWhiteSpace(refModelName) || !string.IsNullOrWhiteSpace(refModelPath);
                output.Add(new PartPayload
                {
                    NodeId = nodeId,
                    ParentNodeId = parentNodeId,
                    Depth = ancestorPath.Count,
                    ChildCount = children.Count,
                    EntityKind = ResolveEntityKind(children.Count, ancestorPath.Count, hasExternalReference),
                    TreePath = currentPath,
                    Name = name,
                    Comment = ReflectionHelpers.GetString(info, "comment"),
                    ExInfo = exInfo,
                    ExInfoFields = ParseExInfoFields(exInfo),
                    RefModelName = refModelName,
                    RefModelPath = refModelPath,
                    IsExternal = isExternal,
                    IsMirror = ReflectionHelpers.GetBool(info, "is_mirror"),
                    IsReadOnly = ReflectionHelpers.GetBool(info, "is_read_only"),
                    IsUnloaded = ReflectionHelpers.GetBool(info, "is_unloaded"),
                    Materials = scanPartMaterials ? ExtractPartMaterials(node, currentPath, warnings) : new List<MaterialPayload>(),
                });
            }

            foreach (var child in children)
            {
                VisitNode(
                    child,
                    currentPath,
                    info != null ? nodeId : parentNodeId,
                    output,
                    warnings,
                    scanPartMaterials,
                    scanPartExtendedInfo,
                    ref sequence
                );
            }
        }

        private static string ResolveEntityKind(int childCount, int depth, bool hasExternalReference)
        {
            if (childCount == 0)
            {
                return "part";
            }
            if (depth == 0)
            {
                return "assembly";
            }
            return hasExternalReference ? "subassembly" : "assembly";
        }

        private static Dictionary<string, string> ParseExInfoFields(string? exInfo)
        {
            var fields = new Dictionary<string, string>();
            if (string.IsNullOrWhiteSpace(exInfo))
            {
                return fields;
            }

            foreach (Match match in Regex.Matches(exInfo, "(?:\"(?<key_quoted>[^\"]+)\"|(?<key>[^,\\s]+))\\s*,\\s*\"(?<value>[^\"]*)\""))
            {
                var key = (match.Groups["key_quoted"].Success ? match.Groups["key_quoted"].Value : match.Groups["key"].Value).Trim();
                if (key.Length == 0)
                {
                    continue;
                }

                fields[key] = match.Groups["value"].Value.Trim();
            }

            return fields;
        }

        private static List<MaterialPayload> ExtractPartMaterials(object node, List<string> partPath, List<WarningPayload>? warnings)
        {
            var entPart = ReflectionHelpers.GetMemberValue(node, "entpart");
            var getInfMaterialList = entPart?.GetType().GetMethod("getInfMaterialList", System.Type.EmptyTypes);
            if (getInfMaterialList == null)
            {
                return new List<MaterialPayload>();
            }

            try
            {
                var materialInfos = getInfMaterialList.Invoke(entPart, null);
                return new List<MaterialPayload>(IcadMaterialProbe.MapMaterials(ReflectionHelpers.Enumerate(materialInfos)));
            }
            catch (System.Reflection.TargetInvocationException ex)
            {
                AddPartMaterialWarning(partPath, ex.InnerException ?? ex, warnings);
                return new List<MaterialPayload>();
            }
            catch (System.Runtime.InteropServices.COMException ex)
            {
                AddPartMaterialWarning(partPath, ex, warnings);
                return new List<MaterialPayload>();
            }
        }

        private static void AddPartMaterialWarning(List<string> partPath, System.Exception ex, List<WarningPayload>? warnings)
        {
            if (warnings == null)
            {
                return;
            }

            var path = partPath.Count == 0 ? "(unknown)" : string.Join(".", partPath);
            warnings.Add(new WarningPayload
            {
                Code = "part_material_probe_failed",
                Message = $"部品材質の取得に失敗しました。part_path={path}; {ex.GetType().Name}: {ex.Message}",
            });
        }
    }
}
