import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const MODES = {
  room: {
    url: "/assets/room.glb",
    kicker: "SPACE TWIN",
    title: "Bedroom",
    summary: "当前 Sweet Home 3D 房间的只读 Web 视图。",
    assumption: "房间 GLB 来自当前 Sweet Home 3D 场景导出；canonical 空间尺寸仍然是事实源。"
  },
  combined: {
    url: "/assets/scene-combined.glb",
    kicker: "PERSONAL TWIN",
    title: "Integrated Room + Body",
    summary: "真实房间与坐姿 Body Twin 已通过 Sweet Home 3D 锚点统一到同一坐标系。",
    assumption: "组合场景使用已验证的 room ↔ ergonomics transform；房间、人体和测量事实仍由各自 canonical/source 数据维护。"
  },
  standing: {
    url: "/assets/avatar-standing.glb",
    kicker: "BODY TWIN",
    title: "Standing Body",
    summary: "由 canonical body measurements 驱动的 neutral standing avatar。",
    assumption: "人体 mesh 是测量数据的派生视图。站立模式不包含桌椅环境。"
  },
  seated: {
    url: "/assets/avatar-seated.glb",
    kicker: "ERGONOMICS",
    title: "Seated Workstation",
    summary: "基于当前 private canonical desk setup 和键鼠/显示器位置生成的坐姿工学场景。",
    assumption: "坐姿用于空间与人体工学推理；刚性 mesh 不模拟软组织与座面压缩。"
  }
};

const viewport = document.querySelector("#viewport");
const loading = document.querySelector("#loading");
const modeKicker = document.querySelector("#mode-kicker");
const modeTitle = document.querySelector("#mode-title");
const modeSummary = document.querySelector("#mode-summary");
const metrics = document.querySelector("#metrics");
const assumption = document.querySelector("#assumption");
const assetStatus = document.querySelector("#asset-status");
const assetCount = document.querySelector("#asset-count");
const resetButton = document.querySelector("#reset-view");
const modeButtons = [...document.querySelectorAll(".mode-button")];

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0d0f13);

const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 100);
camera.position.set(4, 3, 4);

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
viewport.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.screenSpacePanning = true;
controls.minDistance = 0.25;
controls.maxDistance = 30;

scene.add(new THREE.HemisphereLight(0xdde6ff, 0x44403a, 2.1));
const keyLight = new THREE.DirectionalLight(0xffffff, 2.7);
keyLight.position.set(4, 7, 5);
scene.add(keyLight);
const fillLight = new THREE.DirectionalLight(0xaec7ff, 1.0);
fillLight.position.set(-4, 3, -5);
scene.add(fillLight);

const grid = new THREE.GridHelper(10, 20, 0x343a46, 0x20242c);
grid.material.opacity = 0.55;
grid.material.transparent = true;
scene.add(grid);

const loader = new GLTFLoader();
const cache = new Map();
let currentMode = "room";
let currentObject = null;

function resize() {
  const width = viewport.clientWidth;
  const height = viewport.clientHeight;
  if (!width || !height) return;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(viewport);

function setLoading(message, error) {
  loading.textContent = message;
  loading.classList.toggle("is-visible", Boolean(message));
  loading.classList.toggle("is-error", Boolean(error));
}

function loadGltf(url) {
  if (cache.has(url)) return Promise.resolve(cache.get(url));
  return new Promise((resolve, reject) => {
    loader.load(url, (gltf) => {
      const root = gltf.scene;
      root.traverse((node) => {
        if (node.isMesh) {
          node.castShadow = false;
          node.receiveShadow = false;
        }
      });
      cache.set(url, root);
      resolve(root);
    }, undefined, reject);
  });
}

function fitCamera(object, mode) {
  const box = new THREE.Box3().setFromObject(object);
  if (box.isEmpty()) return;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const maxSize = Math.max(size.x, size.y, size.z);
  const fov = THREE.MathUtils.degToRad(camera.fov);
  let distance = maxSize / (2 * Math.tan(fov / 2));
  const roomLike = mode === "room" || mode === "combined";
  distance *= roomLike ? 1.35 : 1.15;
  const direction = roomLike
    ? new THREE.Vector3(1.15, 0.9, 1.25)
    : new THREE.Vector3(1.15, 0.55, 1.65);
  direction.normalize();
  camera.position.copy(center).addScaledVector(direction, distance);
  camera.near = Math.max(distance / 200, 0.01);
  camera.far = Math.max(distance * 30, 50);
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.minDistance = Math.max(maxSize * 0.08, 0.15);
  controls.maxDistance = Math.max(maxSize * 8, 10);
  controls.update();
}

function metric(label, value) {
  const item = document.createElement("div");
  item.className = "metric";
  const caption = document.createElement("span");
  caption.textContent = label;
  const strong = document.createElement("strong");
  strong.textContent = value;
  item.append(caption, strong);
  return item;
}

function showMetrics(items) {
  metrics.replaceChildren(...items.map((item) => metric(item[0], item[1])));
}

async function roomMetrics() {
  const response = await fetch("/assets/room.json", { cache: "no-store" });
  if (!response.ok) return [];
  const data = await response.json();
  const width = data.dimensions_m[0];
  const length = data.dimensions_m[1];
  const height = data.dimensions_m[2];
  return [
    ["房间外包络", width.toFixed(2) + " × " + length.toFixed(2) + " m"],
    ["层高", height.toFixed(2) + " m"],
    ["来源单位", "Sweet Home 3D · cm"],
    ["Web 单位", "meter"]
  ];
}

async function seatedMetrics() {
  const response = await fetch("/assets/seated-v1-report.json", { cache: "no-store" });
  if (!response.ok) return [];
  const data = await response.json();
  return [
    ["视距", Math.round(data.display.viewDistanceY_mm) + " mm"],
    ["眼-屏中心差", Math.round(data.display.eyeMinusMonitorCenter_mm) + " mm"],
    ["膝部余量", Math.round(data.clearance.leftKneeToDeskUndersideProxy_mm) + " mm"],
    ["脚底离地", data.geometry.footFloorGap_mm.toFixed(1) + " mm"],
    ["座面高度", Math.round(data.geometry.seatTop_mm) + " mm"],
    ["桌面高度", Math.round(data.geometry.deskTop_mm) + " mm"]
  ];
}

async function standingMetrics() {
  const [bodyResponse, meshResponse] = await Promise.all([
    fetch("/assets/body-summary.json", { cache: "no-store" }),
    fetch("/assets/avatar-standing.json", { cache: "no-store" })
  ]);
  if (!bodyResponse.ok) return [["模型", "MPFB fitted V2"]];

  const data = await bodyResponse.json();
  const mesh = meshResponse.ok ? await meshResponse.json() : null;
  const items = [];
  const measurements = data.measurements || {};

  const height = measurements.height;
  if (height && height.value !== undefined && height.unit) {
    items.push(["Canonical 身高", String(height.value) + " " + height.unit]);
  }

  if (mesh && Array.isArray(mesh.dimensions_m) && mesh.dimensions_m.length >= 3) {
    const meshHeightMm = mesh.dimensions_m[2] * 1000;
    items.push(["Mesh 高度", Math.round(meshHeightMm) + " mm"]);
    if (height && height.unit === "mm") {
      const drift = meshHeightMm - Number(height.value);
      const sign = drift > 0 ? "+" : "";
      items.push(["几何高度差", sign + Math.round(drift) + " mm"]);
    }
  }

  for (const [key, label] of [["weight", "体重"], ["shoulderBreadth", "肩宽"]]) {
    const value = measurements[key];
    if (value && value.value !== undefined && value.unit) {
      items.push([label, String(value.value) + " " + value.unit]);
    }
  }

  items.push(["模型", "MPFB fitted V2"]);
  return items;
}

async function combinedMetrics() {
  const [integrationResponse, sceneResponse] = await Promise.all([
    fetch("/assets/room-integration.json", { cache: "no-store" }),
    fetch("/assets/scene-combined.json", { cache: "no-store" })
  ]);
  if (!integrationResponse.ok || !sceneResponse.ok) return [];

  const integration = await integrationResponse.json();
  const combined = await sceneResponse.json();
  const localResidual = integration.validation?.deskLocalResidual_mm || [];
  const roomResidual = integration.validation?.deskRoomResidual_mm || [];
  const residuals = [...localResidual, ...roomResidual].map((value) => Math.abs(Number(value)));
  const maxResidual = residuals.length ? Math.max(...residuals) : NaN;
  const bounds = combined.bodyBounds_m || {};
  const min = bounds.min || [];
  const max = bounds.max || [];

  return [
    ["坐标锚点", integration.validation?.ok ? "validated" : "check"],
    ["最大锚点误差", Number.isFinite(maxResidual) ? maxResidual.toFixed(3) + " mm" : "—"],
    ["人体脚底", min.length >= 3 ? (min[2] * 1000).toFixed(1) + " mm" : "—"],
    ["人体头顶", max.length >= 3 ? Math.round(max[2] * 1000) + " mm" : "—"]
  ];
}

async function updateMetrics(mode) {
  try {
    if (mode === "room") showMetrics(await roomMetrics());
    else if (mode === "combined") showMetrics(await combinedMetrics());
    else if (mode === "seated") showMetrics(await seatedMetrics());
    else showMetrics(await standingMetrics());
  } catch {
    showMetrics([["状态", "指标读取失败"]]);
  }
}

async function setMode(mode, options) {
  if (!MODES[mode]) return;
  const reset = !options || options.reset !== false;
  currentMode = mode;
  const config = MODES[mode];

  modeButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.mode === mode);
  });
  modeKicker.textContent = config.kicker;
  modeTitle.textContent = config.title;
  modeSummary.textContent = config.summary;
  assumption.textContent = config.assumption;
  grid.visible = mode !== "room" && mode !== "combined";
  setLoading("正在加载 " + config.title + "…", false);

  try {
    const object = await loadGltf(config.url);
    if (currentMode !== mode) return;
    if (currentObject && currentObject.parent === scene) scene.remove(currentObject);
    currentObject = object;
    scene.add(object);
    if (reset) fitCamera(object, mode);
    await updateMetrics(mode);
    setLoading("", false);
  } catch (error) {
    console.error(error);
    setLoading("加载失败：" + config.url, true);
    showMetrics([["状态", "资产不可用"]]);
  }
}

async function loadAssetManifest() {
  try {
    const response = await fetch("/assets/manifest.json", { cache: "no-store" });
    if (!response.ok) throw new Error("manifest unavailable");
    const manifest = await response.json();
    const entries = Object.entries(manifest.assets || {});
    assetCount.textContent = entries.length + " assets";
    const rows = entries.map(([name, info]) => {
      const row = document.createElement("div");
      row.className = "asset-row";
      const code = document.createElement("code");
      code.textContent = name;
      const size = document.createElement("span");
      size.className = "asset-size";
      size.textContent = (info.sizeBytes / 1024 / 1024).toFixed(1) + " MB";
      row.append(code, size);
      return row;
    });
    assetStatus.replaceChildren(...rows);
  } catch {
    assetCount.textContent = "unavailable";
    assetStatus.textContent = "manifest.json 读取失败";
  }
}

modeButtons.forEach((button) => {
  button.addEventListener("click", () => setMode(button.dataset.mode));
});
resetButton.addEventListener("click", () => {
  if (currentObject) fitCamera(currentObject, currentMode);
});
window.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
  if (event.key === "1") setMode("room");
  if (event.key === "2") setMode("combined");
  if (event.key === "3") setMode("standing");
  if (event.key === "4") setMode("seated");
  if (event.key.toLowerCase() === "r" && currentObject) fitCamera(currentObject, currentMode);
});

renderer.setAnimationLoop(() => {
  controls.update();
  renderer.render(scene, camera);
});

resize();
loadAssetManifest();
const requestedMode = new URLSearchParams(window.location.search).get("mode");
setMode(MODES[requestedMode] ? requestedMode : "room");
