// このファイルは、指定DLLが必要なSXNET型を持つか検証してから抽出処理へ渡す。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
using System;
using System.IO;
using System.Linq;
using System.Reflection;

namespace IcadExtraction.SxNet
{
    /// <summary>
    /// 指定DLLが必要なSXNET型を持つか検証してから抽出処理へ渡す。
    /// </summary>
    public sealed class SxNetRuntimeGuard
    {
        public Assembly LoadAssembly(string sxnetDllPath)
        {
            if (string.IsNullOrWhiteSpace(sxnetDllPath))
            {
                throw new InvalidOperationException("sxnet.dll path is required");
            }

            if (!File.Exists(sxnetDllPath))
            {
                throw new FileNotFoundException("sxnet.dll was not found", sxnetDllPath);
            }

            return Assembly.LoadFrom(sxnetDllPath);
        }

        public void ValidateRequiredTypes(Assembly assembly)
        {
            var requiredTypes = new[]
            {
                "sxnet.SxFileModel",
                "sxnet.SxModel",
            };

            foreach (var typeName in requiredTypes)
            {
                if (assembly.GetType(typeName, false) == null)
                {
                    throw new InvalidOperationException($"required sxnet type is missing: {typeName}");
                }
            }
        }

        public Assembly LoadAndValidateAssembly(string sxnetDllPath)
        {
            var assembly = LoadAssembly(sxnetDllPath);
            ValidateRequiredTypes(assembly);
            return assembly;
        }

        public string SelfCheck(string sxnetDllPath)
        {
            var assembly = LoadAndValidateAssembly(sxnetDllPath);
            var exported = assembly.GetExportedTypes().Select(type => type.FullName).Where(name => !string.IsNullOrWhiteSpace(name)).Take(10);
            return $"loaded={assembly.FullName}; exported={string.Join(",", exported)}";
        }
    }
}
