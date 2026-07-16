using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    internal sealed class IcadMassPropertyProbe
    {
        public void Apply(object globalWf, Assembly assembly, RawExtract3DPayload payload, IList<WarningPayload> warnings)
        {
            payload.MassProbeStatus = "attempted";

            try
            {
                var extent = InvokeRequired(globalWf, "getExtent", Type.EmptyTypes, null);
                var entities = GetEntities(globalWf, assembly, extent);
                if (entities == null || entities.Length == 0)
                {
                    payload.MassProbeStatus = "no_entities";
                    warnings.Add(new WarningPayload
                    {
                        Code = "mass_probe_no_entities",
                        Message = "SxWF.getEntList returned no searchable 3D elements for mass property calculation.",
                    });
                    return;
                }

                var option = CreateMassOption(assembly);
                var massInfo = InvokeMassCalculation(assembly, option, entities);
                payload.MassProperties = MapMassProperties(massInfo, entities.Length, assembly);
                payload.MassProbeStatus = "available";
            }
            catch (Exception ex)
            {
                payload.MassProbeStatus = "failed";
                warnings.Add(new WarningPayload
                {
                    Code = "mass_probe_failed",
                    Message = "SxEnt.getMass probe failed: " + Unwrap(ex).Message,
                });
            }
        }

        internal static MassPropertyPayload MapMassProperties(object massInfo, int elementCount, Assembly? assembly = null)
        {
            var unitType = ReflectionHelpers.GetInt(massInfo, "unit_type");
            var center = ReflectionHelpers.GetMemberValue(massInfo, "pos");
            var globalMoment = ReflectionHelpers.GetMemberValue(massInfo, "inf_global_moment");
            var gravityMoment = ReflectionHelpers.GetMemberValue(massInfo, "inf_gravity_moment");
            var mainMoment = ReflectionHelpers.GetMemberValue(massInfo, "inf_main_moment");

            return new MassPropertyPayload
            {
                ElementCount = elementCount,
                UnitType = unitType,
                UnitName = ResolveUnitName(unitType, assembly),
                IsSi = ReflectionHelpers.GetBool(massInfo, "is_SI"),
                Density = ReflectionHelpers.GetDouble(massInfo, "density"),
                Area = ReflectionHelpers.GetDouble(massInfo, "area"),
                Volume = ReflectionHelpers.GetDouble(massInfo, "volume"),
                Mass = ReflectionHelpers.GetDouble(massInfo, "mass"),
                Weight = ReflectionHelpers.GetDouble(massInfo, "weight"),
                Length = ReflectionHelpers.GetDouble(massInfo, "length"),
                CenterOfGravityX = ReflectionHelpers.GetDouble(center, "x"),
                CenterOfGravityY = ReflectionHelpers.GetDouble(center, "y"),
                CenterOfGravityZ = ReflectionHelpers.GetDouble(center, "z"),
                GlobalMoment = MapMomentValues(globalMoment),
                GravityMoment = MapMomentValues(gravityMoment),
                MainMoment = MapMomentValues(mainMoment),
                RawFields = ReflectionHelpers.FlattenScalarMembers(massInfo),
            };
        }

        private static Dictionary<string, double?> MapMomentValues(object? momentInfo)
        {
            var values = new Dictionary<string, double?>(StringComparer.OrdinalIgnoreCase);
            if (momentInfo == null)
            {
                return values;
            }

            foreach (var key in new[] { "x", "y", "z", "xx", "yy", "zz", "xy", "yz", "zx", "ix", "iy", "iz", "i", "j", "k" })
            {
                var value = ReflectionHelpers.GetDouble(momentInfo, key);
                if (value.HasValue)
                {
                    values[key] = value.Value;
                }
            }

            if (values.Count > 0)
            {
                return values;
            }

            foreach (var item in ReflectionHelpers.FlattenScalarMembers(momentInfo))
            {
                if (double.TryParse(item.Value, NumberStyles.Float, CultureInfo.InvariantCulture, out var parsed)
                    || double.TryParse(item.Value, out parsed))
                {
                    values[item.Key] = parsed;
                }
            }

            return values;
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

        private static object CreateMassOption(Assembly assembly)
        {
            var optionType = assembly.GetType("sxnet.SxOptMass", throwOnError: true);
            var option = Activator.CreateInstance(optionType);
            if (option == null)
            {
                throw new InvalidOperationException("sxnet.SxOptMass could not be constructed");
            }

            var infMassType = assembly.GetType("sxnet.SxInfMass", throwOnError: true);
            var unitField = infMassType.GetField("UNIT_MM_KG", BindingFlags.Public | BindingFlags.Static);
            if (unitField != null)
            {
                ReflectionHelpers.SetMemberValue(option, "unit_type", unitField.GetValue(null));
            }

            return option;
        }

        private static object InvokeMassCalculation(Assembly assembly, object option, object[] entities)
        {
            var entityType = assembly.GetType("sxnet.SxEnt", throwOnError: true);
            var optionType = assembly.GetType("sxnet.SxOptMass", throwOnError: true);
            var entityArray = Array.CreateInstance(entityType, entities.Length);
            for (var index = 0; index < entities.Length; index++)
            {
                entityArray.SetValue(entities[index], index);
            }

            var getMassMethod = entityType.GetMethod("getMass", BindingFlags.Public | BindingFlags.Static, null, new[] { optionType, entityArray.GetType() }, null);
            if (getMassMethod == null)
            {
                throw new MissingMethodException(entityType.FullName, "getMass(SxOptMass,SxEnt[])");
            }

            var result = getMassMethod.Invoke(null, new[] { option, entityArray });
            if (result == null)
            {
                throw new InvalidOperationException("SxEnt.getMass returned null");
            }

            return result;
        }

        private static Exception Unwrap(Exception ex)
        {
            while (ex is TargetInvocationException targetInvocation && targetInvocation.InnerException != null)
            {
                ex = targetInvocation.InnerException;
            }

            return ex;
        }

        private static string ResolveUnitName(int unitType, Assembly? assembly)
        {
            if (assembly != null)
            {
                var infMassType = assembly.GetType("sxnet.SxInfMass", throwOnError: false);
                if (infMassType != null)
                {
                    var unitFields = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
                    {
                        { "UNIT_MM_G", "mm-g" },
                        { "UNIT_MM_KG", "mm-kg" },
                        { "UNIT_CM_G", "cm-g" },
                        { "UNIT_CM_KG", "cm-kg" },
                        { "UNIT_M_G", "m-g" },
                        { "UNIT_M_KG", "m-kg" },
                    };

                    foreach (var item in unitFields)
                    {
                        var field = infMassType.GetField(item.Key, BindingFlags.Public | BindingFlags.Static);
                        if (field == null)
                        {
                            continue;
                        }

                        var value = field.GetValue(null);
                        if (value != null && int.TryParse(value.ToString(), out var mapped) && mapped == unitType)
                        {
                            return item.Value;
                        }
                    }
                }
            }

            return "unknown";
        }
    }
}
