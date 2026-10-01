<?php
$dataDir = __DIR__ . "/data";
$homes = [];

if (is_dir($dataDir)) {
  foreach (scandir($dataDir) ?: [] as $file) {
    if ($file === "." || $file === "..") {
      continue;
    }
    $full = $dataDir . "/" . $file;
    if (is_file($full) && str_ends_with($file, ".sh3x")) {
      $homes[] = substr($file, 0, -5);
    }
  }
}

sort($homes, SORT_NATURAL | SORT_FLAG_CASE);
header("Content-Type: application/json; charset=utf-8");
echo json_encode($homes, JSON_UNESCAPED_SLASHES);
