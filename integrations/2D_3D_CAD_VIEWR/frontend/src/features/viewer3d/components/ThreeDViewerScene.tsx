import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useLoader, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import {
  AlwaysStencilFunc,
  BackSide,
  Box3,
  Color,
  DecrementWrapStencilOp,
  DoubleSide,
  EdgesGeometry,
  FrontSide,
  Group,
  IncrementWrapStencilOp,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  NotEqualStencilFunc,
  PerspectiveCamera,
  Plane,
  PlaneGeometry,
  ReplaceStencilOp,
  Vector3,
} from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

import type { ClippingAxis } from "../state/viewer3dState";
import { analyzeClosedMesh, createCapPlaneTransform } from "../utils/meshAnalysis";

interface ThreeDViewerSceneProps {
  modelUrl: string;
  modelFormat: "stl";
  clippingEnabled: boolean;
  clippingAxis: ClippingAxis;
  clippingValue: number;
  edgeHighlightEnabled: boolean;
  resetSignal: number;
  cameraCommand: { kind: "zoomIn" | "zoomOut" | "reset"; token: number } | null;
  onBoundsResolved: (bounds: { min: number; max: number }) => void;
  onCapSupportResolved: (supported: boolean) => void;
  onReady?: () => void;
}

export function ThreeDViewerScene(props: ThreeDViewerSceneProps) {
  return (
    <div className="viewer-stage viewer-stage-3d viewer-stage-model">
      <Canvas
        gl={{ stencil: true }}
        camera={{ position: [3.5, 3.5, 3.5], fov: 45 }}
        onCreated={({ gl }) => {
          // 断面キャップは stencil clipping 前提なので、renderer 側で stencil / local clipping を有効にする。
          gl.localClippingEnabled = true;
        }}
      >
        <color attach="background" args={["#102033"]} />
        <ambientLight intensity={0.9} />
        <directionalLight intensity={1.3} position={[6, 8, 10]} />
        <Suspense fallback={null}>
          <ModelContent {...props} />
        </Suspense>
      </Canvas>
    </div>
  );
}

function ModelContent({
  modelUrl,
  modelFormat,
  clippingEnabled,
  clippingAxis,
  clippingValue,
  edgeHighlightEnabled,
  resetSignal,
  cameraCommand,
  onBoundsResolved,
  onCapSupportResolved,
  onReady,
}: ThreeDViewerSceneProps) {
  const controlsRef = useRef<any>(null);
  const { camera } = useThree();
  // UI が持つ軸と値を Three.js の Plane に変換し、STL / GLB のどちらにも同じ断面指定を渡す。
  const plane = useMemo(() => buildPlane(clippingAxis, clippingValue), [clippingAxis, clippingValue]);
  const [modelBounds, setModelBounds] = useState<Box3 | null>(null);
  const handleModelBoundsResolved = useCallback(
    (bounds: { min: number; max: number }, box: Box3) => {
      onBoundsResolved(bounds);
      setModelBounds((previous) => {
        if (previous && previous.equals(box)) {
          return previous;
        }
        return box.clone();
      });
    },
    [onBoundsResolved],
  );

  useEffect(() => {
    if (!modelBounds || !controlsRef.current) {
      return;
    }

    // 初回表示でモデル全体が収まるようにカメラを寄せ、読み込み直後でも見失いにくくする。
    const perspectiveCamera = camera as PerspectiveCamera;
    const center = modelBounds.getCenter(new Vector3());
    const size = modelBounds.getSize(new Vector3());
    const maxDim = Math.max(size.x, size.y, size.z, 1);
    const fov = (perspectiveCamera.fov * Math.PI) / 180;
    const distance = maxDim / (2 * Math.tan(fov / 2));
    const offset = distance * 1.8;

    perspectiveCamera.position.set(center.x + offset, center.y + offset, center.z + offset);
    perspectiveCamera.near = Math.max(distance / 100, 0.01);
    perspectiveCamera.far = Math.max(distance * 100, 1000);
    perspectiveCamera.updateProjectionMatrix();
    controlsRef.current.target.copy(center);
    controlsRef.current.update();
  }, [camera, modelBounds, resetSignal]);

  useEffect(() => {
    if (!cameraCommand || !controlsRef.current) {
      return;
    }

    const controls = controlsRef.current;
    const perspectiveCamera = camera as PerspectiveCamera;
    const target = controls.target.clone();
    const direction = perspectiveCamera.position.clone().sub(target);

    if (cameraCommand.kind === "zoomIn" || cameraCommand.kind === "zoomOut") {
      const factor = cameraCommand.kind === "zoomIn" ? 0.85 : 1.15;
      perspectiveCamera.position.copy(target.clone().add(direction.multiplyScalar(factor)));
      perspectiveCamera.updateProjectionMatrix();
      controls.update();
      return;
    }

    controls.update();
  }, [camera, cameraCommand]);

  return (
    <>
      {modelFormat === "stl" ? (
        <StlModel
          modelUrl={modelUrl}
          plane={plane}
          clippingEnabled={clippingEnabled}
          clippingAxis={clippingAxis}
          edgeHighlightEnabled={edgeHighlightEnabled}
          onBoundsResolved={handleModelBoundsResolved}
          onCapSupportResolved={onCapSupportResolved}
        />
      ) : (
        <GlbModel
          modelUrl={modelUrl}
          plane={plane}
          clippingEnabled={clippingEnabled}
          clippingAxis={clippingAxis}
          edgeHighlightEnabled={edgeHighlightEnabled}
          onBoundsResolved={handleModelBoundsResolved}
          onCapSupportResolved={onCapSupportResolved}
        />
      )}
      <OrbitControls ref={controlsRef} makeDefault enablePan enableZoom screenSpacePanning />
      <SceneReadySignal onReady={onReady} />
    </>
  );
}

function StlModel({
  modelUrl,
  plane,
  clippingEnabled,
  clippingAxis,
  edgeHighlightEnabled,
  onBoundsResolved,
  onCapSupportResolved,
}: {
  modelUrl: string;
  plane: Plane;
  clippingEnabled: boolean;
  clippingAxis: ClippingAxis;
  edgeHighlightEnabled: boolean;
  onBoundsResolved: (bounds: { min: number; max: number }, box: Box3) => void;
  onCapSupportResolved: (supported: boolean) => void;
}) {
  const geometry = useLoader(STLLoader, modelUrl);
  // STL は単一 geometry として扱えるため、断面キャップ可否もこの場で判定する。
  const analysis = useMemo(() => analyzeClosedMesh(geometry), [geometry]);
  const effectiveEdgeHighlightEnabled = edgeHighlightEnabled && !clippingEnabled;
  const material = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#e6eaee",
        metalness: 0.08,
        roughness: 0.52,
        side: DoubleSide,
        clippingPlanes: clippingEnabled ? [plane] : [],
      }),
    [clippingEnabled, plane],
  );
  const edgeGeometry = useMemo(
    () => (effectiveEdgeHighlightEnabled ? new EdgesGeometry(geometry, 28) : null),
    [effectiveEdgeHighlightEnabled, geometry],
  );
  const edgeMaterial = useMemo(
    () =>
      new LineBasicMaterial({
        color: "#4a5663",
        transparent: true,
        opacity: 0.9,
        clippingPlanes: clippingEnabled ? [plane] : [],
      }),
    [clippingEnabled, plane],
  );
  const capSize = useMemo(() => {
    const size = analysis.bounds.getSize(new Vector3());
    return Math.max(size.x, size.y, size.z, 1) * 3;
  }, [analysis.bounds]);
  const planeGeometry = useMemo(() => new PlaneGeometry(capSize, capSize), [capSize]);
  const stencilGroup = useMemo(
    () => (analysis.isClosed && clippingEnabled ? createPlaneStencilGroup(geometry, plane, 1) : null),
    [analysis.isClosed, clippingEnabled, geometry, plane],
  );
  const capMaterial = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#dde2e7",
        metalness: 0.03,
        roughness: 0.62,
        // 断面キャップは視点が切断面の表裏どちらに回っても同じ面として見せる。
        side: DoubleSide,
        clippingPlanes: [],
        stencilWrite: true,
        stencilRef: 0,
        stencilFunc: NotEqualStencilFunc,
        stencilFail: ReplaceStencilOp,
        stencilZFail: ReplaceStencilOp,
        stencilZPass: ReplaceStencilOp,
      }),
    [],
  );
  const capTransform = useMemo(
    () => createCapPlaneTransform(plane.normal, plane.constant),
    [plane],
  );

  useEffect(() => {
    const box = analysis.bounds.clone();
    const min = axisValue(box.min, clippingAxis);
    const max = axisValue(box.max, clippingAxis);
    // 断面スライダーの可動域は、実際の bounding box から毎回作り直す。
    onBoundsResolved({ min, max }, box);
    onCapSupportResolved(analysis.isClosed);
  }, [analysis, clippingAxis, onBoundsResolved, onCapSupportResolved]);

  return (
    <>
      {stencilGroup ? <primitive object={stencilGroup} /> : null}
      {analysis.isClosed && clippingEnabled ? (
        <mesh
          geometry={planeGeometry}
          material={capMaterial}
          position={capTransform.position}
          renderOrder={1.1}
          onAfterRender={(renderer) => renderer.clearStencil()}
          // 断面キャップ用の平面を現在の切断面へ向けて回転させる。
          onUpdate={(mesh) => mesh.lookAt(capTransform.target)}
        />
      ) : null}
      <mesh geometry={geometry} material={material} renderOrder={2}>
        {edgeGeometry ? <lineSegments geometry={edgeGeometry} material={edgeMaterial} /> : null}
      </mesh>
    </>
  );
}

function GlbModel({
  modelUrl,
  plane,
  clippingEnabled,
  clippingAxis,
  edgeHighlightEnabled,
  onBoundsResolved,
  onCapSupportResolved,
}: {
  modelUrl: string;
  plane: Plane;
  clippingEnabled: boolean;
  clippingAxis: ClippingAxis;
  edgeHighlightEnabled: boolean;
  onBoundsResolved: (bounds: { min: number; max: number }, box: Box3) => void;
  onCapSupportResolved: (supported: boolean) => void;
}) {
  const gltf = useLoader(GLTFLoader, modelUrl);
  // GLB は複数 mesh / material を含み得るため、viewer 専用に clone してから加工する。
  const root = useMemo(() => gltf.scene.clone(true), [gltf.scene]);
  const effectiveEdgeHighlightEnabled = edgeHighlightEnabled && !clippingEnabled;

  useEffect(() => {
    const box = new Box3().setFromObject(root);
    onBoundsResolved({
      min: axisValue(box.min, clippingAxis),
      max: axisValue(box.max, clippingAxis),
    }, box);
    onCapSupportResolved(false);

    root.traverse((child) => {
      const mesh = child as any;
      if (!mesh.material) {
        return;
      }
      // 読み込み結果の material を直接共有すると他の scene と干渉しやすいので clone する。
      if (Array.isArray(mesh.material)) {
        mesh.material = mesh.material.map((item: any) => item.clone());
        mesh.material.forEach((item: any) => {
          if ("color" in item && item.color) {
            item.color = new Color("#e6eaee");
          }
          item.metalness = 0.08;
          item.roughness = 0.52;
          item.clippingPlanes = clippingEnabled ? [plane] : [];
        });
      } else {
        mesh.material = mesh.material.clone();
        if ("color" in mesh.material && mesh.material.color) {
          mesh.material.color = new Color("#e6eaee");
        }
        mesh.material.metalness = 0.08;
        mesh.material.roughness = 0.52;
        mesh.material.clippingPlanes = clippingEnabled ? [plane] : [];
      }

      if (effectiveEdgeHighlightEnabled && !mesh.userData.__viewerEdgeLine && mesh.geometry) {
        // 輪郭線は元 mesh を壊さず、viewer 補助線として追加・表示切替だけ行う。
        const edgeGeometry = new EdgesGeometry(mesh.geometry, 28);
        const edgeMaterial = new LineBasicMaterial({
          color: "#4a5663",
          transparent: true,
          opacity: 0.9,
          clippingPlanes: clippingEnabled ? [plane] : [],
        });
        const edgeLines = new LineSegments(edgeGeometry, edgeMaterial);
        edgeLines.renderOrder = 2;
        mesh.add(edgeLines);
        mesh.userData.__viewerEdgeLine = edgeLines;
      }

      const existingEdgeLine = mesh.userData.__viewerEdgeLine as LineSegments | undefined;
      if (existingEdgeLine) {
        existingEdgeLine.visible = effectiveEdgeHighlightEnabled;
        if (existingEdgeLine.material instanceof LineBasicMaterial) {
          existingEdgeLine.material.clippingPlanes = clippingEnabled ? [plane] : [];
          existingEdgeLine.material.needsUpdate = true;
        }
      }
    });
  }, [root, clippingAxis, clippingEnabled, effectiveEdgeHighlightEnabled, plane, onBoundsResolved, onCapSupportResolved]);

  return <primitive object={root} />;
}

function createPlaneStencilGroup(geometry: Mesh["geometry"], plane: Plane, renderOrder: number) {
  const group = new Group();
  // stencil を使って断面内部だけを塗るため、表面と裏面を別々に数える。
  const baseMaterial = new MeshBasicMaterial();
  baseMaterial.depthWrite = false;
  baseMaterial.depthTest = false;
  baseMaterial.colorWrite = false;
  baseMaterial.stencilWrite = true;
  baseMaterial.stencilFunc = AlwaysStencilFunc;

  const backFaceMaterial = baseMaterial.clone();
  backFaceMaterial.side = BackSide;
  backFaceMaterial.clippingPlanes = [plane];
  backFaceMaterial.stencilFail = IncrementWrapStencilOp;
  backFaceMaterial.stencilZFail = IncrementWrapStencilOp;
  backFaceMaterial.stencilZPass = IncrementWrapStencilOp;

  const backMesh = new Mesh(geometry, backFaceMaterial);
  backMesh.renderOrder = renderOrder;
  group.add(backMesh);

  const frontFaceMaterial = baseMaterial.clone();
  frontFaceMaterial.side = FrontSide;
  frontFaceMaterial.clippingPlanes = [plane];
  frontFaceMaterial.stencilFail = DecrementWrapStencilOp;
  frontFaceMaterial.stencilZFail = DecrementWrapStencilOp;
  frontFaceMaterial.stencilZPass = DecrementWrapStencilOp;

  const frontMesh = new Mesh(geometry, frontFaceMaterial);
  frontMesh.renderOrder = renderOrder;
  frontMesh.scale.multiplyScalar(0.9999);
  group.add(frontMesh);

  return group;
}

function buildPlane(axis: ClippingAxis, value: number) {
  switch (axis) {
    case "x":
      return new Plane(new Vector3(-1, 0, 0), value);
    case "y":
      return new Plane(new Vector3(0, -1, 0), value);
    case "z":
    default:
      return new Plane(new Vector3(0, 0, -1), value);
  }
}

function SceneReadySignal({ onReady }: { onReady?: () => void }) {
  const notifiedRef = useRef(false);
  const { invalidate } = useThree();

  useEffect(() => {
    notifiedRef.current = false;
  }, [onReady]);

  useEffect(() => {
    if (!onReady || notifiedRef.current) {
      return;
    }

    // API 完了だけでなく初回フレーム描画後に ready を返し、UI の完了表示と揃える。
    const frameId = requestAnimationFrame(() => {
      if (!notifiedRef.current) {
        notifiedRef.current = true;
        invalidate();
        onReady();
      }
    });

    return () => cancelAnimationFrame(frameId);
  }, [invalidate, onReady]);

  return null;
}

function axisValue(vector: Vector3, axis: ClippingAxis) {
  if (axis === "x") {
    return vector.x;
  }
  if (axis === "y") {
    return vector.y;
  }
  return vector.z;
}
