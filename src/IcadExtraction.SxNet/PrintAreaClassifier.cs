// このファイルは、2D要素の代表座標が印刷枠の内側・外側・不明のどれかを判定する。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
using System;
using System.Collections.Generic;
using System.Linq;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    /// <summary>
    /// 2D要素の代表座標が印刷枠の内側・外側・不明のどれかを判定する。
    /// </summary>
    internal static class PrintAreaClassifier
    {
        public static PrintAreaClassificationResult Resolve(IEnumerable<PrintFramePayload> printFrames, double? x, double? y)
        {
            if (!x.HasValue || !y.HasValue)
            {
                return PrintAreaClassificationResult.Unknown();
            }

            var usableFrames = printFrames
                .Where(frame =>
                    frame.RangeMinX.HasValue &&
                    frame.RangeMinY.HasValue &&
                    frame.RangeMaxX.HasValue &&
                    frame.RangeMaxY.HasValue)
                .ToArray();
            if (usableFrames.Length == 0)
            {
                return PrintAreaClassificationResult.Unknown();
            }

            foreach (var frame in usableFrames.OrderBy(frame => frame.No))
            {
                var minX = Math.Min(frame.RangeMinX!.Value, frame.RangeMaxX!.Value);
                var maxX = Math.Max(frame.RangeMinX!.Value, frame.RangeMaxX!.Value);
                var minY = Math.Min(frame.RangeMinY!.Value, frame.RangeMaxY!.Value);
                var maxY = Math.Max(frame.RangeMinY!.Value, frame.RangeMaxY!.Value);
                if (x.Value >= minX && x.Value <= maxX && y.Value >= minY && y.Value <= maxY)
                {
                    return PrintAreaClassificationResult.Inside(frame.No);
                }
            }

            return PrintAreaClassificationResult.Outside();
        }
    }

    /// <summary>

    /// PrintAreaClassificationResultに関する処理と状態を一つの責務としてまとめます。

    /// </summary>

    internal sealed class PrintAreaClassificationResult
    {
        private PrintAreaClassificationResult(bool? insidePrintArea, int? printFrameNo)
        {
            InsidePrintArea = insidePrintArea;
            PrintFrameNo = printFrameNo;
        }

        public bool? InsidePrintArea { get; }
        public int? PrintFrameNo { get; }

        public static PrintAreaClassificationResult Inside(int printFrameNo)
        {
            return new PrintAreaClassificationResult(true, printFrameNo);
        }

        public static PrintAreaClassificationResult Outside()
        {
            return new PrintAreaClassificationResult(false, null);
        }

        public static PrintAreaClassificationResult Unknown()
        {
            return new PrintAreaClassificationResult(null, null);
        }
    }
}
