// このファイルは、材質候補の取得と重複除去が想定どおりに動くことを検証する。
// テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
// 外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
using System.Linq;
using IcadExtraction.SxNet;
using Xunit;

namespace IcadExtraction.SxNet.Tests
{
    /// <summary>
    /// 材質候補の取得と重複除去が想定どおりに動くことを検証する。
    /// </summary>
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

        /// <summary>

        /// FakeMaterialに関する処理と状態を一つの責務としてまとめます。

        /// </summary>

        public sealed class FakeMaterial
        {
            public string? matid;
            public string? name;
            public double spe_grav;
        }
    }
}
