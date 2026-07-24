using System;
using System.Collections.Generic;
using System.Reflection;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    public sealed class SxNetOpenContext : IDisposable
    {
        private readonly object _model;

        private SxNetOpenContext(Assembly assembly, object model)
        {
            Assembly = assembly;
            _model = model;
        }

        public Assembly Assembly { get; }

        public object OpenedModel => _model;

        public ModelInfoPayload GetModelInfo()
        {
            var info = InvokeModelMethod("getInf");
            return new ModelInfoPayload
            {
                Name = ReflectionHelpers.GetString(info, "name"),
                Comment = ReflectionHelpers.GetString(info, "comment"),
                Path = ReflectionHelpers.GetString(info, "path"),
                IsReadOnly = ReflectionHelpers.GetBool(info, "is_read_only"),
                ViewSheetCount = ReflectionHelpers.GetInt(info, "nvs"),
                WorkPlaneCount = ReflectionHelpers.GetInt(info, "nwf"),
            };
        }

        public static SxNetOpenContext OpenReadOnly(string sxnetDllPath, string inputPath)
        {
            var runtimeGuard = new SxNetRuntimeGuard();
            var assembly = runtimeGuard.LoadAndValidateAssembly(sxnetDllPath);
            return OpenReadOnly(assembly, inputPath);
        }

        public static SxNetOpenContext OpenReadOnly(Assembly assembly, string inputPath)
        {
            var fileModelType = assembly.GetType("sxnet.SxFileModel", throwOnError: true);
            var openMethod = fileModelType.GetMethod("open", new[] { typeof(bool) });
            if (openMethod == null)
            {
                throw new MissingMethodException("sxnet.SxFileModel.open(bool) could not be resolved");
            }

            var fileModel = Activator.CreateInstance(fileModelType, inputPath);
            if (fileModel == null)
            {
                throw new InvalidOperationException("sxnet.SxFileModel could not be constructed");
            }

            var model = openMethod.Invoke(fileModel, new object[] { true });
            if (model == null)
            {
                throw new InvalidOperationException("sxnet.SxFileModel.open returned null");
            }

            return new SxNetOpenContext(assembly, model);
        }

        public object GetGlobalWf()
        {
            return InvokeModelMethod("getGlobalWF");
        }

        public object GetGlobalVs()
        {
            return InvokeModelMethod("getGlobalVS");
        }

        public IEnumerable<object> GetVsList()
        {
            return InvokeModelCollectionMethod("getVSList");
        }

        public IEnumerable<object> GetInfPrintList()
        {
            return InvokeModelCollectionMethod("getInfPrintList");
        }

        public IEnumerable<object> GetInfLayerList()
        {
            var sxSysType = Assembly.GetType("sxnet.SxSys", throwOnError: true);
            var method = sxSysType.GetMethod("getInfLayer", Type.EmptyTypes);
            if (method == null)
            {
                throw new MissingMethodException("sxnet.SxSys.getInfLayer()");
            }

            return ReflectionHelpers.Enumerate(method.Invoke(null, null));
        }

        public void ExportModel(string outputDirectory, string fileName, int fileType)
        {
            var exportMethod = _model.GetType().GetMethod("export", new[] { typeof(string), typeof(string), typeof(int) });
            if (exportMethod == null)
            {
                throw new MissingMethodException($"{_model.GetType().FullName}.export(string, string, int)");
            }

            exportMethod.Invoke(_model, new object[] { outputDirectory, fileName, fileType });
        }

        private object InvokeModelMethod(string methodName)
        {
            var method = _model.GetType().GetMethod(methodName, Type.EmptyTypes);
            if (method == null)
            {
                throw new MissingMethodException($"{_model.GetType().FullName}.{methodName}()");
            }

            var result = method.Invoke(_model, null);
            if (result == null)
            {
                throw new InvalidOperationException($"{methodName} returned null");
            }

            return result;
        }

        private IEnumerable<object> InvokeModelCollectionMethod(string methodName)
        {
            var method = _model.GetType().GetMethod(methodName, Type.EmptyTypes);
            if (method == null)
            {
                throw new MissingMethodException($"{_model.GetType().FullName}.{methodName}()");
            }

            return ReflectionHelpers.Enumerate(method.Invoke(_model, null));
        }

        public void Dispose()
        {
            TryInvoke("close");
            TryInvoke("delete");
        }

        private void TryInvoke(string methodName)
        {
            try
            {
                var method = _model.GetType().GetMethod(methodName, Type.EmptyTypes);
                method?.Invoke(_model, null);
            }
            catch
            {
                // PoC 段階では cleanup 失敗で本体エラーを上書きしない。
            }
        }
    }
}
