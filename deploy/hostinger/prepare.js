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

function write(file, content) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content);
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

  // Static export for Hostinger shared/static Node build pipeline
  write(
    path.join(dest, "next.config.ts"),
    `import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};
export default nextConfig;
`
  );

  // generateStaticParams must be in a Server Component (not the "use client" page)
  for (const rel of ["src/app/(app)/matters/[id]", "src/app/(app)/entities/[id]"]) {
    write(
      path.join(dest, rel, "layout.tsx"),
      `export function generateStaticParams() {\n  return [{ id: "placeholder" }];\n}\n\nexport default function Layout({ children }: { children: React.ReactNode }) {\n  return children;\n}\n`
    );
  }

  console.log("npm install + next build (static export)...");
  execSync("npm install", {
    stdio: "inherit",
    cwd: dest,
    env: { ...process.env, NODE_ENV: "development" },
  });
  execSync("npm run build", {
    stdio: "inherit",
    cwd: dest,
    env: { ...process.env, NODE_ENV: "production" },
  });

  const outDir = path.join(dest, "out");
  if (!fs.existsSync(outDir)) throw new Error("missing out/ after export build");

  // Hostinger Vite/SPA pipeline publishes dist/ to the live site
  const dist = path.join(__dirname, "dist");
  fs.rmSync(dist, { recursive: true, force: true });
  fs.cpSync(outDir, dist, { recursive: true });

  write(
    path.join(dist, ".htaccess"),
    `RewriteEngine On
RewriteBase /
RewriteCond %{REQUEST_FILENAME} -f [OR]
RewriteCond %{REQUEST_FILENAME} -d
RewriteRule ^ - [L]
RewriteRule ^matters/[^/]+/?$ /matters/placeholder/index.html [L]
RewriteRule ^entities/[^/]+/?$ /entities/placeholder/index.html [L]
`
  );

  // Also copy into public_html in case detector leaves output_directory empty
  const publicHtml = path.resolve(__dirname, "..", "..");
  if (fs.existsSync(publicHtml) && publicHtml.includes("public_html")) {
    for (const name of fs.readdirSync(dist)) {
      fs.cpSync(path.join(dist, name), path.join(publicHtml, name), { recursive: true });
    }
    console.log("Also copied dist ->", publicHtml);
  }

  console.log("Static dist/ ready");
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
