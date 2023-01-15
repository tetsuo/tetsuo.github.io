#!/usr/bin/env node

const favicons = require("favicons").favicons;
const fs = require("fs");

let source = process.argv.slice(2);

if (!source.length) {
  console.log("No source provided");
  process.exit(1);
}

source = source[0]

const config = {
  appName: "{{ settings.title }}",
  appShortName: "{{ settings.site_name }}",
  appDescription: "{{ settings.description }}",
  version: "1.0",
  lang: "en-US",
  background: "#fff",
  theme_color: "#fff", // #0000ff
  appleStatusBarStyle: "default",
  display: "standalone", // "fullscreen", "standalone", "minimal-ui" or "browser"
  orientation: "any", // "any", "natural", "portrait" or "landscape"
  scope: "/",
  start_url: "/",
  pixel_art: false,
  manifestMaskable: true,
  icons: {
    android: true,
    appleIcon: true,
    appleStartup: true,
    favicons: true,
    windows: false,
    yandex: false,
  },
};

try {
  favicons(source, config).then((response) => {
    response.files.forEach((file) => {
      fs.writeFileSync(
        __dirname + "/templates/" + file.name,
        file.contents,
        "utf-8"
      );
    });
    response.images.forEach((file) => {
      fs.writeFileSync(
        __dirname + "/public/" + file.name,
        file.contents,
        "binary"
      );
    });
    const html = response.html.join("\n");
    fs.writeFileSync(__dirname + "/templates/favicons.html", html, "utf-8");
  });
} catch (error) {
  console.log(error.message);
  process.exit(1);
}
