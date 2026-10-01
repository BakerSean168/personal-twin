<?php
if ($argc !== 2) {
  fwrite(STDERR, "usage: patch-index.php <index.html>\n");
  exit(2);
}

$path = $argv[1];
$html = file_get_contents($path);
if ($html === false) {
  fwrite(STDERR, "cannot read $path\n");
  exit(1);
}

$old = <<<'HTML'
  setTimeout(function() {
      application.addHome(application.createHome());
    });
HTML;

$new = <<<'HTML'
  setTimeout(function() {
      var initialHomeName = "bedroom";
      application.getHomeRecorder().readHome(initialHomeName, {
          homeLoaded: function(home) {
            home.setName(initialHomeName);
            application.addHome(home);
          },
          homeError: function(error) {
            console.warn("Personal Twin: bedroom.sh3x unavailable, opening a new home", error);
            var home = application.createHome();
            home.setName(initialHomeName);
            application.addHome(home);
          }
        });
    });
HTML;

if (strpos($html, $old) === false) {
  fwrite(STDERR, "startup block not found; upstream index changed\n");
  exit(1);
}

file_put_contents($path, str_replace($old, $new, $html));
