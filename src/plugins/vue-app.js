// src/plugins/vue-app.js
import fontawesome from './fontawesome';

export default function createApp(app) {
  app.use(fontawesome);
  return app;
}
