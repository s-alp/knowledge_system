// このファイルは、2D/3D操作アイコンの見た目とアクセシビリティ属性を共通化する。
// 初めて読むときは、公開されている入口から呼び出し先を順に追う。
// 外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
import type { ReactNode } from "react";

interface IconToolbarButtonProps {
  ariaLabel: string;
  children: ReactNode;
  disabled?: boolean;
  onClick?: () => void;
}

export function IconToolbarButton({
  ariaLabel,
  children,
  disabled = false,
  onClick,
}: IconToolbarButtonProps) {
  return (
    <button
      type="button"
      className="icon-toolbar-button"
      aria-label={ariaLabel}
      title={ariaLabel}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
