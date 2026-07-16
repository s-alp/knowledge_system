using System.Collections.Generic;
using IcadExtraction.SxNet;
using Xunit;

namespace IcadExtraction.SxNet.Tests
{
    public sealed class PartTreeFlattenerTests
    {
        [Fact]
        public void Flatten_FlattensNestedChildren()
        {
            var root = new FakePartTree
            {
                inf = new FakePartInfo { name = "Top", comment = "root" },
                ex_inf = "root ex",
                child_list = new[]
                {
                    new FakePartTree
                    {
                        inf = new FakePartInfo
                        {
                            name = "ChildA",
                            comment = "comment-a",
                            ref_model_name = "ref-a",
                            path = @"C:\ref-a.icd",
                            is_external = true,
                        },
                        ex_inf = "User_WBZAI1,\"RM\",\"User_WCMNA\",\"ＳＵＳ\"",
                        entpart = new FakeEntPart
                        {
                            Materials = new[]
                            {
                                new FakeMaterial { matid = "SUS304", name = "SUS304", spe_grav = 7.93 },
                                new FakeMaterial { matid = "SUS304", name = "SUS304", spe_grav = 7.93 },
                            }
                        },
                        child_list = new[]
                        {
                            new FakePartTree
                            {
                                inf = new FakePartInfo { name = "Leaf", comment = "leaf" },
                            }
                        }
                    }
                }
            };

            var payload = new PartTreeFlattener().Flatten(root, "top ex");
            Assert.Equal("Top", payload.TopPart.Name);
            Assert.Equal("top ex", payload.TopPart.ExInfo);
            Assert.Equal(3, payload.Parts.Count);
            Assert.Equal("RM", payload.Parts[1].ExInfoFields["User_WBZAI1"]);
            Assert.Equal("ＳＵＳ", payload.Parts[1].ExInfoFields["User_WCMNA"]);
            Assert.Single(payload.Parts[1].Materials);
            Assert.Equal("SUS304", payload.Parts[1].Materials[0].MatId);
            Assert.Equal(2, payload.Parts[1].Materials[0].ElementCount);
            Assert.Empty(payload.Parts[2].Materials);
            Assert.Equal(new List<string> { "Top", "ChildA", "Leaf" }, payload.Parts[2].TreePath);
            Assert.Equal("assembly", payload.Parts[0].EntityKind);
            Assert.Equal("subassembly", payload.Parts[1].EntityKind);
            Assert.Equal("part", payload.Parts[2].EntityKind);
        }

        [Fact]
        public void Flatten_DoesNotTreatInternalChildContainerAsSubassembly()
        {
            var root = new FakePartTree
            {
                inf = new FakePartInfo { name = "Top" },
                child_list = new[]
                {
                    new FakePartTree
                    {
                        inf = new FakePartInfo
                        {
                            name = "InternalContainer",
                            is_external = false,
                        },
                        child_list = new[]
                        {
                            new FakePartTree
                            {
                                inf = new FakePartInfo { name = "Leaf" },
                            }
                        }
                    }
                }
            };

            var payload = new PartTreeFlattener().Flatten(root, null);

            Assert.Equal(3, payload.Parts.Count);
            Assert.Equal("assembly", payload.Parts[0].EntityKind);
            Assert.Equal("assembly", payload.Parts[1].EntityKind);
            Assert.Equal("part", payload.Parts[2].EntityKind);
        }

        [Fact]
        public void Flatten_TreatsReferencedChildContainerAsSubassemblyEvenWhenExternalFlagIsFalse()
        {
            var root = new FakePartTree
            {
                inf = new FakePartInfo { name = "Top" },
                child_list = new[]
                {
                    new FakePartTree
                    {
                        inf = new FakePartInfo
                        {
                            name = "ReferencedContainer",
                            ref_model_name = "REF-001",
                            path = @"J:\ref\REF-001.icd",
                            is_external = false,
                        },
                        child_list = new[]
                        {
                            new FakePartTree
                            {
                                inf = new FakePartInfo { name = "Leaf" },
                            }
                        }
                    }
                }
            };

            var payload = new PartTreeFlattener().Flatten(root, null);

            Assert.Equal("subassembly", payload.Parts[1].EntityKind);
        }

        [Fact]
        public void Flatten_RespectsMaterialAndExtendedInfoOptions()
        {
            var root = new FakePartTree
            {
                inf = new FakePartInfo { name = "Top", comment = "root" },
                ex_inf = "User_TOP,\"TOP-EX\"",
                child_list = new[]
                {
                    new FakePartTree
                    {
                        inf = new FakePartInfo { name = "ChildA", comment = "comment-a" },
                        ex_inf = "User_WCMNA,\"ＳＵＳ\"",
                        entpart = new FakeEntPart
                        {
                            Materials = new[]
                            {
                                new FakeMaterial { matid = "SUS304", name = "SUS304", spe_grav = 7.93 },
                            }
                        },
                    }
                }
            };

            var payload = new PartTreeFlattener().Flatten(
                root,
                "top ex",
                warnings: null,
                scanPartMaterials: false,
                scanPartExtendedInfo: false
            );

            Assert.Null(payload.TopPart.ExInfo);
            Assert.Empty(payload.TopPart.ExInfoFields);
            Assert.Equal(2, payload.Parts.Count);
            Assert.Null(payload.Parts[1].ExInfo);
            Assert.Empty(payload.Parts[1].ExInfoFields);
            Assert.Empty(payload.Parts[1].Materials);
        }

        public sealed class FakePartTree
        {
            public FakePartInfo? inf;
            public string? ex_inf;
            public FakeEntPart? entpart;
            public FakePartTree[]? child_list;
        }

        public sealed class FakePartInfo
        {
            public string? name;
            public string? comment;
            public string? ref_model_name;
            public string? path;
            public bool is_external;
            public bool is_mirror;
            public bool is_read_only;
            public bool is_unloaded;
        }

        public sealed class FakeEntPart
        {
            public FakeMaterial[]? Materials { get; set; }

            public FakeMaterial[]? getInfMaterialList()
            {
                return Materials;
            }
        }

        public sealed class FakeMaterial
        {
            public string? matid;
            public string? name;
            public double spe_grav;
        }
    }
}
