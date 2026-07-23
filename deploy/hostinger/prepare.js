const https = require("https");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const REPO = process.env.UMIC_REPO || "ibrahimAltaf/umic";
const REF = process.env.UMIC_REF || "main";
const url = `https://codeload.github.com/${REPO}/tar.gz/refs/heads/${REF}`;
const tgz = path.join(__dirname, "repo.tgz");

function download(u, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    https
      .get(u, { headers: { "User-Agent": "umic-hostinger-boot" } }, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          file.close();
          try {
            fs.unlinkSync(dest);
          } catch {}
          return download(res.headers.location, dest).then(resolve, reject);
        }
        if (res.statusCode !== 200) {
          reject(new Error(`download failed: ${res.statusCode}`));
          return;
        }
        res.pipe(file);
        file.on("finish", () => file.close(resolve));
      })
      .on("error", reject);
  });
}

(async () => {
  console.log("Downloading", url);
  await download(url, tgz);
  execSync("tar -xzf repo.tgz", { stdio: "inherit", cwd: __dirname });
  const dir = fs
    .readdirSync(__dirname)
    .find((d) => d.startsWith("umic-") && fs.statSync(path.join(__dirname, d)).isDirectory());
  if (!dir) throw new Error("extract failed");
  const src = path.join(__dirname, dir, "apps", "web");
  const dest = path.join(__dirname, "app");
  fs.rmSync(dest, { recursive: true, force: true });
  fs.cpSync(src, dest, { recursive: true });

  const pkgPath = path.join(dest, "package.json");
  const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
  pkg.scripts = pkg.scripts || {};
  // Hostinger injects PORT; next start respects it. Bind all interfaces.
  pkg.scripts.start = "next start -H 0.0.0.0";
  fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2));
  console.log("Prepared", src);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
