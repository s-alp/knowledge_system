using IcadExtraction.SxNet;
using Xunit;

namespace IcadExtraction.SxNet.Tests
{
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
