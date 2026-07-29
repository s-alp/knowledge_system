// このファイルは、保存確認ダイアログとICAD終了操作の選択規則を検証する。
// テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
// 外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
using IcadExtraction.SxNet;
using Xunit;

namespace IcadExtraction.SxNet.Tests
{
    /// <summary>
    /// 保存確認ダイアログとICAD終了操作の選択規則を検証する。
    /// </summary>
    public sealed class IcadWindowCloserTests
    {
        [Theory]
        [InlineData("変更があります。保存しますか？")]
        [InlineData("変更を保存して終了しますか")]
        [InlineData("保存して終了")]
        public void IsSaveConfirmationMessage_AcceptsKnownSavePrompts(string message)
        {
            Assert.True(IcadWindowCloser.IsSaveConfirmationMessage(message));
        }

        [Fact]
        public void IsSaveConfirmationMessage_RejectsUnrelatedDialog()
        {
            Assert.False(IcadWindowCloser.IsSaveConfirmationMessage("ライセンスを確認してください"));
        }

        [Theory]
        [InlineData("いいえ(N)")]
        [InlineData("保存しない")]
        [InlineData("破棄")]
        [InlineData("No")]
        public void IsDiscardButtonText_AcceptsButtonsThatDoNotSave(string buttonText)
        {
            Assert.True(IcadWindowCloser.IsDiscardButtonText(buttonText));
        }

        [Theory]
        [InlineData("はい(Y)")]
        [InlineData("保存")]
        [InlineData("キャンセル")]
        public void IsDiscardButtonText_RejectsSaveAndCancelButtons(string buttonText)
        {
            Assert.False(IcadWindowCloser.IsDiscardButtonText(buttonText));
        }
    }
}
