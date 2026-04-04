/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  webpack: (config, { isServer }) => {
    // Exclude onnxruntime-web from server-side bundling
    if (isServer) {
      config.externals.push('onnxruntime-web');
    }

    // Allow WASM files to be loaded
    config.experiments = {
      ...config.experiments,
      asyncWebAssembly: true,
    };

    return config;
  },
};

module.exports = nextConfig;
