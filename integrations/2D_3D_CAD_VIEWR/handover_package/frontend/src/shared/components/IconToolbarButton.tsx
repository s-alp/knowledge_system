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
