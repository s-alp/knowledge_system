using System;
using IcadExtraction.SxNet;
using Xunit;

namespace IcadExtraction.SxNet.Tests
{
    public sealed class IcadCadFormatExporterTests
    {
        [Theory]
        [InlineData("step", "step", "3d", "model/step")]
        [InlineData(".stp", "step", "3d", "model/step")]
        [InlineData("dxf", "dxf", "2d", "application/dxf")]
        public void ResolveFormat_MapsSupportedFormats(string input, string extension, string mode, string mimeType)
        {
            var format = IcadCadFormatExporter.ResolveFormat(input);

            Assert.Equal(extension, format.Extension);
            Assert.Equal(mode, format.Mode);
            Assert.Equal(mimeType, format.MimeType);
            Assert.NotEmpty(format.CandidateSxOptExportFields);
            Assert.Contains(extension, format.ExportedExtensions);
        }

        [Fact]
        public void ResolveFormat_TreatsStpAsStepExportAlias()
        {
            var format = IcadCadFormatExporter.ResolveFormat("step");

            Assert.Contains("step", format.ExportedExtensions);
            Assert.Contains("stp", format.ExportedExtensions);
        }

        [Fact]
        public void ResolveFormat_RejectsUnsupportedFormat()
        {
            var exception = Assert.Throws<ArgumentException>(() => IcadCadFormatExporter.ResolveFormat("iges"));

            Assert.Contains("unsupported output-format", exception.Message);
        }

        [Fact]
        public void ListSxOptExportIntegerFields_ReturnsPublicStaticIntFields()
        {
            var fields = IcadCadFormatExporter.ListSxOptExportIntegerFields(typeof(sxnet.SxOptExport).Assembly);

            Assert.Equal(101, fields["FILE_TYPE_STEP"]);
            Assert.Equal(202, fields["FILE_TYPE_DXF"]);
            Assert.False(fields.ContainsKey("NonIntegerField"));
        }
    }
}

namespace sxnet
{
    public static class SxOptExport
    {
        public static int FILE_TYPE_STEP = 101;
        public static int FILE_TYPE_DXF = 202;
        public static string NonIntegerField = "ignore";
    }
}
