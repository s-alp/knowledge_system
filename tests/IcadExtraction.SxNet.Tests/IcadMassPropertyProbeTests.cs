using IcadExtraction.SxNet;
using Xunit;

namespace IcadExtraction.SxNet.Tests
{
    public sealed class IcadMassPropertyProbeTests
    {
        [Fact]
        public void MapMassProperties_MapsScalarValuesAndCenterOfGravity()
        {
            var massInfo = new FakeMassInfo
            {
                unit_type = 999,
                is_SI = false,
                density = 7.85,
                area = 1200.5,
                volume = 340.25,
                mass = 2.67,
                weight = 26.1,
                length = 0.0,
                pos = new FakePos { x = 10.0, y = 20.0, z = 30.0 },
            };

            var payload = IcadMassPropertyProbe.MapMassProperties(massInfo, 4);

            Assert.Equal(4, payload.ElementCount);
            Assert.Equal("unknown", payload.UnitName);
            Assert.Equal(999, payload.UnitType);
            Assert.Equal(7.85, payload.Density);
            Assert.Equal(1200.5, payload.Area);
            Assert.Equal(340.25, payload.Volume);
            Assert.Equal(2.67, payload.Mass);
            Assert.Equal(26.1, payload.Weight);
            Assert.Equal(10.0, payload.CenterOfGravityX);
            Assert.Equal(20.0, payload.CenterOfGravityY);
            Assert.Equal(30.0, payload.CenterOfGravityZ);
            Assert.Equal("2.67", payload.RawFields["mass"]);
        }

        public sealed class FakeMassInfo
        {
            public int unit_type;
            public bool is_SI;
            public double density;
            public double area;
            public double volume;
            public double mass;
            public double weight;
            public double length;
            public FakePos? pos;
        }

        public sealed class FakePos
        {
            public double x;
            public double y;
            public double z;
        }
    }
}
