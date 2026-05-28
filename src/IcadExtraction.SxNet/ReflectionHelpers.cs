using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;

namespace IcadExtraction.SxNet
{
    internal static class ReflectionHelpers
    {
        public static object? GetMemberValue(object? instance, string memberName)
        {
            if (instance == null)
            {
                return null;
            }

            var type = instance.GetType();
            var property = type.GetProperty(memberName, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
            if (property != null)
            {
                return property.GetValue(instance, null);
            }

            var field = type.GetField(memberName, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
            return field?.GetValue(instance);
        }

        public static string? GetString(object? instance, string memberName)
        {
            var value = GetMemberValue(instance, memberName);
            if (value == null)
            {
                return null;
            }

            var text = value.ToString();
            return string.IsNullOrWhiteSpace(text) ? null : text;
        }

        public static bool GetBool(object? instance, string memberName)
        {
            var value = GetMemberValue(instance, memberName);
            if (value is bool boolean)
            {
                return boolean;
            }

            return false;
        }

        public static int GetInt(object? instance, string memberName)
        {
            var value = GetMemberValue(instance, memberName);
            if (value is int number)
            {
                return number;
            }

            if (value != null && int.TryParse(value.ToString(), out var parsed))
            {
                return parsed;
            }

            return 0;
        }

        public static IEnumerable<object> Enumerate(object? instance)
        {
            if (instance == null)
            {
                return Enumerable.Empty<object>();
            }

            if (instance is string)
            {
                return new[] { instance };
            }

            if (instance is IEnumerable enumerable)
            {
                var items = new List<object>();
                foreach (var item in enumerable)
                {
                    if (item != null)
                    {
                        items.Add(item);
                    }
                }

                return items;
            }

            return new[] { instance };
        }

        public static List<string> ExtractStringList(object? instance, string memberName)
        {
            var value = GetMemberValue(instance, memberName);
            return Enumerate(value)
                .Select(item => item.ToString())
                .Where(item => !string.IsNullOrWhiteSpace(item))
                .Select(item => item!.Trim())
                .ToList();
        }

        public static Dictionary<string, string> FlattenScalarMembers(object? instance)
        {
            var flattened = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            if (instance == null)
            {
                return flattened;
            }

            var members = instance.GetType()
                .GetMembers(BindingFlags.Public | BindingFlags.Instance)
                .Where(member => member.MemberType == MemberTypes.Field || member.MemberType == MemberTypes.Property);

            foreach (var member in members)
            {
                object? value = member.MemberType == MemberTypes.Field
                    ? ((FieldInfo)member).GetValue(instance)
                    : ((PropertyInfo)member).GetValue(instance, null);
                if (value == null)
                {
                    continue;
                }

                if (value is string text)
                {
                    if (!string.IsNullOrWhiteSpace(text))
                    {
                        flattened[member.Name] = text.Trim();
                    }
                    continue;
                }

                var valueType = value.GetType();
                if (valueType.IsPrimitive || value is decimal)
                {
                    flattened[member.Name] = Convert.ToString(value)!;
                    continue;
                }

                if (value is IEnumerable enumerable && !(value is string))
                {
                    var values = new List<string>();
                    foreach (var item in enumerable)
                    {
                        if (item == null)
                        {
                            continue;
                        }
                        var scalar = item.ToString();
                        if (!string.IsNullOrWhiteSpace(scalar))
                        {
                            values.Add(scalar.Trim());
                        }
                    }
                    if (values.Count > 0)
                    {
                        flattened[member.Name] = string.Join(" / ", values);
                    }
                }
            }

            return flattened;
        }

        public static string BuildSummaryText(object? instance)
        {
            var flattened = FlattenScalarMembers(instance);
            return string.Join("; ", flattened.Select(item => item.Key + "=" + item.Value));
        }
    }
}
