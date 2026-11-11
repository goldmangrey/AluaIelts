import {defineConfig} from '@playwright/test';
export default defineConfig({testDir: './tests', testMatch: ['ai-orchestrator.spec.ts','reading-ai-contracts.spec.ts','smart-translate-contracts.spec.ts'],
  workers: 1, retries: 0, reporter: 'list', outputDir: '.next/ai-test-results'});
