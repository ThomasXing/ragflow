import type { Config } from 'jest';

const config: Config = {
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/src'],
  testMatch: [
    '**/__tests__/**/*.test.ts',
    '**/__tests__/**/*.test.tsx',
    '**/*.test.ts',
    '**/*.test.tsx',
  ],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^umi$': '<rootDir>/src/__mocks__/umi.ts',
    '^umi/test-setup$': '<rootDir>/src/__mocks__/umi-test-setup.ts',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
  setupFilesAfterEnv: ['<rootDir>/jest-setup.ts'],
  transform: {
    '^.+\\.tsx?$': [
      'ts-jest',
      {
        tsconfig: {
          jsx: 'react-jsx',
          esModuleInterop: true,
          allowSyntheticDefaultImports: true,
          module: 'ESNext',
          moduleResolution: 'node',
        },
      },
    ],
  },
  transformIgnorePatterns: [
    'node_modules/(?!(@tanstack|react-day-picker|recharts|d3-.*|internmap)/)',
  ],
  collectCoverageFrom: [
    '**/*.{ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!.umi/**',
    '!.umi-test/**',
    '!.umi-production/**',
    '!coverage/**',
    '!dist/**',
    '!config/**',
    '!mock/**',
  ],
  coverageThreshold: {
    global: {
      lines: 1,
    },
  },
};

export default config;
