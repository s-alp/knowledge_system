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
            Assert.Equal(new List<string> { "Top", "ChildA", "Leaf" }, payload.Parts[2].TreePath);
        }

        public sealed class FakePartTree
        {
            public FakePartInfo? inf;
            public string? ex_inf;
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
    }
}
