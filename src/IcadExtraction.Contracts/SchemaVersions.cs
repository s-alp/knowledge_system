// このファイルは、Django側が判定できるよう、C#抽出JSONのスキーマ版番号を一か所で定義する。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
namespace IcadExtraction.Contracts
{
    /// <summary>
    /// Django側が判定できるよう、C#抽出JSONのスキーマ版番号を一か所で定義する。
    /// </summary>
    public static class SchemaVersions
    {
        public const string SchemaVersion = "1.0.0";
        public const string ExtractorName = "icad-csharp-extractor";
    }
}
