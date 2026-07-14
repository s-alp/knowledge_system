using System.Linq;
using IcadExtraction.SxNet;
using Xunit;

namespace IcadExtraction.SxNet.Tests
{
    public sealed class IcadMaterialProbeTests
    {
        [Fact]
        public void MapMaterials_GroupsMaterialsAndMapsScalarFields()
        {
            var materials = new object[]
            {
                new[]
                {
                    new FakeMaterial { matid = "SUS304", name = "SUS304", spe_grav = 7.93 },
                    new FakeMaterial { matid = "SUS304", name = "SUS304", spe_grav = 7.93 },
                },
                new FakeMaterial { matid = "SUS304", name = "SUS304", spe_grav = 7.93 },
                new FakeMaterial { matid = "A5052", name = "AL", spe_grav = 2.68 },
            };

            var payload = IcadMaterialProbe.MapMaterials(materials).ToArray();

            Assert.Equal(2, payload.Length);
            Assert.Equal("SUS304", payload[0].MatId);
            Assert.Equal("SUS304", payload[0].Name);
            Assert.Equal(7.93, payload[0].SpecificGravity);
            Assert.Equal(3, payload[0].ElementCount);
            Assert.Equal("7.93", payload[0].RawFields["spe_grav"]);
            Assert.Equal("A5052", payload[1].MatId);
            Assert.Equal(1, payload[1].ElementCount);
        }

        public sealed class FakeMaterial
        {
            public string? matid;
            public string? name;
            public double spe_grav;
        }
    }
}
