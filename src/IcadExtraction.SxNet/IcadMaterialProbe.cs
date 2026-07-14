using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    internal sealed class IcadMaterialProbe
    {
        public void Apply(object globalWf, Assembly assembly, RawExtract3DPayload payload, IList<WarningPayload> warnings)
        {
            payload.MaterialProbeStatus = "attempted";

            try
            {
                var extent = InvokeRequired(globalWf, "getExtent", Type.EmptyTypes, null);
                var entities = GetEntities(globalWf, assembly, extent);
                if (entities == null || entities.Length == 0)
                {
                    payload.MaterialProbeStatus = "no_entities";
                    warnings.Add(new WarningPayload
                    {
                        Code = "material_probe_no_entities",
                        Message = "SxWF.getEntList returned no searchable 3D elements for material extraction.",
                    });
                    return;
                }

            var materialInfos = InvokeMaterialList(assembly, entities);
            payload.Materials = MapMaterials(materialInfos).ToList();
                payload.MaterialProbeStatus = payload.Materials.Count > 0 ? "available" : "no_materials";
            }
            catch (Exception ex)
            {
                payload.MaterialProbeStatus = "failed";
                warnings.Add(new WarningPayload
                {
                    Code = "material_probe_failed",
                    Message = "SxEnt.getInfMaterialList probe failed: " + Unwrap(ex).Message,
                });
            }
        }

        internal static IEnumerable<MaterialPayload> MapMaterials(IEnumerable<object> materialInfos)
        {
            return materialInfos
                .SelectMany(FlattenMaterialInfos)
                .Select(MapMaterial)
                .GroupBy(item => new
                {
                    MatId = item.MatId ?? string.Empty,
                    Name = item.Name ?? string.Empty,
                    SpecificGravity = item.SpecificGravity,
                })
                .Select(group =>
                {
                    var first = group.First();
                    first.ElementCount = group.Count();
                    return first;
                });
        }

        private static MaterialPayload MapMaterial(object materialInfo)
        {
            return new MaterialPayload
            {
                MatId = ReflectionHelpers.GetString(materialInfo, "matid"),
                Name = ReflectionHelpers.GetString(materialInfo, "name"),
                SpecificGravity = ReflectionHelpers.GetDouble(materialInfo, "spe_grav"),
                ElementCount = 1,
                RawFields = ReflectionHelpers.FlattenScalarMembers(materialInfo),
            };
        }

        private static object InvokeRequired(object target, string methodName, Type[] parameterTypes, object[]? arguments)
        {
            var method = target.GetType().GetMethod(methodName, parameterTypes);
            if (method == null)
            {
                throw new MissingMethodException(target.GetType().FullName, methodName);
            }

            var result = method.Invoke(target, arguments);
            if (result == null)
            {
                throw new InvalidOperationException(methodName + " returned null");
            }

            return result;
        }

        private static object[] GetEntities(object globalWf, Assembly assembly, object extent)
        {
            var boxType = assembly.GetType("sxnet.SxBox", throwOnError: true);
            var getEntListMethod = globalWf.GetType().GetMethod("getEntList", new[] { boxType, typeof(bool) });
            if (getEntListMethod == null)
            {
                throw new MissingMethodException(globalWf.GetType().FullName, "getEntList(SxBox,bool)");
            }

            var entities = getEntListMethod.Invoke(globalWf, new[] { extent, false });
            return ReflectionHelpers.Enumerate(entities).ToArray();
        }

        private static object[] InvokeMaterialList(Assembly assembly, object[] entities)
        {
            var entityType = assembly.GetType("sxnet.SxEnt", throwOnError: true);
            var entityArray = Array.CreateInstance(entityType, entities.Length);
            for (var index = 0; index < entities.Length; index++)
            {
                entityArray.SetValue(entities[index], index);
            }

            var getMaterialMethod = entityType.GetMethod("getInfMaterialList", BindingFlags.Public | BindingFlags.Static, null, new[] { entityArray.GetType() }, null);
            if (getMaterialMethod == null)
            {
                throw new MissingMethodException(entityType.FullName, "getInfMaterialList(SxEnt[])");
            }

            var result = getMaterialMethod.Invoke(null, new[] { entityArray });
            return FlattenMaterialInfos(result).ToArray();
        }

        private static IEnumerable<object> FlattenMaterialInfos(object? value)
        {
            foreach (var item in ReflectionHelpers.Enumerate(value))
            {
                if (item == null)
                {
                    continue;
                }

                if (item is IEnumerable && !(item is string) && !string.Equals(item.GetType().Name, "SxInfMaterial", StringComparison.Ordinal))
                {
                    foreach (var nested in FlattenMaterialInfos(item))
                    {
                        yield return nested;
                    }
                    continue;
                }

                yield return item;
            }
        }

        private static Exception Unwrap(Exception ex)
        {
            while (ex is TargetInvocationException targetInvocation && targetInvocation.InnerException != null)
            {
                ex = targetInvocation.InnerException;
            }

            return ex;
        }
    }
}
