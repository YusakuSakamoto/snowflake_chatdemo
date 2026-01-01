/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  output: 'standalone',
  env: {
    API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7071/api',
  },
}

module.exports = nextConfig
