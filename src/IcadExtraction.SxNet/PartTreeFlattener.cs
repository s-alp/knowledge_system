using System.Collections.Generic;
using System.Text.RegularExpressions;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    public sealed class PartTreeFlattener
    {
        public RawExtract3DPayload Flatten(object rootNode, string? topPartExInfo)
        {
            var payload = new RawExtract3DPayload();
            var rootInf = ReflectionHelpers.GetMemberValue(rootNode, "inf");
            payload.TopPart = new TopPartPayload
            {
                Name = ReflectionHelpers.GetString(rootInf, "name"),
                Comment = ReflectionHelpers.GetString(rootInf, "comment"),
                ExInfo = topPartExInfo ?? ReflectionHelpers.GetString(rootNode, "ex_inf"),
            };
            payload.TopPart.ExInfoFields = ParseExInfoFields(payload.TopPart.ExInfo);

            VisitNode(rootNode, new List<string>(), payload.Parts);
            return payload;
        }

        private void VisitNode(object node, List<string> ancestorPath, List<PartPayload> output)
        {
            var info = ReflectionHelpers.GetMemberValue(node, "inf");
            var name = ReflectionHelpers.GetString(info, "name");
            var currentPath = new List<string>(ancestorPath);
            if (!string.IsNullOrWhiteSpace(name))
            {
                currentPath.Add(name!);
            }

            if (info != null)
            {
                var exInfo = ReflectionHelpers.GetString(node, "ex_inf");
                output.Add(new PartPayload
                {
                    TreePath = currentPath,
                    Name = name,
                    Comment = ReflectionHelpers.GetString(info, "comment"),
                    ExInfo = exInfo,
                    ExInfoFields = ParseExInfoFields(exInfo),
                    RefModelName = ReflectionHelpers.GetString(info, "ref_model_name"),
                    RefModelPath = ReflectionHelpers.GetString(info, "path"),
                    IsExternal = ReflectionHelpers.GetBool(info, "is_external"),
                    IsMirror = ReflectionHelpers.GetBool(info, "is_mirror"),
                    IsReadOnly = ReflectionHelpers.GetBool(info, "is_read_only"),
                    IsUnloaded = ReflectionHelpers.GetBool(info, "is_unloaded"),
                });
            }

            foreach (var child in ReflectionHelpers.Enumerate(ReflectionHelpers.GetMemberValue(node, "child_list")))
            {
                VisitNode(child, currentPath, output);
            }
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
    }
}
