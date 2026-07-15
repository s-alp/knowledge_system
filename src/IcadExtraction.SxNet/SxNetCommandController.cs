using System;
using System.Reflection;

namespace IcadExtraction.SxNet
{
    public sealed class SxNetCommandController
    {
        public void Cancel(string sxnetDllPath, int port)
        {
            var sxSysType = Initialize(sxnetDllPath, port);
            var cancelMethod = sxSysType.GetMethod("cancel", Type.EmptyTypes);
            if (cancelMethod == null)
            {
                throw new MissingMethodException("sxnet.SxSys.cancel()");
            }

            cancelMethod.Invoke(null, null);
        }

        public string GetAndClearCommand(string sxnetDllPath, int port)
        {
            var sxSysType = Initialize(sxnetDllPath, port);
            var getCommandMethod = sxSysType.GetMethod("getCommand", Type.EmptyTypes);
            if (getCommandMethod == null)
            {
                throw new MissingMethodException("sxnet.SxSys.getCommand()");
            }

            return Convert.ToString(getCommandMethod.Invoke(null, null)) ?? string.Empty;
        }

        private static Type Initialize(string sxnetDllPath, int port)
        {
            var assembly = Assembly.LoadFrom(sxnetDllPath);
            var sxSysType = assembly.GetType("sxnet.SxSys", throwOnError: true);
            var initMethod = sxSysType.GetMethod("init", new[] { typeof(int) });
            if (initMethod == null)
            {
                throw new MissingMethodException("sxnet.SxSys.init(int)");
            }

            initMethod.Invoke(null, new object[] { port });
            return sxSysType;
        }
    }
}
