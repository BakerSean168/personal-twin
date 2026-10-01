<?php
$dataDir = __DIR__ . "/data";
$path = $_GET["path"] ?? "";

if ($path === ""
    || str_starts_with($path, "/")
    || str_contains($path, "..")
    || !preg_match('/^[A-Za-z0-9._\/-]+$/', $path)) {
  http_response_code(400);
  exit("invalid path");
}

$target = $dataDir . "/" . $path;
$dir = dirname($target);
if (!is_dir($dir) && !mkdir($dir, 0770, true) && !is_dir($dir)) {
  http_response_code(500);
  exit("cannot create directory");
}

$input = fopen("php://input", "rb");
$tmp = $target . ".tmp-" . bin2hex(random_bytes(6));
$output = fopen($tmp, "wb");
if ($input === false || $output === false) {
  http_response_code(500);
  exit("cannot open stream");
}

while (!feof($input)) {
  $chunk = fread($input, 1024 * 1024);
  if ($chunk === false || fwrite($output, $chunk) === false) {
    fclose($input);
    fclose($output);
    @unlink($tmp);
    http_response_code(500);
    exit("write failed");
  }
}

fclose($input);
fflush($output);
fclose($output);

if (!rename($tmp, $target)) {
  @unlink($tmp);
  http_response_code(500);
  exit("commit failed");
}

header("Content-Type: text/plain; charset=utf-8");
echo "ok";
