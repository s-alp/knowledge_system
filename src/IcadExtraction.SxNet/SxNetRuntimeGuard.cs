using System;
using System.IO;
using System.Linq;
using System.Reflection;

namespace IcadExtraction.SxNet
{
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

        public string SelfCheck(string sxnetDllPath)
        {
            var assembly = LoadAssembly(sxnetDllPath);
            ValidateRequiredTypes(assembly);
            var exported = assembly.GetExportedTypes().Select(type => type.FullName).Where(name => !string.IsNullOrWhiteSpace(name)).Take(10);
            return $"loaded={assembly.FullName}; exported={string.Join(",", exported)}";
        }
    }
}
