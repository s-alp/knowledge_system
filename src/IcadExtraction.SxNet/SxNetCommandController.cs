// このファイルは、SXNETへキャンセル・クリアなどの制御コマンドを送る小さな境界を提供する。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
using System;
using System.Reflection;

namespace IcadExtraction.SxNet
{
    /// <summary>
    /// SXNETへキャンセル・クリアなどの制御コマンドを送る小さな境界を提供する。
    /// </summary>
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
