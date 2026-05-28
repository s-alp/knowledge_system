using System;
using System.Reflection;

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

        public static SxNetOpenContext OpenReadOnly(string sxnetDllPath, string inputPath)
        {
            var runtimeGuard = new SxNetRuntimeGuard();
            var assembly = runtimeGuard.LoadAssembly(sxnetDllPath);
            runtimeGuard.ValidateRequiredTypes(assembly);

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
