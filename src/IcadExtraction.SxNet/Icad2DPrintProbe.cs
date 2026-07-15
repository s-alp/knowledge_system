using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using IcadExtraction.Contracts;

namespace IcadExtraction.SxNet
{
    public sealed class Icad2DPrintProbe
    {
        public PrintProbeEnvelope Probe(string sxnetDllPath, string inputPath)
        {
            var warnings = new List<WarningPayload>();
            using var context = SxNetOpenContext.OpenReadOnly(sxnetDllPath, inputPath);
            var payload = new PrintProbePayload
            {
                PrintFrames = TryResolvePrintFrames(context, warnings).ToList(),
                Plotters = TryResolvePlotters(context.Assembly, warnings).ToList(),
                DefaultPlotter = TryResolveDefaultPlotter(context.Assembly, warnings),
            };

            MarkDefaultPlotter(payload);

            return new PrintProbeEnvelope
            {
                InputPath = inputPath,
                Warnings = warnings,
                PrintProbe = payload,
            };
        }

        private static IEnumerable<PrintFramePayload> TryResolvePrintFrames(SxNetOpenContext context, IList<WarningPayload> warnings)
        {
            try
            {
                return context.GetInfPrintList().Select(MapPrintFrame).ToArray();
            }
            catch (Exception exception)
            {
                warnings.Add(new WarningPayload
                {
                    Code = "print_frame_probe_failed",
                    Message = "2D print frame probing failed: " + exception.Message,
                });
                return Array.Empty<PrintFramePayload>();
            }
        }

        private static IEnumerable<PlotterPayload> TryResolvePlotters(Assembly assembly, IList<WarningPayload> warnings)
        {
            try
            {
                var plotterType = assembly.GetType("sxnet.SxInfPlot", throwOnError: true);
                var method = plotterType.GetMethod("getInfPlotList", Type.EmptyTypes);
                if (method == null)
                {
                    throw new MissingMethodException("sxnet.SxInfPlot.getInfPlotList()");
                }

                return ReflectionHelpers.Enumerate(method.Invoke(null, null))
                    .Select(MapPlotter)
                    .ToArray();
            }
            catch (Exception exception)
            {
                warnings.Add(new WarningPayload
                {
                    Code = "plotter_probe_failed",
                    Message = "ICAD plotter definition probing failed: " + exception.Message,
                });
                return Array.Empty<PlotterPayload>();
            }
        }

        private static PlotterPayload? TryResolveDefaultPlotter(Assembly assembly, IList<WarningPayload> warnings)
        {
            try
            {
                var plotterType = assembly.GetType("sxnet.SxInfPlot", throwOnError: true);
                var method = plotterType.GetMethod("getInfDefPlot", Type.EmptyTypes);
                if (method == null)
                {
                    throw new MissingMethodException("sxnet.SxInfPlot.getInfDefPlot()");
                }

                var defaultPlotter = method.Invoke(null, null);
                if (defaultPlotter == null)
                {
                    return null;
                }

                var mapped = MapPlotter(defaultPlotter);
                mapped.IsDefault = true;
                return mapped;
            }
            catch (Exception exception)
            {
                warnings.Add(new WarningPayload
                {
                    Code = "default_plotter_probe_failed",
                    Message = "ICAD default plotter probing failed: " + exception.Message,
                });
                return null;
            }
        }

        private static PrintFramePayload MapPrintFrame(object printFrame)
        {
            var dinfo = ReflectionHelpers.ExtractDoubleList(printFrame, "dinfo");
            return new PrintFramePayload
            {
                No = ReflectionHelpers.GetInt(printFrame, "no"),
                Size = ReflectionHelpers.GetString(printFrame, "size"),
                Vertical = ReflectionHelpers.GetBool(printFrame, "vertical"),
                Dinfo = dinfo,
                DrawingScale = dinfo.Count > 2 ? dinfo[2] : null,
                RangeMinX = dinfo.Count > 3 ? dinfo[3] : null,
                RangeMinY = dinfo.Count > 4 ? dinfo[4] : null,
                RangeMaxX = dinfo.Count > 5 ? dinfo[5] : null,
                RangeMaxY = dinfo.Count > 6 ? dinfo[6] : null,
            };
        }

        private static PlotterPayload MapPlotter(object plotter)
        {
            return new PlotterPayload
            {
                No = ReflectionHelpers.GetString(plotter, "no"),
                Name = ReflectionHelpers.GetString(plotter, "name"),
            };
        }

        private static void MarkDefaultPlotter(PrintProbePayload payload)
        {
            if (payload.DefaultPlotter == null)
            {
                return;
            }

            foreach (var plotter in payload.Plotters)
            {
                if (string.Equals(plotter.No, payload.DefaultPlotter.No, StringComparison.OrdinalIgnoreCase))
                {
                    plotter.IsDefault = true;
                }
            }
        }
    }
}
