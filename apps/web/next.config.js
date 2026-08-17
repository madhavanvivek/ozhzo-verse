/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  transpilePackages: ["@ozhzo/types", "@ozhzo/shared"],

  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination:
          "https://ozhzo-api.onrender.com/api/v1/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
