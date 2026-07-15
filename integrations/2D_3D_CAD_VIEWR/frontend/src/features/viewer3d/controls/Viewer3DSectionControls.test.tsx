import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Viewer3DSectionControls } from "./Viewer3DSectionControls";

describe("Viewer3DSectionControls", () => {
  it("renders clipping values and triggers section callbacks", () => {
    const onAxisChange = vi.fn();
    const onValueChange = vi.fn();

    render(
      <Viewer3DSectionControls
        clippingAxis="z"
        clippingValue={0}
        clippingMin={-1}
        clippingMax={1}
        onAxisChange={onAxisChange}
        onValueChange={onValueChange}
      />,
    );

    fireEvent.change(screen.getByDisplayValue("Z"), { target: { value: "x" } });
    fireEvent.change(screen.getByRole("slider"), { target: { value: "0.5" } });

    expect(screen.getByText("断面位置: 0.000 (-1.00 から 1.00)")).toBeInTheDocument();
    expect(onAxisChange).toHaveBeenCalledWith("x");
    expect(onValueChange).toHaveBeenCalledWith(0.5);
  });
});
