<?php
$dataDir = __DIR__ . "/data";
$home = $_GET["home"] ?? "";

if ($home === "" || !preg_match('/^[A-Za-z0-9._-]+$/', $home)) {
  http_response_code(400);
  exit("invalid home");
}

$target = $dataDir . "/" . $home . ".sh3x";
if (is_file($target) && !unlink($target)) {
  http_response_code(500);
  exit("delete failed");
}

http_response_code(204);
