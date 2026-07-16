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
                inf_global_moment = new FakeMoment { x = 1.1, y = 2.2, z = 3.3 },
                inf_gravity_moment = new FakeMoment { ix = 4.4, iy = 5.5, iz = 6.6 },
                inf_main_moment = new FakeRawMoment { Ixx = 7.7, Iyy = 8.8 },
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
            Assert.Equal(1.1, payload.GlobalMoment["x"]);
            Assert.Equal(2.2, payload.GlobalMoment["y"]);
            Assert.Equal(3.3, payload.GlobalMoment["z"]);
            Assert.Equal(4.4, payload.GravityMoment["ix"]);
            Assert.Equal(5.5, payload.GravityMoment["iy"]);
            Assert.Equal(6.6, payload.GravityMoment["iz"]);
            Assert.Equal(7.7, payload.MainMoment["Ixx"]);
            Assert.Equal(8.8, payload.MainMoment["Iyy"]);
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
            public FakeMoment? inf_global_moment;
            public FakeMoment? inf_gravity_moment;
            public FakeRawMoment? inf_main_moment;
        }

        public sealed class FakePos
        {
            public double x;
            public double y;
            public double z;
        }

        public sealed class FakeMoment
        {
            public double x;
            public double y;
            public double z;
            public double ix;
            public double iy;
            public double iz;
        }

        public sealed class FakeRawMoment
        {
            public double Ixx;
            public double Iyy;
        }
    }
}
