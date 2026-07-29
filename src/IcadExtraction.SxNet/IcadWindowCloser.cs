// このファイルは、自動起動したICADへ保存しない終了操作を送り、既存起動分を保護する。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

namespace IcadExtraction.SxNet
{
    /// <summary>
    /// 自動起動したICADへ保存しない終了操作を送り、既存起動分を保護する。
    /// </summary>
    internal static class IcadWindowCloser
    {
        private const uint WmClose = 0x0010;
        private const uint BmClick = 0x00F5;

        public static bool TryCloseWithoutSaving(Process process, TimeSpan timeout)
        {
            process.Refresh();
            if (process.HasExited)
            {
                return true;
            }

            var mainWindow = process.MainWindowHandle;
            if (mainWindow == IntPtr.Zero || !PostMessage(mainWindow, WmClose, IntPtr.Zero, IntPtr.Zero))
            {
                return false;
            }

            var deadline = DateTime.UtcNow.Add(timeout);
            while (DateTime.UtcNow < deadline)
            {
                process.Refresh();
                if (process.HasExited)
                {
                    return true;
                }

                foreach (var dialog in FindTopLevelWindows(process.Id))
                {
                    if (GetClassNameText(dialog) != "#32770")
                    {
                        continue;
                    }

                    var childWindows = FindChildWindows(dialog);
                    var message = string.Join("\n", childWindows.ConvertAll(GetWindowTextValue));
                    if (!IsSaveConfirmationMessage(message))
                    {
                        continue;
                    }

                    var noButton = childWindows.Find(
                        window =>
                            GetClassNameText(window) == "Button"
                            && IsDiscardButtonText(GetWindowTextValue(window))
                    );
                    if (noButton != IntPtr.Zero)
                    {
                        SendMessage(noButton, BmClick, IntPtr.Zero, IntPtr.Zero);
                    }
                }

                Thread.Sleep(100);
            }

            process.Refresh();
            return process.HasExited;
        }

        internal static bool IsSaveConfirmationMessage(string message)
        {
            if (string.IsNullOrWhiteSpace(message))
            {
                return false;
            }

            return message.IndexOf("保存しますか", StringComparison.Ordinal) >= 0
                || message.IndexOf("変更を保存", StringComparison.Ordinal) >= 0
                || message.IndexOf("保存して終了", StringComparison.Ordinal) >= 0;
        }

        internal static bool IsDiscardButtonText(string buttonText)
        {
            if (string.IsNullOrWhiteSpace(buttonText))
            {
                return false;
            }

            return buttonText.StartsWith("いいえ", StringComparison.Ordinal)
                || buttonText.StartsWith("保存しない", StringComparison.Ordinal)
                || buttonText.StartsWith("破棄", StringComparison.Ordinal)
                || buttonText.StartsWith("No", StringComparison.OrdinalIgnoreCase);
        }

        private static List<IntPtr> FindTopLevelWindows(int processId)
        {
            var windows = new List<IntPtr>();
            EnumWindows(
                (window, _) =>
                {
                    GetWindowThreadProcessId(window, out var windowProcessId);
                    if (windowProcessId == processId)
                    {
                        windows.Add(window);
                    }

                    return true;
                },
                IntPtr.Zero
            );
            return windows;
        }

        private static List<IntPtr> FindChildWindows(IntPtr parent)
        {
            var windows = new List<IntPtr>();
            EnumChildWindows(
                parent,
                (window, _) =>
                {
                    windows.Add(window);
                    return true;
                },
                IntPtr.Zero
            );
            return windows;
        }

        private static string GetWindowTextValue(IntPtr window)
        {
            var length = GetWindowTextLength(window);
            var text = new StringBuilder(length + 1);
            GetWindowText(window, text, text.Capacity);
            return text.ToString();
        }

        private static string GetClassNameText(IntPtr window)
        {
            var className = new StringBuilder(256);
            GetClassName(window, className, className.Capacity);
            return className.ToString();
        }

        private delegate bool EnumWindowsCallback(IntPtr window, IntPtr parameter);

        [DllImport("user32.dll")]
        private static extern bool EnumWindows(EnumWindowsCallback callback, IntPtr parameter);

        [DllImport("user32.dll")]
        private static extern bool EnumChildWindows(IntPtr parent, EnumWindowsCallback callback, IntPtr parameter);

        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr window, out int processId);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetWindowText(IntPtr window, StringBuilder text, int maxCount);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetWindowTextLength(IntPtr window);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetClassName(IntPtr window, StringBuilder className, int maxCount);

        [DllImport("user32.dll")]
        private static extern bool PostMessage(IntPtr window, uint message, IntPtr wParam, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern IntPtr SendMessage(IntPtr window, uint message, IntPtr wParam, IntPtr lParam);
    }
}
