import type { ClippingAxis } from "../state/viewer3dState";

interface Viewer3DSectionControlsProps {
  clippingAxis: ClippingAxis;
  clippingValue: number;
  clippingMin: number;
  clippingMax: number;
  onAxisChange: (axis: ClippingAxis) => void;
  onValueChange: (value: number) => void;
}

export function Viewer3DSectionControls({
  clippingAxis,
  clippingValue,
  clippingMin,
  clippingMax,
  onAxisChange,
  onValueChange,
}: Viewer3DSectionControlsProps) {
  return (
    <div className="slider-row viewer-section-controls-shell">
      <span>
        断面位置: {clippingValue.toFixed(3)} ({clippingMin.toFixed(2)} から {clippingMax.toFixed(2)})
      </span>
      <div className="toolbar slider-toolbar">
        <label className="input-stack inline-select-stack">
          <span>軸</span>
          <select value={clippingAxis} onChange={(event) => onAxisChange(event.target.value as ClippingAxis)}>
            <option value="x">X</option>
            <option value="y">Y</option>
            <option value="z">Z</option>
          </select>
        </label>
        <input
          type="range"
          min={clippingMin}
          max={clippingMax}
          step="0.01"
          value={clippingValue}
          onChange={(event) => onValueChange(Number(event.target.value))}
        />
      </div>
    </div>
  );
}
