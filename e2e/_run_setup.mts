import setup from './global-setup.js';

const fn = (setup as any).default ?? setup;

try {
  await fn({} as any);
  console.log('Setup complete');
} catch (e: any) {
  console.error('Setup failed:', e.message);
  console.error(e.stack);
  process.exit(1);
}
